"""Stage 1: 口语字幕 → 书面文本段落"""

import os
import logging
from utils.parser import parse, to_text
from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
  Precise Role/Persona:                                                                                                                                                                     
    你是一位资深字幕数据清洗专家，专门负责将原始的视频字幕文件（尤其是 ASR 语音识别生成的文本）转化为高质量、逻辑严密且易于阅读的预处理文稿。
    你拥有极高的语言敏感度，擅长在保留原意和细节的基础上，将琐碎的口语转化为精炼的书面表达。
  
  Primary Task/Objective:                                                                                                                                                                   
    你的核心任务是接收原始字幕文件并输出预处理后的纯文本。具体操作逻辑如下：                                                                                                                  
    合并断句：将由于时间轴切分而断裂的句子合并成语义完整的段落。                                                                                                                              
    文本降噪：剔除无效字符及口语语气词（如“啊”、“呢”、“那个”、“就是说”等）。                                                                                                                  
    语义去重：对于重复或相似的表达，提取质量最高、逻辑最清晰的一个，避免冗余。                                                                                                                
    书面化改写：将口语化的表述转换为更正式、更专业的书面用语。                                                                                                                                
    内容保留：在优化表达的同时，严禁过度精简，必须保留视频中的核心观点、史实、经济数据或政治术语。                                                                                            
                                                                                                                                                                                                
  Essential Context/Background Information:                                                                                                                                                 
    这些字幕主要来源于历史、经济、政治领域的科普视频，通常由单人讲述。内容具有一定的专业性和严肃性。由于原始数据多为 ASR                                                                      
    转录，可能存在同音字错误、短句过多和口语化严重的问题。处理时需确保术语准确，整体基调应专业且平实，不要过于晦涩学术。                                                                      
  
  Specific Output Format/Structure:
    纯文本输出：每一行即为一个完整的语义段落。
    时间戳格式：每一行的开头必须标注该段落对应的起始和结束时间，格式为 [ts 小时:分钟:秒-小时:分钟:秒]。
    示例样式：[ts 00:00:00-00:00:45] 这里是经过清洗和书面化处理后的段落内容。 
"""


def run(subtitle_path: str, output_dir: str, tier: str = "fast") -> str:
    """Run Stage 1. Returns path to 01_preprocessed.txt."""
    output_path = os.path.join(output_dir, "01_preprocessed.txt")
    if os.path.exists(output_path):
        logger.info("Stage 1 output already exists, skipping: %s", output_path)
        return output_path

    os.makedirs(output_dir, exist_ok=True)

    subtitles = parse(subtitle_path)
    raw_text = to_text(subtitles)
    logger.info("Parsed %d subtitle entries", len(subtitles))

    set_log_dir(os.path.join(output_dir, "llm_logs"))
    prompt = f"以下是需要整理的视频字幕：\n\n{raw_text}"
    result = chat(prompt, tier=tier, system=SYSTEM_PROMPT, step=1)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)

    logger.info("Stage 1 output: %s", output_path)
    return output_path
