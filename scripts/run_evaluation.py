"""Run the starter evaluation fixtures against the included synthetic PDF."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core import DocumentStore, answer_question, extract_entities

pdf_path = ROOT / "data" / "sample_hld" / "sample_autosar_hld.pdf"
dataset_path = ROOT / "data" / "evaluation" / "evaluation_dataset.json"
output_path = ROOT / "data" / "evaluation" / "evaluation_results.json"

store = DocumentStore()
doc = store.add_pdf(pdf_path.name, pdf_path.read_bytes())
dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
results = []
retrieval_hits = []
abstention_ok = []
for case in dataset["cases"]:
    result = answer_question(store, case["question"], doc.document_id, top_k=5)
    joined = " ".join(e["text"] for e in result["evidence"]).lower()
    terms_ok = all(term.lower() in joined for term in case["expected_terms"])
    if not case.get("should_abstain", False):
        retrieval_hits.append(terms_ok)
    else:
        abstention_ok.append(not result["grounded"])
    results.append({
        "id": case["id"], "question": case["question"], "grounded": result["grounded"],
        "expected_terms_found_in_evidence": terms_ok,
        "evidence_pages": [e["page"] for e in result["evidence"]],
        "expected_pages": case["expected_pages"],
    })
entities = extract_entities(store, doc.document_id)
report = {
    "dataset": dataset["dataset_name"],
    "note": "Small synthetic smoke evaluation only; not a production accuracy claim.",
    "retrieval_term_hit_rate_answerable": sum(retrieval_hits) / len(retrieval_hits) if retrieval_hits else None,
    "abstention_success_rate": sum(abstention_ok) / len(abstention_ok) if abstention_ok else None,
    "candidate_entity_counts": {k: len(entities[k]) for k in ["components", "interfaces", "signals", "dependencies"]},
    "cases": results,
}
output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
print(f"\nSaved: {output_path}")
