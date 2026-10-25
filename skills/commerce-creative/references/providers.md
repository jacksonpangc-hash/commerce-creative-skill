# 服务连接说明

直连服务的凭据只在执行时从进程环境变量读取；工具不会自动加载 `.env` 文件。使用密钥管理工具或明确配置环境变量。`doctor` 只报告是否存在，不输出密钥，也不进行线上认证。运行时请求与配置 JSON 不接受凭据字段。

| 服务 | 凭据环境变量 | 接口与限制 |
| --- | --- | --- |
| MiniMax 视频 | MINIMAX_API_KEY | `https://api.minimax.cn/v2/video_generation`；模型必须为 `MiniMax-H3`；轮询 `/v2/query/video_generation/{task_id}`；原生结果字段为 `task.content.url`。 |
| MiniMax 图片 | MINIMAX_API_KEY | `/v1/image_generation`，模型 `image-01`；通过官方角色参考接口最多提供一张参考图。不保证商品外观完全一致。 |
| Seedance 视频 | ARK_API_KEY | `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`；默认 `doubao-seedance-2-5-260628`；账号需要模型调用权限。 |
| Seedream 图片 | ARK_API_KEY | `/api/v3/images/generations`；默认 `doubao-seedream-5-0-pro-260628`；本适配器每次请求一张结果，最多十张参考图。 |
| OpenAI 图片 | OPENAI_API_KEY | `https://api.openai.com/v1/images/generations`，或 JSON `/v1/images/edits`；默认 `gpt-image-2.5-flare`，可选 Sunburst。不能假定 ChatGPT 订阅包含 API 权益。 |
| 蝉妈妈相关洞察 | CHANJING_ACCESS_TOKEN | `https://open-api.chanjing.cc/open/v1/creative/creative_briefing`；除 HTTP 状态外，还须检查响应正文的业务码。 |
| 有米云洞察 | YOUCLOUD_API_KEY | 先以 GET 查询身份，再调用 NDJSON `/api/rpc/ai/claw/v1/chat`；认证前缀 `YC_API_KEY`；对话模式为 2/3；读取超时为 650 秒。 |
| Clipcat | 原客户端配置 | 调用外部 Clipcat CLI，沿用原服务与计费；不随本技能分发原客户端。 |

## 蝉镜 token 与数据边界

蝉镜也支持通过 app id 和 secret 获取 token，但刷新会使旧 token 失效。只有请求包含 `allow_token_refresh: true` 且执行明确带 `--allow-token-refresh` 时才刷新；其余情况使用已有 token。未经授权，不刷新其他应用正在使用的 token。

品类简报不能替代 TikTok 或蝉妈妈原始商家、达人、GMV 数据表。原 Clipcat 查询仍可使用；有米云报告可见内容取决于账号权益。

## 接口地址与参考素材

API 地址明确固定为上表官方服务源，不将密钥发给自定义地址。火山方舟要求参考视频使用 URL 时，单独批准 `stage` 请求，使用用户自己提供的 HTTPS 预签名 PUT 与读取链接。不能虚构公网链接、绕过人脸或素材授权，或上传到未经说明的站点。

图片、音频上传和直连视频能力仍受各家格式与大小限制；超限内容应明确拆分或暂存。首尾帧模式不能与参考素材模式混用。

## 使用前核验

模型 ID、能力、价格与账号资格会变化，真实调用前应重新核实。调用失败不代表允许自动切换供应商。账号权限、创意质量及真实服务验收，应与离线接口测试分别报告。
