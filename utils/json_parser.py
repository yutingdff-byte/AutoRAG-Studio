import json
import re


def parse_json(text):

    """
    清洗并解析LLM返回JSON
    """


    # 去除markdown代码块

    text = re.sub(
        r"```json",
        "",
        text
    )


    text = re.sub(
        r"```",
        "",
        text
    )


    text = text.strip()


    return json.loads(text)