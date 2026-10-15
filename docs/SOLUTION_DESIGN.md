# Solution Design — AUTOSAR InsightAI

## 1. Problem statement

AUTOSAR HLD documents can be long and difficult to search. Manual interpretation can make it harder to identify components, ports/interfaces, signals, dependencies, inconsistencies, and downstream test implications. The reference case study proposes a secure AI assistant that organizes architecture knowledge and returns traceable evidence.

## 2. Pilot scope

| Capability | Implementation |
|---|---|
| PDF ingestion | PyMuPDF text extraction with page numbering |
| Chunking | Page-preserving chunks with overlap |
| Semantic-like search | Local TF-IDF cosine similarity |
| Cited Q&A | Ranked evidence passages and explicit citations |
| Architecture inventory | Rule-based candidate extraction |
| Dependency candidates | Text-pattern extraction with source page |
| Revision comparison | TF-IDF similarity threshold and candidate additions/removals |
| Exports | JSON and CSV |
| UI / API | Streamlit / FastAPI |

## 3. Data model

- **Document:** UUID, source filename, SHA-256, page count, extracted character count.
- **Chunk:** document UUID, source filename, page, chunk index, text.
- **Entity:** type, name, source page(s); candidate dependency records also contain evidence text.
- **Query evidence:** document ID, source filename, page, retrieval score, source passage.

## 4. Evidence and confidence

Retrieval score is a ranking score, not a calibrated probability of truth. The system returns the source passage and page number, and avoids synthesizing an answer when no passage exceeds a minimum score. Engineers must verify whether the cited text supports the interpretation.

## 5. Security and privacy controls in this pilot

- Local processing; no external LLM/API call.
- 20 MB upload limit and 800-page cap.
- PDF extension and file signature validation.
- Safe parser use; uploaded files are not executed.
- No persistent upload directory; documents live in API process memory.
- CORS restricted to local Streamlit origins.
- SHA-256 provenance metadata.
- Explicit warning that authentication, RBAC, encryption-at-rest, and audit persistence are not yet implemented.

For real engineering data, use an approved isolated environment, add identity and project-level authorization, protect logs, implement retention controls, and complete a security review before deployment.

## 6. Non-functional goals

- Reproducible local execution.
- Page-level traceability for retrieved evidence.
- Deterministic baseline retrieval.
- Clear error messages for unsupported or scanned-only PDFs.
- Testable core logic separated from UI and HTTP routes.

## 7. Out of scope

- Automatic architecture approval.
- Formal AUTOSAR conformance verification.
- Complete ARXML/metamodel parsing.
- OCR and diagram understanding.
- Guaranteed extraction from complex tables.
- Automatic modification of source documents.
- Production multi-user access control.
