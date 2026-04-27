"""Stage 1: 口语字幕 → 书面文本段落"""

import os
import logging
from utils.parser import parse, to_text
from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业文字编辑。你的任务是将视频字幕的口语文本整理为流畅的书面文本段落。

规则：
1. 将碎片的字幕行合并为完整语义句（原字幕每行可能被时间戳切断）
2. 删除口语填充词（如"就是说"、"然后呢"、"那个"、"嗯"、"这个"等）
3. 合并语义重复的表述——同一个意思用不同话说了多次，只保留最清晰的一次
4. 识别自然段落边界——话题转折、语气停顿处作为分段点
5. 保留所有实质性内容和关键细节，不要遗漏信息

输出格式：
- 纯文本段落，段落之间用空行分隔
- 每个段落末尾附带时间戳范围标记，格式：[ts: HH:MM:SS-HH:MM:SS]
- 时间戳从输入中提取，标记该段落覆盖的时间范围
- 不要添加任何额外的标题或说明文字"""


def run(subtitle_path: str, output_dir: str, tier: str = "best") -> str:
    """Run Stage 1. Returns path to 01_preprocessed.txt."""
    os.makedirs(output_dir, exist_ok=True)

    subtitles = parse(subtitle_path)
    raw_text = to_text(subtitles)
    logger.info("Parsed %d subtitle entries", len(subtitles))

    set_log_dir(os.path.join(output_dir, "llm_logs"))
    prompt = f"以下是需要整理的视频字幕：\n\n{raw_text}"
    result = chat(prompt, tier=tier, system=SYSTEM_PROMPT)

    output_path = os.path.join(output_dir, "01_preprocessed.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)

    logger.info("Stage 1 output: %s", output_path)
    return output_path
