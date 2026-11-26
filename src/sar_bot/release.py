"""Congelación y apertura única de prueba con alcance explícito de entrega."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4


def json_hash(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return sha256(json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def final_marker(protocol_path):
    path=Path(protocol_path)
    return path.with_name(path.stem+".started.json")


def check_release_protocol(protocol_path,manifest_path,model_paths,root):
    root=Path(root)
    protocol=json.loads(Path(protocol_path).read_text(encoding="utf-8"))
    problems=[]
    if protocol.get("schema_version")!=1:problems.append("Version de protocolo desconocida")
    minimum=protocol.get("minimum_training_seeds")
    if type(minimum) is not int or minimum<1:problems.append("El protocolo debe declarar al menos una semilla")
    if protocol.get("manifest_json_sha256")!=json_hash(manifest_path):
        problems.append("El manifiesto no coincide con la congelacion")
    declared=protocol.get("models",[])
    if len(declared)!=len(model_paths):problems.append("La cantidad de modelos no coincide con la congelacion")
    for model in model_paths:
        model=Path(model).resolve()
        matching=[m for m in declared if (root/m["path"]).resolve()==model]
        if len(matching)!=1:problems.append("Modelo no declarado en el protocolo: "+model.name)
        elif (file_hash(model)!=matching[0]["sha256"] or
              json_hash(model.parent/"metadata.json")!=matching[0]["metadata_json_sha256"]):
            problems.append("Modelo o metadatos cambiaron despues de congelar")
    if protocol.get("random_seeds")!=[0,1,2,3,4]:
        problems.append("La entrega requiere cinco semillas de acciones aleatorias")
    if protocol.get("strategies")!=["dqn","shortest","thermal","random"]:
        problems.append("El protocolo debe declarar las cuatro estrategias")
    if not protocol.get("scope_note"):problems.append("Falta declarar el alcance y sus limitaciones")
    if final_marker(protocol_path).exists():problems.append("La prueba ya fue abierta con este protocolo")
    return problems


def begin_final_test(protocol_path,output):
    marker=final_marker(protocol_path)
    record={"status":"started","started_utc":datetime.now(timezone.utc).isoformat(),
            "protocol_json_sha256":json_hash(protocol_path),"output":Path(output).as_posix()}
    with marker.open("x",encoding="utf-8") as stream:
        json.dump(record,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    return marker


def complete_final_test(marker,csv_path):
    from sar_bot.partitions import file_sha256
    marker=Path(marker)
    record=json.loads(marker.read_text(encoding="utf-8"))
    record.update(status="completed",completed_utc=datetime.now(timezone.utc).isoformat(),
                  csv_sha256=file_sha256(csv_path))
    temporary=marker.with_name("."+marker.name+uuid4().hex+".tmp")
    try:
        with temporary.open("x",encoding="utf-8") as stream:
            json.dump(record,stream,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,marker)
    finally:temporary.unlink(missing_ok=True)
