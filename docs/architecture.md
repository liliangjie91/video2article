# Architecture

## Pipeline 流程

```
subtitle.srt / video.mp4 / YouTube URL
        │
        ├──[YouTube URL]──→ download/handle_youtube_api.py (字幕API直取，零下载)
        │                       └── 失败 → download/handle_yt_dlp.py (yt-dlp音频)
        │                                            └── stt/transcribe.py
        │
        ├──[视频文件]─────→ stt/transcribe.py (可选前置，语音→字幕)
        │
        ▼
   [Stage 1: 预处理]         ← pipeline/preprocess.py   → 01_preprocessed.txt
   [Stage 2: 结构识别]       ← pipeline/structure.py    → 02_structure.json
   [Stage 3: 深度挖掘] ←核心 ← pipeline/insights.py     → 03_insights.json
        │                      └── 每段附带 concept_queries + explore_queries
   [Stage 4: 大纲生成]       ← pipeline/outline.py      → 04_outline.json
        │                      └── LLM 对搜索词去重筛选 → search_queries
        │
        ├──[--search]──────→ 搜索阶段（执行 outline 中的 search_queries）
        │                       search/ (Tavily/Brave/DuckDuckGo) → 原始结果
        │                       search/integrate.py → search_references.json
        │
   [Stage 5: 逐段合成]       ← pipeline/synthesize.py   → 05_article.md
        │
        ├──[--search]──────→ pipeline/synthesize_link.py (插入引用链接) → 05_article_link.md
        │                      └── 不覆盖原文，跨段落同词不重复链接
        │
        ▼
   [截图+图文合成]           ← image/screenshot.py      → 06_illustrated.md
        │
        ▼
   [TTS: 文章→语音]          ← tts/speak.py (可选后置)
```

### Stage 3 是核心

结构识别只是分段落，Stage 3 对每段做六个维度的分析：
- **核心提炼** — 一句话说清楚本段在说什么
- **隐含假设** — 说话者默认了什么前提
- **背景补充** — 相关的历史、科学或文化背景
- **延伸关联** — 和其他事件/理论的联系
- **批判追问** — 换个视角能看到什么
- **搜索建议** — 生成 concept_queries（实体词，查百科）+ explore_queries（探索短语，深度追问）

这些搜索词在 Stage 4（大纲）阶段由 LLM 统一去重筛选，最终由 search/integrate 执行检索。
        │
   [Stage 5: 逐段合成]       ← pipeline/synthesize.py   → 05_article.md
        │
        ├──[--search]──────→ pipeline/synthesize_link.py (插入引用链接) → 05_article_link.md
        │
        ▼
   [截图+图文合成]           ← image/screenshot.py      → 06_illustrated.md
        │
        ▼
   [TTS: 文章→语音]          ← tts/speak.py (可选后置)
```

### Stage 3 是核心

结构识别只是分段落，Stage 3 对每段做五个维度分析：
- **核心提炼** — 一句话说清楚本段在说什么
- **隐含假设** — 说话者默认了什么前提
- **背景补充** — 相关的历史、科学或文化背景
- **延伸关联** — 和其他事件/理论的联系
- **批判追问** — 换个视角能看到什么

## 模块职责

| 模块 | 职责 |
|------|------|
| `main.py` | 薄 CLI 入口，初始化日志 + argparse，命令分发到 `commands.py` |
| `commands.py` | 命令处理函数 (`cmd_*`) + 核心流程 (`process_one`, `process_batch`) |
| `llm.py` | LLM 封装，`chat()` 透传 config 给 litellm，主模型失败自动 fallback |
| `config.py` | 两级配置加载 (`fast`/`best`) |
| `utils/__init__.py` | 通用工具：`project_dir()`、`detect_input_type()`、文件扩展名判断 |
| `utils/logging.py` | 集中日志配置（文件 + 控制台）、`log_banner()` 醒目标识 |
| `utils/parser.py` | 字幕解析统一接口，支持 SRT/VTT/Simple 三种格式 |
| `download/` | 下载模块：YouTube API 直取字幕 + yt-dlp 兜底 |
| `pipeline/` | 五阶段文章管线，stage 3 附带搜索词生成，stage 4 附带搜索词筛选 |
| `pipeline/synthesize_link.py` | 文章后处理：基于搜索结果插入 `[词](url)` 内联引用链接，跨段落同词不重复，输出 `05_article_link.md` 不覆盖原文 |
| `delivery/` | 文章投送：Telegram、Discord |
| `image/` | 视频截图 + 图文合成 |
| `search/` | 联网搜索（Tavily / Brave / DuckDuckGo），含集成整合模块 |
| `search/integrate.py` | 执行 outline search_queries + LLM 去重/排序/整合 |

### Pipeline 模块约定

每个 Stage 暴露 `run(input_path, output_dir) -> output_path`，输出自动命名 `0N_name.ext`。

## 核心函数

- **`commands:process_one()`** — 统一入口：任意输入格式 → 自动检测类型 → 完整 pipeline
- **`commands:process_batch()`** — 批量处理核心循环
- **`commands:_run_article_pipeline()`** — SRT → 文章的五阶段管线 + 搜索结果整合 + 链接后处理
- **`search.integrate:search_from_outline()`** — 从 outline search_queries 执行检索并整合
- **`pipeline.synthesize_link:run()`** — 文章后处理，插入内联引用链接，跨段落去重，输出 `05_article_link.md`

## 输出结构

```
output/<channel_title>/<uploaddate>_<videoid>/
├── videoid.mp4 / .m4a            # yt-dlp 下载的原始音视频
├── videoid.srt                   # YouTube API 直取字幕 / STT 转写字幕
├── 01_preprocessed.txt           # Stage 1
├── 02_structure.json             # Stage 2
├── 03_insights.json              # Stage 3 深度挖掘
├── 04_outline.json               # Stage 4 大纲
├── search_references.json        # 搜索结果整合（--search 开启时）
├── 05_article.md                 # Stage 5 初版文章
├── 05_article_link.md            # 引用链接版本（--search 开启时，不覆盖 05_article.md）
├── 06_illustrated.md             # 图文合成（可选）
├── screenshots/
└── llm_logs/
```

**原则**：一个 pipeline = 一个文件夹，所有产物集中存放。

## 包组织规范

```
__init__.py     # 仅包初始化（load_dotenv、logger、常量），不放实现代码
_utils.py       # 包内共享的内部工具函数（_ 前缀表明私有）
module.py       # 公开 API，外部通过 from pkg.module import func 导入
```

- `__init__.py` 不做重导出
- 内部工具放 `_utils.py`，包外不应直接引用
