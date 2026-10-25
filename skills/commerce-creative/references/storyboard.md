# 分镜格式与编写要求

分镜 JSON 由当前 Agent 编写。CLI 的 `context` 只整理证据与提示资料，不能将其输出说成已经生成的创作结果。可以从仓库的 `examples/storyboard.json` 开始；仅安装 Skill 时，按下面的结构编写。

## 必填结构

根对象需要以下字段：

- `version: 1`：分镜格式版本。
- `product`：包含商品名 `name`，以及记录真实商品事实的 `facts` 数组。
- `sources`：来源数组；每条包含 `provider`，以及 `report` 或 `url`。
- `platform`、`language`、`ratio`：目标平台、语言、画面比例。
- `shots`：镜头数组。

每个镜头需要唯一 `id`、以秒为单位的整数 `duration`、画面描述 `visual` 和生成提示词 `prompt`；可选口播 `narration`、字幕 `subtitle`、素材 `assets`。

每条素材只能指定一个项目内 `path` 或已获授权的 HTTPS `url`，并注明 `kind`（image/video/audio）与合适的角色（first_frame/last_frame/reference_image/reference_video/reference_audio）。

## 事实、来源与创意

区分供应商洞察和新提出的创意建议。商品事实来自用户或已授权的商品证据，不能从参考素材抄入未经证实的功效、评分或销量。标注来源视频时间码时，必须有实际观察到的视频证据。

口播长度和镜头节奏应匹配所选时长；数值校验通过不代表创意质量合格。

## 校验与导出

使用 `storyboard-check` 校验；通过 `storyboard-export --provider minimax|seedance|clipcat --out requests-v1` 导出逐镜头请求。导出不会生成或提交任务。

MiniMax H3 每个镜头限制为 4–15 秒。已批准的镜头过长时，在分镜中拆分并重新审核，不暗中缩短。Seedance 2.5 可支持更长镜头，具体受当前供应商限制。Clipcat 需要选用实时模型目录中的模型，并带 `--catalog-checked`；这个参数表示 Agent 已核对，命令本身不会调用 API 验证。

项目配置中默认图片服务为 Seedream，这只是请求构建的技术默认值。实际创作图片时让用户选择，不擅自选择或替换供应商。生成提示词保留用户修改后的镜头提示、口播及字幕文字。拿到结果后仍须检查生成文字、声音和商品外观一致性。
