import json
import os


from agents.fact_agent import extract_facts
from agents.rag_agent import generate_rag
from agents.qc_agent import quality_check

from generator.excel_generator import generate_excel



# =========================
# JSON保存工具
# =========================

def save_json(filename, data):

    os.makedirs(
        "output",
        exist_ok=True
    )


    with open(
        f"output/{filename}",
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
    progress_callback=None
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
        facts,
        rag,
        qc,
        excel_path
    }

    """



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
        "facts.json",
        facts
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
        "rag.json",
        rag
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


    excel_path = (
        "output/"
        "汽车外呼RAG知识库.xlsx"
    )


    generate_excel(
        facts,
        rag,
        qc,
        excel_path
    )


    print(
        "===== Finished ====="
    )




    return {


        "facts": facts,


        "rag": rag,


        "qc": qc,


        "excel_path": excel_path


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