"""Existing chat attachment validation and context preparation."""
import base64
from pathlib import Path
from fastapi import HTTPException
from backend.core.config import CHAT_MAX_MB as MAX_MB, IMG_EXT, TEXT_EXT
from backend.services.ollama_service import caps
from backend.services.pdf_service import chat_pdf
from backend.services.document_service import nb_cells

async def prepare_attachments(files, model: str, ctx: int):
    imgs, parts, names = [], [], []
    limit = max(1500, ctx * 3 - 1500)
    for f in files:
        d = await f.read(); ext = Path(f.filename).suffix.lower(); names.append(f.filename)
        if len(d) > MAX_MB * 2**20: raise HTTPException(413, f"{f.filename} exceeds the {MAX_MB} MB limit.")
        if ext in IMG_EXT:
            if "vision" not in caps(model): raise HTTPException(400, f"'{model}' is not a vision model. Pick a vision-capable model (e.g. qwen3-vl) to send images.")
            imgs.append(base64.b64encode(d).decode())
        elif ext == ".pdf":
            parts.append(chat_pdf(d, f.filename, limit))
        elif ext == ".ipynb":
            try: parts.append(f"[Attached notebook: {f.filename}]\n" + "\n\n".join(t for _, _, t in nb_cells(d.decode("utf-8")))[:limit])
            except Exception as e: raise HTTPException(400, f"{f.filename}: invalid notebook ({e})")
        elif ext in TEXT_EXT:
            t = d.decode("utf-8", "replace")
            parts.append(f"[Attached file: {f.filename}]\n{t[:limit]}" + ("\n[Truncated]" if len(t) > limit else ""))
        else:
            raise HTTPException(415, f"{f.filename}: unsupported file type '{ext}' (DOCX arrives in a later stage).")
    return imgs, parts, names
