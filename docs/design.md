# Design Principles

## 核心原则

- **文件即接口** — 每个阶段输出都是普通文本文件，可随时查看、修改、替换
- **分治而非黑盒** — 不做一键全自动，每个阶段单独可控
- **深度优先** — 不满足于摘要，追求原文之外的信息增量
- **litellm 接入** — 通过 litellm 接入 100+ LLM provider，支持自定义 provider

## 包组织规范

```
__init__.py     # 仅包初始化（load_dotenv、logger、常量），不放实现代码
_utils.py       # 包内共享的内部工具函数，以 _ 前缀表明私有
module.py       # 公开 API，外部通过 from pkg.module import func 导入
```

### 为什么这样设计？

**`__init__.py` 只做初始化，不做重导出：**
- 重导出（`from .module import func`）在实际项目中会造成循环导入、测试 mock 困难
- 调用方直接 `from pkg.module import func` 更清晰，没有"这个函数到底定义在哪"的疑问
- `__init__.py` 一旦做重导出，随着项目增长会变成"垃圾抽屉"，而只做初始化则永远轻量

**`_utils.py` 作为包内共享空间：**
- 公共函数如果放在 `__init__.py`，同样面临"垃圾抽屉"问题
- 放在 `_utils.py` 语义清晰：以下划线结尾表明"包内使用，外部不应直接引用"
- 多个模块间共享的逻辑有了明确归属

**monkeypatch 兼容性：**
- `from pkg import CONST` 会在导入方创建局部绑定，monkeypatch 无法生效
- 使用 `import pkg; pkg.CONST` 方式访问，使测试可以正确 mock
- 这一模式在 `download/_utils.py` 中应用，保证了缓存函数的可测试性

### 包规范示例

- `delivery/__init__.py` — 仅 `load_dotenv()` + logger
- `delivery/_utils.py` — 内部共享工具（如 `split_text()`）
- `delivery/deliver.py` — 公开 API（`deliver_article()`）
- `delivery/telegram.py` — 渠道实现（`deliver()`）
- `download/__init__.py` — 仅常量 + `load_dotenv()` + logger
- `download/_utils.py` — 内部工具（缓存、URL 检测）

## 输出组织

**一个 pipeline = 一个文件夹**：从下载到最终文章，所有产物集中在 `output/<channel>/<date>_<videoid>/`。

不存在中间产物散落的问题，每个 stage 的输出都是下一个 stage 的输入。
