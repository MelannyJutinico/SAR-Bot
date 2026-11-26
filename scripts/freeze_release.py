"""Congela un modelo de una semilla y escribe el protocolo antes de abrir prueba."""

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from sar_bot.final_check import check_final_models
from sar_bot.release import file_hash,json_hash


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir",type=Path,required=True)
    parser.add_argument("--destination",type=Path,default=ROOT/"artifacts/final")
    parser.add_argument("--manifest",type=Path,default=ROOT/"configs/partitions/v2_12x12.json")
    parser.add_argument("--protocol",type=Path,default=ROOT/"configs/final_protocol.json")
    args=parser.parse_args()
    if args.destination.exists() or args.protocol.exists():parser.error("La congelacion debe ser nueva")
    for path in (args.destination,args.protocol):
        if not path.resolve().is_relative_to(ROOT):parser.error("Congelar dentro del repositorio")
    problems=check_final_models(args.manifest,[args.run_dir/"best_model.zip"],ROOT,min_seeds=1)
    if problems:parser.error("; ".join(problems))
    summary=json.loads((args.run_dir/"training_summary.json").read_text(encoding="utf-8"))
    metadata=json.loads((args.run_dir/"metadata.json").read_text(encoding="utf-8"))
    if summary["model_sha256"]!=file_hash(args.run_dir/"best_model.zip"):
        parser.error("El resumen pertenece a otro checkpoint")
    args.destination.mkdir(parents=True)
    shutil.copyfile(args.run_dir/"best_model.zip",args.destination/"model.zip")
    for name in ("training_summary.json","best_results.json","evaluations.jsonl","pretraining.jsonl","demonstrations.jsonl"):
        if (args.run_dir/name).exists():shutil.copyfile(args.run_dir/name,args.destination/name)
    metadata.update(release_status="final - una semilla",release_frozen_utc=datetime.now(timezone.utc).isoformat())
    (args.destination/"metadata.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    protocol={"schema_version":1,"frozen_utc":datetime.now(timezone.utc).isoformat(),
              "scope_note":"Alcance reducido acordado el 26 de noviembre: una semilla de entrenamiento; sin estimar variabilidad entre semillas. Aprendizaje entre misiones separado del modelo congelado.",
              "scope_document":"docs/ALCANCE.md","minimum_training_seeds":1,
              "manifest":args.manifest.resolve().relative_to(ROOT).as_posix(),
              "manifest_json_sha256":json_hash(args.manifest),
              "random_seeds":[0,1,2,3,4],"strategies":["dqn","shortest","thermal","random"],
              "models":[{"path":(args.destination/"model.zip").resolve().relative_to(ROOT).as_posix(),
                         "sha256":file_hash(args.destination/"model.zip"),
                         "metadata_json_sha256":json_hash(args.destination/"metadata.json"),
                         "training_seed":metadata["config"]["seed"],
                         "validation_successes":summary["successes"],"validation_cases":summary["validation_cases"]}]}
    args.protocol.parent.mkdir(parents=True,exist_ok=True)
    with args.protocol.open("x",encoding="utf-8") as stream:json.dump(protocol,stream,indent=2)
    print(f"Congelado: {args.destination}; protocolo: {args.protocol}. La prueba sigue sin abrirse.")


if __name__=="__main__":main()
