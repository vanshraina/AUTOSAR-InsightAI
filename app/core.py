"""Core local-first HLD ingestion, retrieval, entity extraction, and comparison."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib
import re
import uuid

import fitz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


MAX_PDF_BYTES = 20 * 1024 * 1024
CHUNK_CHARS = 1100
CHUNK_OVERLAP = 140


@dataclass
class Chunk:
    document_id: str
    document_name: str
    page: int
    chunk_index: int
    text: str


@dataclass
class Document:
    document_id: str
    filename: str
    sha256: str
    pages: int
    chunks: list[Chunk]
    extracted_text_chars: int


class DocumentStore:
    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}

    def add_pdf(self, filename: str, data: bytes) -> Document:
        if not filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF documents are supported.")
        if not data:
            raise ValueError("The uploaded file is empty.")
        if len(data) > MAX_PDF_BYTES:
            raise ValueError(f"PDF exceeds the {MAX_PDF_BYTES // (1024 * 1024)} MB limit.")
        if not data.startswith(b"%PDF-"):
            raise ValueError("The uploaded file does not have a valid PDF signature.")

        try:
            pdf = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise ValueError("The PDF could not be opened. It may be corrupted or encrypted.") from exc

        if pdf.page_count == 0:
            raise ValueError("The PDF contains no pages.")
        if pdf.page_count > 800:
            raise ValueError("PDF exceeds the 800-page pilot limit.")

        doc_id = str(uuid.uuid4())
        chunks: list[Chunk] = []
        all_chars = 0
        try:
            for page_index, page in enumerate(pdf, start=1):
                text = normalize_text(page.get_text("text"))
                all_chars += len(text)
                if not text.strip():
                    continue
                for chunk_index, chunk_text in enumerate(split_text(text), start=1):
                    chunks.append(Chunk(doc_id, filename, page_index, chunk_index, chunk_text))
        finally:
            pdf.close()

        if not chunks:
            raise ValueError(
                "No selectable text was found. This pilot needs a text-based PDF; OCR support is not enabled."
            )

        doc = Document(
            document_id=doc_id,
            filename=Path(filename).name,
            sha256=hashlib.sha256(data).hexdigest(),
            pages=pdf_page_count(data),
            chunks=chunks,
            extracted_text_chars=all_chars,
        )
        self.documents[doc_id] = doc
        return doc

    def get(self, document_id: str) -> Document:
        if document_id not in self.documents:
            raise KeyError("Document not found. Upload it again or select an ingested document.")
        return self.documents[document_id]

    def list_documents(self) -> list[dict[str, Any]]:
        return [{
            "document_id": d.document_id,
            "filename": d.filename,
            "sha256": d.sha256,
            "pages": d.pages,
            "chunks": len(d.chunks),
            "extracted_text_chars": d.extracted_text_chars,
        } for d in self.documents.values()]


def pdf_page_count(data: bytes) -> int:
    with fitz.open(stream=data, filetype="pdf") as pdf:
        return pdf.page_count


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, max_chars: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text on paragraph/sentence boundaries while preserving a small overlap."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if boundary > start + int(max_chars * 0.55):
                end = boundary + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _requested_case_study(question: str) -> int | None:
    """Return an explicitly requested case-study number, if present."""
    patterns = [
        r"\bcase\s*study\s*(?:number\s*)?(1|2|3|4|5)\b",
        r"\bcase\s*study\s*(?:no\.?\s*)?(one|two|three|four|five)\b",
    ]
    match = re.search(patterns[0], question, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(patterns[1], question, flags=re.IGNORECASE)
    if match:
        return {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}[match.group(1).lower()]
    return None


def _filter_to_case_study(chunks: list[Chunk], case_number: int) -> list[Chunk]:
    """Filter to the body of a numbered case study, ignoring contents-page mentions.

    The source PDF lists all five case studies in its table of contents on page 2.
    Therefore, the first occurrence of "Case Study N" is not a reliable section
    boundary. A real section start must also contain the section's body markers
    (Project Overview and Business Context) on that PDF page. If we cannot locate
    both the requested section and a later section boundary reliably, fail closed.
    """
    heading = re.compile(r"(?im)^\s*Case\s+Study\s+([1-5])\b")
    by_page: dict[int, list[Chunk]] = {}
    for chunk in chunks:
        by_page.setdefault(chunk.page, []).append(chunk)
    page_text: dict[int, str] = {}
    for page, page_chunks in by_page.items():
        # Chunks overlap, so de-duplicate their text when building page-level signals.
        ordered = sorted(page_chunks, key=lambda c: c.chunk_index)
        combined = ""
        for c in ordered:
            piece = c.text
            if not combined:
                combined = piece
            elif piece and piece not in combined:
                # split_text uses a small overlap; append only the non-overlapping tail.
                overlap_len = min(len(combined), len(piece))
                while overlap_len > 0 and not combined.endswith(piece[:overlap_len]):
                    overlap_len -= 1
                combined += piece[overlap_len:]
        page_text[page] = combined

    starts: dict[int, int] = {}
    for page, text in page_text.items():
        matches = list(heading.finditer(text))
        if not matches:
            continue
        # Contents pages mention many headings but lack these section-body markers.
        if not re.search(r"Project\s+Overview", text, re.IGNORECASE):
            continue
        if not re.search(r"Business\s+Context", text, re.IGNORECASE):
            continue
        # A real section page should identify one case-study heading, not a TOC list.
        numbers = {int(m.group(1)) for m in matches}
        if numbers == {case_number}:
            starts[case_number] = page if case_number not in starts else min(starts[case_number], page)
        for number in numbers:
            if number not in starts:
                starts[number] = page

    if case_number not in starts:
        return []
    start_page = starts[case_number]
    later_starts = [page for number, page in starts.items() if number > case_number and page > start_page]
    if case_number < 5 and not later_starts:
        # Do not let an unrecognized section boundary cause cross-case retrieval.
        return []
    end_page = min(later_starts) if later_starts else max(by_page) + 1
    filtered = [chunk for chunk in chunks if start_page <= chunk.page < end_page]
    # Trim any leading contents/preceding text before the actual requested heading.
    cleaned: list[Chunk] = []
    for chunk in filtered:
        if chunk.page == start_page:
            matches = list(heading.finditer(chunk.text))
            target = next((m for m in matches if int(m.group(1)) == case_number), None)
            if target:
                chunk = Chunk(chunk.document_id, chunk.document_name, chunk.page, chunk.chunk_index, chunk.text[target.start():])
        cleaned.append(chunk)
    return cleaned


def retrieve(store: DocumentStore, question: str, document_id: str | None = None, top_k: int = 5) -> list[dict[str, Any]]:
    if document_id:
        documents = [store.get(document_id)]
    else:
        documents = list(store.documents.values())
    corpus = [chunk for doc in documents for chunk in doc.chunks]
    requested_case = _requested_case_study(question)
    if requested_case is not None:
        corpus = _filter_to_case_study(corpus, requested_case)
    if not corpus:
        return []
    texts = [c.text for c in corpus]
    # Word + character features make retrieval more robust to identifiers and spelling variants.
    vectorizer = TfidfVectorizer(
        lowercase=True, ngram_range=(1, 2), sublinear_tf=True,
        token_pattern=r"(?u)\b[\w.-]+\b", strip_accents="unicode",
    )
    try:
        matrix = vectorizer.fit_transform(texts + [question])
        scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    except ValueError:
        return []
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)[:top_k]
    results = []
    for index, score in ranked:
        if float(score) < 0.05:
            continue
        chunk = corpus[index]
        results.append({
            "document_id": chunk.document_id,
            "document_name": chunk.document_name,
            "page": chunk.page,
            "score": round(float(score), 4),
            "text": chunk.text,
        })
    return results


def answer_question(store: DocumentStore, question: str, document_id: str | None = None, top_k: int = 5) -> dict[str, Any]:
    requested_case = _requested_case_study(question)
    evidence = retrieve(store, question, document_id, top_k)
    if not evidence:
        return {
            "question": question,
            "answer": "I could not find sufficient evidence in the ingested HLD documents to answer this question. Try using a component, interface, signal, or section name that appears in the document.",
            "evidence": [],
            "grounded": False,
            "note": (f"No relevant passage was found in Case Study {requested_case}; section-scoped retrieval was applied. " if requested_case is not None else "No relevant passage exceeded the minimum retrieval threshold. ") + "No answer was inferred.",
        }
    snippets = []
    for item in evidence[:3]:
        excerpt = re.sub(r"\s+", " ", item["text"]).strip()
        if len(excerpt) > 650:
            excerpt = excerpt[:647].rsplit(" ", 1)[0] + "..."
        snippets.append(f"[{item['document_name']}, p. {item['page']}] {excerpt}")
    return {
        "question": question,
        "answer": "The most relevant source passages are listed below. Use them as evidence and verify the interpretation with the architecture owner:\n\n" + "\n\n".join(snippets),
        "evidence": evidence,
        "grounded": True,
        "note": "Extractive evidence response; not an LLM-generated conclusion. Citations refer to source PDF pages.",
    }


def extract_entities(store: DocumentStore, document_id: str) -> dict[str, list[dict[str, Any]]]:
    doc = store.get(document_id)
    components: dict[str, set[int]] = {}
    interfaces: dict[str, set[int]] = {}
    signals: dict[str, set[int]] = {}
    dependencies: list[dict[str, Any]] = []

    comp_patterns = [
        re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Component|Manager|Controller|Service|Gateway|Monitor|Handler))\b"),
        re.compile(r"\b(SWC_[A-Za-z0-9_]+)\b"),
    ]
    interface_pattern = re.compile(r"\b((?:I|P|R)?Port_[A-Za-z0-9_]+|[A-Z][A-Za-z0-9]*Interface)\b")
    signal_pattern = re.compile(r"\b((?:Vehicle|Engine|Brake|Wheel|Steering|Battery|Door|Cabin)[A-Z][A-Za-z0-9]*(?:Signal|Status|Speed|Torque|Temperature|Pressure|Request|Command))\b")
    dependency_pattern = re.compile(
        r"\b([A-Z][A-Za-z0-9]*(?:Component|Manager|Controller|Service|Gateway|Monitor|Handler))\s+"
        r"(?:depends on|uses|consumes from|receives from|communicates with|publishes to|sends to)\s+"
        r"([A-Z][A-Za-z0-9]*(?:Component|Manager|Controller|Service|Gateway|Monitor|Handler))\b",
        re.IGNORECASE,
    )

    for chunk in doc.chunks:
        text = chunk.text
        for pattern in comp_patterns:
            for match in pattern.finditer(text):
                name = match.group(1)
                components.setdefault(name, set()).add(chunk.page)
        for match in interface_pattern.finditer(text):
            interfaces.setdefault(match.group(1), set()).add(chunk.page)
        for match in signal_pattern.finditer(text):
            signals.setdefault(match.group(1), set()).add(chunk.page)
        for match in dependency_pattern.finditer(text):
            dependencies.append({
                "source": match.group(1), "relationship": "text-stated dependency",
                "target": match.group(2), "page": chunk.page,
                "evidence": match.group(0),
            })

    return {
        "components": [{"name": n, "pages": sorted(p)} for n, p in sorted(components.items())],
        "interfaces": [{"name": n, "pages": sorted(p)} for n, p in sorted(interfaces.items())],
        "signals": [{"name": n, "pages": sorted(p)} for n, p in sorted(signals.items())],
        "dependencies": dependencies,
        "metadata": {
            "document_id": doc.document_id, "filename": doc.filename, "sha256": doc.sha256,
            "pages": doc.pages, "extracted_text_chars": doc.extracted_text_chars,
            "disclaimer": "Rule-based candidate extraction; validate all entities and relationships against the source.",
        },
    }


def compare_documents(store: DocumentStore, a_id: str, b_id: str, threshold: float = 0.72) -> dict[str, Any]:
    a, b = store.get(a_id), store.get(b_id)
    a_texts = [c.text for c in a.chunks]
    b_texts = [c.text for c in b.chunks]
    if not a_texts and not b_texts:
        return {"document_a": a.filename, "document_b": b.filename, "added": [], "removed": [], "similarity_threshold": threshold}
    if not a_texts:
        return {"document_a": a.filename, "document_b": b.filename, "added": [{"page": c.page, "text": c.text[:250]} for c in b.chunks], "removed": [], "similarity_threshold": threshold}
    if not b_texts:
        return {"document_a": a.filename, "document_b": b.filename, "added": [], "removed": [{"page": c.page, "text": c.text[:250]} for c in a.chunks], "similarity_threshold": threshold}
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), token_pattern=r"(?u)\b[\w.-]+\b")
    matrix = vectorizer.fit_transform(a_texts + b_texts)
    sim = cosine_similarity(matrix[len(a_texts):], matrix[:len(a_texts)])
    best_a_for_b = sim.argmax(axis=1)
    best_b_for_a = sim.argmax(axis=0)
    added = []
    matched_a = set()
    for j, best_i in enumerate(best_a_for_b):
        score = float(sim[j, best_i])
        if score < threshold:
            added.append({"page": b.chunks[j].page, "similarity": round(score, 3), "text": b.chunks[j].text[:300]})
        else:
            matched_a.add(int(best_i))
    removed = []
    for i, best_j in enumerate(best_b_for_a):
        score = float(sim[best_j, i])
        if score < threshold:
            removed.append({"page": a.chunks[i].page, "similarity": round(score, 3), "text": a.chunks[i].text[:300]})
    return {
        "document_a": a.filename, "document_b": b.filename,
        "added": added, "removed": removed, "similarity_threshold": threshold,
        "method": "TF-IDF cosine similarity; possible changes require engineer confirmation.",
    }


# Architecture graph and consistency checks, informed by the uploaded reference implementation.
def build_architecture_graph(store: DocumentStore, document_id: str) -> dict[str, Any]:
    """Return candidate entities and text-supported relationships with page-level evidence."""
    doc = store.get(document_id)
    entities = extract_entities(store, document_id)
    all_entities = []
    for kind in ("components", "interfaces", "signals"):
        for item in entities[kind]:
            all_entities.append({"type": kind[:-1] if kind.endswith("s") else kind,
                                 "name": item["name"], "pages": item["pages"]})
    relationships = []
    seen = set()
    for chunk in doc.chunks:
        text = chunk.text
        components = [e["name"] for e in all_entities if e["type"] == "component" and e["name"] in text]
        interfaces = [e["name"] for e in all_entities if e["type"] == "interface" and e["name"] in text]
        signals = [e["name"] for e in all_entities if e["type"] == "signal" and e["name"] in text]
        for comp in components:
            for interface in interfaces:
                key = (comp, "mentions_interface", interface, chunk.page)
                if key not in seen:
                    seen.add(key); relationships.append({"source": comp, "relation": "mentions_interface", "target": interface, "page": chunk.page, "evidence": text[:500], "evidence_status": "text co-occurrence; verify semantics"})
            for signal in signals:
                key = (comp, "mentions_signal", signal, chunk.page)
                if key not in seen:
                    seen.add(key); relationships.append({"source": comp, "relation": "mentions_signal", "target": signal, "page": chunk.page, "evidence": text[:500], "evidence_status": "text co-occurrence; verify semantics"})
        for match in re.finditer(r"\b([A-Z][A-Za-z0-9]*(?:Component|Manager|Controller|Service|Gateway|Monitor|Handler))\s+(?:depends on|uses|consumes from|receives from|communicates with|publishes to|sends to)\s+([A-Z][A-Za-z0-9]*(?:Component|Manager|Controller|Service|Gateway|Monitor|Handler))\b", text, re.I):
            key = (match.group(1), "text_stated_dependency", match.group(2), chunk.page)
            if key not in seen:
                seen.add(key); relationships.append({"source": match.group(1), "relation": "text_stated_dependency", "target": match.group(2), "page": chunk.page, "evidence": match.group(0), "evidence_status": "explicit text pattern; engineer review required"})
    return {"document": doc.filename, "document_id": doc.document_id, "entities": all_entities,
            "relationships": relationships,
            "note": "Relationships are candidates extracted from text, not a formal AUTOSAR model or verified architecture graph."}


def analyze_impact(store: DocumentStore, document_id: str, entity_name: str) -> dict[str, Any]:
    graph = build_architecture_graph(store, document_id)
    related = [r for r in graph["relationships"] if r["source"].lower() == entity_name.lower() or r["target"].lower() == entity_name.lower()]
    neighbors = sorted({r["target"] if r["source"].lower() == entity_name.lower() else r["source"] for r in related})
    return {"entity": entity_name, "document": graph["document"], "direct_relationships": related,
            "directly_related_entities": neighbors,
            "potential_impact": "Review the directly related entities and their cited passages. No transitive or safety impact is asserted by this prototype.",
            "status": "REQUIRES_ENGINEER_REVIEW"}


def detect_inconsistencies(store: DocumentStore, document_id: str) -> dict[str, Any]:
    """Conservative lexical checks; report candidates, never claim formal conformance failure."""
    doc = store.get(document_id)
    graph = build_architecture_graph(store, document_id)
    findings = []
    # Flag signals that appear in relationship/architecture language but do not match any extracted signal candidate.
    known = {e["name"].lower() for e in graph["entities"] if e["type"] == "signal"}
    for chunk in doc.chunks:
        for match in re.finditer(r"\b([A-Z][A-Za-z0-9]*(?:Signal|Status|Speed|Torque|Temperature|Pressure|Request|Command))\b", chunk.text):
            candidate = match.group(1)
            if candidate.lower() not in known:
                findings.append({"type": "unclassified_signal_reference", "severity": "low", "entity": candidate,
                                 "page": chunk.page, "evidence": chunk.text[:400],
                                 "recommendation": "Confirm whether this token is a valid signal/entity and add it to the approved project taxonomy if applicable."})
    # Duplicate definitions are only candidates because text-only extraction cannot distinguish mention from definition.
    for kind in ("components", "interfaces", "signals"):
        for item in graph["entities"]:
            if item["type"] == kind[:-1]:
                pages = item.get("pages", [])
                if len(pages) > 1:
                    findings.append({"type": "multi_page_reference_review", "severity": "info", "entity": item["name"],
                                     "pages": pages, "evidence": f"Entity appears on pages {pages}.",
                                     "recommendation": "Check whether repeated mentions are consistent; repeated mentions alone are not an inconsistency."})
    return {"document": doc.filename, "finding_count": len(findings), "findings": findings,
            "disclaimer": "Heuristic review candidates only. This is not an AUTOSAR conformance checker."}
