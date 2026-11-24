"""Bounded SearXNG search, Ollama tool loop, and SSRF-resistant page extraction."""
import hashlib,html,http.client,ipaddress,json,re,socket,ssl,threading,time
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
MAX_RESULTS=8;MAX_PAGES=3;MAX_FETCH_BYTES=1500000;MAX_TEXT=12000;MAX_REDIRECTS=3;MAX_CALLS=4;MAX_ROUNDS=3;MAX_SECONDS=45
TOOL_SEMAPHORE=threading.BoundedSemaphore(3);RECENCY={'day','week','month','year'};BLOCKED={'localhost','metadata.google.internal','metadata.google','instance-data.ec2.internal'}
TOOLS=[{'type':'function','function':{'name':'web_search','description':'Search configured SearXNG for public web pages.','parameters':{'type':'object','properties':{'query':{'type':'string'},'count':{'type':'integer'},'recency':{'type':'string','enum':['day','week','month','year']}},'required':['query']}}},{'type':'function','function':{'name':'web_fetch','description':'Fetch readable text from a public HTTP/HTTPS webpage.','parameters':{'type':'object','properties':{'url':{'type':'string'}},'required':['url']}}}]
def _cfg():
 from backend.services.settings_service import get_settings
 return get_settings()
def _now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def _text(v,n=800):return ' '.join(html.unescape(str(v or '')).split())[:n]
def _base(value=None):
 raw=(value if value is not None else _cfg().get('web_instance_url',''));raw=(raw or '').strip().rstrip('/')
 if not raw:raise RuntimeError('Search provider is not configured. Open Settings → Web & Research and set a SearXNG instance URL.')
 u=urlsplit(raw)
 if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.fragment:raise ValueError('SearXNG URL must be HTTP(S), without credentials or a fragment.')
 return raw
def valid_count(n,default=5):
 if n is None:return max(1,min(8,int(default)))
 if isinstance(n,bool) or not isinstance(n,int) or not 1<=n<=8:raise ValueError('Result count must be from 1 to 8.')
 return n
def _search(base,query,count,recency=None,timeout=None):
 import requests
 query=_text(query,512)
 if not query:raise ValueError('Search query is required.')
 count=valid_count(count)
 if recency not in (None,'') and recency not in RECENCY:raise ValueError('Recency must be day, week, month, or year.')
 timeout=max(3,min(30,int(timeout or _cfg().get('web_timeout',12))))
 r=requests.get(base.rstrip('/')+'/search',params={'q':query,'format':'json',**({'time_range':recency} if recency else {})},timeout=(3,timeout),allow_redirects=False,headers={'Accept':'application/json','User-Agent':'Nexora-WebResearch/1.0'},stream=True)
 try:
  if 300<=r.status_code<400:raise RuntimeError('SearXNG redirected; set the final instance URL directly.')
  r.raise_for_status();buf=bytearray()
  for chunk in r.iter_content(65536):
   if chunk:
    buf.extend(chunk)
    if len(buf)>1000000:raise ValueError('Search response exceeded size limit.')
  data=json.loads(buf.decode('utf-8','replace'))
 finally:r.close()
 out=[]
 for x in data.get('results',[]) if isinstance(data,dict) else []:
  if not isinstance(x,dict):continue
  url=str(x.get('url') or x.get('link') or '').strip();u=urlsplit(url)
  if u.scheme not in ('http','https') or not u.hostname:continue
  out.append({'title':_text(x.get('title') or u.hostname,300),'url':url,'snippet':_text(x.get('content') or x.get('snippet'),800),'domain':u.hostname.lower(),'published_date':_text(x.get('publishedDate') or x.get('published_date') or x.get('date'),80) or None})
  if len(out)>=count:break
 return out
class SearXNGProvider:
 name='searxng'
 def search(self,query,count=None,recency=None,instance_url=None,timeout=None):
  cfg=_cfg();return _search(_base(instance_url),query,valid_count(count,cfg.get('web_result_count',5)),recency,timeout)
 def test(self,instance_url=None,timeout=None):
  base=_base(instance_url);rows=_search(base,'Nexora connection test',1,None,timeout);return {'ok':True,'provider':self.name,'instance_url':base,'results':len(rows),'sample_title':rows[0]['title'] if rows else None}
SEARCH_PROVIDERS={'searxng':SearXNGProvider()}
def _selected_provider():
 cfg=_cfg();provider=SEARCH_PROVIDERS.get(cfg.get('web_provider','searxng'))
 if provider is None:raise RuntimeError('Unsupported search provider; select a configured provider.')
 return provider
def search(query,count=None,recency=None,instance_url=None,timeout=None):return _selected_provider().search(query,count,recency,instance_url,timeout)
def test_provider(instance_url=None,timeout=None):return _selected_provider().test(instance_url,timeout)
def _public_ip(value):
 try:ip=ipaddress.ip_address(value)
 except ValueError:return False
 return ip.is_global and not(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified)
def validate_public_url(url):
 if not isinstance(url,str) or len(url)>2048 or any(ord(c)<32 for c in url):raise ValueError('URL invalid or too long.')
 u=urlsplit(url.strip())
 if u.scheme.lower() not in ('http','https') or not u.hostname or u.username is not None or u.password is not None:raise ValueError('Only HTTP(S) URLs with a hostname and no credentials are allowed.')
 host=u.hostname.rstrip('.').encode('idna').decode('ascii').lower()
 if host in BLOCKED or host.endswith(('.localhost','.local','.internal','.lan')):raise ValueError('Local/internal hostnames are blocked.')
 default=443 if u.scheme.lower()=='https' else 80
 try:port=u.port or default
 except ValueError as e:raise ValueError('Invalid URL port.') from e
 if port!=default:raise ValueError('Only standard HTTP/HTTPS ports are allowed.')
 try:ipaddress.ip_address(host);addresses=[host]
 except ValueError:
  try:addresses=sorted({x[4][0] for x in socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)})
  except OSError as e:raise ValueError('Could not resolve public hostname.') from e
 if not addresses or any(not _public_ip(x) for x in addresses):raise ValueError('Private, reserved, or non-public network destinations are blocked.')
 return {'scheme':u.scheme.lower(),'host':host,'port':port,'ips':addresses,'path':u.path or '/','query':u.query}
class _PinnedHTTP(http.client.HTTPConnection):
 def __init__(self,h,p,ip,t):super().__init__(h,p,timeout=t);self.ip=ip
 def connect(self):self.sock=socket.create_connection((self.ip,self.port),self.timeout,self.source_address)
class _PinnedHTTPS(http.client.HTTPSConnection):
 def __init__(self,h,p,ip,t):super().__init__(h,p,timeout=t,context=ssl.create_default_context());self.ip=ip
 def connect(self):
  s=socket.create_connection((self.ip,self.port),self.timeout,self.source_address);self.sock=self._context.wrap_socket(s,server_hostname=self.host)
def _get(url,timeout):
 v=validate_public_url(url);c=(_PinnedHTTPS if v['scheme']=='https' else _PinnedHTTP)(v['host'],v['port'],v['ips'][0],timeout);path=v['path']+('?' + v['query'] if v['query'] else '')
 try:
  c.request('GET',path,headers={'User-Agent':'Nexora-WebResearch/1.0','Accept':'text/html,application/xhtml+xml,application/pdf,text/plain;q=0.8','Accept-Encoding':'identity','Connection':'close'});r=c.getresponse();h={k.lower():v for k,v in r.getheaders()};n=h.get('content-length')
  if n and n.isdigit() and int(n)>MAX_FETCH_BYTES:raise ValueError('Webpage exceeds response size limit.')
  b=r.read(MAX_FETCH_BYTES+1)
  if len(b)>MAX_FETCH_BYTES:raise ValueError('Webpage exceeds response size limit.')
  if h.get('content-encoding','identity').lower() not in ('','identity'):raise ValueError('Compressed responses are not supported.')
  return r.status,h,b
 finally:c.close()
class _HTML(HTMLParser):
 SKIP={'script','style','noscript','iframe','svg','canvas','nav','footer','form','button','input','select','textarea','template'};BLOCK={'p','div','section','article','main','h1','h2','h3','h4','h5','h6','ul','ol','li','blockquote','pre','br','hr','table','tr'}
 def __init__(self,base):super().__init__(convert_charrefs=True);self.base=base;self.skip=0;self.depth=0;self.all=[];self.main=[];self.title=[];self.in_title=False;self.meta={};self.canonical='';self.links=[]
 def add(self,s):
  if not self.skip:self.all.append(s);self.main.append(s) if self.depth else None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in self.SKIP:self.skip+=1;return
  if self.skip:return
  if tag=='title':self.in_title=True
  if tag in ('main','article'):self.depth+=1
  if tag=='meta':
   k=(a.get('property') or a.get('name') or '').lower();v=a.get('content') or ''
   if k and v:self.meta[k]=_text(v,500)
  if tag=='link' and 'canonical' in (a.get('rel') or '').lower().split():self.canonical=a.get('href','')
  if tag in self.BLOCK:self.add('\n\n')
  if tag.startswith('h') and len(tag)==2 and tag[1].isdigit():self.add('#'*int(tag[1])+' ')
  if tag=='li':self.add('- ')
  if tag in ('th','td'):self.add(' | ')
  if tag=='a':self.links.append([a.get('href',''),[]])
 def handle_endtag(self,tag):
  if tag in self.SKIP:
   if self.skip:self.skip-=1
   return
  if self.skip:return
  if tag=='title':self.in_title=False
  if tag=='a' and self.links:
   href,parts=self.links.pop();label=' '.join(''.join(parts).split());target=urljoin(self.base,href or '')
   if label:self.add('['+label+']('+target+')' if href and urlsplit(target).scheme in ('http','https') else label)
  if tag in ('td','th'):self.add(' | ')
  if tag in self.BLOCK:self.add('\n')
  if tag in ('main','article'):self.depth=max(0,self.depth-1)
 def handle_data(self,d):
  if self.skip:return
  if self.in_title:self.title.append(d)
  if self.links:self.links[-1][1].append(d)
  else:self.add(d)
 def result(self):
  raw=''.join(self.main) if len(''.join(self.main).strip())>=80 else ''.join(self.all);raw=html.unescape(raw);raw=re.sub(r'[ \t\xa0]+',' ',raw);raw=re.sub(r' *\n *','\n',raw);raw=re.sub(r'\n{3,}','\n\n',raw);raw='\n'.join(x.strip() for x in raw.splitlines()).strip();tr=len(raw)>MAX_TEXT
  title=_text(''.join(self.title) or self.meta.get('og:title'),300);date=self.meta.get('article:published_time') or self.meta.get('date') or self.meta.get('pubdate');desc=self.meta.get('description') or self.meta.get('og:description') or '';canonical=urljoin(self.base,self.canonical) if self.canonical else self.base
  return title,raw[:MAX_TEXT],date,desc,canonical,tr
def _extract(body,url,ctype):
 m=re.search(r'charset\s*=\s*["\']?([^;"\' ]+)',ctype,re.I);enc=m.group(1) if m else 'utf-8'
 try:t=body.decode(enc,errors='replace')
 except LookupError:t=body.decode('utf-8',errors='replace')
 p=_HTML(url);p.feed(t);p.close();return p.result()
def _sid(url):return hashlib.sha256(url.split('#',1)[0].encode()).hexdigest()[:16]
def _snippet(row):
 u=row['url'].split('#',1)[0];return {'sid':_sid(u),'kind':'web','title':row['title'],'url':u,'final_url':u,'canonical_url':None,'domain':row['domain'],'retrieved_at':_now(),'published_date':row.get('published_date'),'content':row.get('snippet',''),'snippet':row.get('snippet',''),'full':False,'extraction_status':'snippet_only','truncated':False}
def fetch(url,timeout=None):
 timeout=max(3,min(30,int(timeout or _cfg().get('web_timeout',12))));cur=url.strip();redirects=0
 while True:
  status,h,b=_get(cur,timeout)
  if status in (301,302,303,307,308):
   if not h.get('location'):raise RuntimeError('Redirect lacks Location header.')
   if redirects>=MAX_REDIRECTS:raise RuntimeError('Redirect limit exceeded.')
   cur=urljoin(cur,h['location']);redirects+=1;continue
  if status<200 or status>=300:raise RuntimeError('Webpage returned HTTP '+str(status)+'.')
  final=cur.split('#',1)[0];ctype=h.get('content-type','').lower();domain=urlsplit(final).hostname or ''
  if 'application/pdf' in ctype or b.startswith(b'%PDF-'):
   from backend.services.pdf_service import chat_pdf
   text=chat_pdf(b,'web-source.pdf',MAX_TEXT);tr='Truncated' in text
   return {'sid':_sid(final),'kind':'web','title':domain or 'PDF source','url':final,'final_url':final,'canonical_url':None,'domain':domain,'retrieved_at':_now(),'published_date':None,'content':text[:MAX_TEXT],'snippet':text[:600],'full':True,'extraction_status':'truncated' if tr else 'full_pdf_text','truncated':tr}
  if not any(x in ctype for x in ('text/html','application/xhtml+xml','text/plain')):raise ValueError('Unsupported webpage content type.')
  if 'text/plain' in ctype:text=b.decode('utf-8',errors='replace');tr=len(text)>MAX_TEXT;title=domain;date=desc='';canonical=final;text=text[:MAX_TEXT]
  else:title,text,date,desc,canonical,tr=_extract(b,final,ctype)
  if not text.strip():raise ValueError('No readable text extracted.')
  return {'sid':_sid(final),'kind':'web','title':title or domain,'url':final,'final_url':final,'canonical_url':canonical,'domain':domain,'retrieved_at':_now(),'published_date':date,'content':text,'snippet':(desc or text)[:800],'full':True,'extraction_status':'truncated' if tr else 'full','truncated':tr}
def _add(sources,x):
 for i,o in enumerate(sources):
  if o.get('sid')==x.get('sid') or o.get('url')==x.get('url'):
   x['citation']=o.get('citation') or i+1
   if o.get('full') and not x.get('full'):return o
   sources[i]=x;return x
 x['citation']=1+sum(1 for a in sources if a.get('kind')=='web');sources.append(x);return x
def search_first(query,count=None,recency=None):
 rows=search(query,count,recency);sources=[]
 for row in rows:_add(sources,_snippet(row))
 for row in rows[:MAX_PAGES]:
  try:_add(sources,fetch(row['url']))
  except Exception:pass
 return sources
def context_for(sources,limit=10000):
 out=[];used=0
 for s in sources:
  if s.get('kind')!='web':continue
  head=f"[{s.get('citation',1)}] {s.get('title','Untitled')} — {s.get('url','')} ({'full page' if s.get('full') else 'search snippet only'})\n";body=s.get('content') or s.get('snippet') or '';room=limit-used-len(head)
  if room<=0:break
  part=body[:room];out.append(head+part);used+=len(head)+len(part)
  if len(part)<len(body):break
 return '\n\n'.join(out)
def clean_citations(text,sources):
 valid={str(s.get('citation')) for s in sources if s.get('kind')=='web' and s.get('citation') is not None}
 return re.sub(r'(?<![A-Za-z0-9])\[(\d+)\](?![A-Za-z0-9])',lambda m:m.group(0) if m.group(1) in valid else '',text or '')
def execute(name,args,sources):
 if not isinstance(args,dict):raise ValueError('Tool arguments must be a JSON object.')
 if name=='web_search':
  q=args.get('query');n=args.get('count')
  if not isinstance(q,str) or not q.strip() or len(q)>512:raise ValueError('Search query must be 1–512 characters.')
  rows=search(q,n,args.get('recency'));out=[]
  for row in rows:
   s=_add(sources,_snippet(row));out.append({k:s.get(k) for k in ('sid','citation','title','url','snippet','domain','published_date')})
  return {'results':out,'count':len(out)}
 if name=='web_fetch':
  url=args.get('url')
  if not isinstance(url,str):raise ValueError('URL is required.')
  s=_add(sources,fetch(url));return {k:s.get(k) for k in ('sid','citation','title','url','domain','retrieved_at','published_date','full','extraction_status','content')}
 raise ValueError('Unknown web tool.')
def tool_loop(messages,request_fn,executor,max_rounds=MAX_ROUNDS,max_calls=MAX_CALLS,time_limit=MAX_SECONDS):
 notes=[];count=0;start=time.monotonic()
 for _ in range(max_rounds):
  if time.monotonic()-start>time_limit:raise TimeoutError('Web tool execution timed out.')
  data=request_fn(messages,TOOLS);msg=data.get('message') or {};calls=msg.get('tool_calls') or []
  if not calls:return msg,notes
  messages.append(msg)
  for call in calls:
   if count>=max_calls:return {'content':'Configured web tool-call limit reached.'},notes
   count+=1;fn=call.get('function') or {};name=fn.get('name','');args=fn.get('arguments',{})
   if isinstance(args,str):
    try:args=json.loads(args)
    except Exception:args=None
   try:content=json.dumps(executor(name,args),ensure_ascii=False);notes.append(('success','Used '+name.replace('_',' ')))
   except Exception as e:content=json.dumps({'error':str(e)[:400]},ensure_ascii=False);notes.append(('warning',name.replace('_',' ')+' failed: '+str(e)[:120]))
   messages.append({'role':'tool','tool_name':name,'content':content[:MAX_TEXT+2000]})
  if time.monotonic()-start>time_limit:raise TimeoutError('Web tool execution timed out.')
 return {'content':'Research round limit reached; use Search first to guarantee search.'},notes
