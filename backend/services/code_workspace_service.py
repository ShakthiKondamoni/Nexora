"""Local project browsing and review-first code patches; never executes commands."""
import hashlib,ipaddress,os,re,stat,threading,uuid
from pathlib import Path
from urllib.parse import urlsplit
EXTS={'.py','.js','.mjs','.cjs','.ts','.tsx','.jsx','.html','.css','.scss','.json','.md','.txt','.yaml','.yml','.toml','.ini','.sql','.java','.c','.h','.cpp','.hpp','.cs','.go','.rs','.php','.rb','.swift','.kt','.sh','.bat','.ps1','.xml','.vue','.svelte'}
SKIP={'.git','.svn','.hg','node_modules','vendor','dist','build','target','.venv','venv','env','__pycache__','.pytest_cache','.mypy_cache','.next','coverage','out','.idea','.vscode','.nexora-backups'}
SECRET=re.compile(r'^(?:\.env(?:\..*)?|id_rsa|id_ed25519|credentials?(?:\..*)?|secrets?(?:\..*)?|.*\.(?:pem|key|p12|pfx|db|sqlite|sqlite3))$',re.I)
MAX_FILES=4000;MAX_FILE=1024*1024;MAX_SCAN=12*1024*1024;MAX_PATCH=200000;MAX_PATCH_FILES=10
ROOTS={};LOCK=threading.RLock();PATCH_LOCK=threading.RLock()
class WorkspaceError(ValueError):pass

def is_local_ollama_url(url):
 try:
  u=urlsplit((url or '').strip());h=(u.hostname or '').lower().rstrip('.')
  return u.scheme in ('http','https') and not u.username and not u.password and (h=='localhost' or ipaddress.ip_address(h).is_loopback)
 except Exception:return False

def _link(st):return stat.S_ISLNK(st.st_mode) or bool(getattr(st,'st_file_attributes',0)&0x400)
def _parts(rel):
 if not isinstance(rel,str) or not rel or len(rel)>500 or '\0' in rel or '\\' in rel or rel.startswith('/') or re.match(r'^[A-Za-z]:',rel):raise WorkspaceError('Unsafe project path.')
 ps=rel.split('/')
 if any(x in ('','.','..') or SECRET.match(x) for x in ps):raise WorkspaceError('Path traversal or sensitive path is not allowed.')
 return ps
def _within(root,p):
 try:return os.path.commonpath([os.path.normcase(str(root)),os.path.normcase(str(p))])==os.path.normcase(str(root))
 except Exception:return False
def safe_path(root,rel,missing=False):
 root=Path(root).resolve(strict=True);cur=root;ps=_parts(rel)
 for i,x in enumerate(ps):
  cur=cur/x
  try:st=cur.lstat()
  except FileNotFoundError:
   if missing and i==len(ps)-1:break
   raise WorkspaceError('Project file does not exist.')
  if _link(st):raise WorkspaceError('Symbolic links and reparse points are not followed.')
  if i<len(ps)-1 and not stat.S_ISDIR(st.st_mode):raise WorkspaceError('A path component is not a directory.')
 try:r=cur.resolve(strict=not missing)
 except OSError:raise WorkspaceError('Project path could not be resolved.')
 if not _within(root,r):raise WorkspaceError('Path escapes the selected project root.')
 return cur
def project(token):
 with LOCK:r=ROOTS.get(token)
 if r is None:raise WorkspaceError('Project selection expired. Select its folder again.')
 if not r.is_dir():raise WorkspaceError('Selected project folder is unavailable.')
 return r
def register(path):
 if not isinstance(path,str) or not path.strip() or len(path)>4096:raise WorkspaceError('Select a valid project folder.')
 r=Path(path).expanduser().resolve(strict=True)
 if not r.is_dir():raise WorkspaceError('Selected path is not a directory.')
 t=uuid.uuid4().hex
 with LOCK:ROOTS[t]=r
 return {'token':t,'name':r.name or str(r)}
def list_files(token):
 root=project(token);out=[]
 for cur,dirs,files in os.walk(root,followlinks=False):
  base=Path(cur);keep=[]
  for n in dirs:
   p=base/n
   if n.startswith('.') or n in SKIP:continue
   try:st=p.lstat()
   except OSError:continue
   if _link(st) or not stat.S_ISDIR(st.st_mode):continue
   try:
    if _within(root,p.resolve(strict=True)):keep.append(n)
   except OSError:pass
  dirs[:]=keep
  for n in files:
   p=base/n
   if SECRET.match(n) or p.suffix.lower() not in EXTS:continue
   try:
    st=p.lstat();rel=p.relative_to(root).as_posix()
    if _link(st) or not stat.S_ISREG(st.st_mode) or st.st_size>MAX_FILE:continue
    safe_path(root,rel)
   except (OSError,WorkspaceError):continue
   out.append({'path':rel,'size':st.st_size,'extension':p.suffix.lower()})
   if len(out)>=MAX_FILES:return sorted(out,key=lambda x:x['path'].lower())
 return sorted(out,key=lambda x:x['path'].lower())
def read_file(root,rel):
 p=safe_path(root,rel)
 if p.suffix.lower() not in EXTS:raise WorkspaceError('File type is not allowed.')
 try:fd=os.open(str(p),os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0))
 except OSError:raise WorkspaceError('Could not open this project file safely.')
 try:
  st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_size>MAX_FILE:raise WorkspaceError('File exceeds the 1 MiB limit.')
  data=b''
  while len(data)<=MAX_FILE:
   b=os.read(fd,min(65536,MAX_FILE+1-len(data)))
   if not b:break
   data+=b
  if len(data)>MAX_FILE or b'\0' in data:raise WorkspaceError('Binary or oversized file is excluded.')
  safe_path(root,rel)
  try:return data.decode('utf-8')
  except UnicodeDecodeError:raise WorkspaceError('File is not valid UTF-8 text.')
 finally:os.close(fd)
def search(token,q='',selected=''):
 root=project(token);items=list_files(token);terms=[x.lower() for x in re.findall(r'[\w.-]{3,}',q or '')][:12];scanned=0;hits=[]
 if selected:
  try:hits.append((1000,selected,read_file(root,selected)))
  except WorkspaceError:pass
 for x in items:
  path=x['path']
  if path==selected or scanned>=MAX_SCAN or x['size']>300000 or scanned+x['size']>MAX_SCAN:continue
  try:text=read_file(root,path);scanned+=x['size']
  except WorkspaceError:continue
  lines=text.splitlines();matches=[i for i,l in enumerate(lines) if any(t in l.lower() for t in terms)];score=sum(4 for t in terms if t in path.lower())+min(8,len(matches))*2
  if score<=0:continue
  excerpt='\n'.join(f'{path}:{j+1}: {lines[j]}' for i in matches[:3] for j in range(max(0,i-3),min(len(lines),i+4)))[:4500]
  hits.append((score,path,excerpt))
 hits.sort(key=lambda x:(-x[0],x[1].lower()));out=[];total=0
 for score,path,text in hits[:5]:
  text=text[:4500]
  if total+len(text)>18000:break
  out.append({'path':path,'score':score,'excerpt':text});total+=len(text)
 return {'files':out,'scanned_bytes':scanned,'limit_bytes':MAX_SCAN}
def parse_diff(patch):
 if not isinstance(patch,str) or not patch.strip() or len(patch.encode())>MAX_PATCH:raise WorkspaceError('Patch is empty or exceeds 200 KB.')
 ls=patch.replace('\r\n','\n').replace('\r','\n').split('\n');i=0;files=[]
 while i<len(ls):
  if not ls[i].strip():i+=1;continue
  if not ls[i].startswith('--- a/'):raise WorkspaceError('Use unified diff headers: --- a/path and +++ b/path.')
  old=ls[i][6:];i+=1
  if i>=len(ls) or not ls[i].startswith('+++ b/'):raise WorkspaceError('Missing +++ b/path diff header.')
  new=ls[i][6:];i+=1
  if old!=new:raise WorkspaceError('New, deleted, and renamed files are not supported.')
  _parts(old);hunks=[]
  while i<len(ls) and not ls[i].startswith('--- a/'):
   if not ls[i].strip():i+=1;continue
   m=re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',ls[i])
   if not m:raise WorkspaceError('Malformed unified diff hunk.')
   start=int(m.group(1));oc=int(m.group(2) or 1);nc=int(m.group(4) or 1);i+=1;ops=[];a=b=0
   while i<len(ls) and ls[i][:1] in (' ','+','-','\\'):
    line=ls[i];i+=1
    if line.startswith('\\'):continue
    k=line[0];ops.append((k,line[1:]));a+=k in (' ','-');b+=k in (' ','+')
   if a!=oc or b!=nc:raise WorkspaceError('Diff hunk line counts are invalid.')
   hunks.append((start,oc,ops))
  if not hunks:raise WorkspaceError('Diff has no hunks.')
  files.append((old,hunks))
  if len(files)>MAX_PATCH_FILES:raise WorkspaceError('A diff may change at most 10 files.')
 if not files or len(set(x[0] for x in files))!=len(files):raise WorkspaceError('Diff has no files or repeats a path.')
 return files
def _apply(original,hunks):
 eol='\r\n' if '\r\n' in original else '\n';s=original.replace('\r\n','\n').replace('\r','\n');final=s.endswith('\n');src=s.split('\n');
 if final:src.pop()
 out=[];cur=0
 for start,count,ops in hunks:
  pos=start if count==0 else start-1
  if pos<cur or pos>len(src):raise WorkspaceError('Diff hunk is outside the current file.')
  out.extend(src[cur:pos]);cur=pos;used=0
  for k,t in ops:
   if k in (' ','-') and (cur>=len(src) or src[cur]!=t):raise WorkspaceError('Diff context is stale; regenerate and review it again.')
   if k==' ':out.append(t);cur+=1;used+=1
   elif k=='-':cur+=1;used+=1
   else:out.append(t)
  if used!=count:raise WorkspaceError('Diff does not match expected source lines.')
 out.extend(src[cur:]);r='\n'.join(out)+('\n' if final else '')
 return r.replace('\n',eol) if eol!='\n' else r
def preview(root,patch):
 root=Path(root).resolve(strict=True);out=[]
 for rel,hunks in parse_diff(patch):
  p=safe_path(root,rel)
  if p.suffix.lower() not in EXTS:raise WorkspaceError('Patch target is not an allowed source file.')
  old=read_file(root,rel);new=_apply(old,hunks)
  if old==new:raise WorkspaceError('Diff does not change the file.')
  out.append({'path':rel,'old_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_sha256':hashlib.sha256(new.encode()).hexdigest(),'old':old,'new':new})
 return out
def _mkdir_safe(path,root):
 root=Path(root).resolve(strict=True);cur=root
 for part in path.relative_to(root).parts:
  cur=cur/part
  try:cur.mkdir()
  except FileExistsError:pass
  st=cur.lstat()
  if _link(st) or not stat.S_ISDIR(st.st_mode) or not _within(root,cur.resolve(strict=True)):raise WorkspaceError('Backup path is unsafe.')
def _atomic_write(root,rel,text):
 target=safe_path(root,rel);tmp=target.parent/('.nexora-tmp-'+uuid.uuid4().hex);fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0),0o600)
 try:
  b=text.encode();pos=0
  while pos<len(b):pos+=os.write(fd,b[pos:pos+65536])
  os.fsync(fd)
 finally:os.close(fd)
 safe_path(root,rel);os.replace(tmp,target)
def apply_patch(root,patch,expected):
 root=Path(root).resolve(strict=True)
 with PATCH_LOCK:
  changes=preview(root,patch)
  if not isinstance(expected,dict) or set(expected)!={c['path'] for c in changes}:raise WorkspaceError('Review expired; reopen the diff before applying.')
  if any(expected[c['path']]!=c['old_sha256'] for c in changes):raise WorkspaceError('Files changed since preview; review the updated diff.')
  backup=root/'.nexora-backups'/(__import__('datetime').datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);_mkdir_safe(backup,root);backups=[]
  for c in changes:
   b=backup/Path(c['path']);_mkdir_safe(b.parent,root);fd=os.open(str(b),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0),0o600)
   try:os.write(fd,c['old'].encode())
   finally:os.close(fd)
   backups.append((c['path'],b.relative_to(root).as_posix(),c['old']))
  applied=[]
  try:
   for c in changes:
    if hashlib.sha256(read_file(root,c['path']).encode()).hexdigest()!=c['old_sha256']:raise WorkspaceError('File changed after diff review; no rebase was attempted.')
    _atomic_write(root,c['path'],c['new']);applied.append(c['path'])
  except Exception:
   for rel,_,old in reversed(backups):
    if rel in applied:
     try:_atomic_write(root,rel,old)
     except Exception:pass
   raise
  return {'applied':[c['path'] for c in changes],'backups':[b for _,b,_ in backups],'tested':False}
