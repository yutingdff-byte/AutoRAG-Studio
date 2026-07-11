import json

from agents.llm_client import call_llm


def extract_facts(material):

    """
    Step1:
    从车型资料中抽取事实信息

    参数:
        material:
            用户上传资料文本

    返回:
        facts json
    """


    # 读取Prompt

    with open(
        "prompts/step1_prompt.txt",
        "r",
        encoding="utf-8"
    ) as f:

        system_prompt = f.read()


    # 调用大模型

    result = call_llm(
        system_prompt,
        material
    )


    # 转JSON

    try:

        from utils.json_parser import parse_json
        data = parse_json(result)

        return data


    except Exception:

        print("JSON解析失败")
        print(result)

        return None