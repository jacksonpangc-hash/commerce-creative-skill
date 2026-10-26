# 命令使用流程

## 商业创作新增命令（0.2）

以下命令均加 `--project PATH`，路径都在当前项目中；示例使用已配置的 Python 3.10+ 解释器与 Skill 内的 `scripts/commerce.py`。下面的媒体制作不调用模型，也不发布平台。

```bash
python scripts/commerce.py storyboard-check storyboard.json --project PATH
python scripts/commerce.py storyboard-export storyboard.json --provider minimax --out requests-r1 --project PATH
python scripts/commerce.py media-inspect local-reference.mp4 --out reference-inspection --samples 24 --project PATH
python scripts/commerce.py render storyboard.json --segments segments.json --out final-r1.mp4 --project PATH
python scripts/commerce.py media-inspect final-r1.mp4 --out final-inspection-r1 --samples 24 --project PATH
python scripts/commerce.py review-template storyboard.json --inspection final-inspection-r1/inspection.json --out review-r1.json --project PATH
python scripts/commerce.py acceptance-check storyboard.json --inspection final-inspection-r1/inspection.json --review review-r1.json --out acceptance-r1.json --project PATH
```

`segments.json` 将镜头 id 映射到下载后的视频路径。外部配音/音乐可在 render 时添加 `--voiceover voice.wav --music music.mp3`，自有或已获许可的字体可用 `--font-file font.ttf`；素材授权由用户/Agent核对。默认本地制作不启动第三方云服务。

review-template 只建一个全部 UNKNOWN 的表，不替 Agent 看视频。实际完整观看并听音后才填写 PASS 与时间点；不能从退出码0推断内容通过。acceptance-check 返回 accepted=false 时停止交付为“已通过”，保留问题镜头并修改。

本地组件安装：仓库解释器运行 `python -m pip install '.[media]'`；仅装 Skill 的用户，在同一个 Python 环境安装 `av>=14,<17`、`Pillow>=10,<13`、`imageio-ffmpeg>=0.6,<0.7`。遇到缺组件会报错，不改系统软件或偷偷下载依赖。

下载在 TUN fake-DNS 下被公网检查拦截时，可选择 `download LOCAL_JOB_ID --public-dns --project PATH`，只查询当前产物主机名并固定公网连接，不改变其他任务的网络。普通私网不会因此放行。付费提交仍使用原有 prepare/execute 流程，下载兼容选项不会重新生成。

使用 Python 3.10 或更新版本运行 `scripts/commerce.py`。通过 pip 安装后的命令名为 `commerce-creative`。所有项目命令都必须带 `--project PATH`；JSON、素材输入与输出限定在该项目根目录内。这是程序自身的路径校验，不能替代操作系统级权限隔离。

1. `init --project PATH`：创建私有 `.commerce` 状态目录，不修改全局配置或凭据。
2. `doctor --project PATH`：离线检查依赖和凭据是否存在，不验证线上账号是否可用。
3. `prepare request.json --project PATH`：生成离线固定计划。请求字段为 `operation`、`provider`、`params`；可选 `cost: {estimate, currency, source}`。报价必须真实且可追溯，不使用零值占位。支持视频、图片、洞察、发布、原 Clipcat 命令，以及明确授权的预签名暂存。
4. `show PLAN_ID --project PATH`：向用户展示准确的计划快照。费用估算不等于供应商端的强制消费上限。
5. 获得实际授权后，运行 `execute PLAN_ID --confirm PLAN_ID --project PATH`，并按操作附加 `--allow-paid`、`--allow-upload`、`--allow-publish`、`--allow-schedule`、`--allow-token-refresh`。价格仍未知且用户明确接受时，增加 `--allow-unknown-cost`。参数本身不能代替用户同意。
6. `status JOB_ID --project PATH`：读取本地任务状态；加 `--refresh` 查询供应商，不重新提交。如果提交时崩溃且尚未保存远端 ID，先核对供应商历史，不删除锁文件来重试。
7. `download JOB_ID --project PATH`：将成功结果链接下载到项目内，不向媒体下载站点转发 API Key。链接过期或发生重定向时，重新取得并检查有效链接。

## Clipcat 的二次确认

Clipcat 返回 `awaiting_provider_confirmation` 及服务端核对清单。展示清单并取得用户后续明确确认后，执行 `confirm-clipcat JOB_ID --confirm SERVER_CONFIRM_ID --project PATH`，带上对应操作的授权参数。素材或配置变化会使原批准失效。

其他 Clipcat 操作使用 `{operation:"clipcat",provider:"clipcat",params:{argv:["video","rank",...],query_type:"raw"}}`；先查原 CLI 帮助。此入口不允许任意 shell、配置或更新命令、凭据覆盖或绕过确认。依赖原客户端的流程继续使用原客户端。

## 编写分镜与导出请求

运行 `context --product product.json --report briefing.md --project PATH`，为当前 Agent 汇集事实与证据。编写并审核分镜 JSON，运行 `storyboard-check storyboard.json`，再运行 `storyboard-export storyboard.json --provider minimax --out requests-v1`。逐条准备并批准导出的请求。`context` 和导出操作都不会暗中调用付费服务。

## 本地拼接

`compose --files shot1.mp4 shot2.mp4 --out final.mp4 --project PATH` 使用另外安装的 FFmpeg/ffprobe 做无损拼接。片段的编码、尺寸和音频参数必须一致；不一致时停止，不暗中改变画质。拼接后检查成片。FFmpeg 属于外部依赖，不随本技能打包。

## 素材暂存

本地参考视频需要托管时，使用 `stage` 请求：`provider` 为 `presigned`，`params.assets` 包含一个本地文件，`put_url` 与 `read_url` 由用户的存储服务提供。准备阶段不会上传；执行需要 `--allow-upload`。回执返回读取链接与原文件指纹。存储费用、链接有效期和访问权限由存储账号负责。签名链接属于敏感资料，私有状态目录不能公开发布。

## 国内平台与 TikTok 发布

SAU 使用当前项目内的源码和独立 Python 环境。只有安装步骤记录并校验过解释器指纹时，环境中的解释器链接才可指向基础 Python；素材路径仍限定在项目内。配置步骤见源码仓库的 `docs/PUBLISHING.md`。

发布请求应包含平台、准确的账号别名、标题、正文与标签、本地素材，以及类型 `kind`（`video` 或 `note`）；可选 `YYYY-MM-DD HH:MM` 格式的定时时间，时区为 Asia/Shanghai。TikTok 使用 Clipcat，必须指定准确的 open id 和隐私选项。提交成功后仍需到创作者中心核对公开状态。需要人工登录时暂停。本技能不自动购买广告。
