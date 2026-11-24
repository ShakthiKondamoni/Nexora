import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.services import web_research_service as w
class WebTests(unittest.TestCase):
 def test_unsafe_urls(self):
  for u in ('http://127.0.0.1','http://169.254.169.254/latest','file:///etc/passwd','http://example.com:8501','http://router.local'):
   with self.subTest(u=u),self.assertRaises(ValueError):w.validate_public_url(u)
 def test_dns_ip_pinning_validation(self):
  with patch.object(w.socket,'getaddrinfo',return_value=[(2,1,6,'',('10.0.0.2',443))]),self.assertRaises(ValueError):w.validate_public_url('https://x.example')
  with patch.object(w.socket,'getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]):self.assertEqual(w.validate_public_url('https://x.example')['ips'],['8.8.8.8'])
 def test_html(self):
  body=("<html><head><title>Release notes</title><meta name='description' content='Summary'><meta property='article:published_time' content='2026-10-01'><link rel='canonical' href='/docs/release'></head>" "<body><nav>Noise</nav><main><h1>Release notes</h1><p>Readable article paragraph.</p><ul><li>First item</li><li><a href='https://example.org/a'>Useful link</a></li></ul><script>ignore this</script></main><footer>Footer</footer></body></html>").encode()
  title,content,date,desc,canonical,tr=w._extract(body,'https://example.org/release','text/html; charset=utf-8')
  self.assertEqual(title,'Release notes');self.assertIn('Readable article',content);self.assertIn('- First item',content);self.assertIn('[Useful link](https://example.org/a)',content);self.assertNotIn('Noise',content);self.assertNotIn('ignore this',content);self.assertEqual(date,'2026-10-01');self.assertEqual(canonical,'https://example.org/docs/release');self.assertFalse(tr)
 def test_citations_and_count(self):
  self.assertEqual(w.clean_citations('yes [1] no [9] local [S1]',[{'kind':'web','citation':1}]),'yes [1] no  local [S1]');self.assertEqual(w.valid_count(None,99),8)
  for n in (0,9,True,'3'):
   with self.subTest(n=n),self.assertRaises(ValueError):w.valid_count(n)
 def test_mock_tool_cycle_and_limit(self):
  answers=[{'message':{'tool_calls':[{'function':{'name':'web_search','arguments':{'query':'Nexora'}}}]}},{'message':{'content':'Answer [1]'}}];msgs=[]
  def request(m,t):return answers.pop(0)
  final,notes=w.tool_loop(msgs,request,lambda n,a:{'ok':True});self.assertEqual(final['content'],'Answer [1]');self.assertEqual(msgs[-1]['role'],'tool');self.assertTrue(notes)
  final,_=w.tool_loop([],lambda m,t:{'message':{'tool_calls':[{'function':{'name':'web_fetch','arguments':{'url':'https://example.org'}}}]}},lambda n,a:{'ok':True},max_rounds=5,max_calls=1);self.assertIn('limit',final['content'])
if __name__=='__main__':unittest.main()
