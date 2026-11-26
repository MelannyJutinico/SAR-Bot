"""Verifica trazas y genera tablas del agente neuronal desde la evidencia guardada."""
from collections import defaultdict
from decimal import Decimal,ROUND_HALF_UP
import csv
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sar_bot.core import Scenario
from sar_bot.experiment import replay_actions,metrics_from_trace
from sar_bot.partitions import file_sha256
from sar_bot.release import file_hash,json_hash


def build():
    folder=ROOT/'results/assignment'
    protocol=json.loads((ROOT/'configs/assignment_protocol.json').read_text())
    marker=json.loads((ROOT/'configs/assignment_protocol.started.json').read_text())
    assert marker['status']=='completed','La prueba no ha terminado'
    assert protocol['model_sha256']==file_hash(ROOT/protocol['model'])
    assert protocol['metadata_json_sha256']==json_hash(ROOT/protocol['model'].replace('model.zip','metadata.json'))
    assert protocol['manifest_json_sha256']==json_hash(ROOT/protocol['manifest'])
    metadata=json.loads((folder/'holdout.metadata.json').read_text())
    assert metadata['csv_sha256']==file_sha256(folder/'holdout.csv')
    with (folder/'holdout.csv').open(newline='',encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
    lookup={(r['scenario'],r['policy']):r for r in rows}
    assert len(lookup)==len(rows)
    count=0
    for line in (folder/'holdout.traces.jsonl').read_text(encoding='utf-8').splitlines():
        trace=json.loads(line);scenario=Scenario.load(ROOT/trace['scenario'])
        assert scenario.scenario_id==trace['scenario_id']
        states=replay_actions(scenario,trace['actions'])
        metrics=metrics_from_trace(scenario,states,trace['actions'])
        assert metrics==trace['metrics']
        row=lookup[(trace['scenario'],trace['policy'])]
        for key,value in metrics.items():assert row[key]==str(value),(key,row[key],value)
        count+=1
    assert count==len(rows)
    grouped=defaultdict(list)
    for row in rows:grouped[row['policy']].append(row)
    names={'neural_assignment':'Red entrenada (semilla 7)','thermal':'Referencia térmica','shortest':'Referencia de ruta corta'}
    def name(label):return names.get(label,'Red sin entrenar · semilla '+label.removeprefix('untrained_s'))
    def mean(items,key):return sum(float(r[key]) for r in items)/len(items) if items else None
    def fmt(value):return '—' if value is None else str(Decimal(str(value)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
    text=['# Evaluación del agente neuronal de asignación y riesgo','',
          'Tablas generadas por `scripts/report_assignment.py`. Se verificaron todas las acciones en un motor nuevo antes de generar.',
          '',f'**Casos:** 40 ubicaciones reservadas nuevas, dos edificios conocidos, {len(rows)} episodios. Una red entrenada (semilla 7), seis inicializaciones sin entrenar y dos referencias.',
          '',f'**Modelo congelado:** `{protocol["model_sha256"]}`. Protocolo conservado antes de prueba en el commit `c2bf859`.',
          '', '## Rescates reales','',
          '| Controlador | Éxitos | Personas entregadas | Pasos medios en éxitos | Daño medio en éxitos |',
          '|---|---:|---:|---:|---:|']
    for label,items in grouped.items():
        successful=[r for r in items if r['success']=='True']
        text.append(f'| {name(label)} | {len(successful)}/{len(items)} | {sum(int(r["rescued"]) for r in items)}/{3*len(items)} | {fmt(mean(successful,"steps"))} | {fmt(mean(successful,"damage_total"))} |')
    text+=['','El planificador A* y las restricciones factibles son comunes a las redes entrenada y sin entrenar. Los rescates completos por sí solos no prueban que el entrenamiento explique la capacidad básica de navegación. Las seis inicializaciones no son seis réplicas de entrenamiento.','',
           '## Comparaciones emparejadas','',
           'Solo se comparan pasos y daño en las mismas misiones exitosas para ambos controladores. Δ = red entrenada menos referencia; un valor negativo reduce el coste.',
           '', '| Referencia | Éxitos comunes | Δ pasos | Δ daño |', '|---|---:|---:|---:|']
    learned={r['scenario']:r for r in grouped['neural_assignment']}
    for label in ['untrained_s7','thermal','shortest']:
        pairs=[(learned[r['scenario']],r) for r in grouped[label]
               if r['success']=='True' and learned[r['scenario']]['success']=='True']
        delta_steps=sum(int(a['steps'])-int(b['steps']) for a,b in pairs)/len(pairs) if pairs else None
        delta_damage=sum(int(a['damage_total'])-int(b['damage_total']) for a,b in pairs)/len(pairs) if pairs else None
        text.append(f'| {name(label)} | {len(pairs)} | {fmt(delta_steps)} | {fmt(delta_damage)} |')
    diagnostic=json.loads((folder/'holdout.choices.json').read_text())['metrics']
    text+=['','## Qué aprendió la red','',
           'Se plantearon las mismas 2400 preguntas sintéticas de asignación y riesgo a todas las redes, usando únicamente las posiciones reservadas después de congelar. La coincidencia se mide frente al estimador de coste programado que proporciona las etiquetas. No es una prueba de rescate óptimo ni una recompensa obtenida por DQN.',
           '', '| Red | Preguntas | Elección con coste experto mínimo | Arrepentimiento medio (coste / 100) |',
           '|---|---:|---:|---:|']
    for label,metrics in diagnostic.items():
        text.append(f'| {name(label)} | {metrics["questions"]} | {metrics["teacher_best_fraction"]*100:.2f}% | {metrics["mean_teacher_regret"]:.6f} |')
    text+=['','## Límites','',
           '- Aprendizaje supervisado de un estimador experto: no es aprendizaje por refuerzo desde cero ni navegación aprendida de extremo a extremo.',
           '- Una semilla de entrenamiento, dos geometrías conocidas y selección repetida sobre validación. Las 40 posiciones nuevas no se usaron para ajustar la red después de prueba.',
           '- Los casos se admitieron por certificación de referencias: sus tasas están favorecidas por construcción. No se promete rescatar cualquier colocación del profesor.',
           '- Las preguntas sintéticas y los episodios comparten mapas y posiciones. Se informan conteos y pares; no intervalos que supongan independencia.',
           '- El aprendizaje de sesión usa memoria, etiquetas del mismo experto y controles de entrenamiento; sus actualizaciones pueden rechazarse. Las cifras anteriores usan el modelo base congelado.',
           '', '## Fuentes verificadas','',f'- CSV (SHA-256 normalizado LF): `{file_sha256(folder/"holdout.csv")}`.',
           f'- Trazas (SHA-256 normalizado LF): `{file_sha256(folder/"holdout.traces.jsonl")}`.',
           f'- Protocolo (JSON canónico): `{json_hash(ROOT/"configs/assignment_protocol.json")}`.',
           '', 'Regenerar: `.venv\\Scripts\\python.exe scripts/report_assignment.py`. No entrena ni vuelve a ejecutar las políticas; reproduce acciones guardadas.','']
    return '\n'.join(text)


if __name__=='__main__':
    content=build()
    target=ROOT/'results/assignment/report.md'
    if '--check' in sys.argv:
        assert target.read_text(encoding='utf-8')==content,'El informe no coincide con sus fuentes'
        print('OK: tablas, hashes y trazas del agente neuronal verificados')
    else:
        target.write_text(content,encoding='utf-8');print(target)
