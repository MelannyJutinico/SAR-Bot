"""Compara asignación neuronal, red sin entrenar y referencias, con trazas reales."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import torch
from sar_bot.agents import create_policy
from sar_bot.agents.assignment import AssignmentPolicy,AssignmentNetwork
from sar_bot.core import Scenario,RescueSimulation
from sar_bot.experiment import metrics_from_trace,replay_actions
from sar_bot.release import json_hash,file_hash


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=ROOT/'configs/partitions/v2_12x12.json')
    parser.add_argument('--split',choices=('validation','test'),default='validation')
    parser.add_argument('--model',type=Path,default=ROOT/'artifacts/rescue_network/model.zip')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--untrained-seeds',type=int,nargs='+',default=[7])
    args=parser.parse_args()
    torch.set_num_threads(1)
    manifest=json.loads(args.manifest.read_text())
    marker=None
    if args.split=='test':
        protocol_path=ROOT/'configs/assignment_protocol.json'
        protocol=json.loads(protocol_path.read_text())
        assert protocol['model_sha256']==file_hash(args.model)
        assert protocol['manifest_json_sha256']==json_hash(args.manifest)
        assert args.untrained_seeds==protocol['untrained_seeds']
        marker=protocol_path.with_name('assignment_protocol.started.json')
        with marker.open('x',encoding='utf-8') as stream:
            json.dump({'status':'started','protocol_sha256':json_hash(protocol_path)},stream)
    rows=[];traces=[]
    policies=('neural_assignment',*(f'untrained_s{seed}' for seed in args.untrained_seeds),'thermal','shortest')
    for entry in manifest['entries']:
        if entry['partition']!=args.split:continue
        scenario=Scenario.load(ROOT/entry['path'])
        for label in policies:
            simulation=RescueSimulation(scenario)
            if label=='neural_assignment':policy=AssignmentPolicy(simulation,args.model,record=True)
            elif label.startswith('untrained_s'):
                torch.manual_seed(int(label.removeprefix('untrained_s')))
                policy=AssignmentPolicy(simulation,network=AssignmentNetwork().eval(),record=True)
            else:policy=create_policy(simulation,label)
            states=[simulation.state];actions=[]
            while simulation.state.outcome=='running':
                action=policy.act(simulation.state)
                actions.append(action);states.append(simulation.step(action))
            metrics=metrics_from_trace(scenario,states,actions)
            assert replay_actions(scenario,actions)==states
            row={key:entry[key] for key in ('building','difficulty')}
            row.update(scenario=entry['path'],policy=label,**metrics)
            rows.append(row)
            traces.append({'scenario':entry['path'],'scenario_id':scenario.scenario_id,'policy':label,
                           'actions':actions,'metrics':metrics,'decisions':getattr(policy,'decisions',[])})
        print(entry['path'],flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    args.output.with_suffix('.traces.jsonl').write_text('\n'.join(json.dumps(t) for t in traces)+'\n',encoding='utf-8')
    summary={}
    for label in policies:
        selected=[r for r in rows if r['policy']==label];success=[r for r in selected if r['success']]
        summary[label]={'episodes':len(selected),'successes':len(success),'rescued':sum(r['rescued'] for r in selected),
                        'mean_success_steps':sum(r['steps'] for r in success)/len(success) if success else None,
                        'mean_success_damage':sum(r['damage_total'] for r in success)/len(success) if success else None}
    args.output.with_suffix('.summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    # Mismas preguntas de asignación para todas las redes: medir aprendizaje del coste experto.
    from train_assignment import dataset
    from sar_bot.agents.assignment import load_network
    paths=[e['path'] for e in manifest['entries'] if e['partition']==args.split]
    x,y,groups=dataset(paths,1126,60)
    diagnostic={}
    for label in policies:
        if label=='neural_assignment':network,_=load_network(args.model)
        elif label.startswith('untrained_s'):
            torch.manual_seed(int(label.removeprefix('untrained_s')));network=AssignmentNetwork().eval()
        else:continue
        with torch.no_grad():predictions=network(torch.as_tensor(x)).numpy()
        regrets=[float(y[a+int(predictions[a:b].argmin())]-y[a:b].min()) for a,b in groups]
        diagnostic[label]={'questions':len(groups),'teacher_best_fraction':sum(r<=1e-5 for r in regrets)/len(regrets),
                           'mean_teacher_regret':sum(regrets)/len(regrets)}
    args.output.with_suffix('.choices.json').write_text(json.dumps({'note':'Agreement with the programmed cost estimator, not proof of optimal rescue; identical synthetic questions per network.','metrics':diagnostic},indent=2),encoding='utf-8')
    args.output.with_suffix('.metadata.json').write_text(json.dumps({'model_sha256':file_hash(args.model),
        'manifest_json_sha256':json_hash(args.manifest),'split':args.split,'csv_sha256':file_hash(args.output),
        'traces_verified':True,'note':'The learned component assigns targets; joint thermal A* supplies navigation. Untrained ablation has the identical planner.'},indent=2),encoding='utf-8')
    if marker:marker.write_text(json.dumps({'status':'completed','csv':str(args.output.relative_to(ROOT)),
                                           'csv_sha256':file_hash(args.output)},indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
