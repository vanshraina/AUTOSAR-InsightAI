# AUTOSAR InsightAI — HLD Document Analysis Assistant

**Case Study 1 | Automotive Engineering AI | Pilot implementation**

A local-first prototype for extracting, organizing, searching, and comparing architecture knowledge in AUTOSAR High-Level Design (HLD) documents. It follows the case-study workflow: document ingestion → page-aware chunking → local retrieval → cited answers → entity inventory → revision comparison → export.

> **Engineering boundary:** This is a decision-support prototype, not an AUTOSAR conformance checker and not an architecture approval tool. Results are candidates for review by a qualified engineer. The included sample HLD is synthetic and contains no proprietary OEM data.

## What is implemented

- PDF upload and text extraction with page metadata.
- Context-aware, page-preserving chunks.
- Local TF-IDF retrieval (no cloud API or API key required).
- Evidence-grounded Q&A with page citations and an explicit “insufficient evidence” response.
- Candidate architecture entity extraction for software components, interfaces/ports, signals, and dependencies.
- Document inventory and source-page traceability.
- Two-document revision comparison (added/removed/changed page-level chunks).
- JSON/CSV export for extracted entities and findings.
- FastAPI backend and Streamlit engineering UI.
- File-type and size validation, safe temporary storage, request validation, tests, evaluation dataset, and metric definitions.

## Architecture

```text
Engineer
  │
  ▼
Streamlit UI ──HTTP/JSON──► FastAPI service
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
              PDF ingestion        Retrieval / analysis
          PyMuPDF + page IDs       TF-IDF + entity rules
                    │                     │
                    └──────────┬──────────┘
                               ▼
                  Cited evidence / JSON exports
```

The reference case study suggests an approved local LLM, BGE/E5 embeddings, ChromaDB/FAISS, and optional PostgreSQL. This pilot deliberately uses local TF-IDF retrieval so it can be evaluated and run without model downloads or credentials. `docs/ROADMAP.md` describes the upgrade path.

## Quick start (Windows PowerShell)

1. Install Python 3.10 or newer.
2. Extract the ZIP and open a terminal in this folder.
3. Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. Start the API in terminal 1:

```powershell
uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```

5. Start the UI in terminal 2:

```powershell
streamlit run app/ui.py
```

6. Open the local Streamlit URL shown in the terminal. The API health endpoint is `http://127.0.0.1:8000/health`; interactive API documentation is at `http://127.0.0.1:8000/docs`.

## Quick start (Linux/macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
# in another terminal
streamlit run app/ui.py
```

## Run tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Try the included sample

Use `data/sample_hld/sample_autosar_hld.pdf` in the UI. It is a synthetic mini-HLD created for demonstrating the workflow. Ask questions such as:
- “Which components publish vehicle speed?”
- “What does the VehicleSpeed interface connect?”
- “Which dependencies involve BrakeController?”
- “Summarize the signal routing.”

Citations point to page numbers in the ingested document. A cited passage is evidence, not a guarantee of correctness.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness and loaded-document count |
| `POST` | `/documents/upload` | Ingest a PDF |
| `GET` | `/documents` | List ingested documents |
| `GET` | `/documents/{document_id}/entities` | Extract candidate architecture entities |
| `POST` | `/query` | Search evidence and answer a question |
| `POST` | `/documents/compare` | Compare two ingested revisions |
| `GET` | `/documents/{document_id}/architecture` | Candidate entities and evidence-backed relationship graph |
| `GET` | `/documents/{document_id}/impact?entity_name=...` | Direct relationship review for a named entity |
| `GET` | `/documents/{document_id}/inconsistencies` | Heuristic review candidates |
| `GET` | `/documents/{document_id}/export/entities.csv` | Export entity inventory |
| `GET` | `/documents/{document_id}/export/entities.json` | Export entity inventory |

Example upload:

```bash
curl -F "file=@data/sample_hld/sample_autosar_hld.pdf" http://127.0.0.1:8000/documents/upload
```

Example query:

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Which components publish vehicle speed?","document_id":"PASTE_DOCUMENT_ID"}'
```

## Project layout

```text
app/
  api.py             FastAPI endpoints
  core.py            ingestion, retrieval, extraction, comparison
  schemas.py         typed request/response models
  ui.py              Streamlit interface
tests/               automated tests
data/sample_hld/     synthetic sample PDF
data/evaluation/     evaluation dataset and metrics
docs/                design, threat controls, evaluation, roadmap
scripts/             sample-data generator
```

## Evaluation discipline

The supplied evaluation examples and expected answers are **starter fixtures**, not independently validated benchmark results. Run `python scripts/run_evaluation.py` after installing dependencies to produce `data/evaluation/evaluation_results.json`. Report measured precision/recall and citation validity from the run; do not claim business impact or accuracy without a representative engineer-labelled HLD set.

## Reference sample documents

Additional synthetic reference HLD PDFs are available under `data/sample_hld/reference_samples/`. The uploaded reference implementation review is documented in `docs/REFERENCE_IMPLEMENTATION_REVIEW.md`.

## Limitations and next steps

- Text-based PDFs are supported; scanned PDFs require OCR (e.g., Tesseract) and are not silently treated as successfully parsed.
- Tables and diagrams may need specialized parsers and human verification.
- Entity extraction is rule-based and returns candidate entities; it is not a complete AUTOSAR metamodel parser.
- Retrieval is local and deterministic; answer generation is extractive rather than LLM-generated.
- No authentication or multi-tenant RBAC is included in this educational pilot. Run only on trusted local systems with approved documents.
- No automatic architecture approval or source-document modification is performed.
