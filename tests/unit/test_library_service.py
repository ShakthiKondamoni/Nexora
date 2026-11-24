import pathlib,sqlite3,tempfile,unittest
from unittest.mock import patch
from backend.database import connection
from backend.services import library_service
class LibraryServiceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)/"test.db"
  with sqlite3.connect(self.path) as db:
   db.executescript("""
   CREATE TABLE collections(id TEXT PRIMARY KEY,name TEXT);
   CREATE TABLE sources(id TEXT PRIMARY KEY,coll_id TEXT,type TEXT,title TEXT,hash TEXT,status TEXT,error TEXT,size_bytes INTEGER,extension TEXT,added REAL,updated REAL);
   CREATE TABLE pages(source_id TEXT,loc INTEGER,kind TEXT,status TEXT,text TEXT,error TEXT);
   CREATE TABLE github_projects(id TEXT PRIMARY KEY,repo_id INTEGER,owner TEXT,name TEXT,description TEXT,html_url TEXT,private INTEGER,default_branch TEXT,branch TEXT,commit_sha TEXT,indexed_revision TEXT,status TEXT,last_synced REAL,updated REAL);
   CREATE TABLE github_project_files(id TEXT PRIMARY KEY,project_id TEXT,path TEXT,language TEXT,size_bytes INTEGER,content TEXT);
   INSERT INTO collections VALUES('c1','Research'),('c2','Archive');
   INSERT INTO sources VALUES('doc-a','c1','pdf','guide.pdf','same-hash','ready',NULL,100,'pdf',10,20);
   INSERT INTO sources VALUES('doc-b','c2','pdf','guide-copy.pdf','same-hash','ready',NULL,100,'pdf',10,19);
   INSERT INTO sources VALUES('cite','c1','text','a_clean_title.md','citation-hash','ready',NULL,200,'md',15,21);
   INSERT INTO sources VALUES('untitled','c1',NULL,NULL,'null-hash','queued',NULL,NULL,NULL,5,6);
   INSERT INTO pages VALUES('doc-a',1,'page','ok','PDF document body','');
   INSERT INTO pages VALUES('doc-b',1,'page','ok','PDF document body','');
   INSERT INTO github_projects VALUES('gh-a',42,'acme','nexora','Desktop client','https://github.com/acme/nexora',0,'main','main','abc123','rev1','indexed',30,31);
   INSERT INTO github_projects VALUES('gh-duplicate',42,'acme','nexora','Desktop client','https://github.com/acme/nexora',0,'main','main','abc123','rev1','indexed',29,30);
   INSERT INTO github_project_files VALUES('f1','gh-a','README.md','Markdown',40,'# Nexora');
   """)
   citation="# Original Web Title"+chr(10)+chr(10)+"Source URL: https://example.org/article"+chr(10)+"Retrieved: 2026-10-27"+chr(10)+"Extraction: Full extracted page"+chr(10)+chr(10)+"Saved article body"
   db.execute("INSERT INTO pages VALUES(?,?,?,?,?,?)",('cite',1,'text','ok',citation,''))
  self.patcher=patch.object(connection,"DB_PATH",self.path);self.patcher.start()
 def tearDown(self):self.patcher.stop();self.tmp.cleanup()
 def test_sources_citations_metadata_and_duplicate_prevention(self):
  r=library_service.list_items();self.assertEqual(set(r),{"items","total","source_status"});self.assertEqual(r["total"],4)
  self.assertEqual(r["source_status"]["knowledge"]["state"],"Ready");self.assertEqual(r["source_status"]["github"]["state"],"Ready")
  cite=next(x for x in r["items"] if x["type"]=="web_citation");self.assertEqual(cite["title"],"Original Web Title");self.assertEqual(cite["metadata"]["source_url"],"https://example.org/article");self.assertEqual(cite["open"],{"kind":"knowledge","source_id":"cite"})
  doc=next(x for x in r["items"] if x["type"]=="pdf");self.assertEqual(set(doc["source_ids"]),{"doc-a","doc-b"});self.assertEqual(set(doc["collections"]),{"Research","Archive"})
  repo=next(x for x in r["items"] if x["source"]=="github");self.assertEqual(repo["title"],"acme/nexora");self.assertEqual(set(repo["project_ids"]),{"gh-a","gh-duplicate"});self.assertEqual(repo["metadata"]["file_count"],1);self.assertEqual(repo["open"],{"kind":"github","project_id":"gh-a"})
  missing=next(x for x in r["items"] if x["id"]=="untitled");self.assertEqual(missing["title"],"untitled");self.assertEqual(missing["type"],"document")
 def test_search_source_and_type_filters_and_empty_state(self):
  self.assertEqual(library_service.list_items(source="github")["total"],1);self.assertEqual(library_service.list_items(item_type="web_citation")["total"],1);self.assertEqual(library_service.list_items(q="example.org")["total"],1);self.assertEqual(library_service.list_items(q="not-a-match")["items"],[])
  with sqlite3.connect(self.path) as db:db.execute("DELETE FROM sources");db.execute("DELETE FROM github_projects")
  r=library_service.list_items();self.assertEqual(r["items"],[]);self.assertEqual(r["total"],0)
 def test_persistence_and_deleted_records(self):
  self.assertEqual(library_service.list_items()["total"],4)
  with sqlite3.connect(self.path) as db:db.execute("DELETE FROM sources WHERE id='cite'")
  r=library_service.list_items();self.assertEqual(r["total"],3);self.assertNotIn("cite",[sid for x in r["items"] for sid in x.get("source_ids",[])])
 def test_one_source_failure_does_not_hide_the_other(self):
  with sqlite3.connect(self.path) as db:db.execute("DROP TABLE github_projects")
  with patch.object(library_service.logger,"exception"):
   r=library_service.list_items()
  self.assertEqual(r["source_status"]["github"]["state"],"Unavailable");self.assertEqual(r["source_status"]["knowledge"]["state"],"Ready");self.assertTrue(any(x["source"]=="knowledge" for x in r["items"]))
if __name__=="__main__":unittest.main()
