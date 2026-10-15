# Reference Implementation Review and Adaptation

The uploaded reference ZIP contains a FastAPI service, Streamlit interface, PDF ingestion/chunking, Ollama client, TF-IDF/Chroma retrieval paths, regex-based entity extraction, relationship candidates, entity-set comparison, direct impact analysis, prompt configuration, synthetic HLDs, evaluation fixtures, and documentation artifacts.

This project adopts the useful modular workflow while keeping its original API/UI operational. The added endpoints provide candidate architecture graph relationships, direct impact review, and heuristic inconsistency candidates.

## Important engineering distinctions
- Text co-occurrence is not proof that a component owns or uses an interface/signal.
- A lexical revision difference is not automatically a semantic change.
- Directly related entities are not a validated transitive impact analysis.
- Repeated entity mentions are not automatically inconsistencies.
- Synthetic evaluation fixtures cannot support production accuracy claims.
- The reference's local Ollama/Chroma settings are optional design directions; this baseline does not silently require a model download or remote API.

## New API endpoints
- `GET /documents/{document_id}/architecture`
- `GET /documents/{document_id}/impact?entity_name=BrakeController`
- `GET /documents/{document_id}/inconsistencies`

## Included reference samples
Synthetic reference PDFs from the provided bundle are copied into `data/sample_hld/reference_samples/` for local comparison and demonstration. Use only documents you are authorized to process.
