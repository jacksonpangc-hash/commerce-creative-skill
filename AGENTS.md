# Development contract

Implement the approved specification in docs/SPEC.md. Keep original Clipcat external and unchanged. The repository contains independently written integration code, not Clipcat's private backend or proprietary client.

Run offline tests before delivery. Tests use synthetic inputs and injected transports; never use real API keys, media uploads, browser sessions, paid calls or social publishing during development. Live acceptance requires a separately authorized account, sample, cost and publishing scope.

Use project-local .commerce state. Prepared requests are immutable; changing files or project configuration invalidates approval. A timeout after dispatch is submission_unknown, not permission to retry. Credentials and private paths do not belong in source or release artifacts. GitHub publication is authorized for this independently authored repository by the user on 2026-10-26. Limit publication to the audited public file manifest; keep runtime state, credentials and personal files private. Tags and GitHub Releases require a separate explicit request.
