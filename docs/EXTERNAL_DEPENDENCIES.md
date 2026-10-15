# External Dependencies and Data Sources

## Runtime dependencies

| Package | Purpose | Network required at runtime? |
|---|---|---|
| FastAPI | REST API and request validation | No |
| Uvicorn | Local ASGI server | No |
| Streamlit | Engineering UI | No |
| PyMuPDF (`pymupdf`) | Text extraction and page metadata from PDFs | No |
| scikit-learn | Local TF-IDF retrieval and cosine similarity | No |
| Pydantic | Typed request/response schemas | No |
| requests | UI-to-API HTTP requests | Local network only |
| pandas | UI tables | No |
| python-multipart | PDF upload handling | No |

Exact compatible version ranges are declared in `requirements.txt`. Install packages from an approved package index or internal mirror according to your organization's policy.

## External services / APIs

- No hosted LLM API is called.
- No external embedding API is called.
- No telemetry or analytics service is intentionally configured.
- No user account or cloud storage is required.

## Included data

`data/sample_hld/sample_autosar_hld.pdf` is a synthetic demo artifact generated from `sample_hld_content.txt`. It is not an OEM HLD, AUTOSAR standard, or production engineering source.

## Licensing and use

Review dependency licenses and your organization's software-supply-chain requirements before distribution. Only ingest HLD documents and engineering artifacts that you are authorized to use. Do not add proprietary OEM documents to a public repository.
