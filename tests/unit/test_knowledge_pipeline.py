import sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from backend.services.document_service import safe_upload_name,chunk_spans,extract_document
from backend.services.knowledge_index import index_source,search_chunks,rank_candidates
from backend.services.ocr_service import validate_vision_capability
from backend.database import schema
class KnowledgeTests(unittest.TestCase):
 def test_path_and_chunks(self):
  self.assertEqual(safe_upload_name('../../folder\\a.txt'),'a.txt')
  with self.assertRaises(ValueError): safe_upload_name('../')
  text=('Alpha paragraph with a distinct token.\n\n'*150); chunks=chunk_spans(text,500,80)
  self.assertGreater(len(chunks),2)
  for c in chunks:self.assertEqual(c['text'],text[c['start_char']:c['end_char']])
  self.assertTrue(any(chunks[i]['start_char']<chunks[i-1]['end_char'] for i in range(1,len(chunks))))
 def test_txt_markdown_csv_json_empty_binary_and_invalid_json(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'a.md').write_text('# Plant\nchloroplasts',encoding='utf-8');self.assertIn('Plant',extract_document(p/'a.md','.md')[0][0][2])
   (p/'a.csv').write_text('name,value\nplant,chloroplast',encoding='utf-8');self.assertIn('plant | chloroplast',extract_document(p/'a.csv','.csv')[0][0][2])
   (p/'a.json').write_text('{"energy":"light"}',encoding='utf-8');self.assertIn('energy',extract_document(p/'a.json','.json')[0][0][2])
   (p/'bad.json').write_text('{oops',encoding='utf-8')
   with self.assertRaisesRegex(ValueError,'Invalid JSON'):extract_document(p/'bad.json','.json')
   (p/'empty.txt').write_bytes(b'')
   with self.assertRaisesRegex(ValueError,'empty'):extract_document(p/'empty.txt','.txt')
   (p/'binary.txt').write_bytes(b'\x00\xff')
   with self.assertRaisesRegex(ValueError,'binary'):extract_document(p/'binary.txt','.txt')
 def test_docx_and_code_text(self):
  from docx import Document
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.docx';doc=Document();doc.add_paragraph('Local document.');t=doc.add_table(rows=1,cols=2);t.cell(0,0).text='alpha';t.cell(0,1).text='beta';doc.save(p)
   rows,method=extract_document(p,'.docx');self.assertEqual(method,'python-docx');self.assertIn('alpha | beta',rows[0][2])
   code=Path(d)/'src.py';code.write_text('def hello(): return "local"',encoding='utf-8');self.assertIn('hello',extract_document(code,'.py')[0][0][2])
 def test_ocr_capability_errors(self):
  with self.assertRaisesRegex(RuntimeError,'Select an installed local vision'):validate_vision_capability('',[])
  with self.assertRaisesRegex(RuntimeError,'vision-capable'):validate_vision_capability('text-model',['completion'])
  self.assertEqual(validate_vision_capability('vision-model',['vision']),'vision-model')
 def test_fts_chunk_locations_and_search_ranking(self):
  db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
  db.executescript("CREATE TABLE sources(id TEXT,coll_id TEXT,type TEXT,title TEXT);CREATE TABLE pages(source_id TEXT,loc INTEGER,kind TEXT,status TEXT,text TEXT,error TEXT);CREATE VIRTUAL TABLE fts USING fts5(text,source_id UNINDEXED,coll_id UNINDEXED,loc UNINDEXED);CREATE TABLE chunks(id TEXT PRIMARY KEY,source_id TEXT,coll_id TEXT,ordinal INTEGER,loc INTEGER,kind TEXT,label TEXT,start_char INTEGER,end_char INTEGER,text TEXT,created REAL);CREATE VIRTUAL TABLE chunk_fts USING fts5(text,chunk_id UNINDEXED,source_id UNINDEXED,coll_id UNINDEXED,loc UNINDEXED,label UNINDEXED);")
  db.execute('INSERT INTO sources VALUES(?,?,?,?)',('doc','co','pdf','plants.pdf'))
  db.executemany('INSERT INTO pages VALUES(?,?,?,?,?,?)',[('doc',1,'page','ok','Astronomy text describes distant galaxies and stars.',None),('doc',2,'page','ok','Photosynthesis converts light energy into chemical energy in plant chloroplasts.',None)]);db.commit()
  def q(sql,*args,one=False):
   cur=db.execute(sql,args);rows=[dict(r) for r in cur.fetchall()] if cur.description else [];db.commit();return (rows[0] if rows else None) if one else rows
  def many(sql,rows):db.executemany(sql,rows);db.commit()
  with patch('backend.services.knowledge_index.q',q),patch('backend.services.knowledge_index.many',many):
   self.assertEqual(index_source('doc'),2);hits=search_chunks('photosynthesis chloroplasts',['doc'],4);self.assertTrue(hits);self.assertEqual(hits[0]['loc'],2)
  ranked=rank_candidates([{'text':'alpha'},{'text':'alpha beta gamma'}],'alpha beta');self.assertIn('beta',ranked[0]['text'])
 def test_migration_preserves_data_and_backs_up(self):
  with tempfile.TemporaryDirectory() as d:
   db=Path(d)/'studio.db';files=Path(d)/'files';c=sqlite3.connect(db)
   for sql in schema.STATEMENTS:c.execute(sql)
   c.execute("INSERT INTO projects(id,name) VALUES('p','kept')");c.execute("INSERT INTO messages(chat_id,role,content,context,images,names,model,created) VALUES('c','user','history',NULL,NULL,NULL,NULL,1)");c.commit();c.close()
   with patch.object(schema,'DB_PATH',db),patch.object(schema,'FILES',files):schema.initialize_database()
   c=sqlite3.connect(db);self.assertEqual(c.execute('SELECT name FROM projects').fetchone()[0],'kept');self.assertEqual(c.execute('SELECT content FROM messages').fetchone()[0],'history');self.assertIn('chunks',{r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")});c.close()
   self.assertTrue(list(Path(d).glob('studio.db.backup-*')))
if __name__=='__main__':unittest.main()
