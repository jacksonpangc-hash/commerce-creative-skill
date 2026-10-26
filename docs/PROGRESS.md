# Execution ledger

## 0.2 商业创作闭环

- 用户明确授权补齐能力并虚构绿豆饼；沿用既有供应商及独立编排设计，本轮不重跑同范围设计审批。新增 SPEC AC21–28 与 UPGRADE_PLAN。复用现有规格真源，未初始化或覆盖 Spec Kit 脚手架，也未运行其要求不同目录结构的 converge 命令。
- Skill 基线只读测试复现：空事实/无效来源及无业务要素仍可通过旧格式。保留旧格式技术用途，修复空值验证；商业 v2 独立记录声明状态、来源范围、主/替代策略、外观锁和镜头目的。
- 商业合同测试观察 RED→GREEN：v2 不存在、空值通过、缺导出绑定，到竞品不能验证 SKU、未知声明不能进脚本、已保存脚本/证据指纹与请求绑定。单镜短片允许 hook_proof_cta，不强制拉长影片。
- 本地媒体测试 RED→GREEN：新增可选 PyAV/Pillow/imageio-ffmpeg；真实合成媒体验证全程解码、帧/音轨提取、标准化拼接、字幕/概念披露和保留原文件。组件仅安装在本仓库解释器，不改全局工具。
- 验收测试 RED→GREEN：未知/未视听、成片或证据变化、比例/时长/音轨错误均不能通过；每镜必须有对应时间范围内的实际观察，不只勾名字。通过只表示所填审阅的内容结论，不是第三方真实性或销量认证。
- 网络测试 RED→GREEN：DNS 固定公网地址后保持 TLS 主机名校验；fake-DNS 仅显式公共解析，内网/重定向/超限继续拒绝。实际只读重下载旧水杯701335字节，SHA256与原件完全一致，零新增生成提交；未修改系统 DNS/代理。
- 绿豆饼一手来源已核实并登记：稻香村、立高、麦维客。仅作所属品牌/品类参考；虚构 A-01 独立 concept 来源，未套入配料、功效、销量或供应商广告数据。18秒三镜概念方案及两种替代角度已完成。
- 新付费验收提议：1张image-01概念图＋3段H3各6秒，按核实官方价格估算CNY9.025，建议预算CNY12；最多四次提交、不自动付费重试、不发布。尚未获新授权时保持NOT_RUN；旧水杯单次授权已关闭。

- 独立行为复测：18秒三镜离线检查/导出通过，竞品来源验证真实 SKU 的反例被拒绝；仅分析不生成、包装变化应失败、竞品图不能证明实物等规则模拟符合要求，真实服务/成片仍未由该测试代验。
- 独立审查发现5项重要问题：音轨掩盖短画面、非方形像素变形、DISPLAYMATRIX旋转漏读、真实SKU缺参考仍通过、review顶层数组崩溃。逐项添加复现测试并观察RED，再修复：记录完整解码帧覆盖、保持显示比例/方向、真实图缺失仅草稿或披露概念、JSON类型错误清楚返回。无延后次要项；修复后全套测试记录在最新验证节。

## 0.1 历史记录（保留原文）

Plan: docs/IMPLEMENTATION.md; authority: docs/SPEC.md and approved conversation revision.

- Workspace: new dedicated repository, branch codex/clipcat-multiservice; no existing business checkout touched.
- Pre-flight: all provider handlers consume RequestPlan; persistence owns Job state before dispatch. Storyboard is separate from vendor generation. No conflicting existing implementation.
- Baseline: existing Clipcat skill cannot use own MiniMax/Ark credentials or the Chanjing-to-storyboard chain; dry-run can upload. Domestic publishing absent. Read-only independent baseline confirmed these gaps.
- Decision: publish independently authored adapters with original Clipcat and SAU as external dependencies; public Clipcat repository has no verified redistribution license for its client/backend. No copying that content.
- Task 1 complete: 8 core tests observed RED (missing core) then GREEN; bounded paths, fingerprints, permissions and replay/uncertainty behavior implemented.
- Task 2 complete: provider-native contract tests observed RED then GREEN; H3/Ark/three image providers/Chanjing/YouCloud adapters implemented with injected offline transport.
- Task 3 complete: workflow and CLI tests RED then GREEN. Original Clipcat two-stage raw bridge and SAU submission adapter added; local storyboard/export, downloads and composition implemented.
- Safety pass: missing credentials now fail before claiming dispatch; unsupported Ark local video URLs require explicit user-owned presigned staging; unknown params are rejected instead of silently ignored. No automatic token refresh. These are implementation details required by the approved effect and continuity boundaries.
- Task 4: packaging tests RED then GREEN; bilingual documentation, standalone Skill, Chinese UI fields, installer, pinned optional publisher setup and source packaging prepared. No account calls or uploads.
- Independent whole-repository review found eight material issues. Added failing regression cases, then fixed input switching with frozen dispatch snapshots, Clipcat equal/positional argument validation, schedule effects, publisher interpreter handling, YouCloud session/identity continuity, resumable downloads and audited install/release manifests. Do not interpret the review as a second review of the fixed tree.
- Independent forward test exercised 16 synthetic offline CLI invocations, five prepared plans and no jobs/dispatches/socket attempts. Fixed the presence-boolean finding and made UNKNOWN cost explicit.
- Final edge cases were observed RED then GREEN: empty report retains session, Clipcat result URLs expose download artifacts, partial image success is explicit and extensionless existing inputs enter approval fingerprints. Source tarball now includes the install manifest rather than losing it through extension globs.
- Intel runtime ruling: a copied-interpreter venv caused ensurepip SIGABRT. Retained failed owned setup privately, switched to normal venv links with verified interpreter fingerprints, then installed pinned SAU and dependency wheels successfully. Main/Douyin/Kuaishou/Xiaohongshu help passed. Browser, login and publishing NOT_RUN; no system/global configuration changed.
- Final packaging and local installation results are recorded in docs/VALIDATION.md. Preserve this local branch; no remote, push or release in this task.

- Archive extraction caught build-generated egg-info in the Skill install list. A failing manifest-closure regression confirmed it; removed those entries. Final ZIP installs must depend only on audited public source files.

- User-authorized Chinese translation: SKILL.md and all three references translated, original English files backed up privately. Frontmatter, invocation policy, command literals, API origins and Python code retained. Installed Skill and source package synchronized. No account or publishing action.

- Publication phase authorized by the user on 2026-10-26: publish the independent Skill repository to GitHub and finish public docs. Missing real cases are omitted. Do not make paid calls or social posts. Repository owner verified as jacksonpangc-hash; target commerce-creative-skill, public. No tag/Release requested.

- GitHub publication verified: public main branch contains the audited 66-file repository. Actual npx installation from GitHub passed in a temporary project; all 18 Skill resources matched and CLI reported 0.1.0. Global installation unchanged. No tag, Release, paid generation or social post created.

- First GitHub CI run exposed a non-hermetic test: command construction relied on the author machine having Clipcat installed. Reproduced with client lookup unavailable (RED), isolated executable lookup inside the command-construction test, then all 60 local tests passed (GREEN). Product code and installed Skill unchanged. Cloud matrix rerun follows the correction.
