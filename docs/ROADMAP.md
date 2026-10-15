# Roadmap from Pilot to Evaluation-Ready Engineering Tool

## Stage 1 — Current pilot
PDF text ingestion, local TF-IDF retrieval, citations, candidate entity inventory, comparison, and JSON/CSV export.

## Stage 2 — Stronger architecture extraction
- Parse headings and tables using layout-aware extraction.
- Add configurable entity dictionaries and AUTOSAR-specific naming conventions.
- Add human correction/review interface and export reviewed labels.
- Support OCR for scanned documents with confidence and page-level quality checks.
- Add graph representation for component → port → interface → signal relationships.

## Stage 3 — RAG quality
- Benchmark approved local embedding models (BGE/E5) on engineer-labelled query/evidence pairs.
- Add FAISS or ChromaDB persistent project collections with metadata filtering.
- Add an approved local LLM only after groundedness, citation precision, latency, and security benchmarks.
- Enforce context-only answers, refusal when evidence is insufficient, and citation validation.

## Stage 4 — Enterprise controls
- Enterprise SSO, RBAC, project isolation, immutable audit events, retention policy, encrypted storage, and secrets management.
- Containerized deployment, monitoring, backups, and dependency scanning.
- Approval and revision lifecycle integration.

## Stage 5 — Validation and governance
- Establish representative and version-controlled HLD benchmark set.
- Have two engineers label gold entities and evidence passages; adjudicate disagreements.
- Track precision, recall, F1, citation validity, answer groundedness, latency, and user acceptance.
- Keep formal design approval and vehicle validation outside the assistant.
