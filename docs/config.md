# Configuration Reference

## .env — API 密钥与敏感配置

复制 `.env.example` 为 `.env`，按需填入密钥：

```bash
cp .env.example .env
```

`.env.example` 包含所有可用的环境变量及详细注释。各变量的作用说明：

| 变量 | 用途 | 必需 |
|------|------|------|
| `DEEPSEEK_API_KEY` (或 `OPENAI_API_KEY` 等) | LLM 调用 | 是 |
| `CUSTOM_API_KEY` + `CUSTOM_BASE_URL` | 自定义 LLM provider | 按需 |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram 投送 | 按需 |
| `DISCORD_WEBHOOK_URL` | Discord 投送 | 按需 |
| `YOUTUBE_API_KEY` | 频道视频列表 (`uploads`) | 仅 uploads |

**自定义 provider 约定**：`{PROVIDER}_API_KEY` + `{PROVIDER}_BASE_URL` + `{PROVIDER}_API_PROTOCOL`（`openai` 或 `anthropic`，默认 `openai`）。config.ini 中以 `custom/` 前缀引用。

## config.ini — 模型与功能配置

### 模型档位

```ini
[fast]
model = deepseek/deepseek-v4-flash
fallback = custom/MiniMax-M2.7-highspeed

[best]
model = deepseek/deepseek-v4-flash
fallback = deepseek/deepseek-v4-flash

[top]
model = deepseek/deepseek-v4-pro
```

**双档位机制**：`fast` 轻量快速，`best` 高质量。`top` 为保留档位。

### model 格式

`provider/model-name` — provider 决定路由：
- **已知 provider**（deepseek/、openai/、anthropic/ 等）：litellm 直接透传
- **自定义 provider**：通过约定环境变量自动发现：
  - `{PROVIDER}_API_KEY` — API 密钥
  - `{PROVIDER}_BASE_URL` — API 地址
  - `{PROVIDER}_API_PROTOCOL` — `openai`（默认）或 `anthropic`

### fallback

每个 tier 可选 `fallback` 字段，主模型失败时自动降级。

### STT 配置

```ini
[stt]
model_dir = /path/to/whisper/models
```

### Delivery 配置

```ini
[delivery]
default_channels = telegram
```

`default_channels` 为逗号分隔的渠道列表，优先级低于 CLI `--channel` / `--all` 参数，高于 `deliver_article()` 函数内置的 `["telegram"]` 默认值。

可用渠道：`telegram`、`discord`。

## 配置加载流程

1. `config.py` 读取 `config.ini`，返回 `(fast_conf, best_conf)` 两个配置字典
2. `llm.py` 根据 tier 选择对应配置，调用 litellm
3. 主模型失败 → 自动尝试 fallback
