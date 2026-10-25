# Source contracts and provenance

Checked 2026-10-26. Public documentation and offline CLI help informed independently written adapters. No private backend/source, paid data or personal account contents are included. Live acceptance is a separate activity.

| Integration | Primary references | Contract used |
| --- | --- | --- |
| MiniMax H3 | [create](https://platform.minimax.cn/docs/api-reference/video-generation-v2-create), [query](https://platform.minimax.cn/docs/api-reference/video-generation-v2-query) | V2 content array, task_id, native task envelope/content.url |
| MiniMax image | [generation](https://platform.minimax.cn/docs/api-reference/image-generation-t2i), [references](https://platform.minimax.cn/docs/api-reference/image-generation-i2i) | image-01, base64 output, one subject reference |
| Ark Seedance | [create](https://docs.volcengine.com/docs/ark/create-video-generation-task-api?lang=zh), [query](https://docs.volcengine.com/docs/ark/get-video-generation-task-api?lang=zh) | async video task; content.video_url; model-specific assets/limits |
| Ark Seedream | [images API](https://docs.volcengine.com/docs/ark/image-generation-api?lang=zh&redirect=1) | images/generations, model-specific refs and base64 images |
| GPT Image | [guide](https://developers.openai.com/api/docs/guides/image-generation), [JSON edit](https://developers.openai.com/api/reference/resources/images/methods/edit) | generation plus JSON edits images[].image_url |
| Chanjing | [auth](https://doc.chanjing.cc/api/get-access-token.html), [briefing](https://doc.chanjing.cc/api/creative/creative-briefing), [base](https://doc.chanjing.cc/api/open-api-common-knowledge.html) | access_token header, business code, category Markdown |
| YouCloud | [vendor overview](https://page.youcloud.com/s/BMw1arT/), [cmclaw entry](https://clawhub.ai/youcloud/skills/cmclaw) | independently implemented identity + cmclaw NDJSON 2/3 protocol; installed vendor reference was inspected, not copied |
| Clipcat | [original repository](https://github.com/Clipcat-ai/clipcat-skill), [skill](https://github.com/Clipcat-ai/clipcat-skill/blob/main/skills/clipcat/SKILL.md) | external CLI 1.0.49 help; raw generation/confirmation and documented original operations; source commit 7f850cae569dfe52c3d80be1fa454727b3228e7a |
| SAU | [source](https://github.com/dreammis/social-auto-upload/tree/3847fff01f5434a8a32829833163cd6723cabc59), [CLI](https://github.com/dreammis/social-auto-upload/blob/3847fff01f5434a8a32829833163cd6723cabc59/docs/CLI.md) | project-owned checkout; three upload-video/upload-note and schedule entrypoints |

SAU commit 3847fff01f5434a8a32829833163cd6723cabc59 was resolved through the GitHub connector after direct GitHub API transport failed. Its commit is unsigned; commit pinning is reproducibility, not a security certification. Its project-owned runtime was installed on Intel macOS with Python 3.12; main and three platform help commands started successfully. Browser download, login and publishing acceptance were not performed. Dependency wheel availability and platform web flows can change.

Provider/SDK versions can change. This source record does not establish account entitlements, published rate cards, commercial redistribution permission for vendor datasets or practical media quality. Chanjing's briefing sample is not observed commerce data.
