"""Archiva una sesión local terminada sin entrenar ni modificar el modelo base."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sar_bot.online import LearningSession


def parameter_hash(path):
    import torch
    from zipfile import ZipFile
    torch.set_num_threads(1)
    with ZipFile(path) as archive:
        assignment = "assignment.json" in archive.namelist()
    if assignment:
        from sar_bot.agents.assignment import load_network
        network,_=load_network(path)
    else:
        from stable_baselines3 import DQN
        network=DQN.load(path,device="cpu").q_net
    digest = sha256()
    for name, tensor in sorted(network.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().numpy().tobytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--base", type=Path, default=ROOT / "artifacts/final/model.zip")
    parser.add_argument("--output", type=Path, default=ROOT / "results/online")
    args = parser.parse_args()
    session = LearningSession(args.session, args.base)
    snapshot = session.snapshot()
    if snapshot.generation is None:
        parser.error("La sesión todavía no tiene misiones guardadas")
    destination = args.output / "session_after"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(snapshot.model_path, destination / "model.zip")
    metadata = json.loads(args.base.with_name("metadata.json").read_text(encoding="utf-8"))
    metadata.pop("release_status", None)
    metadata["online_session"] = snapshot.metadata
    metadata["source_model_sha256"] = session.base_hash
    metadata["training_method"] = "online session study; not a final-test candidate"
    (destination / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    generations = []
    for path in args.session.glob("g-*/metadata.json"):
        meta = json.loads(path.read_text(encoding="utf-8"))
        generations.append({key: meta.get(key) for key in (
            "missions", "transitions", "updates", "buffer_size", "model_timesteps",
            "model_sha256", "last_mission")})
    evidence = {
        "scope": "Snapshot of a completed local session; a separate validation comparison is descriptive, not a new final-model selection.",
        "base_sha256": session.base_hash,
        "after_sha256": snapshot.metadata["model_sha256"],
        "base_parameters_sha256": parameter_hash(args.base),
        "after_parameters_sha256": parameter_hash(snapshot.model_path),
        "generations": sorted(generations, key=lambda item: item["missions"]),
        "session": snapshot.metadata,
    }
    assert sha256(args.base.read_bytes()).hexdigest() == session.base_hash
    changed = evidence["base_parameters_sha256"] != evidence["after_parameters_sha256"]
    evidence["parameters_changed"] = changed
    (args.output / "persistence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"missions": snapshot.metadata["missions"], "transitions": snapshot.metadata["transitions"],
                      "updates": snapshot.metadata["updates"], "parameters_changed": changed,
                      "base_unchanged": True}))


if __name__ == "__main__":
    main()
