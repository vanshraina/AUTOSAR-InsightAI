from pathlib import Path
import fitz
import pytest

from app.core import DocumentStore, split_text, answer_question, extract_entities, compare_documents


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(__import__("fitz").Rect(60, 60, 535, 760), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def test_split_text_keeps_content():
    text = ("BrakeController depends on VehicleSpeedService. " * 80)
    chunks = split_text(text, max_chars=250, overlap=30)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
    assert "BrakeController" in " ".join(chunks)


def test_rejects_non_pdf():
    store = DocumentStore()
    with pytest.raises(ValueError, match="Only PDF"):
        store.add_pdf("notes.txt", b"not a pdf")


def test_rejects_pdf_signature():
    store = DocumentStore()
    with pytest.raises(ValueError, match="signature"):
        store.add_pdf("fake.pdf", b"not really a pdf")


def test_ingestion_query_and_entities():
    store = DocumentStore()
    pdf = make_pdf(
        "AUTOSAR HLD. VehicleSpeedService publishes VehicleSpeedSignal through VehicleSpeedInterface. "
        "BrakeController consumes VehicleSpeedSignal. BrakeController depends on VehicleSpeedService."
    )
    document = store.add_pdf("sample.pdf", pdf)
    assert document.pages == 1
    assert document.chunks
    result = answer_question(store, "VehicleSpeedSignal BrakeController", document.document_id)
    assert result["grounded"] is True
    assert result["evidence"][0]["page"] == 1
    entities = extract_entities(store, document.document_id)
    assert any(item["name"] == "BrakeController" for item in entities["components"])
    assert any(item["name"] == "VehicleSpeedSignal" for item in entities["signals"])


def test_unknown_question_does_not_invent_answer():
    store = DocumentStore()
    document = store.add_pdf("sample.pdf", make_pdf("The BrakeController receives a brake request."))
    result = answer_question(store, "Explain quantum computing in detail", document.document_id)
    assert result["grounded"] is False
    assert "could not find sufficient evidence" in result["answer"]


def test_revision_comparison():
    store = DocumentStore()
    a = store.add_pdf("rev_a.pdf", make_pdf("BrakeController uses VehicleSpeedSignal."))
    b = store.add_pdf("rev_b.pdf", make_pdf("BrakeController uses VehicleSpeedSignal. New CabinMonitor checks cabin status."))
    result = compare_documents(store, a.document_id, b.document_id, threshold=0.8)
    assert result["document_a"] == "rev_a.pdf"
    assert "added" in result and "removed" in result


def test_graph_impact_and_inconsistency_endpoints_core():
    from app.core import build_architecture_graph, analyze_impact, detect_inconsistencies
    store = DocumentStore()
    document = store.add_pdf("graph.pdf", make_pdf(
        "VehicleSpeedService publishes VehicleSpeedSignal through VehicleSpeedInterface. "
        "BrakeController depends on VehicleSpeedService and consumes VehicleSpeedSignal."
    ))
    graph = build_architecture_graph(store, document.document_id)
    assert graph["entities"]
    assert graph["relationships"]
    impact = analyze_impact(store, document.document_id, "BrakeController")
    assert impact["status"] == "REQUIRES_ENGINEER_REVIEW"
    assert "direct_relationships" in impact
    findings = detect_inconsistencies(store, document.document_id)
    assert "findings" in findings


def test_case_study_query_is_scoped_to_requested_section():
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_textbox(fitz.Rect(50, 50, 540, 760),
                      "Executive Summary\nCase Study 1\nAUTOSAR HLD analysis architecture search", fontsize=11)
    p2 = doc.new_page()
    p2.insert_textbox(fitz.Rect(50, 50, 540, 760),
                      "Case Study 2\nFunctional Safety HARA\nProject Overview\n1. Business Context\nASIL recommendation and safety requirement traceability", fontsize=11)
    p3 = doc.new_page()
    p3.insert_textbox(fitz.Rect(50, 50, 540, 760),
                      "Case Study 3\nCybersecurity TARA\nProject Overview\n1. Business Context\nthreat mitigation", fontsize=11)
    data = doc.tobytes()
    doc.close()
    store = DocumentStore()
    uploaded = store.add_pdf("five_cases.pdf", data)
    result = answer_question(store, "Give evidence for Case Study 2 HARA ASIL", uploaded.document_id)
    assert result["grounded"] is True
    assert all(item["page"] == 2 for item in result["evidence"])
    assert all("HARA" in item["text"] or "ASIL" in item["text"] for item in result["evidence"])
