import json

from agents.llm_client import call_llm


def quality_check(rag_data):

    """
    Step3:
    对RAG知识进行质量检测
    """


    with open(
        "prompts/step3_prompt.txt",
        "r",
        encoding="utf-8"
    ) as f:

        system_prompt = f.read()


    user_content = json.dumps(
        rag_data,
        ensure_ascii=False
    )


    result = call_llm(
        system_prompt,
        user_content
    )


    try:

        from utils.json_parser import parse_json
        data = parse_json(result)

        return data


    except Exception:

        print("QC JSON解析失败")
        print(result)

        return None