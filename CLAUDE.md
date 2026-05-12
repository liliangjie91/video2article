# CLAUDE.md

Agent guidance for the video2article project.

## 项目概述

命令行工具箱：字幕 → 深度文章 → 图文。输入 SRT/视频/YouTube URL/ID，经五阶段 pipeline 产出深度长文。

## 包组织规范（关键）

```
__init__.py     # 仅包初始化（load_dotenv、logger、常量），不放实现代码
_utils.py       # 包内共享的内部工具函数，以 _ 前缀表明私有
module.py       # 公开 API，外部通过 from pkg.module import func 导入
```

- `__init__.py` **不做重导出**（`from .module import func`），调用方直接 `from pkg.module import func`
- 内部工具放在 `_utils.py`，包外不应直接引用
- 避免循环导入，避免 `__init__.py` 膨胀
- monkeypatch 兼容：`from pkg import CONST` 创建局部绑定无法 mock，需用 `import pkg; pkg.CONST`

详见 [docs/design.md](docs/design.md)。

## 架构速览

```
main.py (CLI入口) → commands.py (命令处理 + 流程编排)
                        │
                        ├── download/    (字幕下载/音视频获取)
                        ├── pipeline/    (五阶段 + 链接后处理)
                        │   └── synthesize_link.py  (搜索结果 → 文章插入引用链接)
                        ├── search/      (联网搜索 + 结果整合)
                        │   ├── integrate.py (去重/排序/整合)
                        │   └── engine_*.py (Tavily/Brave/DuckDuckGo)
                        ├── delivery/    (文章投送：Telegram、Discord)
                        ├── image/       (视频截图+图文合成)
                        ├── stt/         (语音转文字)
                        ├── tts/         (文章转语音)
                        ├── llm.py       (LLM 封装，自动 fallback)
                        ├── config.py    (两级配置加载)
                        └── utils/       (通用工具：字幕解析、路径、类型检测)
```

详见 [docs/architecture.md](docs/architecture.md)。

### Pipeline 模块约定

每个 stage 暴露 `run(input_path, output_dir) -> output_path`，输出自动命名 `0N_name.ext`。

### 核心函数

- `commands:process_one()` — 统一入口，任意输入格式 → 完整 pipeline
- `commands:process_batch()` — 批量处理循环
- `commands:_run_article_pipeline()` — SRT → 文章的五阶段管线 + 搜索结果整合 + 链接后处理
- `search.integrate:search_from_outline()` — 从 outline search_queries 执行检索并整合
- `pipeline.synthesize_link:run()` — 文章后处理，插入内联引用链接（跨段落同词不重复）

## 命名

项目 logger name 统一使用 `video2article`。

## 测试

```bash
pytest -v
```

- **第一梯队**（纯函数，无 mock）：`test_parser.py`、`test_utils.py`、`test_download_cache.py`、`test_config.py`
- **第二梯队**（mock LLM）：`test_preprocess.py`、`test_structure.py`、`test_insights.py`、`test_outline.py`、`test_synthesize.py`、`test_simple.py`、`test_commands.py`

## 文档映射

| 文件 | 内容 | 受众 |
|------|------|------|
| [docs/cli.md](docs/cli.md) | 完整 CLI 命令参考 | 所有人 |
| [docs/config.md](docs/config.md) | .env + config.ini 配置参考 | 部署者 |
| [docs/architecture.md](docs/architecture.md) | 管线流程、模块职责、输出结构 | 开发者 |
| [docs/design.md](docs/design.md) | 设计原则、包规范哲学 | 贡献者 |
| [README.md](README.md) | 项目定位、快速开始、常用命令 | 人类用户 |
