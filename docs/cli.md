# CLI Reference

## article — 字幕/视频/URL → 文章

```bash
python main.py article <subtitle.srt>          # 本地字幕文件
python main.py article <video.mp4>             # 本地视频（自动 STT）
python main.py article <youtube_url>           # YouTube URL
python main.py article <video_id>              # YouTube video ID
python main.py article <url> --simple          # 快速产出模式（一次 LLM 调用）
python main.py article <url> --tier fast       # 指定模型档位
python main.py article <url> --dry-run         # 空跑验证
```

输入自动检测类型（SRT/音视频/URL/ID）。

## debug — 单阶段调试

```bash
python main.py debug preprocess   <subtitle.srt>
python main.py debug structure    <01_preprocessed.txt>
python main.py debug insights     <02_structure.json>
python main.py debug outline      <03_insights.json>
python main.py debug synthesize   <03_insights.json> <04_outline.json>
```

每个 stage 输出到 `0N_name.ext`，输入前一步的输出文件。

## deliver — 文章投送

```bash
python main.py deliver <article.md>                        # 默认渠道（config.ini > telegram）
python main.py deliver <article.md> --channel discord      # 指定渠道
python main.py deliver <article.md> --all                  # 所有可用渠道
python main.py deliver <article.md> --as-text              # 文本形式（默认发 .md 文件）
```

渠道：`telegram`（Bot API）、`discord`（Webhook）。

优先级：`--channel`/`--all` > `config.ini [delivery] default_channels` > 内置 `["telegram"]`。

## review — 文章审阅

```bash
python main.py review <article.md>                         # 单篇审阅
python main.py review <article.md> --interactive           # 交互式逐段审阅
python main.py review <article1.md> <article2.md>          # 多篇对比
python main.py review <article.md> --dry-run               # 空跑验证
```

## info — 视频信息查询

```bash
python main.py info <url>              # 标题、可用字幕、时长、频道等
python main.py info <video_id>
```

## download — 下载资源

```bash
python main.py download <url>                     # URL → SRT（API 直取 / yt-dlp+STT 兜底）
python main.py download <url> --media audio       # 下载音频文件
python main.py download <url> --media video       # 下载视频文件
python main.py download <url> --dry-run           # 空跑验证
```

## uploads — 频道视频列表

```bash
python main.py uploads <@channel>                 # 频道最新视频列表
```

## batch — 批量处理

```bash
python main.py batch <url1> <url2>                          # 多个输入逐个生成文章
python main.py batch -f urls.txt                             # 从文件读输入列表
python main.py batch --from-channel @channel                 # 从频道拉取视频处理
python main.py batch --from-channel @channel --limit 5       # 限制总处理数量
python main.py batch url1 --from-channel @channel            # 混合来源
```

## stt — 语音转文字

```bash
python main.py stt <video.mp4>                    # 本地音视频 → SRT 字幕
```

## 全局选项

- `--tier fast|best|top` — 模型档位（config.ini 配置）
- `--simple` — 快速产出模式
- `--dry-run` — 空跑验证（article / download / review）
