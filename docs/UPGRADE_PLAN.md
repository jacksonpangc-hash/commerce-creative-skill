# 商业创作闭环实施计划

> 使用 executing-plans 在当前专用分支实施；用户已明确要求补齐能力，不重复同范围访谈。规格真源：SPEC.md 的 AC21–AC28。

## 接口与步骤

1. `campaign.py`：`check_campaign(story, ws=None)`、`campaign_requests(story, provider, ws, ...)`、`creation_context(...)`。对应 AC21–24；先观察空证据、竞品证据串用、缺钩子/证明/CTA、脚本修改后的请求失效测试失败，再实现。
2. `inspection.py`：`inspect_media(ws, file, out, ...)`、`render_media(ws, story, segments, out, ...)`。可选 PyAV/Pillow/imageio-ffmpeg 本地组件，不改系统软件。对应 AC25；坏文件、比例/时长不符、缺音轨、已有输出、字幕/配音和原片保留测试先失败，再实现。
3. `acceptance.py`：绑定成片/分镜/技术报告的审阅模板与 `accept_campaign`；逐镜头、全程视听覆盖、所有检查均完成才通过。对应 AC26；未知、片段审阅、旧指纹、遗漏镜头先失败。
4. `http.py`：固定公网连接并保留 TLS SNI，显式公共解析兼容；对应 AC27。fake-DNS、内网/重绑定、重定向与大小上限测试先失败。
5. CLI/中文文档/绿豆饼案例/包与安装清单：对应 AC28。真实本地命令演练，独立 Skill 行为复测及最终代码审查。安装前保留旧版回滚备份；只替换 commerce-creative。付费生成与社交发布不在本轮开发验证范围。

## 审查重点

- 来源有网址不等于支持 SKU 声明；虚构设定不得标作真实证明。
- 文件存在不等于实物参考；无实物时保留概念交付边界。
- 技术通过不得自动标作创意通过；只有采样不得冒充全程观看。
- 失败/超时与 UNKNOWN 不能触发重投；旧水杯授权不覆盖新案例。
- 媒体可选组件缺失应给可执行安装路径；不修改全局配置、不接管其他项目。

执行证据持续追加 PROGRESS.md；完整测试、独立审查、重定位包验证在交付前完成。
