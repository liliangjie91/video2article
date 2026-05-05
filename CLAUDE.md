# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

命令行工具箱：字幕 → 深度文章 → 图文

核心目标：从口语字幕中挖掘深度，产出有观点、有背景、有结构的优质长文，配上视频截图转为图文。

## 依赖与设置

```bash
pip install -r requirements.txt  # LLM, STT, yt-dlp, YouTube Transcript API 等
brew install ffmpeg              # 截图提取 + 音频提取 + yt-dlp 后处理需要
```

YouTube 字幕直取（`youtube-transcript-api`）无需 API Key。
YouTube Data API（频道上传列表功能）需要在 `.env` 设置 `YOUTUBE_API_KEY`。

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
subtitle.srt / video.mp4 / YouTube URL
        │
        ├──[YouTube URL]──→ download/youtube.py (字幕API直取，零下载)
        │                       └── 失败 → download/handle_yt_dlp.py (yt-dlp音频)
        │                                            └── STT
        │
        ├──[视频文件]─────→ stt/transcribe.py (可选前置，语音→字幕)
        │
        ▼
   [Stage 1: 预处理]         ← pipeline/preprocess.py   → 01_preprocessed.txt
   [Stage 2: 结构识别]       ← pipeline/structure.py    → 02_structure.json
   [Stage 3: 深度挖掘] ←核心 ← pipeline/insights.py     → 03_insights.json
   [Stage 4: 大纲生成]       ← pipeline/outline.py      → 04_outline.json
   [Stage 5: 逐段合成]       ← pipeline/synthesize.py   → 05_article.md
        │
        ▼
   [Step 2: 视频截图+图文合成] ← image/screenshot.py    → 06_illustrated.md
        │
        ▼
   [TTS: 文章→语音]          ← tts/speak.py (可选后置)
```

### 项目文件

- **`main.py`** — 薄 CLI 入口，仅 logging + argparse 定义，命令分发到 `commands.py`。
- **`commands.py`** — 所有命令处理函数 (`cmd_*`) + 核心流程 (`process_one`, `process_batch`)。
- **`delivery/`** — 文章投送模块。`__init__.py` 仅初始化；`deliver.py` 提供 `deliver_article()` 调度；各渠道 (`telegram.py`, `discord.py`) 实现 `deliver(title, body, file_path) -> bool` 接口；包内共享工具放 `_utils.py`。
- **`utils/__init__.py`** — 通用工具函数：`project_dir()`（输出路径确定）、`detect_input_type()`（输入格式检测）、字幕/音视频扩展名判断。
- **`utils/parser.py`** — 字幕解析统一接口，支持 SRT、VTT、Simple (`[HH:MM:SS] text`) 三种格式，输出统一的 `list[tuple[int, int, str]]`（start_ms, end_ms, text）。
- **`llm.py`** — 核心 LLM 封装。`chat()` 透传 config 给 litellm，主模型失败时自动 fallback。
- **`config.py`** — 两级配置加载 (`fast`/`best`)。
- **`download/`** — 下载模块。`__init__.py` 仅暴露常量；`_utils.py` 含缓存管理、URL 检测等内部工具；两个子模块 `handle_youtube_api.py` 和 `handle_yt_dlp.py` 分别处理 YouTube API 直取和 yt-dlp 兜底。缓存文件 `.download.cache` 以 `type,video_id,path` 格式存储。`get_cache(type, video_id)` 统一查询。

### 核心函数

- **`commands:process_one()`** — 统一入口：输入任意格式（SRT/音视频/URL/ID），自动检测类型并执行完整 pipeline。
- **`commands:process_batch()`** — 批量处理多个输入的核心循环，供 `cmd_batch` 和 future `uploads --process` 共用。
- **`commands:_run_article_pipeline()`** — SRT → 文章的五阶段管线（预处理 → 结构 → 深度挖掘 → 大纲 → 合成）。

### Pipeline 模块约定

每个 Stage 模块暴露一个 `run(input_path, output_dir) -> output_path` 函数，输出文件自动命名为 `0N_name.ext`。

## 包组织规范

```
__init__.py     # 仅包初始化（load_dotenv、logger、常量），不放实现代码
_utils.py       # 包内共享的内部工具函数，以 _ 前缀表明私有
module.py       # 公开 API，外部通过 from pkg.module import func 导入
```

- `__init__.py` 不做重导出（`from .module import func`），调用方直接 `from pkg.module import func`
- 内部工具放在 `_utils.py`，包外不应直接引用

## CLI

```bash
python main.py article <subtitle.srt> / <video.mp4> / <url>                # 字幕/音视频/url/video_id → 文章 （自动检测格式）
python main.py article --simple <input>                                    # 使用快速产出模式而非分步执行

# 单阶段调试
python main.py debug preprocess <subtitle.srt>
python main.py debug structure <01_preprocessed.txt>
python main.py debug insights <02_structure.json>               # 注：insights 输入含结构+原文
python main.py debug outline <03_insights.json>                 # Stage 4 大纲
python main.py debug synthesize <03_insights.json> <04_outline.json>  # Stage 5 逐段合成

# 周边
python main.py stt <video.mp4>
python main.py review <article.md>                    # 文章审阅 (单篇)
python main.py review <article.md> --interactive      # 交互式逐段审阅
python main.py review <article1.md> <article2.md>     # 文章对比 (多篇)

# URL 命令
python main.py info <url>                             # 获取视频信息（标题、可用字幕等）
python main.py download <url>                         # URL → SRT（API 直取 / yt-dlp+STT 兜底）
python main.py download --media audio <url>           # URL → 下载音频文件
python main.py uploads <@channel>                     # 频道最新视频列表

# 批处理
python main.py batch <url1> <url2>                         # 多个输入逐个生成文章
python main.py batch -f urls.txt                            # 从文件读输入列表
python main.py batch --from-channel @channel                # 从频道拉取视频处理
python main.py batch --from-channel @channel --limit 5      # 限制总处理数量
python main.py batch url1 --from-channel @channel           # 混合来源
```

# 投送
python main.py deliver <article.md>                         # Telegram 投送（默认）
python main.py deliver <article.md> --channel discord       # 指定渠道
python main.py deliver <article.md> --all                   # 所有可用渠道
python main.py deliver <article.md> --as-text               # 文本形式（默认发送 .md 文件）

`article`、`download`、`review` 命令支持 `--dry-run` 参数进行空跑验证。

## 输出结构

每个 pipeline 一个独立文件夹：

```
output/<channel_title>/<uploaddate>_<videoid>/
├── videoid.mp4 / .m4a            # yt-dlp 下载的原始音视频
├── videoid.srt                   # YouTube API 直取字幕（0 下载）
├── 01_preprocessed.txt           # Stage 1
├── 02_structure.json             # Stage 2
├── 03_insights.json                # Stage 3 深度挖掘（JSON，含结构字段）
├── 04_outline.json                 # Stage 4 写作大纲
├── 05_article.md                   # Stage 5 逐段合成
├── 06_illustrated.md               # 图文合成（可选）
├── screenshots/
└── llm_logs/
```

### 输出规则

| 步骤 | 默认输出路径 |
|------|-------------|
| 下载字幕/音视频 | `output/<channel>/<date>_<videoid>/<videoid>.<ext>` |
| STT 转写 | 输入文件所在目录 |
| 文章管线（Stage 1-5） | 输入文件所在目录 |
| 截图 | pipeline 目录下的 `screenshots/` |

**整体原则**：一个 pipeline = 一个文件夹，从下载到最终文章所有产物集中存放。

## 命名

项目 logger name 统一使用 `video2article`。

## 测试

测试文件在 `tests/` 目录，149 个测试：

- **第一梯队**（纯函数，无需 mock）：`test_parser.py`、`test_utils.py`、`test_download_cache.py`、`test_config.py`
- **第二梯队**（mock LLM）：`test_preprocess.py`、`test_structure.py`、`test_insights.py`、`test_outline.py`、`test_synthesize.py`、`test_simple.py`、`test_commands.py`

运行：`pytest -v`。CI 通过 `.github/workflows/test.yml` 自动执行。
