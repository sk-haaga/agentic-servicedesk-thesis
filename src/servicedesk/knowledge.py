"""SOP knowledge base: loading, vector index (ChromaDB) and similarity search."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
import yaml

from .config import KB_DIR, RUNTIME_DIR
from .schemas import RetrievedSOP


@dataclass
class SOP:
    sop_id: str
    title: str
    applications: list[str]
    symptoms: str
    text: str


def load_sops(kb_dir: Path = KB_DIR) -> list[SOP]:
    sops = []
    for path in sorted(kb_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
        meta, body = (yaml.safe_load(m.group(1)), m.group(2)) if m else ({"id": path.stem, "title": path.stem}, raw)
        sops.append(SOP(meta["id"], meta.get("title", ""), meta.get("applications", []), meta.get("symptoms", ""), body.strip()))
    return sops


class KnowledgeBase:
    """Vector index of SOPs. Embeddings come from the configured LLM provider, so the same code works
    with Azure OpenAI embeddings and with the offline hashing embeddings of the fake provider."""

    def __init__(self, llm, kb_dir: Path = KB_DIR, persist_dir: Path | None = None):
        self.llm = llm
        self.sops = {s.sop_id: s for s in load_sops(kb_dir)}
        path = persist_dir or RUNTIME_DIR / f"chroma_{llm.name}"
        path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(path))
        name = f"sops_{llm.name}"
        self.col = self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
        if self.col.count() != len(self.sops):
            self._rebuild(name)

    def _index_text(self, s: SOP) -> str:
        return f"{s.title}\nApplies to: {', '.join(s.applications)}\nSymptoms: {s.symptoms}\n{s.text}"

    def _rebuild(self, name: str) -> None:
        self.client.delete_collection(name)
        self.col = self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
        ids = list(self.sops)
        docs = [self._index_text(self.sops[i]) for i in ids]
        self.col.add(ids=ids, documents=docs, embeddings=self.llm.embed(docs),
                     metadatas=[{"title": self.sops[i].title} for i in ids])

    def search(self, query: str, k: int = 3) -> list[RetrievedSOP]:
        res = self.col.query(query_embeddings=self.llm.embed([query]), n_results=min(k, len(self.sops)))
        out = []
        for sid, dist in zip(res["ids"][0], res["distances"][0]):
            s = self.sops[sid]
            out.append(RetrievedSOP(sop_id=sid, title=s.title, similarity=round(1 - float(dist), 4), text=s.text))
        return out
