# Configuration Reference

## .env — API 密钥与敏感配置

```bash
# LLM
DEEPSEEK_API_KEY=sk-...

# 自定义 provider（通过环境变量自动发现）
CUSTOM_API_KEY=...
CUSTOM_BASE_URL=https://...
CUSTOM_API_PROTOCOL=openai    # openai（默认）或 anthropic

# YouTube Data API（频道上传列表功能，可选）
YOUTUBE_API_KEY=...

# 文章投送
TELEGRAM_BOT_TOKEN=...        # Telegram Bot Token（@BotFather 获取）
TELEGRAM_CHAT_ID=...          # Telegram 频道/群组 ID
DISCORD_WEBHOOK_URL=...       # Discord Webhook URL
```

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

## 配置加载流程

1. `config.py` 读取 `config.ini`，返回 `(fast_conf, best_conf)` 两个配置字典
2. `llm.py` 根据 tier 选择对应配置，调用 litellm
3. 主模型失败 → 自动尝试 fallback
