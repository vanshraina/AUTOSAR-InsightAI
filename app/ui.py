from __future__ import annotations

import json
import os
import requests
import streamlit as st
import pandas as pd

API_URL = os.getenv("AUTOSAR_INSIGHTAI_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AUTOSAR InsightAI", page_icon="🚘", layout="wide")
st.title("AUTOSAR InsightAI")
st.caption("High-Level Design document analysis assistant · local-first evaluation pilot")
st.info("Decision support only. Validate extracted entities, relationships, and cited passages with an authorized architecture engineer.")

def api_get(path):
    return requests.get(f"{API_URL}{path}", timeout=30)

def api_post(path, **kwargs):
    return requests.post(f"{API_URL}{path}", timeout=120, **kwargs)

try:
    health = api_get("/health").json()
    st.sidebar.success(f"API connected · {health['loaded_documents']} document(s) loaded")
except requests.RequestException:
    st.error(f"Cannot connect to the API at {API_URL}. Start it with `uvicorn app.api:app --reload --port 8000`.")
    st.stop()

tab_upload, tab_qa, tab_inventory, tab_compare, tab_graph = st.tabs(["1 · Ingest HLD", "2 · Ask with citations", "3 · Architecture inventory", "4 · Compare revisions", "5 · Impact & quality checks"])

with tab_upload:
    st.subheader("Controlled PDF ingestion")
    uploaded = st.file_uploader("Upload a text-based AUTOSAR HLD PDF (max 20 MB)", type=["pdf"])
    if uploaded and st.button("Ingest document", type="primary"):
        with st.spinner("Extracting page text and building local search index…"):
            try:
                response = api_post("/documents/upload", files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")})
                if response.ok:
                    result = response.json()
                    st.success(result["message"])
                    st.json(result)
                else:
                    st.error(response.json().get("detail", response.text))
            except requests.RequestException as exc:
                st.error(f"Upload failed: {exc}")
    docs = api_get("/documents").json().get("documents", [])
    if docs:
        st.subheader("Ingested document register")
        st.dataframe(pd.DataFrame(docs), use_container_width=True, hide_index=True)
    else:
        st.warning("No documents loaded yet. Start with the included synthetic sample PDF.")

with tab_qa:
    st.subheader("Evidence-grounded architecture search")
    docs = api_get("/documents").json().get("documents", [])
    if not docs:
        st.warning("Ingest a PDF first.")
    else:
        options = {"All ingested documents": ""}
        options.update({f"{d['filename']} · {d['pages']} pages": d["document_id"] for d in docs})
        selected_label = st.selectbox("Search scope", list(options.keys()))
        question = st.text_input("Question", placeholder="Which components publish vehicle speed?")
        top_k = st.slider("Evidence passages", min_value=1, max_value=10, value=5)
        if st.button("Find evidence", type="primary") and question.strip():
            try:
                response = api_post("/query", json={"question": question, "document_id": options[selected_label] or None, "top_k": top_k})
                response.raise_for_status()
                result = response.json()
                st.markdown("#### Response")
                st.write(result["answer"])
                st.caption(result["note"])
                if result["evidence"]:
                    st.markdown("#### Retrieved source passages")
                    for i, item in enumerate(result["evidence"], start=1):
                        with st.expander(f"{i}. {item['document_name']} · page {item['page']} · relevance {item['score']:.3f}"):
                            st.write(item["text"])
                else:
                    st.warning("No evidence passed the retrieval threshold.")
            except requests.RequestException as exc:
                st.error(f"Query failed: {exc}")

with tab_inventory:
    st.subheader("Candidate architecture entities")
    docs = api_get("/documents").json().get("documents", [])
    if not docs:
        st.warning("Ingest a PDF first.")
    else:
        doc_map = {f"{d['filename']} · {d['pages']} pages": d["document_id"] for d in docs}
        label = st.selectbox("Document for inventory", list(doc_map.keys()), key="entity_doc")
        if st.button("Extract inventory"):
            try:
                result = api_get(f"/documents/{doc_map[label]}/entities").json()
                meta = result["metadata"]
                st.caption(f"Source SHA-256: {meta['sha256']} · extracted characters: {meta['extracted_text_chars']}")
                cols = st.columns(3)
                for col, key, heading in zip(cols, ["components", "interfaces", "signals"], ["Components", "Interfaces / Ports", "Signals"]):
                    with col:
                        st.metric(heading, len(result[key]))
                        st.dataframe(pd.DataFrame(result[key]), use_container_width=True, hide_index=True)
                st.markdown("#### Candidate dependencies")
                st.dataframe(pd.DataFrame(result["dependencies"]), use_container_width=True, hide_index=True)
                st.download_button("Download full inventory (JSON)", json.dumps(result, indent=2), file_name="architecture_inventory.json", mime="application/json")
                csv_response = api_get(f"/documents/{doc_map[label]}/export/entities.csv")
                if csv_response.ok:
                    st.download_button("Download inventory (CSV)", csv_response.content, file_name="architecture_inventory.csv", mime="text/csv")
                st.caption(meta["disclaimer"])
            except requests.RequestException as exc:
                st.error(f"Extraction failed: {exc}")

with tab_compare:
    st.subheader("Revision comparison")
    docs = api_get("/documents").json().get("documents", [])
    if len(docs) < 2:
        st.warning("Ingest at least two revisions to compare them.")
    else:
        doc_map = {f"{d['filename']} · {d['document_id'][:8]}": d["document_id"] for d in docs}
        left, right = st.columns(2)
        with left:
            a_label = st.selectbox("Baseline revision", list(doc_map.keys()), key="compare_a")
        with right:
            b_label = st.selectbox("New revision", list(doc_map.keys()), index=1, key="compare_b")
        threshold = st.slider("Similarity threshold", 0.10, 1.0, 0.72, 0.01)
        if st.button("Compare documents", type="primary"):
            if doc_map[a_label] == doc_map[b_label]:
                st.error("Choose two different ingested documents.")
            else:
                try:
                    response = api_post("/documents/compare", json={"document_a_id": doc_map[a_label], "document_b_id": doc_map[b_label], "similarity_threshold": threshold})
                    response.raise_for_status()
                    result = response.json()
                    c1, c2 = st.columns(2)
                    c1.metric("Candidate additions", len(result["added"]))
                    c2.metric("Candidate removals", len(result["removed"]))
                    st.caption(result.get("method", "Review comparison output manually."))
                    st.markdown("#### Candidate additions")
                    st.dataframe(pd.DataFrame(result["added"]), use_container_width=True, hide_index=True)
                    st.markdown("#### Candidate removals")
                    st.dataframe(pd.DataFrame(result["removed"]), use_container_width=True, hide_index=True)
                    st.download_button("Download comparison JSON", json.dumps(result, indent=2), file_name="revision_comparison.json", mime="application/json")
                except requests.RequestException as exc:
                    st.error(f"Comparison failed: {exc}")

st.divider()
st.caption("AUTOSAR InsightAI · Prototype v1.0 · No architecture decision is approved automatically.")


with tab_graph:
    st.subheader("Architecture relationship review")
    docs = api_get("/documents").json().get("documents", [])
    if not docs:
        st.warning("Ingest a PDF first.")
    else:
        doc_map = {f"{d['filename']} · {d['pages']} pages": d["document_id"] for d in docs}
        label = st.selectbox("Analysis document", list(doc_map.keys()), key="graph_doc")
        document_id = doc_map[label]
        left, right = st.columns(2)
        with left:
            if st.button("Build relationship view"):
                try:
                    result = api_get(f"/documents/{document_id}/architecture").json()
                    st.metric("Candidate entities", len(result.get("entities", [])))
                    st.metric("Candidate relationships", len(result.get("relationships", [])))
                    st.dataframe(pd.DataFrame(result.get("relationships", [])), use_container_width=True, hide_index=True)
                    st.download_button("Download graph JSON", json.dumps(result, indent=2), file_name="architecture_graph.json", mime="application/json")
                    st.caption(result.get("note", "Review all candidate relationships."))
                except requests.RequestException as exc:
                    st.error(f"Graph extraction failed: {exc}")
        with right:
            entity_name = st.text_input("Entity for direct impact review", placeholder="BrakeController", key="impact_entity")
            if st.button("Analyze direct impact") and entity_name.strip():
                try:
                    result = api_get(f"/documents/{document_id}/impact", params={"entity_name": entity_name.strip()}).json()
                    st.write(result.get("potential_impact"))
                    st.dataframe(pd.DataFrame(result.get("direct_relationships", [])), use_container_width=True, hide_index=True)
                    st.caption(result.get("status", "Requires review"))
                except requests.RequestException as exc:
                    st.error(f"Impact analysis failed: {exc}")
        st.divider()
        if st.button("Run heuristic inconsistency checks"):
            try:
                result = api_get(f"/documents/{document_id}/inconsistencies").json()
                st.metric("Review candidates", result.get("finding_count", 0))
                st.dataframe(pd.DataFrame(result.get("findings", [])), use_container_width=True, hide_index=True)
                st.caption(result.get("disclaimer", "Heuristic candidates only."))
                st.download_button("Download findings JSON", json.dumps(result, indent=2), file_name="inconsistency_findings.json", mime="application/json")
            except requests.RequestException as exc:
                st.error(f"Consistency checks failed: {exc}")
