# Evaluation Plan

## Objective
Measure whether the pilot retrieves relevant source passages and identifies candidate architecture entities with useful page traceability.

## Dataset
`data/evaluation/evaluation_dataset.json` includes synthetic starter questions and expected concepts. It is intentionally small and must not be presented as a production-quality benchmark.

## Metrics
- **Entity precision:** correct extracted entities / all extracted entities reviewed.
- **Entity recall:** correct extracted entities / all gold entities.
- **Entity F1:** harmonic mean of entity precision and recall.
- **Retrieval hit@k:** fraction of questions where at least one gold evidence page appears in top-k retrieved passages.
- **Citation validity:** fraction of returned citations whose page exists and passage is present in that source.
- **Abstention quality:** whether out-of-scope/unanswerable questions are not answered with invented facts.
- **Revision review quality:** engineer-confirmed changes / all suggested changes.

## Procedure
1. Select representative, authorized HLDs with version labels.
2. Create engineer-reviewed gold entities and query-to-page labels.
3. Keep a held-out set separate from development examples.
4. Run the evaluation script and manually audit incorrect hits, missed entities, and false revision flags.
5. Report sample size, document characteristics, limitations, and confidence intervals where appropriate.
6. Do not claim productivity gains until a timed baseline and pilot comparison have been performed.

## Acceptance targets (proposed, not achieved claims)
- 100% of displayed evidence citations refer to an existing ingested page.
- No fabricated answer for questions with no retrieved evidence.
- Establish baseline entity F1 and retrieval hit@5; set targets only after the gold set is labelled.
- All generated inventory and revision outputs include review caveats.
