# 验证记录 / Validation

Date: 2026-10-26. Scope: local implementation, synthetic offline tests, packaging and Intel Mac startup. This is not paid-model or public-post acceptance.

| Check | Observed result |
| --- | --- |
| Full offline unittest suite | PASS: 60 tests, 0 failures/errors; Python 3.12 on Intel macOS |
| Skill frontmatter validator | PASS: Skill is valid |
| Independent forward test | 16 CLI invocations: 15 normal exits and one expected rejection for an unverified Clipcat model; 5 prepared plans, 0 jobs, 0 dispatch locks, no socket attempts |
| Whole-repository review | Eight material issues identified; regression tests added before fixes. No second independent review is claimed |
| Intel SAU dependency installation | PASS on Intel macOS 14.8.9 with Python 3.12; external source pinned to 3847fff01f5434a8a32829833163cd6723cabc59 |
| SAU CLI startup | Main help plus Douyin, Kuaishou and Xiaohongshu help returned exit 0; no login/check/upload command executed |
| Wheel / source tarball | PASS: both built locally; source tarball includes the audited public manifest entries |
| Complete source ZIP | Produced from the audited manifest; archive digest is recorded in its adjacent source-manifest.json |
| Relocated wheel / source-tarball Skill install | PASS: installed wheel into a fresh venv, copied Skill from extracted source tarball, ran relocated CLI and prepared an UNKNOWN-cost synthetic plan; 0 jobs, 0 API calls |
| Local Codex Skill installation | PASS: new commerce-creative only; installed standalone CLI reports 0.1.0 |
| Original Clipcat | Preserved; entry/client hashes checked locally outside the public repository |
| GitHub repository publication | PASS: public repository [jacksonpangc-hash/commerce-creative-skill](https://github.com/jacksonpangc-hash/commerce-creative-skill), branch main |
| GitHub npx Skill installation | PASS: installed from the public repository in an isolated temporary project, compared all 18 Skill resources, standalone CLI reports 0.1.0; existing global installation untouched |

## What the tests establish

Tests use synthetic payloads, temporary workspaces, injected HTTP transports and fake process results. They cover fixed official-origin request contracts, native task statuses, JSON image editing, business errors inside HTTP 200, interrupted/empty streaming reports with session preservation, partial image success, explicit schedule effects, project path rejection, symlink input rejection, frozen approved bytes, file/config/session changes invalidating approval, no replay after unknown dispatch, Clipcat's separate confirmation, artifact-download continuation, packaging/installer exclusion of private files and closure of the Skill install list over the public source manifest. A clean ZIP extraction found a build-metadata dependency in the initial install list; it was removed and given a regression test before final delivery.

An independent agent exercised product facts → synthetic briefing → editable two-shot storyboard → H3/Seedance exports → offline plans. Its early finding about redacted presence booleans was corrected and covered by a regression test. Synthetic reports are explicitly labeled and do not demonstrate vendor insight quality.

## Review fixes and Intel runtime decision

The review identified input-file switching, Clipcat argument forms escaping input checks, missing schedule authorization, venv interpreter handling, interrupted YouCloud continuity, lost download progress, installer private-file inclusion and unsafe release file discovery. These were addressed with regression tests. Approved inputs are copied into project-private frozen snapshots before dispatch; credentials never enter approval JSON.

On this Intel Mac, creating a venv with copied interpreter binaries caused `ensurepip` to abort. The final setup uses the normal project-local venv link and records its interpreter SHA-256. This trust rule is specific to execution: media inputs still cannot escape the project. Changing the base Python requires verifying/updating that runtime and preparing requests again. The failed setup was retained privately outside release contents.

## 尚未验证的部分 / Not validated

- No real model key was used. Authentication, entitlement, balance, actual rate cards, media fidelity, latency and generated-content quality are NOT_RUN. Model IDs and public docs must be rechecked before live use.
- No real Chanjing/YouCloud report, private video or paid dataset was fetched; category briefing access is not proof of raw GMV/merchant/creator coverage.
- No project browser was downloaded or launched. Account login, platform challenge handling, real uploads, schedules and public-post verification are NOT_RUN. A SAU zero exit would remain `submitted_unverified` until the original work is verified.
- FFmpeg and ffprobe were absent from the tested PATH. Real lossless composition is NOT_RUN; the adapter stops explicitly when they are missing. Its offline command/error tests do not establish native media compatibility.
- GitHub CI is configured for Python 3.10/3.12 on macOS/Linux/Windows. Check the repository Actions for actual cloud results; installation passing does not establish cloud CI success. Windows/Linux live-provider acceptance is NOT_RUN.
- Original Clipcat and SAU remain external dependencies. Vendor backends, paid datasets and proprietary clients are not reproduced or redistributed. This delivery does not claim model-quality or commercial-data parity.

The complete source ZIP is the full repository deliverable. The wheel contains the CLI package; the Skill installer copies the self-contained Skill. Private runtime dependencies, account state, generated media and credentials are excluded.

## 中文翻译同步核验

Skill 正文、命令流程、服务连接与分镜指南已翻译为中文。核对 frontmatter、界面与自动调用配置、原命令与接口字面值及 Python 文件指纹未变；源码与本机安装内容一致。原英文文件已在本机私有备份中保留，不写入公开包。此前真实调用与发布未验收的限制继续有效。

## 首次云端检查与修复

首次 GitHub Actions 的 Linux 检查发现命令构建测试误依赖本机已安装的原 Clipcat。用不可用的客户端查找复现后，将该测试改为独立构建参数，不调用真实客户端。产品代码未变，本机60项离线测试通过；云端结果以修复提交对应的 Actions 为准。
