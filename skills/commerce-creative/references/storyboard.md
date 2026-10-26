# 分镜格式与编写要求

## 商业创作：version 2

完整可编辑案例：[虚构绿豆饼](../assets/mung-bean-storyboard.json)。普通创作从此结构开始，业务判断方法见 [commercial.md](commercial.md)。version-1 仅用于兼容与技术试跑。

| 字段 | 要求 |
| --- | --- |
| version/id/revision/mode | 2、项目内方案标识、正整数版本、directed/explore/inspire；修订可加 parent_digest 和修改理由 |
| product | name、kind(real/fictional)、claims、visual_lock；fictional 还需 disclosure |
| claims | 每项 id/text/status(verified/fictional/unknown)/evidence；被脚本采用的声明必须已支持或明确虚构 |
| visual_lock | description、must_keep、avoid、reference_assets；没图用空数组，不能声称实物已还原 |
| sources | 唯一 id、type(web/vendor/user/local)、scope(product/category/reference/concept)、title、locator、accessed_at(YYYY-MM-DD)、summary、usage(owned/licensed/reference_only/unknown)。vendor/local 的 locator 是项目内报告路径，必须 sha256 |
| strategy | audience/situation/job/objective/angle/hook/proof/cta、claim_ids、evidence、assumptions、alternatives；alternative 含 angle/rationale/evidence，探索或灵感至少有不同的替代方向 |
| delivery | duration 必须等于镜头时间和；audio(required/silent)、narration_mode(generated/external/none)、subtitle_mode(post/generated/none)、min_short_side、duration_tolerance(秒，0–2)、ratio_tolerance(比例相对误差，0–0.05) |
| shots | 唯一 id、整数 duration、role(hook/proof/context/cta/proof_cta/hook_proof_cta)、purpose、claim_ids、visual、prompt、narration、subtitle、assets、acceptance(可观察标准数组) |
| platform/language/ratio/unknowns | 目标平台、语言、固定比例、明确未知项列表；空未知项也要写 [] |

第一镜是 hook，至少有 proof/proof_cta，最后是 cta/proof_cta；单镜短片可用 hook_proof_cta 承担三段目的。口播太密会警告，需要实际听音计时。真实商品缺少同一 SKU 的实物参考时只可保留草稿；明确用 product.visual_mode=concept 并填写 disclosure 后才能作为概念画面生成，验收仍是概念内容。参考素材另外标记 origin(real_product/concept) 和 rights(owned/licensed)，支持 image/video，原 role 与供应商限制继续有效。商品参考图是概念图时仍为概念交付。

导出使用已保存真源，CLI 自动附带 `creative_contract`。生成请求里不要手改提示词：改分镜并重新导出。参考图和供应商参数发生变化时重新准备并审核。`post` 字幕不会要求模型生成汉字，交给本地制作；概念披露由 render 在每镜字幕中烧录，仍需肉眼检查。

分镜 JSON 由当前 Agent 编写。CLI 的 `context` 只整理证据与提示资料，不能将其输出说成已经生成的创作结果。可以从仓库的 `examples/storyboard.json` 开始；仅安装 Skill 时，按下面的结构编写。

## 兼容技术格式 version 1

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
