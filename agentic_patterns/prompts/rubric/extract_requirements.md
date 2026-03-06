You are a policy analyst. Extract all evaluable requirements from the following policy text chunk.

For each requirement, determine:
- **title**: short descriptive name
- **requirement_level**: MUST (mandatory), SHOULD (recommended), or MAY (optional)
- **requirement_text**: the full requirement statement as written in the policy
- **evidence_required**: what evidence would demonstrate compliance (list of concrete artifact types or observations)
- **framework_mappings**: if the text references specific framework controls (e.g. SOC 2, HIPAA, ISO 27001), map them as framework_name -> list of control IDs
- **tags**: relevant topic tags (e.g. "access-control", "encryption", "logging")

Be precise. Only extract requirements that are explicitly stated or clearly implied by the text. Do not invent requirements.

## Policy text

{chunk_text}