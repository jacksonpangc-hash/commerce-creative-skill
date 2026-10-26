# 绿豆饼：完整概念案例

本目录可随开源仓库公开，只有虚构设定和公开来源。真实密钥、任务、供应商签名链接、下载视频和个人路径只留在项目 `.commerce/` 中。

1. 阅读 `品类洞察与创意判断.md`，区分公开品类资料、虚构商品和待证假设。
2. `product.json` 是商品设定，`sources.json` 是一手来源，`storyboard.json` 是 version-2 商业分镜。默认定向分析；需要比较时把 `mode` 改成 `explore` 或 `inspire`，沿用已有替代角度。
3. 在当前项目初始化后，运行 `storyboard-check`，再运行 `storyboard-export --provider minimax --out requests-v1`。不会联网。没有参考图时只作为待审稿，不声称实物还原。
4. `image-minimax.json` 是一张统一商品概念图请求。真实生成需批准费用。检查概念图后，将其项目内路径写入 `product.visual_lock.reference_assets`，注明 `kind:image`、`role:reference_image`、`origin:concept`、`rights:owned`。更新 revision，再导出新请求，避免复用旧计划。
5. 把每个下载镜头写入映射文件，例如 `{"s1":"outputs/shot1.mp4","s2":"outputs/shot2.mp4","s3":"outputs/shot3.mp4"}`；用 `render` 标准化、拼接并烧录确定性字幕与概念披露。
6. 对最终文件运行 `media-inspect`，再用 `review-template` 生成审阅表。Agent/用户观看整片并听音后，填写实际观察到的时间点、商品外观与问题，通过 `acceptance-check` 检查。

本地测试用合成色块视频验证制作程序，不把它冒充绿豆饼真实成片。真实案例只有获得单独授权并完成生成与视听审阅后才登记通过。当前真实视频状态见本地交付记录，开源示例不伪造成交或投放效果。

完整命令见 Skill 的 `references/commercial.md` 和 `references/cli.md`。原有所有供应商选择均保留；此案例不购买数据、不发布平台、不自动付费重试。
