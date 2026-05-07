# video2article

**把视频里的口水话，变成值得读的长文。**

刷到好视频但觉得拖沓、散乱、看过就忘？这个工具把视频字幕拆解、深挖、重组，输出一篇有骨架、有观点、有背景的深度文章。

## 快速开始

```bash
pip install -r requirements.txt
brew install ffmpeg           # macOS，截图提取需要
```

配置 `config.ini`（模型档位）和 `.env`（API 密钥），详见 [docs/config.md](docs/config.md)。

## 常用命令

```bash
# 视频链接 / ID → 深度文章（核心功能）
python main.py article https://youtube.com/watch?v=xxxxx
python main.py article dQw4w9WgXcQ
python main.py article <url> --simple            # 快速产出模式

# 批量处理一整个频道
python main.py batch --from-channel @TED -l 5

# 文章投送
python main.py deliver <article.md>              # 默认 Telegram
python main.py deliver <article.md> --all        # 所有可用渠道

# 单步调试
python main.py debug preprocess <subtitle.srt>
python main.py debug insights   <02_structure.json>
```

完整命令参考见 [docs/cli.md](docs/cli.md)。

## 设计原则

- **文件即接口** — 每阶段输出都是普通文本文件，可随时修改替换
- **分治而非黑盒** — 不做一键全自动，每个阶段单独可控
- **深度优先** — 不满足于摘要，追求原文之外的信息增量
- **litellm 接入** — 100+ LLM provider 支持

详见 [docs/design.md](docs/design.md)。

## 管线流程

```
字幕/音频 → [Stage 1 预处理] → [Stage 2 结构识别] → [Stage 3 深度挖掘] → [Stage 4 大纲] → [Stage 5 合成] → 文章
```

Stage 3 是核心：对每段做核心提炼、隐含假设、背景补充、延伸关联、批判追问。

管线详情见 [docs/architecture.md](docs/architecture.md)。

## 文档总览

| 文件 | 内容 |
|------|------|
| [docs/cli.md](docs/cli.md) | 完整 CLI 命令参考 |
| [docs/config.md](docs/config.md) | .env + config.ini 配置参考 |
| [docs/architecture.md](docs/architecture.md) | 管线流程、模块职责、输出结构 |
| [docs/design.md](docs/design.md) | 设计原则、包组织规范 |
| [CLAUDE.md](CLAUDE.md) | Agent 开发指南 |
