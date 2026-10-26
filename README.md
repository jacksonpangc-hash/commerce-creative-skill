# Commerce Creative · 电商素材创作与多平台发布

[English](README_EN.md) · [中文 Skill](skills/commerce-creative/SKILL.md) · [快速开始](docs/QUICKSTART.md)

把**商品事实、创意洞察、可编辑脚本分镜、视频与图片生成、发布审核**接成一条工作流。运行在本地 AI Agent 中，使用用户自己选择的云服务和密钥。

**0.2.0 增加完整商业创作合同、本地视频分析与制作、证据绑定的内容验收。接口调用、内容审阅、真实商品还原和投放效果分别报告；仍需自己的服务账号与授权。**

## 适合谁使用

适合希望用自己的模型 API Key 生产电商素材、需要修改脚本后再逐镜头生成，以及希望保留不同数据源和发布通道选择的用户。可以安装到 Codex；Skill 目录也可供兼容 Agent 使用，其他客户端的实际调用效果须分别验证。

## 功能与服务选择

| 环节 | 可选能力 | 使用边界 |
| --- | --- | --- |
| 视频生成 | 原 Clipcat、直连 MiniMax H3（默认）、直连火山方舟 Seedance 2.5 | 服务独立计费；失败不会自动换供应商 |
| 图片生成 | MiniMax image-01、Seedream 5.0 pro、GPT Image 2.5 | 各家参考图、编辑、数量及尺寸限制不同 |
| 创意洞察 | 原 Clipcat、蝉镜创意雷达（蝉妈妈相关来源）、有米云 | 品类报告不等于逐条素材销量、GMV 或商家达人数据库 |
| 脚本与分镜 | 当前 Agent 基于商品事实和洞察编写可编辑 JSON | 编排与生成分开；不暗中增加一套付费大模型调用 |
| 内容发布 | Clipcat 对接 TikTok；项目内 SAU 对接抖音、快手、小红书 | 必须授权对应账号；提交完成后仍须核对原作品 |
| 素材与定时 | 保留 Clipcat 云端素材和排期；支持下载、明确授权的暂存、FFmpeg 本地拼接 | 新适配器不会自动接入 Clipcat 云调度；本机执行依赖电脑运行 |

推荐流程：**商品资料 → 选择洞察来源 → Agent 脚本与分镜 → 审核 → MiniMax H3 等生成 → 成片审核 → 选择账号发布 → 核对平台结果。**

## 0.2 商业创作能力

- 三种任务：定向分析、策略探索、灵感激发；由宿主 Agent 阅读实际证据、提出判断并写可编辑分镜。
- 商品声明分真实、虚构和未知；分镜包含人群、购买任务、钩子、证明与行动。逐镜外观锁与共同参考图保持一致。
- 本地视频全程解码、带时间戳采样帧及音轨导出；支持等比补边、标准化拼接、本地配音/音乐和确定性字幕。
- 规格与实际视听审阅双重检查，绑定分镜、证据及成片指纹；只看采样或状态成功不能通过完整验收。

详见 [完整绿豆饼案例](examples/mung-bean/README.md)、[商业流程](skills/commerce-creative/references/commercial.md)。本地媒体组件安装：`python -m pip install '.[media]'`。组件可选，核心准备和 API 编排仍只依赖标准库。

## 安装 Skill

有 Node.js/npm 时，安装到 Codex：

```bash
npx -y skills add jacksonpangc-hash/commerce-creative-skill --skill commerce-creative --agent codex -g --yes
```

该命令面向 Codex 用户安装，不主动覆盖其他客户端。已有同名定制时先备份、比较再升级。

也可克隆完整仓库，使用 Python 安装器：

```bash
git clone https://github.com/jacksonpangc-hash/commerce-creative-skill.git
cd commerce-creative-skill
python3 scripts/install_skill.py
```

Python 需要 **3.10 或更新版本**；macOS 自带版本可能过旧。核心 CLI 只依赖标准库。安装器新增 `commerce-creative`，遇到同名目录会停止；保留原 Clipcat，不修改全局配置或现有项目权限。

对 Agent 说：

> 使用 `$commerce-creative`，根据我的真实商品资料，用蝉妈妈做创意洞察，再帮我写可编辑脚本和分镜。视频先选 MiniMax H3；先展示来源、完整提示词和费用，等我确认后再生成。

## 不填密钥也能先试

在克隆的仓库中运行：

```bash
python3 skills/commerce-creative/scripts/commerce.py init --project .
python3 skills/commerce-creative/scripts/commerce.py doctor --project .
python3 skills/commerce-creative/scripts/commerce.py storyboard-check examples/mung-bean/storyboard.json --project .
python3 skills/commerce-creative/scripts/commerce.py storyboard-export examples/mung-bean/storyboard.json --provider minimax --out requests-v1 --project .
python3 skills/commerce-creative/scripts/commerce.py prepare requests-v1/shot-1.json --project .
```

这些操作仅在本地准备，不上传、不付费、不发布。`examples/` 是明确标注的合成输入与格式示例，不是真实客户案例、投放效果或供应商生成结果。缺少的真实案例不展示、不补造。

完整步骤见[快速开始](docs/QUICKSTART.md)和[命令使用流程](skills/commerce-creative/references/cli.md)。

## 密钥、费用与隐私

按 [.env.example](.env.example) 和[服务连接说明](skills/commerce-creative/references/providers.md)配置当前选用服务的环境变量。无需把密钥贴到聊天中。工具不会自动读取 `.env`，`doctor` 只检查配置是否存在，不能证明认证、余额或接口权限通过。

`prepare` 完全离线。执行前展示所选模型、完整提示词、素材、账号、时间与有来源依据的费用；未知费用保留 `UNKNOWN`。用户批准后再执行相应操作。费用估算不能限制供应商实际扣费，Clipcat 自己的二次确认也会保留。

商品、报告、账号与任务状态保存在各项目的私有 `.commerce/` 中。发布包排除密钥、Cookie、个人素材、本机路径和运行环境。此路径约束属于应用检查，不能替代操作系统级权限隔离。详见[安全边界](SECURITY.md)。

## 发布与失败恢复

国内平台需要项目内 SAU 引擎、浏览器与用户登录，见[发布配置](docs/PUBLISHING.md)。安装工具、账号登录、上传受理、排期受理和作品公开是不同步骤。当前版本没有统一的国内平台发布回读验收接口；应到创作者中心核对准确作品。

超时后保留原回执，先查原任务或作品，不直接重发。蝉镜刷新 token 会让旧 token 失效，默认使用已有 token。旧 `compose` 使用独立 FFmpeg/ffprobe；新 `render` 使用项目可选媒体组件，可标准化不同编码镜头并添加字幕。

## 开发与验证

```bash
PYTHONPATH=skills/commerce-creative/scripts python3 -m unittest discover -s tests -v
python3 -m pip install build
python3 -m build
python3 scripts/package_release.py --output dist/source
```

本地测试结果见 [验证记录](docs/VALIDATION.md)，覆盖核心、供应商、商业合同、本地实码媒体与安全边界。GitHub Actions 配置覆盖 Python 3.10/3.12 与 macOS/Linux/Windows；具体云端结果以仓库的 Actions 为准。离线接口测试不代表模型质量或真实平台功能通过。

## 文档与贡献

- [分镜格式](skills/commerce-creative/references/storyboard.md)、[服务接口与来源](docs/SOURCES.md)
- [架构](docs/ARCHITECTURE.md)、[已验证范围与缺口](docs/VALIDATION.md)
- [常见问题](docs/FAQ.md)、[升级与回滚](docs/ROLLBACK.md)
- [贡献指南](CONTRIBUTING.md)、[第三方声明](THIRD_PARTY_NOTICES.md)、[更新记录](CHANGELOG.md)

原创集成代码与文档按 [MIT](LICENSE) 开源。本项目独立开发，与各供应商没有官方隶属关系。原 Clipcat 客户端、供应商私有后端和付费素材库均未复制或分发；账号、数据、生成结果和外部工具遵守各自条款。不保证生成内容必成爆款。
