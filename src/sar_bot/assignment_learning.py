"""Aprendizaje supervisado de asignación entre misiones, con replay y controles."""
from copy import deepcopy
from io import BytesIO
import pickle
import re
import sys
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import numpy as np
import torch
from sar_bot.core import RescueSimulation
from sar_bot.agents.assignment import AssignmentPolicy,AssignmentFeatures,load_network,save_network,ROUTE_WEIGHTS
from sar_bot.online import LearningSession,session_lock,digest


class StoredAssignment:
    def __init__(self,network,profile,optimizer,memory):
        self.network,self.profile,self.optimizer,self.memory=network,profile,optimizer,memory
    def save(self,path):save_network(path,self.network,self.profile,self.optimizer)
    def save_replay_buffer(self,path):
        with Path(path).open('wb') as stream:pickle.dump(self.memory,stream)


def assignment_score(network,scenarios):
    successes=rescued=cost=0
    for scenario in scenarios:
        simulation=RescueSimulation(scenario)
        policy=AssignmentPolicy(simulation,network=network)
        while simulation.state.outcome=='running':simulation.step(policy.act(simulation.state))
        state=simulation.state
        successes+=int(state.outcome=='success');rescued+=len(state.rescued)
        cost+=state.steps+2*sum(r.damage for r in state.robots)
    return (successes,rescued,-cost)


class AssignmentLearningSession(LearningSession):
    def _load(self,snapshot):
        network,header=load_network(snapshot.model_path)
        optimizer=torch.optim.Adam(network.parameters(),lr=self.settings.learning_rate)
        memory={'features':np.empty((0,16),dtype=np.float32),'labels':np.empty(0,dtype=np.float32)}
        if snapshot.generation:
            with ZipFile(snapshot.model_path) as archive:
                optimizer.load_state_dict(torch.load(BytesIO(archive.read('optimizer.pt')),map_location='cpu',weights_only=True))
            with snapshot.model_path.with_name('replay.pkl').open('rb') as stream:memory=pickle.load(stream)
            with snapshot.model_path.with_name('rng.pkl').open('rb') as stream:rng=pickle.load(stream)
            import random
            random.setstate(rng['python']);np.random.set_state(rng['numpy']);torch.set_rng_state(rng['torch'])
        return network,header['profile'],optimizer,memory

    def prepare_episode(self,scenario,seed=0,cancel_event=None):
        from concurrent.futures import CancelledError
        from .ui.playback import Episode
        self._check_scenario(scenario)
        with session_lock(self.directory):
            snapshot=self._snapshot()
            simulation=RescueSimulation(scenario)
            policy=AssignmentPolicy(simulation,snapshot.model_path,record=True)
            states=[simulation.state];actions=[]
            while simulation.state.outcome=='running':
                if cancel_event is not None and cancel_event.is_set():raise CancelledError()
                action=policy.act(simulation.state)
                actions.append(action);states.append(simulation.step(action))
            engine=digest(sys.modules[RescueSimulation.__module__].__file__)
            return Episode(scenario,tuple(states),tuple(actions),snapshot.metadata['model_sha256'],
                           engine,uuid4().hex,tuple(policy.decisions))

    def learn_episode(self,episode):
        self._check_scenario(episode.scenario)
        if not episode.learning_id or not re.fullmatch(r'[0-9a-f]{32}',episode.learning_id):
            raise ValueError('Solo aprende de una misión nueva')
        if (len(episode.states)!=len(episode.actions)+1 or not episode.actions
                or episode.states[0]!=RescueSimulation(episode.scenario).state
                or episode.states[-1].outcome=='running'):
            raise ValueError('La misión debe estar completa y partir del estado inicial')
        simulation=RescueSimulation(episode.scenario)
        helper=AssignmentFeatures(episode.scenario)
        xs=[];ys=[]
        for index,action in enumerate(episode.actions):
            state=simulation.state
            # Estados observados, alternativas factibles y etiquetas de un experto de costes.
            if index%3==0:
                for candidate in helper.candidates(state,{}):
                    for weight in ROUTE_WEIGHTS:
                        x,y=helper.describe(state,candidate,weight);xs.append(x);ys.append(y)
            if simulation.step(action)!=episode.states[index+1]:
                raise ValueError('La experiencia no coincide con el motor')
        with session_lock(self.directory):
            previous=self._snapshot()
            if episode.learning_id in previous.metadata['processed_ids']:
                return {**previous.metadata,'duplicate':True,'recovered':previous.recovered}
            network,profile,optimizer,memory=self._load(previous)
            x=np.asarray(xs,dtype=np.float32).reshape(-1,16);y=np.asarray(ys,dtype=np.float32)
            memory={'features':np.concatenate((memory['features'],x))[-self.settings.capacity:],
                    'labels':np.concatenate((memory['labels'],y))[-self.settings.capacity:]}
            rehearsal=np.load(self.base_model.with_name('rehearsal.npz'))
            tx=np.concatenate((rehearsal['features'],memory['features']))
            ty=np.concatenate((rehearsal['labels'],memory['labels']))
            # Los controles son entrenamiento; la misión nueva también se comprueba.
            controls=tuple({s.scenario_id:s for s in (*self.control_scenarios,episode.scenario)}.values())
            weights=deepcopy(network.state_dict());old_optimizer=deepcopy(optimizer.state_dict())
            attempted=0
            try:
                before=assignment_score(network,controls)
                network.train()
                for _ in range(self.settings.max_updates):
                    indices=np.random.randint(len(tx),size=min(64,len(tx)))
                    loss=torch.nn.functional.smooth_l1_loss(network(torch.as_tensor(tx[indices])),torch.as_tensor(ty[indices]))
                    optimizer.zero_grad();loss.backward();optimizer.step();attempted+=1
                network.eval();after=assignment_score(network,controls)
                accepted=after>=before
                guard={'accepted':accepted,'before':list(before),'after':list(after),
                       'reason':'no_regression_on_controls' if accepted else 'regression_on_controls'}
            except Exception as error:
                accepted=False;guard={'accepted':False,'reason':'control_or_update_error','error':str(error)[:180]}
            if not accepted:
                network.load_state_dict(weights);optimizer.load_state_dict(old_optimizer)
            network.eval()
            guard.update(control_ids=[s.scenario_id for s in controls],attempted_updates=attempted)
            meta={**previous.metadata,'controller':'neural_assignment','profile':profile,'learning_method':'supervised assignment regression',
                  'missions':previous.metadata['missions']+1,'transitions':previous.metadata['transitions']+len(episode.actions),
                  'updates':previous.metadata['updates']+(attempted if accepted else 0),
                  'attempted_updates':previous.metadata.get('attempted_updates',0)+attempted,
                  'buffer_size':len(memory['labels']),'last_guard':guard,
                  'processed_ids':[*previous.metadata['processed_ids'],episode.learning_id],
                  'last_mission':{'scenario_id':episode.scenario_id,'outcome':episode.states[-1].outcome,
                                  'rescued':len(episode.states[-1].rescued),'policy_sha256':episode.checkpoint_sha256}}
            saved=self._save(StoredAssignment(network,profile,optimizer,memory),meta,previous)
            return {**saved.metadata,'duplicate':False,'recovered':previous.recovered}
