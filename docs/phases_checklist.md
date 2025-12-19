# Phases checklist: i18n LLM Translator (file-only)

## Phase 0: Repo skeleton
- [x] Create folder structure (src/, docs/, work/, i18n/)
- [x] Add Cursor rules files (.cursor/index.mdc + .cursor/rules/*.mdc)
- [x] Add Spec Kit constitution (.specify/memory/constitution.md)
- [x] Add minimal README + runbook stub

## Phase 1: Memory artifact + IO
- [x] Read per-language JSON files into memory
- [x] Implement `build-memory`: generate work/memory.jsonl from i18n/*.json
- [x] Implement missing detection per language
- [x] Tests: missing detection, stable key handling

## Phase 2: Validation core
- [x] Implement placeholder extraction + signature
- [x] Implement JSON schema validation for LLM output
- [x] Implement merge-only-missing logic for i18n output files
- [x] Tests: placeholder mismatch fails; merge does not overwrite

## Phase 3: Providers + translation loop
- [x] Implement provider interface `translate_batch(...)`
- [x] Implement Ollama provider (local)
- [x] Implement API provider skeleton (env config, retries, rate limiting)
- [x] Implement batching strategy (by namespace/prefix; stable ordering)
- [x] Implement repair flow for invalid JSON
- [x] Per-run logs: work/runs/<run_id>/

## Phase 4: End-to-end + reporting
- [x] Implement `run`: build-memory -> translate-missing -> validate -> write-back
- [x] Add summary report (missing before/after, invalid, needs_review)
- [x] Ensure reruns are idempotent (no churn)
- [x] Document usage in docs/runbook.md

## Phase 5: Optional hardening
- [ ] Glossary + do-not-translate support
- [ ] Stale detection when sv changes (needs_review flag)
- [ ] CI step: validate placeholders + schema without calling LLM
