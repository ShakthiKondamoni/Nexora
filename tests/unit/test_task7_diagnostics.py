import json,unittest
from unittest.mock import patch
from backend.services import diagnostics_service as d,settings_service as ss
from backend.api.diagnostics import health
class DiagnosticTests(unittest.TestCase):
 def test_health(self):self.assertEqual(health(),{"status":"Ready","service":"Nexora"})
 def test_settings_test_hides_url(self):
  class R:
   def raise_for_status(self):pass
   def json(self):return {"models":[{},{}]}
  with patch.object(ss.requests,'get',return_value=R()):r=ss.test_connection({'url':'http://user:secret@localhost:11434'})
  self.assertTrue(r['ok']);self.assertNotIn('url',r);self.assertNotIn('secret',json.dumps(r))
 def test_report_excludes_secret(self):
  with patch.object(d.settings_service,'get_settings',return_value={'chat_model':'qwen','ollama_url':'http://user:secret@localhost'}),patch.object(d,'_database_status',return_value=d._item('db','DB','Ready','ok')),patch.object(d,'_ollama_status',return_value=(d._item('ollama','Ollama','Unavailable','offline'),[])),patch.object(d,'_web_status',return_value=d._item('web','Web','Ready','ok')),patch.object(d,'_github_status',return_value=d._item('gh','GitHub','Not configured','not configured')):r=d.collect()
  text=json.dumps(r);self.assertNotIn('secret',text);self.assertNotIn('token',text.lower());self.assertIn('Unavailable',text)
 def test_missing_model_attention(self):self.assertEqual(d._model_status('',{'state':'Ready'},[])['state'],'Needs attention')
if __name__=='__main__':unittest.main()
