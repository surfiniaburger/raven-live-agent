# Source Quality Policy (RAVEN)

## Purpose
Ensure grounding corpus quality is high enough for operational incident-response guidance.

## Acceptance Criteria
1. **Authority**: Source must be from recognized authority (government regulator, standards body, official emergency management org, or approved internal policy owner).
2. **Provenance**: Every chunk must preserve `source_url`, `effective_date`, and `version` where available.
3. **Recency**: Prefer documents updated within 24 months unless still active normative standards.
4. **Scope Fit**: Content must map to RAVEN incident categories (evacuation, electrical, chemical spill, crowd safety, emergency comms).
5. **Licensing**: Data use rights must permit internal indexing and model-grounded use.
6. **PII/Sensitive Data**: Remove personal identifiers and confidential content before ingestion.

## Source Tiers
- **Tier 1 (highest)**: Official regulations, emergency management frameworks, audited internal SOPs.
- **Tier 2**: Government advisories and official implementation guides.
- **Tier 3**: Secondary explanatory docs (only with Tier 1/2 backing).

## Gating Policy (Runtime)
- `grounded_answer_ok`: definitive grounded guidance allowed.
- `answer_with_caution`: caveated guidance + clarifying follow-up required.
- `ask_clarifying_or_abstain` / `below_min_confidence` / `abstain_no_results`: do not provide definitive legal/compliance instructions.

## Required Metadata Fields Per Record
- `doc_id`
- `title`
- `source_url`
- `doc_type`
- `jurisdiction`
- `effective_date`
- `version`
- `tags`
- `content`
