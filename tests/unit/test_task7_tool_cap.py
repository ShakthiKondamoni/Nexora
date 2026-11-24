import unittest
from backend.services import web_research_service as w
class ToolCapTests(unittest.TestCase):
 def test_max_calls_is_strict(self):
  calls=[]
  def req(m,t):return {'message':{'tool_calls':[{'function':{'name':'web_search','arguments':{'query':'test'}}}]}}
  def exe(n,a):calls.append(n);return {'ok':True}
  final,_=w.tool_loop([],req,exe,max_rounds=5,max_calls=2,time_limit=2)
  self.assertEqual(len(calls),2);self.assertIn('limit',final.get('content','').lower())
if __name__=='__main__':unittest.main()
