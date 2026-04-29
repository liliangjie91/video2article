# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

命令行工具箱：字幕 → 深度文章 → 图文

核心目标：从口语字幕中挖掘深度，产出有观点、有背景、有结构的优质长文，配上视频截图转为图文。

## 依赖与设置

```bash
pip install litellm         # 必需 — LLM API 调用 (统一调度 100+ provider)
pip install anthropic       # DFDC 等 Anthropic-format 自定义 provider 需要
pip install faster-whisper   # STT 模块需要
brew install ffmpeg         # 截图提取 + 音频提取需要
```

模型配置在 `config.ini`，API 密钥在 `.env`（不入库）：
- 双档位：`[fast]`（轻量模型）和 `[best]`（强模型）
- model 格式 `provider/model-name`，provider 决定路由
- litellm 已知 provider（`deepseek/`、`openai/`、`anthropic/` 等）直接透传
- 自定义 provider 通过约定环境变量自动发现：
  - `{PROVIDER}_API_KEY` — API 密钥
  - `{PROVIDER}_BASE_URL` — API 地址
  - `{PROVIDER}_API_PROTOCOL` — `openai`（默认）或 `anthropic`
- 每个 tier 可选 `fallback` 字段，主模型失败时自动降级

## 架构

```
subtitle.srt / video.mp4
        │
        ▼
   [STT: 语音→字幕]          ← stt/transcribe.py (可选前置)
        │
        ▼
   [Stage 1: 预处理]         ← pipeline/preprocess.py   → 01_preprocessed.txt
   [Stage 2: 结构识别]       ← pipeline/structure.py    → 02_structure.json
   [Stage 3: 深度挖掘] ←核心 ← pipeline/insights.py     → 03_insights.md
   [Stage 4: 合成撰写]       ← pipeline/synthesize.py   → 04_article.md
        │
        ▼
   [Step 2: 视频截图+图文合成] ← image/screenshot.py    → 05_illustrated.md
        │
        ▼
   [TTS: 文章→语音]          ← tts/speak.py (可选后置)
```

### 关键抽象

- **`llm.py`** — 核心 LLM 封装。`chat()` 透传 config 给 litellm，主模型失败时自动 fallback。所有 provider 统一由 litellm 调度。自动记录请求/响应到 `llm_logs/`。
- **`config.py`** — 两级配置加载 (`fast`/`best`)。已知 provider 返回 `{model}`；未知 provider 按约定从 `.env` 读取 `{PROVIDER}_API_KEY` 等变量，映射为 `openai/` 或 `anthropic/` 前缀再传给 litellm。
- **`utils/parser.py`** — 字幕解析统一接口，支持 SRT、VTT、Simple (`[HH:MM:SS] text`) 三种格式，输出统一的 `list[tuple[int, int, str]]`（start_ms, end_ms, text）。

### Pipeline 模块约定

每个 Stage 模块暴露一个 `run(input_path, output_dir) -> output_path` 函数，输出文件自动命名为 `0N_name.ext`。

## CLI

```bash
python main.py article <subtitle.srt>                  # 字幕 → 文章 (Step 1)
python main.py illustrate <article.md> --video <mp4>    # 文章 → 图文 (Step 2)
python main.py full <video.mp4>                         # 全流程

# 单阶段调试
python main.py preprocess <subtitle.srt>
python main.py structure <01_preprocessed.txt>
python main.py insights <01_preprocessed.txt> <02_structure.json>
python main.py synthesize <01_preprocessed.txt> <02_structure.json> <03_insights.md>

# 周边
python main.py stt <video.mp4>
python main.py speak <article.md>
python main.py review <article.md>                    # 文章审阅 (单篇)
python main.py review <article1.md> <article2.md>     # 文章对比 (多篇)
```

所有命令支持 `--dry-run` 参数进行空跑验证。

## 输出结构

```
output/<source_name>/
├── 00_subtitle.srt
├── 01_preprocessed.txt
├── 02_structure.json
├── 03_insights.md
├── 04_article.md
├── 05_illustrated.md
├── screenshots/
└── llm_logs/
```

## 命名

项目 logger name 统一使用 `video2article`。
