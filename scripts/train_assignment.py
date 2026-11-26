"""Entrena asignación neuronal supervisada; no usa las posiciones de prueba."""
import argparse
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import torch
from sar_bot.agents.assignment import AssignmentNetwork,AssignmentFeatures,save_network,FEATURES,CONTROLLER,ROUTE_WEIGHTS
from sar_bot.core import Scenario,RescueSimulation,Robot


def dataset(paths,seed,samples):
    rng=random.Random(seed)
    features=[];labels=[];groups=[]
    for path in paths:
        s=Scenario.load(ROOT/path)
        helper=AssignmentFeatures(s)
        helper.route(s.base,s.base)
        cells=[(x,y) for y in range(s.height) for x in range(s.width)
               if (x,y) in helper.routes[(s.base,2.)] and (x,y) not in s.victims]
        for index in range(samples):
            state=RescueSimulation(s).state
            if index:
                positions=rng.sample(cells,2)
                rescued=set(rng.sample(range(s.victim_count),rng.randrange(s.victim_count)))
                remaining=list(set(range(s.victim_count))-rescued)
                cargo=rng.choice(remaining) if len(remaining)>1 and rng.random()<.3 else None
                robots=(Robot(positions[0],rng.randint(65,100),carrying=cargo),
                        Robot(positions[1],rng.randint(65,100)))
                state=replace(state,robots=robots,rescued=frozenset(rescued))
            candidates=helper.candidates(state,{})
            if not candidates:continue
            start=len(features)
            for candidate in candidates:
                for weight in ROUTE_WEIGHTS:
                    x,y=helper.describe(state,candidate,weight)
                    features.append(x);labels.append(y)
            groups.append((start,len(features)))
    return np.asarray(features,dtype=np.float32),np.asarray(labels,dtype=np.float32),groups


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/rescue_network')
    parser.add_argument('--epochs',type=int,default=250)
    parser.add_argument('--replace-development',action='store_true')
    args=parser.parse_args()
    if args.replace_development:
        if args.output.resolve()!=(ROOT/'artifacts/rescue_network').resolve() or (ROOT/'configs/assignment_protocol.json').exists():
            raise SystemExit('Solo se reemplaza el desarrollo antes de congelar su protocolo')
    elif args.output.exists() and set(p.name for p in args.output.iterdir())!={'model.zip'}:
        raise SystemExit('La carpeta de salida ya contiene evidencia; no se sobrescribe')
    torch.set_num_threads(1);torch.manual_seed(7)
    manifest=json.loads((ROOT/'configs/partitions/v2_12x12.json').read_text())
    paths={part:[e['path'] for e in manifest['entries'] if e['partition']==part]
           for part in ('training','validation')}
    train_x,train_y,_=dataset(paths['training'],7,160)
    val_x,val_y,groups=dataset(paths['validation'],17,60)
    x=torch.as_tensor(train_x);y=torch.as_tensor(train_y)
    vx=torch.as_tensor(val_x)
    network=AssignmentNetwork()
    optimizer=torch.optim.Adam(network.parameters(),lr=.001)
    best=float('inf');best_state=None;best_epoch=0;history=[]
    for epoch in range(1,args.epochs+1):
        order=torch.randperm(len(x))
        network.train()
        for batch in order.split(512):
            loss=torch.nn.functional.smooth_l1_loss(network(x[batch]),y[batch])
            optimizer.zero_grad();loss.backward();optimizer.step()
        network.eval()
        if epoch%10==0 or epoch==1:
            with torch.no_grad():pred=network(vx).numpy()
            regret=np.mean([val_y[a+int(np.argmin(pred[a:b]))]-np.min(val_y[a:b]) for a,b in groups])
            accuracy=np.mean([val_y[a+int(np.argmin(pred[a:b]))]<=np.min(val_y[a:b])+1e-5 for a,b in groups])
            row={'epoch':epoch,'validation_regret':float(regret),'validation_best_choice':float(accuracy),
                 'validation_mae':float(np.mean(abs(pred-val_y)))}
            history.append(row)
            if regret<best:best=float(regret);best_epoch=epoch;best_state=deepcopy(network.state_dict())
            print(json.dumps(row),flush=True)
    network.load_state_dict(best_state);network.eval()
    args.output.mkdir(parents=True,exist_ok=True)
    profile={'width':12,'height':12,'victims':3}
    save_network(args.output/'model.zip',network,profile)
    metadata={'controller':CONTROLLER,'schema_version':1,'profile':profile,'features':FEATURES,
              'architecture':[16,64,32,1],'training_seed':7,'training_method':'supervised route-cost regression',
              'teacher':'programmed thermal route estimator; not an independently learned navigator',
              'selected_epoch':best_epoch,'validation_regret':best,'training_rows':len(x),
              'validation_rows':len(vx),'training_paths':paths['training'],'validation_paths':paths['validation'],
              'test_used':False,'model_sha256':sha256((args.output/'model.zip').read_bytes()).hexdigest()}
    metadata['route_weights']=list(ROUTE_WEIGHTS)
    (args.output/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    (args.output/'training.json').write_text(json.dumps(history,indent=2),encoding='utf-8')
    np.savez_compressed(args.output/'rehearsal.npz',features=train_x,labels=train_y)
    print('Selected',best_epoch,'regret',best,flush=True)


if __name__=='__main__':main()
