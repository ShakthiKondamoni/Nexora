"""Page-preserving PDF text extraction and rendering with PyMuPDF."""
def chat_pdf(data: bytes,filename: str,limit: int)->str:
 import fitz
 with fitz.open(stream=data,filetype='pdf') as doc:
  pages=[]; blank=[]
  for n,page in enumerate(doc,1):
   try: text=page.get_text().strip()
   except Exception: text=''
   if len(text)>=30: pages.append(f'--- Page {n} ---\n{text}')
   else: blank.append(n)
  body='\n\n'.join(pages); note=''
  if len(body)>limit: body=body[:limit]; note+='\n[Truncated to fit context.]'
  if blank: note+=f'\n[Pages with little/no selectable text: {blank}; local OCR is available in Knowledge.]'
  return f'[Attached PDF: {filename}, {len(doc)} pages]\n{body}{note}'
def page_rows(path,sid):
 import fitz
 with fitz.open(path) as doc:
  if len(doc)==0: raise ValueError('PDF contains no pages.')
  rows=[]
  for n,page in enumerate(doc,1):
   try:
    text=page.get_text().strip(); ok=len(text)>=30
    rows.append((sid,n,'page','ok' if ok else 'pending',text if ok else '',None))
   except Exception as exc: rows.append((sid,n,'page','failed','',f'{type(exc).__name__}: {exc}'))
  return rows
def page_image(path,n: int,scale: float=1.2)->bytes:
 import fitz
 with fitz.open(path) as doc:
  if n<1 or n>len(doc): raise IndexError(f'PDF page {n} is outside 1..{len(doc)}.')
  return doc[n-1].get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).tobytes('png')
