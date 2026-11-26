"""Red de asignación de rescates y navegación A* programada, separadas explícitamente.

La red puntúa repartos factibles; no predice movimientos de cuadrícula. Las
etiquetas de entrenamiento son estimaciones de coste de un experto programado.
"""
from collections import deque
from io import BytesIO
from itertools import combinations, permutations
from heapq import heappush, heappop
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
import torch
from torch import nn

from sar_bot.core import damage_rate
from sar_bot.core.simulation import OFFSETS
from .reference import ThermalPathPolicy

FEATURES = 16
CONTROLLER = "neural_assignment"
ROUTE_WEIGHTS = (.05, 2.)


class AssignmentNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(FEATURES,64),nn.ReLU(),nn.Linear(64,32),
                                    nn.ReLU(),nn.Linear(32,1))

    def forward(self, features):
        return self.layers(features).squeeze(-1)


def save_network(path, network, profile, optimizer=None):
    path=Path(path)
    buffer=BytesIO()
    torch.save(network.state_dict(),buffer)
    header={"controller":CONTROLLER,"schema_version":1,"features":FEATURES,
            "architecture":[FEATURES,64,32,1],"profile":profile,"route_weights":list(ROUTE_WEIGHTS)}
    with ZipFile(path,"w",ZIP_DEFLATED) as archive:
        archive.writestr("assignment.json",json.dumps(header,sort_keys=True))
        archive.writestr("weights.pt",buffer.getvalue())
        if optimizer is not None:
            buffer=BytesIO();torch.save(optimizer.state_dict(),buffer)
            archive.writestr("optimizer.pt",buffer.getvalue())


def load_network(path):
    torch.set_num_threads(1)
    with ZipFile(path) as archive:
        if archive.getinfo("weights.pt").file_size>5_000_000:
            raise ValueError("Red de asignación demasiado grande")
        header=json.loads(archive.read("assignment.json"))
        if (header.get("controller")!=CONTROLLER or header.get("features")!=FEATURES or header.get("schema_version")!=1
                or header.get("route_weights")!=list(ROUTE_WEIGHTS)):
            raise ValueError("Formato de red de asignación incompatible")
        network=AssignmentNetwork()
        network.load_state_dict(torch.load(BytesIO(archive.read("weights.pt")),map_location="cpu",weights_only=True))
    network.eval()
    return network,header


class AssignmentFeatures:
    def __init__(self, scenario):
        self.scenario=scenario
        self.routes={}

    def route(self,start,goal,damage_weight=2.):
        """Dijkstra individual: distancia y exposición de una ruta térmica conocida."""
        key=(goal,damage_weight)
        if key not in self.routes:
            costs={goal:(0.,0,0)}
            queue=[(0.,0,0,goal)]
            while queue:
                cost,steps,damage,current=heappop(queue)
                if costs[current]!=(cost,steps,damage):continue
                exposure=damage_rate(self.scenario.temperature_at(current))
                for dx,dy in OFFSETS[:4]:
                    previous=(current[0]+dx,current[1]+dy)
                    if not self.scenario.walkable(previous):continue
                    value=(cost+1+damage_weight*exposure,steps+1,damage+exposure)
                    if value<costs.get(previous,(float("inf"),0,0)):
                        costs[previous]=value
                        heappush(queue,(*value,previous))
            self.routes[key]=costs
        if start not in self.routes[key]:raise ValueError("El objetivo está fuera de la zona accesible")
        _,steps,damage=self.routes[key][start]
        return steps,damage

    def candidates(self,state,assignments):
        carried={r.carrying for r in state.robots if r.carrying is not None}
        pending=set(range(self.scenario.victim_count))-set(state.rescued)-carried
        fixed={i:v for i,v in assignments.items() if state.robots[i].carrying is None and v in pending}
        unassigned=sorted(pending-set(fixed.values()))
        free=[i for i,r in enumerate(state.robots) if r.carrying is None and i not in fixed]
        count=min(len(free),len(unassigned))
        if not count:return []
        return [{**fixed,**dict(zip(robots,victims))}
                for robots in combinations(free,count) for victims in permutations(unassigned,count)]

    def describe(self,state,assignment,damage_weight=2.):
        s=self.scenario
        scale=max(s.width,s.height)*4
        values=[]
        total_steps=[];total_damage=[];deaths=0
        for i,robot in enumerate(state.robots):
            goal=s.victims[assignment[i]] if i in assignment else s.base
            steps,damage=self.route(robot.position,goal,damage_weight)
            back_steps,back_damage=self.route(goal,s.base,damage_weight) if i in assignment else (0,0)
            values.extend((steps/scale,damage/100,back_steps/scale,back_damage/100,
                           (100-robot.integrity)/100,float(robot.carrying is not None)))
            total_steps.append(steps+back_steps);total_damage.append(damage+back_damage)
            deaths+=int(damage+back_damage>=robot.integrity)
        carried={r.carrying for r in state.robots if r.carrying is not None}
        pending=set(range(s.victim_count))-set(state.rescued)-carried
        remaining=pending-set(assignment.values())
        extra_steps=extra_damage=0
        for victim in remaining:
            a,b=self.route(s.base,s.victims[victim],damage_weight);c,d=self.route(s.victims[victim],s.base,damage_weight)
            extra_steps+=a+c;extra_damage+=b+d
        values.extend((extra_steps/scale,extra_damage/100,len(pending)/max(1,s.victim_count),
                       abs(total_steps[0]-total_steps[1])/scale))
        cost=(max(total_steps)+.25*sum(total_steps)+2*sum(total_damage)
              +extra_steps+2*extra_damage+1000*deaths)/100
        return np.asarray(values,dtype=np.float32),float(cost)


class AssignmentPolicy(ThermalPathPolicy):
    """La asignación sale de la red. A* solo conduce a los objetivos elegidos."""
    def __init__(self,simulation,model_path=None,*,network=None,record=False):
        super().__init__(simulation,damage_weight=2.)
        if network is None:
            self.network,header=load_network(model_path)
            profile=header["profile"]
            scenario=simulation.scenario
            if (profile["width"],profile["height"],profile["victims"])!=(scenario.width,scenario.height,scenario.victim_count):
                raise ValueError("Red de asignación incompatible con este mapa")
        else:self.network=network
        self.features=AssignmentFeatures(simulation.scenario)
        self.decisions=[]
        self.record=record

    def targets(self,state):
        carried={r.carrying for r in state.robots if r.carrying is not None}
        pending=set(range(self.simulation.scenario.victim_count))-set(state.rescued)-carried
        self.assignments={i:v for i,v in self.assignments.items()
                          if state.robots[i].carrying is None and v in pending}
        candidates=[(assignment,weight) for assignment in self.features.candidates(state,self.assignments)
                    for weight in ROUTE_WEIGHTS]
        if candidates:
            described=[self.features.describe(state,assignment,weight) for assignment,weight in candidates]
            inputs=np.stack([pair[0] for pair in described])
            with torch.no_grad():
                predictions=self.network(torch.as_tensor(inputs)).numpy()
            if not np.isfinite(predictions).all():raise ValueError("Predicción no finita de la red")
            chosen=int(np.argmin(predictions))
            self.assignments,self.damage_weight=candidates[chosen]
            decision={"step":state.steps,"assignments":dict(self.assignments),
                      "predictions":predictions.tolist(),"chosen":chosen,"options":len(candidates),
                      "route_weight":self.damage_weight}
            if self.record:
                decision.update(features=inputs.tolist(),labels=[pair[1] for pair in described])
            self.decisions.append(decision)
        s=self.simulation.scenario
        return tuple(s.victims[self.assignments[i]] if i in self.assignments else s.base for i in range(2))
