import json
from collections import defaultdict

from agents.llm_client import call_llm



def load_prompt():

    with open(
        "prompts/step2_prompt.txt",
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()



def parse_result(result):

    """
    解析模型JSON
    """

    try:

        from utils.json_parser import parse_json

        data = parse_json(result)

        return data


    except Exception as e:

        print("======================")
        print("RAG JSON解析失败")
        print(e)
        print("======================")

        print(result)

        return None



def normalize_facts(facts):

    """
    兼容不同facts结构

    支持：

    {
      "facts":[]
    }

    或

    []
    """

    if isinstance(facts, dict):

        return facts.get(
            "facts",
            []
        )


    return facts



def group_facts(facts):

    """
    按车型 + category分组

    优先保证：

    同车型
    同类型知识

    不被拆散

    """


    groups = defaultdict(list)



    for fact in facts:


        category = fact.get(
            "category",
            "其他"
        )


        # 尝试识别车型字段
        content = fact.get(
            "content",
            ""
        )


        vehicle = (
            fact.get("vehicle")
            or fact.get("model")
            or "通用"
        )


        key = (
            vehicle,
            category
        )


        groups[key].append(
            fact
        )



    return list(
        groups.values()
    )



def merge_small_groups(
        groups,
        max_size=30
):

    """
    避免过小batch过多

    小于max_size的相邻组进行合并

    """


    merged=[]

    current=[]


    current_size=0



    for group in groups:


        if (
            current_size + len(group)
            <= max_size
        ):

            current.extend(
                group
            )

            current_size += len(group)


        else:

            if current:

                merged.append(
                    current
                )


            current=list(group)

            current_size=len(group)



    if current:

        merged.append(
            current
        )


    return merged



def generate_batch(
        facts_batch,
        system_prompt
):


    user_content=json.dumps(
        {
            "facts":facts_batch
        },
        ensure_ascii=False
    )



    result = call_llm(
        system_prompt,
        user_content
    )


    if not result:

        return None



    return parse_result(
        result
    )



def merge_results(results):


    final = {

        "rag_knowledge":[],

        "info_gaps":[],

        "confirm_items":[]

    }



    rag_index=1



    for result in results:


        if not result:

            continue



        rag_list=result.get(
            "rag_knowledge",
            []
        )



        for rag in rag_list:


            rag["rag_id"] = (
                f"RAG-{rag_index:03d}"
            )


            final[
                "rag_knowledge"
            ].append(
                rag
            )


            rag_index += 1



        final[
            "info_gaps"
        ].extend(
            result.get(
                "info_gaps",
                []
            )
        )


        final[
            "confirm_items"
        ].extend(
            result.get(
                "confirm_items",
                []
            )
        )



    return final




def generate_rag(facts):

    """
    Step2:

    Facts
      |
      ↓
    vehicle/category分组
      |
      ↓
    Batch生成RAG
      |
      ↓
    Merge

    """



    system_prompt = load_prompt()



    facts = normalize_facts(
        facts
    )



    print(
        "===== Step2 Facts数量 ====="
    )

    print(
        len(facts)
    )



    # 1. 按车型/category拆分

    groups = group_facts(
        facts
    )



    print(
        "初始分组数量:",
        len(groups)
    )



    # 2. 合并小组，控制batch规模

    batches = merge_small_groups(
        groups,
        max_size=30
    )



    print(
        "最终Batch数量:",
        len(batches)
    )



    results=[]



    for index,batch in enumerate(
        batches
    ):


        print(
            f"===== Step2 Batch {index+1}/{len(batches)} ====="
        )


        print(
            "Facts数量:",
            len(batch)
        )



        result = generate_batch(
            batch,
            system_prompt
        )



        if result:


            results.append(
                result
            )


        else:

            print(
                f"Batch {index+1}生成失败"
            )



    final_result = merge_results(
        results
    )



    print(
        "===== Step2完成 ====="
    )

    print(
        "最终RAG数量:",
        len(
            final_result[
                "rag_knowledge"
            ]
        )
    )



    return final_result