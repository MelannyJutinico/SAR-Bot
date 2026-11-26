"""Protocolo explícito de una semilla y congelación anterior a prueba."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from sar_bot.release import (file_hash,json_hash,check_release_protocol,
                             begin_final_test,complete_final_test)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        root=ROOT/"tmp/tests";root.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(dir=root)
        self.root=Path(self.temporary.name)
        self.model=self.root/"artifacts/final/model.zip";self.model.parent.mkdir(parents=True)
        self.model.write_bytes(b"pesos congelados")
        self.metadata=self.model.parent/"metadata.json"
        self.metadata.write_text(json.dumps({"config":{"seed":0}}),encoding="utf-8")
        self.manifest=self.root/"manifest.json";self.manifest.write_text('{"test":["case.json"]}',encoding="utf-8")
        self.protocol=self.root/"protocol.json"
        self.data={"schema_version":1,"minimum_training_seeds":1,"scope_note":"Una semilla; alcance acordado antes de prueba",
                   "manifest_json_sha256":json_hash(self.manifest),"random_seeds":[0,1,2,3,4],
                   "strategies":["dqn","shortest","thermal","random"],
                   "models":[{"path":self.model.relative_to(self.root).as_posix(),"sha256":file_hash(self.model),
                              "metadata_json_sha256":json_hash(self.metadata)}]}
        self.write()

    def write(self):self.protocol.write_text(json.dumps(self.data),encoding="utf-8")
    def tearDown(self):self.temporary.cleanup()
    def check(self):return check_release_protocol(self.protocol,self.manifest,[self.model],self.root)

    def test_explicit_single_seed_protocol_and_text_transport(self):
        self.assertEqual(self.check(),[])
        self.metadata.write_text('{\r\n  "config": {"seed": 0}\r\n}',encoding="utf-8")
        self.assertEqual(self.check(),[])

    def test_changed_weights_metadata_or_manifest_are_rejected(self):
        self.model.write_bytes(b"modelo cambiado")
        self.assertTrue(any("cambiaron" in p for p in self.check()))
        self.model.write_bytes(b"pesos congelados")
        self.metadata.write_text('{"config":{"seed":1}}',encoding="utf-8")
        self.assertTrue(any("cambiaron" in p for p in self.check()))
        self.manifest.write_text('{"test":["other.json"]}',encoding="utf-8")
        self.assertTrue(any("manifiesto" in p for p in self.check()))

    def test_single_opening_is_exclusive_and_completion_is_recorded(self):
        output=self.root/"test.csv";output.write_text('case,success\n1,True\n',encoding="utf-8")
        marker=begin_final_test(self.protocol,output)
        self.assertTrue(any("ya fue abierta" in p for p in self.check()))
        with self.assertRaises(FileExistsError):begin_final_test(self.protocol,output)
        complete_final_test(marker,output)
        record=json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(record["status"],"completed")
        self.assertEqual(record["protocol_json_sha256"],json_hash(self.protocol))

    def test_scope_zero_seeds_and_random_seed_changes_are_rejected(self):
        self.data.update(minimum_training_seeds=0,scope_note="",random_seeds=[0])
        self.write();problems=self.check()
        self.assertTrue(any("al menos una" in p for p in problems))
        self.assertTrue(any("limitaciones" in p for p in problems))
        self.assertTrue(any("cinco" in p for p in problems))


if __name__=="__main__":unittest.main()
