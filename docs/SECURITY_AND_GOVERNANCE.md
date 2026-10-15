# Security, Privacy, and Governance Checklist

- [x] Local-only processing by default; no external model provider configured.
- [x] PDF signature/extension validation and size/page caps.
- [x] SHA-256 provenance fingerprint.
- [x] No automatic source-document changes or architecture approvals.
- [x] Explicit warnings on candidate extraction and comparison.
- [ ] Authentication and authorization (required before multi-user use).
- [ ] Project-level document isolation and RBAC.
- [ ] Encryption at rest and in transit for network deployment.
- [ ] Durable audit events and retention controls.
- [ ] Dependency, container, and application security assessment.
- [ ] Review of licenses and permissions for all ingested engineering data.
- [ ] Human validation of extracted entities, cited answers, and revision findings.

**Deployment statement:** The current version is a local evaluation prototype. Do not expose it to a public network or ingest confidential engineering data until the unchecked controls are implemented and approved.
