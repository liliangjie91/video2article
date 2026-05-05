# video2article

**把视频里的口水话，变成值得读的长文。**

你刷到一个视频，内容不错，但总觉得拖沓、散乱、看过就忘。  
这个工具把视频字幕拆解、深挖、重组，输出一篇有骨架、有观点、有背景的深度文章。

## 它能做什么

从视频链接到深度文章，一行命令：

```bash
# 给一个 视频链接(Youtube/BiliBili/...) 或 Youtube video ID，自动出文章
python main.py article https://youtube.com/watch?v=xxxxx
python main.py article dQw4w9WgXcQ

# 批量处理一整个频道的最新视频
python main.py batch --from-channel @TED -l 5
```

## 快速开始

```bash
pip install -r requirements.txt
brew install ffmpeg           # macOS
```

### 配置
#### config.ini
在 `config.ini` 中指定模型档位,或stt模型位置等配置

```yml
[fast]
model = deepseek/deepseek-v4-flash
fallback = custom/MiniMax-M2.7-highspeed
[best]
model = deepseek/deepseek-v4-flash
fallback = deepseek/deepseek-v4-flash
[top]
model = deepseek/deepseek-v4-pro

[stt]
model_dir = /Volumes/data1/bigfile/hfmodel
```

#### .env
`.env` 存放API KEY等不可见信息
支持所有 litellm 兼容的 provider（DeepSeek、OpenAI、Anthropic 等）或自定义 。
```bash
YOUTUBE_API_KEY=... (可选)

# LLM配置
DEEPSEEK_API_KEY=sk-...
# 自定义LLM配置，XXXX_API_KEY 即对应 xxxx provider
CUSTOM_API_KEY=...
CUSTOM_BASE_URL=https://.../v1
CUSTOM_MODELS=...
CUSTOM_API_PROTOCOL=openai
```

## 管线流程

```
字幕/音频
  │
  ▼
[STT] faster-whisper      → 00_subtitle.srt    优先下载使用字幕，获取不到则下载音视频STT转字幕
  │
  ▼
[Stage 1 预处理]           → 01_preprocessed.txt  清洗口语噪声
[Stage 2 结构识别]         → 02_structure.json     语义分段 + 论证骨架
[Stage 3 深度挖掘]    ◀──  → 03_insights.md        挖掘隐含假设/背景/关联
[Stage 4 合成撰写]         → 04_article.md          成文
  │
  ▼ (可选)
[视频截图 + 图文合成]      → 05_illustrated.md
[文章 → 语音]             → TTS
```

每个阶段都可单独运行、替换，输出文件。

### Stage 3 是核心

结构识别只是分段落，真正的价值在 Stage 3。它对每段做五个维度的分析：

- **核心提炼** — 一句话说清楚本段在说什么
- **隐含假设** — 说话者默认了什么前提
- **背景补充** — 相关的历史、科学或文化背景
- **延伸关联** — 和其他事件/理论的联系
- **批判追问** — 换个视角能看到什么

结果不是编辑成文，而是做笔记——方便你审阅、修改、补充，满意了再进 Stage 4 合成。

## 常用命令

```bash
# ── 核心亮点：视频链接 / ID → 深度文章 ──
python main.py article <video.mp4> / <subtitle.srt>      # 本地文件；
python main.py article --tier fast dQw4w9WgXcQ           # 接受 Youtube video ID 直接输入 --tier fast/best 模型等级选择，config.ini配置
python main.py article  <YouTube URL> --simple           # 视频 URL， 支持非Youtube例如BiliBili；--simple 快速产出模式，调用一次LLM直接输出结果

# ── 批量处理：一整个频道 ──
python main.py batch --from-channel @TED -l 5 --simple  # 频道最新 5 个视频自动处理
python main.py batch -f video_ids.txt                   # 从文件读列表
python main.py batch url1 --from-channel @channel       # 混合来源

# 单步调试
python main.py debug preprocess <subtitle.srt>
python main.py debug structure  <01_preprocessed.txt>
python main.py debug insights   <02_structure.json>
python main.py debug synthesize <02_structure.json> <03_insights.md>

# 周边
python main.py stt      <video/audio file>          # 语音转文字
python main.py review   <article.md>               # 审阅
python main.py info     <URL/VideoID>          # 获取视频信息：可用字幕，标题，频道名等
python main.py download <URL/VideoID>          # URL → SRT（默认）；支持参数 --media video/audio 下载视频/音频文件
python main.py uploads  <@channel>                 # 频道最新视频列表
```

## 输出目录

每个 pipeline 一个独立文件夹，从下载到最终文章的所有产物都在里面：

```
output/<channel_title>/<uploaddate>_<videoid>/
├── videoid.mp4 / .m4a            # 下载的原始音视频（yt-dlp）
├── videoid.srt                   # YouTube API 直取的字幕 / STT提取的字幕
├── 01_preprocessed.txt           # Stage 1: 清洗后文本
├── 02_structure.json             # Stage 2: 论证骨架
├── 03_insights.md                # Stage 3: 深度挖掘笔记
├── 04_article.md                 # Stage 4: 最终文章
├── 05_illustrated.md             # 图文合成（可选）
├── screenshots/                  # 视频关键帧
└── llm_logs/                     # LLM 请求/响应日志
```

- 下载（字幕或音视频）自动按 `output/<channleTitle>/<yyyymmdd>_<videoId>/` 组织
- STT 转写的字幕默认输出到音视频所在目录
- 文章管线（preprocess → structure → insights → synthesize）默认输出到输入文件所在目录
- 整体原则：**一个 pipeline = 一个文件夹**，不存在中间产物散落的问题

## 设计原则

- **文件即接口** — 每个阶段的输出都是普通文本文件，可以随时查看、修改、替换
- **分治而非黑盒** — 不做一键全自动，每个阶段单独可控
- **深度优先** — 不满足于摘要，追求原文之外的信息增量
- **litellm 接入** — 通过 litellm 接入 100+ LLM provider + 可自定义 provider
