# Commerce Creative Skill

[中文说明](README.md)

An independent, self-contained AI-agent skill and Python CLI for commerce creative work. Keep original Clipcat services while adding your own MiniMax H3 / Ark Seedance video keys, three image providers, Chanmama-related creative insights and domestic publishing adapters.

**Status: 0.1.0 open-source preview. Offline tests and relocatable installation have passed; live account access, paid media quality and actual social publishing remain unverified.**

## Workflow

Product facts → selected research source → editable agent-authored storyboard → reviewed generation request → selected model → media review → selected publishing account → verified platform result.

| Area | Implemented integration | Boundaries |
| --- | --- | --- |
| Video | Original Clipcat raw; direct MiniMax H3 (default); direct Ark Seedance 2.5 | Separate credentials/billing; no automatic fallback |
| Images | MiniMax image-01; Ark Seedream 5.0 pro; OpenAI GPT Image 2.5 | Different reference/edit/size limits; no silent asset removal |
| Insights | Chanjing creative radar using Chanmama-related data; YouCloud cmclaw; original Clipcat research | Briefings are not raw merchant/creator/GMV tables |
| Scripts | Host agent writes editable JSON storyboard; CLI validates and exports shots | No hidden extra LLM call or invented metrics |
| Publishing | Clipcat TikTok; project-owned SAU for Douyin, Kuaishou and Xiaohongshu | External setup/account authorization required; submit ≠ published |
| Assets / schedules | Original Clipcat operations; explicit user-owned presigned staging; local downloads and FFmpeg assembly | No implicit cloud sync; local execution requires a running machine |

## Install and try without credentials

```bash
npx -y skills add jacksonpangc-hash/commerce-creative-skill --skill commerce-creative --agent codex -g --yes
```

This installs the Skill for Codex. A Node.js/npm environment is required for this installer; use the repository installer below if you prefer Python. Clone the repository for the full CLI, examples and optional publisher setup.


Use Python **3.10 or newer**. macOS system Python may be older; select an existing supported interpreter. No runtime Python dependencies are required for the core CLI.

```bash
python3 scripts/install_skill.py
python3 skills/commerce-creative/scripts/commerce.py --help
python3 -m pip install .  # optional: adds commerce-creative in that Python environment
```

The installer copies only `commerce-creative` to `~/.codex/skills`, refuses to overwrite an existing skill, and does not edit original Clipcat, global Codex settings, shell startup files or other clients. For another compatible agent, explicitly set `--destination` to that agent's skills directory. Chinese UI metadata, Skill instructions and supporting guides are included; the machine name stays `commerce-creative`.

The following commands perform local preparation only:

```bash
python3 skills/commerce-creative/scripts/commerce.py init --project .
python3 skills/commerce-creative/scripts/commerce.py doctor --project .
python3 skills/commerce-creative/scripts/commerce.py storyboard-check examples/storyboard.json --project .
python3 skills/commerce-creative/scripts/commerce.py storyboard-export examples/storyboard.json --provider minimax --out requests-v1 --project .
python3 skills/commerce-creative/scripts/commerce.py prepare requests-v1/shot-1.json --project .
```

Ask your agent: “Use `$commerce-creative` to turn my real product facts into an editable storyboard. Use Chanjing for insights and MiniMax H3 for generation. Prepare only; show the sources, prompt and costs before any paid request or upload.”

## Connect services and execute

Read the [provider reference](skills/commerce-creative/references/providers.md) and [.env.example](.env.example). Credentials are process environment values; the CLI does not silently load `.env`. `doctor` never prints secrets or verifies accounts online.

`prepare` makes no API call, upload or provider quote. After the user reviews the exact snapshot and authorizes its cost/effects, `execute` requires its id plus explicit effect flags. An estimate does not impose a provider-side spending cap. Unknown prices stay unknown; do not fabricate estimates. Clipcat keeps its extra server checklist/confirmation round. See [CLI workflow](skills/commerce-creative/references/cli.md).

Save results per project. Poll the existing task instead of resubmitting. A timeout is `submission_unknown`; inspect vendor history before creating another task. Download signed output links before expiry. For reference-video URLs, explicit presigned staging uses the user's own storage, not an undocumented upload host.

## Domestic publishers

See [publishing setup](docs/PUBLISHING.md). SAU is an external browser automation dependency pinned to a reviewed source commit; it is not bundled. Install only in the current project's private tools directory, then let the human complete login. A browser or CLI success alone is not public-post acceptance. Original Clipcat account setup, cloud storage and scheduling remain external services.

## Development and packaging

```bash
PYTHONPATH=skills/commerce-creative/scripts python3 -m unittest discover -s tests -v
python3 -m pip install build
python3 -m build
python3 scripts/package_release.py --output dist/source
```

The source packager includes public source, documentation, examples and tests; excludes project state, environment files, credentials, account cookies, binaries and personal paths. The Skill works when copied alone; the pip wheel contains the reusable CLI, while the source ZIP also contains the Skill and guides.

Read [architecture](docs/ARCHITECTURE.md), [source contracts](docs/SOURCES.md), [validation](docs/VALIDATION.md), [rollback](docs/ROLLBACK.md), [contributing](CONTRIBUTING.md) and [security boundaries](SECURITY.md).

## License and attribution

Original integration code and documentation: [MIT](LICENSE). This is inspired by Clipcat's workflow, not affiliated with or endorsed by Clipcat, MiniMax, ByteDance, OpenAI, Chanmama or YouCloud. Vendor services, datasets, generated assets and external tools retain their own terms. No Clipcat proprietary binary/backend/instruction body is redistributed. See [third-party notices](THIRD_PARTY_NOTICES.md).
