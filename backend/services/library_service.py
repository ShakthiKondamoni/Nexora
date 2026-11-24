"""Read-only aggregation for Nexora's persisted Unified Library."""
from contextlib import closing
import logging,re
from urllib.parse import urlsplit
from backend.database.connection import connect
logger=logging.getLogger(__name__)
_WEB_URL=re.compile(r"(?im)^Source URL:\s*(https?://\S+)")
def _date_key(value):
 if value is None:return (0,"")
 try:return (1,float(value))
 except (TypeError,ValueError):return (0,str(value))
def _web_citation(text):
 if not isinstance(text,str) or not text:return None,None
 match=_WEB_URL.search(text)
 if not match:return None,None
 url=match.group(1).rstrip(".,;)")
 try:
  parsed=urlsplit(url)
  if parsed.scheme not in ("http","https") or not parsed.hostname or parsed.username or parsed.password:return None,None
 except Exception:return None,None
 lines=text.splitlines();first=lines[0].strip() if lines else "";title=first[2:].strip() if first.startswith("# ") else ""
 return title or None,url
def _knowledge_items():
 with closing(connect()) as db:
  rows=[dict(row) for row in db.execute("""SELECT s.*,c.name AS collection_name,
    (SELECT p.text FROM pages p WHERE p.source_id=s.id ORDER BY p.loc LIMIT 1) AS first_page_text,
    (SELECT COUNT(*) FROM pages p WHERE p.source_id=s.id) AS page_count,
    (SELECT COUNT(*) FROM pages p WHERE p.source_id=s.id AND p.status='ok') AS ready_pages,
    (SELECT COUNT(*) FROM pages p WHERE p.source_id=s.id AND p.status='failed') AS failed_pages
    FROM sources s LEFT JOIN collections c ON c.id=s.coll_id""")]
 rows.sort(key=lambda row:_date_key(row.get("updated") or row.get("added")),reverse=True);groups={}
 for row in rows:
  sid=str(row.get("id") or "")
  if not sid:continue
  h=str(row.get("hash") or "").strip();key=("hash",h) if h else ("id",sid)
  citation_title,url=_web_citation(row.get("first_page_text"));title=citation_title or str(row.get("title") or row.get("filename") or sid)
  typ="web_citation" if url else str(row.get("type") or "document").lower();ext=str(row.get("extension") or "").lower()
  if not ext:ext=title.rsplit(".",1)[-1].lower() if "." in title else ""
  collection=row.get("collection_name")
  metadata={"file_type":ext or typ,"knowledge_type":row.get("type"),"status":row.get("status"),"size_bytes":row.get("size_bytes"),"page_count":int(row.get("page_count") or 0),"ready_pages":int(row.get("ready_pages") or 0),"failed_pages":int(row.get("failed_pages") or 0),"added":row.get("added"),"updated":row.get("updated")}
  if url:metadata["source_url"]=url
  item=groups.get(key)
  if item is None:groups[key]={"id":sid,"source_ids":[sid],"source":"knowledge","source_label":"Knowledge Base","type":typ,"title":title,"collections":[str(collection)] if collection else [],"metadata":metadata,"open":{"kind":"knowledge","source_id":sid}}
  else:
   if sid not in item["source_ids"]:item["source_ids"].append(sid)
   if collection and str(collection) not in item["collections"]:item["collections"].append(str(collection))
   for field in ("page_count","ready_pages","failed_pages"):item["metadata"][field]=max(item["metadata"][field],metadata[field])
 return list(groups.values())
def _repo_key(row):
 repo=str(row.get("repo_id") or "").strip();url=str(row.get("html_url") or "").strip().lower().rstrip("/")
 if url.endswith(".git"):url=url[:-4]
 owner=str(row.get("owner") or "").strip().lower();name=str(row.get("name") or "").strip().lower();identity=repo or url or (f"{owner}/{name}" if owner or name else str(row.get("id") or ""))
 return identity,str(row.get("branch") or row.get("default_branch") or "").strip().lower()
def _github_items():
 with closing(connect()) as db:
  rows=[dict(row) for row in db.execute("SELECT * FROM github_projects")];counts={};warning=False
  for row in rows:
   pid=str(row.get("id") or "")
   try:counts[pid]=int(db.execute("SELECT COUNT(*) FROM github_project_files WHERE project_id=?",(pid,)).fetchone()[0] or 0)
   except Exception:warning=True;counts[pid]=None
 rows.sort(key=lambda row:_date_key(row.get("updated") or row.get("last_synced")),reverse=True);groups={}
 for row in rows:
  pid=str(row.get("id") or "")
  if not pid:continue
  key=_repo_key(row)
  if not key[0]:key=(pid,key[1])
  owner=str(row.get("owner") or "").strip();name=str(row.get("name") or "").strip();title=f"{owner}/{name}".strip("/") or str(row.get("html_url") or pid)
  metadata={"owner":owner or None,"name":name or None,"description":row.get("description"),"repo_id":row.get("repo_id"),"html_url":row.get("html_url"),"private":row.get("private"),"default_branch":row.get("default_branch"),"branch":row.get("branch"),"commit_sha":row.get("commit_sha"),"indexed_revision":row.get("indexed_revision"),"status":row.get("status"),"last_synced":row.get("last_synced"),"updated":row.get("updated"),"file_count":counts.get(pid)}
  item=groups.get(key)
  if item is None:groups[key]={"id":pid,"project_ids":[pid],"source":"github","source_label":"GitHub","type":"github_project","title":title,"collections":[],"metadata":metadata,"open":{"kind":"github","project_id":pid}}
  else:
   if pid not in item["project_ids"]:item["project_ids"].append(pid)
   if item["metadata"].get("file_count") is None and metadata.get("file_count") is not None:item["metadata"]["file_count"]=metadata["file_count"]
 return list(groups.values()),warning
def _matches(item,query):
 fields=[item.get("title"),item.get("source"),item.get("type"),*item.get("collections",[])]
 fields.extend(str(v) for v in item.get("metadata",{}).values() if v is not None)
 return query in " ".join(map(str,fields)).casefold()
def list_items(q="",source="all",item_type="all"):
 query=str(q or "").strip().casefold()[:200];source_filter=str(source or "all").strip().casefold();type_filter=str(item_type or "all").strip().casefold()
 if source_filter not in ("all","knowledge","github"):source_filter="all"
 knowledge=[];github=[];statuses={}
 try:knowledge=_knowledge_items();statuses["knowledge"]={"state":"Ready","message":"Persisted Knowledge items are available.","count":len(knowledge)}
 except Exception:logger.exception("Unified Library could not read Knowledge sources");statuses["knowledge"]={"state":"Unavailable","message":"Knowledge items could not be read from the configured database.","count":0}
 try:
  github,partial=_github_items();statuses["github"]={"state":"Needs attention" if partial else "Ready","message":"GitHub projects are available, but indexed-file counts could not be read." if partial else "Persisted indexed GitHub projects are available.","count":len(github)}
 except Exception:logger.exception("Unified Library could not read GitHub projects");statuses["github"]={"state":"Unavailable","message":"Indexed GitHub projects could not be read from the configured database.","count":0}
 items=knowledge+github
 if source_filter!="all":items=[x for x in items if x["source"]==source_filter]
 if type_filter not in ("","all"):items=[x for x in items if x["type"].casefold()==type_filter]
 if query:items=[x for x in items if _matches(x,query)]
 items.sort(key=lambda x:_date_key(x.get("metadata",{}).get("updated") or x.get("metadata",{}).get("added") or x.get("metadata",{}).get("last_synced")),reverse=True)
 return {"items":items,"total":len(items),"source_status":statuses}
