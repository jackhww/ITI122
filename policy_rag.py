import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
import faiss
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import re
from typing import List

POLICY_DIR = Path("policies")
STORE_DIR = Path("vector_store")
INDEX_PATH = STORE_DIR / "policy.index"
META_PATH = STORE_DIR / "policy_meta.npy"

# Small, good-enough embedding model; CPU-friendly
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def _read_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    parts = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        parts.append(txt)
    return "\n".join(parts)

def _read_txt_text(txt_path: Path) -> str:
    return txt_path.read_text(encoding="utf-8", errors="ignore")

def _chunk_text(text: str, max_chars: int = 900, overlap_lines: int = 2) -> List[str]:
    """
    Chunk text by lines to keep table rows together.
    - Keeps newlines
    - Packs multiple lines into a chunk up to max_chars
    - Adds small overlap in lines to avoid cutting boundaries
    """
    # Normalize line endings and strip weird spacing, but KEEP newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Clean up excessive blank lines
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]  # drop empty

    chunks = []
    buf = []
    buf_len = 0

    def flush():
        nonlocal buf, buf_len
        if buf:
            chunks.append("\n".join(buf).strip())
            buf = []
            buf_len = 0

    i = 0
    while i < len(lines):
        ln = lines[i]
        ln_len = len(ln) + 1

        # If a single line is huge, split it safely
        if ln_len > max_chars:
            flush()
            for j in range(0, len(ln), max_chars):
                chunks.append(ln[j:j+max_chars])
            i += 1
            continue

        if buf_len + ln_len <= max_chars:
            buf.append(ln)
            buf_len += ln_len
            i += 1
        else:
            flush()
            # Overlap a couple of lines from previous chunk
            if overlap_lines > 0 and chunks:
                prev_lines = chunks[-1].split("\n")[-overlap_lines:]
                buf = prev_lines.copy()
                buf_len = sum(len(x)+1 for x in buf)

    flush()
    return chunks

def build_or_load_index() -> Tuple[faiss.IndexFlatIP, List[Dict[str, Any]], SentenceTransformer]:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    embedder = SentenceTransformer(EMBED_MODEL_NAME)

    if INDEX_PATH.exists() and META_PATH.exists():
        index = faiss.read_index(str(INDEX_PATH))
        meta = np.load(str(META_PATH), allow_pickle=True).tolist()
        return index, meta, embedder

    # Ingest PDFs/TXTs
    docs = []
    for p in sorted(POLICY_DIR.glob("*")):
        if p.suffix.lower() == ".pdf":
            docs.append((p.name, _read_pdf_text(p)))
        elif p.suffix.lower() == ".txt":
            docs.append((p.name, _read_txt_text(p)))

    if not docs:
        raise RuntimeError("No policy files found in ./policies (add sample_policy.txt or PDFs).")

    chunks_meta = []
    chunks = []
    for filename, text in docs:
        for idx, ch in enumerate(_chunk_text(text)):
            chunks.append(ch)
            chunks_meta.append({"source": filename, "chunk_id": f"{filename}::chunk{idx}", "text": ch})

    # Embed
    embs = embedder.encode(chunks, normalize_embeddings=True, batch_size=64, show_progress_bar=False)
    embs = np.array(embs, dtype="float32")

    # Index (cosine similarity via inner product on normalized vectors)
    dim = embs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embs)

    faiss.write_index(index, str(INDEX_PATH))
    np.save(str(META_PATH), np.array(chunks_meta, dtype=object))

    return index, chunks_meta, embedder

def rebuild_index():
    # Delete old index files and rebuild
    if INDEX_PATH.exists():
        INDEX_PATH.unlink()
    if META_PATH.exists():
        META_PATH.unlink()
    return build_or_load_index()

def retrieve(query: str, k: int = 5) -> List[Dict[str, Any]]:
    index, meta, embedder = build_or_load_index()
    q = embedder.encode([query], normalize_embeddings=True)
    q = np.array(q, dtype="float32")
    # # Prefer diversity across sources: keep best 3 from risk policy, best 2 from rate policy
    # risk = [r for r in results if "Overall Risk" in r["source"]][:3]
    # rate = [r for r in results if "Interest Rate" in r["source"]][:2]
    # results = risk + rate

    scores, ids = index.search(q, k)
    results = []
    for rank, idx in enumerate(ids[0]):
        if idx == -1:
            continue
        m = meta[idx]
        results.append({
            "rank": rank + 1,
            "score": float(scores[0][rank]),
            "chunk_id": m["chunk_id"],
            "source": m["source"],
            "text": m["text"],
        })
    return results
