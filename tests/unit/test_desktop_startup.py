import json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
from desktop import launcher
class Response:
 status=200
 def __init__(self,body):self.body=body
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def read(self,size=-1):return self.body[:size]
class DesktopStartupTests(unittest.TestCase):
 def test_project_root_is_available_for_script_launch(self):
  self.assertEqual(launcher.ROOT.name,"Nexora_Task7_Stabilization_DesktopRelease");self.assertIn(str(launcher.ROOT),sys.path)
 def test_health_probe_requires_expected_payload_and_route(self):
  body=json.dumps({"status":"Ready","service":"Nexora"}).encode()
  with patch.object(launcher,"urlopen",return_value=Response(body)) as req:ok,detail=launcher._probe_health("http://127.0.0.1:45678")
  self.assertTrue(ok);self.assertEqual(detail,"");self.assertTrue(req.call_args.args[0].endswith("/api/health"))
 def test_health_probe_rejects_wrong_payload(self):
  with patch.object(launcher,"urlopen",return_value=Response(b'{"status":"Ready"}')):ok,detail=launcher._probe_health("http://127.0.0.1:45678")
  self.assertFalse(ok);self.assertIn("Unexpected /api/health payload",detail)
 def test_startup_exception_is_written_with_phase(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=pathlib.Path(tmp)/"desktop.log"
   with patch.object(launcher,"_log_path",return_value=path):summary=launcher._record_startup_error("backend imports",ModuleNotFoundError("No module named 'uvicorn'"))
   self.assertIn("ModuleNotFoundError",summary);log=path.read_text();self.assertIn("backend imports",log);self.assertIn("uvicorn",log)
if __name__=="__main__":unittest.main()
