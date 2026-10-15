from __future__ import annotations

import csv
import io
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core import DocumentStore, answer_question, extract_entities, compare_documents, build_architecture_graph, analyze_impact, detect_inconsistencies
from app.schemas import QueryRequest, QueryResponse, UploadResponse, CompareRequest

app = FastAPI(
    title="AUTOSAR InsightAI API",
    description="Local-first, evidence-grounded AUTOSAR HLD analysis pilot.",
    version="1.0.0",
)
# Local pilot only. Tighten origins before any network-facing deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
store = DocumentStore()


@app.get("/health")
def health():
    return {"status": "ok", "service": "AUTOSAR InsightAI", "loaded_documents": len(store.documents)}


@app.post("/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename or "uploaded.pdf"
    try:
        data = await file.read()
        doc = store.add_pdf(filename, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()
    return UploadResponse(
        document_id=doc.document_id, filename=doc.filename, pages=doc.pages,
        chunks=len(doc.chunks), message="PDF ingested. Review extracted content and citations before use.",
    )


@app.get("/documents")
def list_documents():
    return {"documents": store.list_documents()}


@app.get("/documents/{document_id}/entities")
def get_entities(document_id: str):
    try:
        return extract_entities(store, document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    try:
        result = answer_question(store, request.question, request.document_id, request.top_k)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@app.post("/documents/compare")
def compare(request: CompareRequest):
    try:
        return compare_documents(store, request.document_a_id, request.document_b_id, request.similarity_threshold)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/documents/{document_id}/export/entities.json")
def export_entities_json(document_id: str):
    try:
        return JSONResponse(extract_entities(store, document_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/documents/{document_id}/export/entities.csv")
def export_entities_csv(document_id: str):
    try:
        entities = extract_entities(store, document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["entity_type", "name", "pages", "evidence_or_relationship"])
    for kind in ("components", "interfaces", "signals"):
        for item in entities[kind]:
            writer.writerow([kind[:-1] if kind.endswith("s") else kind, item["name"], ",".join(map(str, item["pages"])), ""])
    for item in entities["dependencies"]:
        writer.writerow(["dependency", item["source"], item["page"], f'{item["relationship"]}: {item["target"]}; evidence={item["evidence"]}'])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{entities["metadata"]["filename"]}_entities.csv"'},
    )


@app.get("/documents/{document_id}/architecture")
def architecture_graph(document_id: str):
    try:
        return build_architecture_graph(store, document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/documents/{document_id}/impact")
def impact_analysis(document_id: str, entity_name: str):
    try:
        return analyze_impact(store, document_id, entity_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/documents/{document_id}/inconsistencies")
def inconsistencies(document_id: str):
    try:
        return detect_inconsistencies(store, document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
