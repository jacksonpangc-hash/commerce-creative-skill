# 快速开始

## 1. 选择安装方式

只需要 Agent Skill 时，按[仓库首页](../README.md)安装。需要独立 CLI、格式示例或国内发布引擎配置时，克隆完整仓库。使用 Python 3.10 或更新版本，核心不依赖第三方 Python 包。

可在独立环境中安装 CLI：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/commerce-creative --version
```

Windows 将上述解释器路径换成 `.venv\Scripts\python.exe`，命令换成 `.venv\Scripts\commerce-creative.exe`；也可直接运行源码中的 `scripts/commerce.py`。

## 2. 先核对真实商品事实

提供商品资料、目标平台、语言、时长和需要的产物。沿用已确认选择，只补影响结果的信息。用来源支持功效、材质、价格与销量；没有证据的项目标为待确认。

## 3. 选择洞察与脚本编排

数据源可选 Clipcat、蝉镜创意雷达或有米云。选择服务后，再配置对应环境变量。蝉镜返回品类创意报告，由当前 Agent 结合商品事实写脚本与分镜；报告不是逐条素材销量数据库。

分镜可参考 `examples/storyboard.json`。这是合成格式示例，不能当作真实案例。修改 `visual`、`prompt`、`narration` 或 `subtitle` 后重新检查，再导出新目录中的请求。

## 4. 先准备，不生成

在项目中运行首页的离线命令。`prepare` 输出计划 ID、请求、素材指纹、操作范围和费用状态。还没有执行付费请求。保留 `UNKNOWN` 费用，不用示例数字代替报价。

## 5. 审核后执行与核对

审核模型、提示词、素材、费用，以及发布时的账号与时间。具体授权标记见[命令流程](../skills/commerce-creative/references/cli.md)。生成后查原任务、下载结果并检查商品一致性、文字、声音及内容质量。超时先核对历史，不重复提交。

国内平台发布另需[项目内发布环境](PUBLISHING.md)和用户登录。通过创作者中心核对准确作品后，才能确认发布或排期结果。素材生成不自动授权发布，也不授权广告投放。

## 6. 保存与升级

私有输入、报告、回执和结果保存在项目内；不要提交 `.commerce/`、`.env` 或 Cookie。升级前备份自定义 Skill，按[回滚说明](ROLLBACK.md)逐项比较。原 Clipcat 不受本 Skill 停用影响。
