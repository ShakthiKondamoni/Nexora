import tempfile,unittest
from pathlib import Path
from backend.services.code_workspace_service import WorkspaceError,preview,apply_patch,is_local_ollama_url
class SafetyTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);(self.root/'app.py').write_text('print("old")\nkeep = True\n')
 def tearDown(self):self.t.cleanup()
 def diff(self,path='app.py'):return f'--- a/{path}\n+++ b/{path}\n@@ -1,2 +1,2 @@\n-print("old")\n+print("new")\n keep = True\n'
 def test_preview_is_read_only(self):
  self.assertEqual(len(preview(self.root,self.diff())),1);self.assertIn('old',(self.root/'app.py').read_text())
 def test_apply_creates_backup(self):
  c=preview(self.root,self.diff())[0];r=apply_patch(self.root,self.diff(),{'app.py':c['old_sha256']});self.assertIn('new',(self.root/'app.py').read_text());self.assertTrue((self.root/r['backups'][0]).exists())
 def test_traversal_rejected(self):
  with self.assertRaises(WorkspaceError):preview(self.root,self.diff('../outside.py'))
 def test_stale_hunk_rejected(self):
  with self.assertRaises(WorkspaceError):preview(self.root,self.diff().replace('print("old")','changed'))
 def test_stale_file_rejected(self):
  c=preview(self.root,self.diff())[0];(self.root/'app.py').write_text('external change');
  with self.assertRaises(WorkspaceError):apply_patch(self.root,self.diff(),{'app.py':c['old_sha256']})
 def test_link_rejected(self):
  x=self.root.parent/'outside.py';x.write_text('secret');l=self.root/'link.py'
  try:l.symlink_to(x)
  except OSError:self.skipTest('symlink unavailable')
  with self.assertRaises(WorkspaceError):preview(self.root,self.diff('link.py'))
 def test_loopback_ollama(self):
  self.assertTrue(is_local_ollama_url('http://127.0.0.1:11434'));self.assertFalse(is_local_ollama_url('https://example.org'))
if __name__=='__main__':unittest.main()
