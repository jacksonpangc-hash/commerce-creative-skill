# Architecture

The standalone Skill routes the host agent through evidence collection, editable storyboarding and explicit execution. Python code is colocated under the Skill so copied installations do not depend on the author's checkout. A wheel exposes the same package as a console command.

`Workspace` bounds file paths to the explicit project and stores private `.commerce` config, immutable plans, dispatch locks, job receipts, reports and artifacts. A plan includes the normalized operation/provider request, local input hashes, config digest and declared effects. Credentials are injected at dispatch, not stored in source or approvals. This is application-level path discipline, not an OS sandbox against arbitrary local code.

`Engine.prepare` runs validation only. `Engine.execute` verifies the snapshot, permissions and local preconditions, claims a single-dispatch lock and persists a dispatching receipt before contacting a provider. If a response cannot establish an outcome, retain submission_unknown. Query the original task instead of replaying. A crash between provider acceptance and storing the id requires manual history reconciliation; the tool never claims exactly-once network delivery.

Provider modules translate common requests to vendor-specific APIs. Direct H3/Seedance task queries normalize state and artifact URLs. Image responses decode base64 results locally. Chanjing produces a category report; YouCloud consumes strict NDJSON and distinguishes incomplete reports. The host agent authors and edits the storyboard—`context` only assembles evidence.

Original Clipcat is invoked with argv and shell=False. Raw generation consumes the reviewed prompt; bundled original flows remain accessible separately through the original CLI. Provider checklist confirmation is retained as a second explicit step. Generic passthrough denies config/update, key/base-URL overrides and confirmation bypasses; some original interactive features remain original-CLI-only.

SAU executes from a current-project checkout with its own runtime and browser cache. A standard venv interpreter link may resolve to the installed base Python; its link must remain inside the project, its SHA-256 must match verified project config and pyvenv.cfg must exist. This narrowly scoped executable-trust rule does not expand media input boundaries. It preserves conservative submitted_unverified state pending platform inspection. Clipcat cloud storage/scheduling remain original service features; the new local adapter is not automatically executed by that cloud scheduler.

No UI server, hosted backend, telemetry, background watcher, shell startup edit or global Codex configuration is introduced. Original Clipcat is not modified.
