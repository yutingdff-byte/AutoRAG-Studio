import json
import os

from datetime import datetime
from time import sleep


from agents.fact_agent import extract_facts
from agents.rag_agent import generate_rag
from agents.qc_agent import quality_check

from generator.excel_generator import generate_excel


class PipelineStepError(RuntimeError):

    pass


def count_facts_result(facts):

    if isinstance(
        facts,
        dict
    ):

        values = facts.get(
            "facts",
            []
        )

        return len(
            values
        ) if isinstance(
            values,
            list
        ) else 0

    if isinstance(
        facts,
        list
    ):

        return len(
            facts
        )

    return 0


def count_rag_result(rag):

    if isinstance(
        rag,
        dict
    ):

        values = rag.get(
            "rag_knowledge",
            []
        )

        return len(
            values
        ) if isinstance(
            values,
            list
        ) else 0

    return 0



# =========================
# JSON保存工具
# =========================

def create_run_context():

    """
    创建本次运行上下文。

    run_id格式：
    YYYYMMDD_HHMMSS
    """


    while True:

        run_id = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_dir = os.path.join(
            "output",
            run_id
        )

        if not os.path.exists(
            output_dir
        ):

            os.makedirs(
                output_dir,
                exist_ok=False
            )

            return {

                "run_id": run_id,

                "output_dir": output_dir,

                "start_time": datetime.now().isoformat(
                    timespec="seconds"
                )

            }


        sleep(1)



def save_json(output_dir, filename, data):


    with open(
        os.path.join(
            output_dir,
            filename
        ),
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )



# =========================
# Pipeline核心入口
# =========================

def run_pipeline(
    material,
    progress_callback=None,
    source_files=None,
    image_parse_stats=None
):

    """
    AutoRAG-Studio核心流程


    参数：

    material:
        原始资料文本


    progress_callback:
        用于通知外部当前执行状态

        例如：

        Streamlit页面更新进度


        callback(step,data)


    返回：

    {
        run_id,
        output_dir,
        facts,
        rag,
        qc,
        excel_paths
    }

    """


    source_files = source_files or []

    image_parse_stats = image_parse_stats or {}


    run_context = create_run_context()


    run_id = run_context[
        "run_id"
    ]


    output_dir = run_context[
        "output_dir"
    ]


    print(
        "===== Run ID ====="
    )


    print(
        run_id
    )



    # =====================
    # Step1 Facts
    # =====================

    print(
        "===== Step1 Fact Extraction ====="
    )


    facts = extract_facts(
        material
    )


    save_json(
        output_dir,
        "facts.json",
        facts
    )

    if not facts or count_facts_result(
        facts
    ) == 0:

        raise PipelineStepError(
            "Facts 提取失败，模型服务暂时不可用或未返回有效事实，请稍后重试。"
        )


    # 通知页面

    if progress_callback:

        progress_callback(
            "Step1",
            facts
        )




    # =====================
    # Step2 RAG
    # =====================

    print(
        "===== Step2 RAG Generation ====="
    )


    rag = generate_rag(
        facts
    )


    save_json(
        output_dir,
        "rag.json",
        rag
    )

    if not rag or count_rag_result(
        rag
    ) == 0:

        raise PipelineStepError(
            "RAG 生成失败，模型服务暂时不可用或未返回有效知识，请稍后重试。"
        )


    # 通知页面

    if progress_callback:

        progress_callback(
            "Step2",
            rag
        )





    # =====================
    # Step3 QC
    # =====================

    print(
        "===== Step3 QC ====="
    )


    qc = quality_check(
        rag
    )


    save_json(
        output_dir,
        "qc_report.json",
        qc
    )


    # 通知页面

    if progress_callback:

        progress_callback(
            "Step3",
            qc
        )





    # =====================
    # Step4 Excel
    # =====================

    print(
        "===== Step4 Excel Generator ====="
    )


    excel_path = os.path.join(
        output_dir,
        "汽车外呼RAG知识库.xlsx"
    )


    excel_paths = generate_excel(
        facts,
        rag,
        qc,
        excel_path
    )


    run_info = {

        "run_id": run_id,

        "start_time": run_context[
            "start_time"
        ],

        "end_time": datetime.now().isoformat(
            timespec="seconds"
        ),

        "source_files": source_files,

        "file_count": len(
            source_files
        ),

        "image_file_count": image_parse_stats.get(
            "image_file_count",
            0
        ),

        "image_parse_success": image_parse_stats.get(
            "image_parse_success",
            0
        ),

        "image_parse_failed": image_parse_stats.get(
            "image_parse_failed",
            0
        ),

        "vision_model": image_parse_stats.get(
            "vision_model",
            ""
        ),

        "output_dir": output_dir,

        "output_files": {

            "facts": os.path.join(
                output_dir,
                "facts.json"
            ),

            "rag": os.path.join(
                output_dir,
                "rag.json"
            ),

            "qc_report": os.path.join(
                output_dir,
                "qc_report.json"
            ),

            "excel": excel_paths

        }

    }


    save_json(
        output_dir,
        "run_info.json",
        run_info
    )


    print(
        "===== Finished ====="
    )




    return {


        "run_id": run_id,


        "output_dir": output_dir,


        "facts": facts,


        "rag": rag,


        "qc": qc,


        "excel_path": excel_paths.get(
            "static",
            ""
        ),


        "excel_paths": excel_paths,


        "run_info": run_info


    }





# =========================
# 本地测试
# =========================


if __name__ == "__main__":


    def test_callback(step, data):

        print(
            f"\n>>> {step} 完成"
        )



    test_material = """

理想i6是一款中大型纯电SUV。

全国统一零售价249800元。

车长4950毫米，
轴距3000毫米。

两驱版CLTC续航720公里，
四驱版660公里。

支持5C超充，
10分钟补能500公里。

搭载理想AD Max高级辅助驾驶系统。


"""



    result = run_pipeline(

        test_material,

        progress_callback=test_callback

    )



    print(
        "\n===== Pipeline Result ====="
    )


    print(

        json.dumps(

            result,

            ensure_ascii=False,

            indent=2

        )

    )
