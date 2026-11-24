# Persistent overlapping FTS5 chunks, retaining source location and character offsets.
import re,time,uuid
from backend.database.connection import q,many
from backend.services.document_service import chunk_spans
STOP=set('a an the and or of in on at to for from by with without into over under about as is are was were be been being do does did it its this that these those there here what how why who when where which you your we our they their he she his her i me my not no so if then than can explain tell give make please describe create'.split())
def query_tokens(query: str):
 out=[]
 for t in re.findall(r'[^\W_][\w-]*',(query or '').lower(),flags=re.UNICODE):
  t=t.strip('-_')
  if len(t)>=2 and t not in STOP and t not in out: out.append(t)
 return out[:16]
def rank_candidates(candidates,query: str):
 terms=query_tokens(query); ranked=[]
 for item in candidates:
  text=(item.get('text') or '').casefold(); matched=sum(t in text for t in terms)
  if matched: ranked.append((-(matched/max(1,len(terms))),item.get('_rank',0),item))
 ranked.sort(key=lambda x:(x[0],x[1])); return [x[2] for x in ranked]
def index_source(sid: str):
 src=q('SELECT id,coll_id,type FROM sources WHERE id=?',sid,one=True)
 if not src: return 0
 pages=q('SELECT loc,kind,status,text,error FROM pages WHERE source_id=? ORDER BY loc',sid)
 q('DELETE FROM chunk_fts WHERE source_id=?',sid); q('DELETE FROM chunks WHERE source_id=?',sid); q('DELETE FROM fts WHERE source_id=?',sid)
 old=[]; chunks=[]; ordinal=0; now=time.time()
 for page in pages:
  if page['status']!='ok' or not (page.get('text') or '').strip(): continue
  text=page['text']; loc=int(page['loc']); kind=page.get('kind') or 'section'; old.append((text,sid,src['coll_id'],str(loc)))
  label=f"Page {loc}" if src['type']=='pdf' else f"Cell {loc}" if src['type']=='notebook' else f"Image {loc}" if src['type']=='image' else f"Section {loc}"
  for span in chunk_spans(text):
   ordinal+=1; cid=uuid.uuid4().hex; chunks.append((cid,sid,src['coll_id'],ordinal,loc,kind,label,span['start_char'],span['end_char'],span['text'],now))
 if old: many('INSERT INTO fts(text,source_id,coll_id,loc) VALUES(?,?,?,?)',old)
 if chunks:
  many('INSERT INTO chunks(id,source_id,coll_id,ordinal,loc,kind,label,start_char,end_char,text,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)',chunks)
  many('INSERT INTO chunk_fts(text,chunk_id,source_id,coll_id,loc,label) VALUES(?,?,?,?,?,?)',[(c[9],c[0],c[1],c[2],str(c[4]),c[6]) for c in chunks])
 return len(chunks)
def search_chunks(query: str,source_ids,k=8,allowed_source_ids=None):
 terms=query_tokens(query)
 if not source_ids or not terms: return []
 allowed=set(source_ids) if allowed_source_ids is None else set(source_ids)&set(allowed_source_ids)
 ids=[i for i in dict.fromkeys(source_ids) if i in allowed]
 if not ids: return []
 slots=','.join('?' for _ in ids); expr=' OR '.join('"'+t.replace('"','')+'"' for t in terms)
 try:
  found=q(f"SELECT c.id AS chunk_id,c.source_id,c.coll_id,c.ordinal,c.loc,c.kind,c.label,c.start_char,c.end_char,c.text,s.title,s.type,bm25(chunk_fts) AS _rank FROM chunk_fts JOIN chunks c ON c.id=chunk_fts.chunk_id JOIN sources s ON s.id=c.source_id WHERE chunk_fts MATCH ? AND chunk_fts.source_id IN ({slots}) ORDER BY bm25(chunk_fts) LIMIT ?",expr,*ids,max(k*5,k))
 except Exception: found=[]
 found=[r for r in found if r.get('source_id') in allowed]
 if found: return rank_candidates(found,query)[:k]
 try: old=q(f"SELECT f.source_id,f.loc,f.text,s.title,s.type,bm25(fts) AS _rank FROM fts JOIN sources s ON s.id=fts.source_id WHERE fts MATCH ? AND f.source_id IN ({slots}) ORDER BY bm25(fts) LIMIT ?",expr,*ids,max(k*3,k))
 except Exception: old=[]
 old=[r for r in old if r.get('source_id') in allowed]
 return [{**r,'chunk_id':'','kind':'legacy','label':f"Section {r['loc']}"} for r in rank_candidates(old,query)[:k]]
