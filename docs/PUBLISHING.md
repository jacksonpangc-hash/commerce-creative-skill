# Domestic publishing setup

The integration calls the external MIT-licensed social-auto-upload project. It does not bundle it, reuse other projects' cookies, read a normal browser profile or bypass platform verification. Source pinned for this release: `3847fff01f5434a8a32829833163cd6723cabc59`.

Run optional setup only when dependency downloads/installations are authorized, using Python 3.10–3.12:

```bash
python3 scripts/setup_publisher.py --project /path/to/project --allow-download
```

This creates `.commerce/tools/social-auto-upload`, a dedicated venv and configuration. Add `--browser` to install project-local Patchright Chromium. It does not log in or publish. Source installation/dependencies can access GitHub and package indexes; they are not charged media API calls. The helper refuses an existing checkout to preserve customizations. Windows uses Scripts/python.exe and adjusts project config automatically.

The pinned source and dependency wheels were installed on Intel macOS 14.8.9 / Python 3.12 in this delivery. Main and three platform help commands passed. Browser installation and account authorization remain separate. The standard venv can link to base Python; setup records its interpreter fingerprint and execution verifies it. Do not change or move that interpreter without re-verifying the project runtime. A copied-interpreter venv was rejected after an actual Intel startup failure; no system Python was changed.

Login is a separate user-authorized stage. From the project-owned checkout, use its venv Python to invoke `sau_cli.py <douyin|kuaishou|xiaohongshu> login --account <simple-alias>`. Set `PLAYWRIGHT_BROWSERS_PATH` to the project's `.commerce/browsers` if using its installed browser. The human completes QR/SMS verification. A fresh alias represents only that project/account; do not export cookies to a public repository.

The wrapper accepts a prepared request with `operation: publish`, `provider: sau`, and params platform, account, title, assets, optional kind(note/video), text, tags and schedule. `schedule` is `YYYY-MM-DD HH:MM` in Asia/Shanghai. Each video's assets array contains one local video; notes use local images. See examples/publish-douyin.json.

Review the concrete media/account/caption/time before execution. Uploading may save drafts on the platform. `submitted_unverified` means the external command returned, not that the content was publicly published or the schedule accepted. Inspect the exact original work in the creator center and retain its URL/id. Unknown outcome means inspect first, not re-upload. This release does not implement a universal SAU readback API because the three platform modules do not expose one common verified result contract.

TikTok keeps original Clipcat accounts and two-step publishing; the exact open id and privacy are required. Content posting does not authorize paid ad campaigns. Clipcat's original cloud schedules do not run the new Python adapter automatically. No accounts, uploads, schedules or posts were created in this delivery.
