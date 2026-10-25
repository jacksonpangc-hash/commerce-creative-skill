# Implementation plan

Use Python 3.10+ standard library, argparse and unittest. Keep package beside Skill scripts so the installed Skill is self-contained; also expose a pip console command. No hosted server or global Codex configuration change.

1. Core: RED tests for bounded project paths, immutable approvals, file/config fingerprints, replay protection and honest submission_unknown. GREEN implement state and authorization engine.
2. Providers: RED contract tests, then implement MiniMax H3/images, Ark Seedance/Seedream, OpenAI image generation/editing, Chanjing briefing, YouCloud streaming. Add external Clipcat bridge with preserved two-stage server confirmation. Query existing tasks without resubmission.
3. Workflow: RED tests, implement validated editable storyboard/export, image/video preparation, result downloads and local segment composition. Add explicit SAU/TikTok publisher and original Clipcat operations with effect classification.
4. Packaging: standalone Skill, Chinese display metadata, Chinese Skill instructions and usage guides, project init/doctor, safe installer, bilingual open-source docs, examples and CI. Independent skill forward-test and whole-repository review.
5. Final: fix meaningful review findings with RED/GREEN tests, validate wheel/source archive and relocatable installation, record checks and live gaps. Public repository publication is now authorized; no tag or GitHub Release is requested.

Shared interfaces: RequestPlan (operation/provider/params/files/config digest/effects/cost), Job (local id/provider remote id/state/raw result), Storyboard (version/product/sources/shots). Operation handlers consume the exact frozen request; credentials are injected at execution, never saved in an approval.

Ledger: docs/PROGRESS.md. Source audit: docs/SOURCES.md. Test reports are local and summarized in docs/VALIDATION.md; synthetic fixtures are not vendor/live acceptance.
