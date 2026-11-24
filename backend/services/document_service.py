"""Original pure notebook parsing and paragraph chunking (never executes cells)."""
import json, re

def chunk(t, size=1000):
    out, cur = [], ""
    for para in re.split(r"\n\s*\n", t):
        para = para.strip()
        while len(para) > size * 1.5:
            cut = para.rfind(" ", 0, size); cut = cut if cut > 200 else size
            if cur: out.append(cur); cur = ""
            out.append(para[:cut]); para = para[cut:].strip()
        if cur and len(cur) + len(para) + 2 > size: out.append(cur); cur = ""
        cur = (cur + "\n\n" + para) if cur else para
    if cur: out.append(cur)
    return [c for c in out if c.strip()]

def nb_cells(raw):
    """Parse notebook JSON only — nothing is ever executed."""
    rows = []
    for i, c in enumerate(json.loads(raw).get("cells", []), 1):
        src = c.get("source", ""); src = "".join(src) if isinstance(src, list) else str(src)
        outs = []
        for o in c.get("outputs", []) or []:
            if o.get("output_type") == "stream": outs.append("".join(o.get("text", [])))
            elif o.get("output_type") == "error": outs.append(f'{o.get("ename")}: {o.get("evalue")}')
            elif "text/plain" in o.get("data", {}): outs.append("".join(o["data"]["text/plain"]))
            elif o.get("data"): outs.append("[non-text output not extracted: " + ", ".join(o["data"]) + "]")
        if src.strip() or outs:
            t = f"[Cell {i} · {c.get('cell_type')}]\n{src}" + ("\n--- output ---\n" + "\n".join(outs)[:2000] if outs else "")
            rows.append((i, c.get("cell_type", "cell"), t))
    return rows

# Knowledge-only file formats. Existing chat attachment behavior is unchanged.
import csv,io,json,re
from pathlib import Path
TEXT_KB_EXT={'.txt','.md','.markdown','.csv','.json','.py','.js','.jsx','.ts','.tsx','.java','.c','.h','.cc','.cpp','.hpp','.cs','.go','.rs','.html','.htm','.css','.sql','.xml','.yaml','.yml','.toml','.ini','.cfg','.conf','.properties','.env','.log','.bat','.cmd','.sh','.ps1','.ipynb'}
IMAGE_KB_EXT={'.png','.jpg','.jpeg','.webp'}
SUPPORTED_KB_EXT=TEXT_KB_EXT|IMAGE_KB_EXT|{'.pdf','.docx'}
def safe_upload_name(name: str)->str:
 if not isinstance(name,str): raise ValueError('A filename is required.')
 base=name.replace('\\','/').split('/')[-1]; base=''.join(c for c in base if c!='\x00' and ord(c)>=32).strip(' .')
 if not base or base in {'.','..'}: raise ValueError('Filename is empty or unsafe.')
 return base[-240:]
def chunk_spans(text: str,size: int=1200,overlap: int=180):
 if size<100: raise ValueError('Chunk size must be at least 100 characters.')
 overlap=max(0,min(overlap,size//2)); text=text or ''; n=len(text); out=[]; start=0
 while start<n:
  end=min(n,start+size)
  if end<n:
   floor=start+int(size*.62); boundary=max(text.rfind('\n\n',floor,end),text.rfind('\n',floor,end),text.rfind('. ',floor,end))
   if boundary>start: end=boundary+(2 if text[boundary:boundary+2]=='. ' else 1)
  body=text[start:end]
  if body.strip(): out.append({'start_char':start,'end_char':end,'text':body})
  if end>=n: break
  start=max(start+1,end-overlap)
 return out
def _decode_text(path: Path):
 raw=path.read_bytes()
 if not raw: raise ValueError('Document is empty.')
 if b'\x00' in raw[:8192]: raise ValueError('File appears to be binary, not a supported text document.')
 text=raw.decode('utf-8-sig',errors='replace'); visible=sum(1 for c in text[:8192] if c.isprintable() or c in '\n\r\t')
 if text and visible/min(len(text),8192)<.75: raise ValueError('File contains binary or unsupported text encoding.')
 return text
def extract_document(path,extension: str):
 path=Path(path); ext=extension.lower(); ext=ext if ext.startswith('.') else '.'+ext
 if ext=='.docx':
  try: from docx import Document
  except ImportError as exc: raise RuntimeError('DOCX extraction requires python-docx; install the declared requirements.') from exc
  doc=Document(str(path)); parts=[p.text for p in doc.paragraphs if p.text.strip()]
  for table in doc.tables:
   for row in table.rows:
    cells=[cell.text.strip().replace('\n',' / ') for cell in row.cells]
    if any(cells): parts.append(' | '.join(cells))
  text='\n'.join(parts)
  if not text.strip(): raise ValueError('DOCX contains no extractable paragraph or table text.')
  return [(1,'document',text)],'python-docx'
 if ext=='.ipynb':
  rows=[(int(loc),str(kind),str(body)) for loc,kind,body in nb_cells(_decode_text(path)) if str(body).strip()]
  if not rows: raise ValueError('Notebook contains no extractable cell text or output.')
  return rows,'notebook-json'
 if ext not in TEXT_KB_EXT: raise ValueError(f'Unsupported document extension: {ext or "(none)"}')
 text=_decode_text(path)
 if ext=='.json':
  try: text=json.dumps(json.loads(text),ensure_ascii=False,indent=2)
  except json.JSONDecodeError as exc: raise ValueError(f'Invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}).') from exc
  kind='json'
 elif ext=='.csv':
  try: rows=list(csv.reader(io.StringIO(text,newline='')))
  except csv.Error as exc: raise ValueError(f'Invalid CSV: {exc}') from exc
  text='\n'.join(' | '.join(cell.strip() for cell in row) for row in rows if any(cell.strip() for cell in row)); kind='table'
 else: kind='text'
 if not text.strip(): raise ValueError('Document contains no extractable text.')
 return [(1,kind,text)],('csv' if ext=='.csv' else 'json' if ext=='.json' else 'utf-8 text')

