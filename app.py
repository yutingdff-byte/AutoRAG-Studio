import streamlit as st
import pandas as pd


from main import run_pipeline

from parser.parser_factory import parse_file



# =====================
# 页面配置
# =====================

st.set_page_config(

    page_title="AutoRAG-Studio",

    page_icon="🚗",

    layout="wide"

)



# =====================
# 标题
# =====================

st.title(
    "🚗 AutoRAG-Studio"
)


st.caption(
    "汽车行业 RAG知识库自动生成平台"
)



# =====================
# 多格式文件上传
# =====================


uploaded_files = st.file_uploader(

    "上传汽车资料（支持 txt / Word / Excel / PDF）",

    type=[
        "txt",
        "docx",
        "xlsx",
        "pdf"
    ],

    accept_multiple_files=True

)



if uploaded_files:


    st.success(

        f"已上传 {len(uploaded_files)} 个文件"

    )


    # =====================
    # 文件列表
    # =====================


    with st.expander(
        "查看上传文件"
    ):


        for file in uploaded_files:


            st.write(
                f"📄 {file.name}"
            )



    # =====================
    # 文件解析
    # =====================


    if st.button(

        "🚀 开始生成RAG知识库"

    ):



        st.divider()


        st.subheader(
            "📂 文件解析过程"
        )


        parse_box = st.empty()


        materials = []



        for file in uploaded_files:


            try:


                parse_box.info(

                    f"正在解析：{file.name}"

                )


                text = parse_file(
                    file
                )


                materials.append(
                    text
                )


            except Exception as e:


                st.error(

                    f"{file.name}解析失败：{e}"

                )



        # 合并所有资料


        material = "\n\n".join(

            materials

        )



        parse_box.success(

            f"全部解析完成，共{len(uploaded_files)}个文件"

        )



        # =====================
        # Agent执行过程
        # =====================


        st.divider()


        st.subheader(

            "🤖 Agent执行过程"

        )


        status_box = st.empty()


        logs = []



        def update_progress(step, data):


            if step == "Step1":


                logs.append(

                    f"""
✅ Step1 Facts事实抽取完成

事实数量：
{len(data.get("facts", []))}
"""

                )



            elif step == "Step2":


                logs.append(

                    f"""
✅ Step2 RAG知识生成完成

知识数量：
{len(data.get("rag_knowledge", []))}
"""

                )



            elif step == "Step3":


                logs.append(

                    """
✅ Step3 QC质量检测完成
"""

                )



            status_box.markdown(

                "\n\n".join(logs)

            )



        # =====================
        # Pipeline
        # =====================


        with st.spinner(

            "AI正在生成知识库..."

        ):


            result = run_pipeline(

                material,

                progress_callback=update_progress,

                source_files=[

                    file.name

                    for file in uploaded_files

                ]

            )



        st.success(

            "🎉 RAG生成完成"

        )


        st.caption(

            f"本次任务编号：{result['run_id']}"

        )



        facts = result["facts"]

        rag = result["rag"]

        qc = result["qc"]



        # =====================
        # 概览
        # =====================


        st.divider()


        st.subheader(

            "📊 生成概览"

        )


        col1,col2,col3 = st.columns(3)



        with col1:


            st.metric(

                "事实数量",

                len(

                    facts.get(

                        "facts",

                        []

                    )

                )

            )



        with col2:


            st.metric(

                "RAG数量",

                len(

                    rag.get(

                        "rag_knowledge",

                        []

                    )

                )

            )



        with col3:


            st.metric(

                "QC状态",

                qc.get(

                    "overall_result",

                    qc.get(

                        "summary",

                        {}

                    ).get(

                        "overall_result",

                        "未知"

                    )

                )

            )



        # =====================
        # Facts
        # =====================


        st.divider()


        st.subheader(

            "① Facts事实抽取"

        )


        st.dataframe(

            pd.DataFrame(

                facts.get(

                    "facts",

                    []

                )

            ),

            use_container_width=True

        )



        # =====================
        # RAG
        # =====================


        st.divider()


        st.subheader(

            "② RAG知识库"

        )


        rag_rows=[]



        for item in rag.get(

            "rag_knowledge",

            []

        ):


            rag_rows.append({

                "模块":

                item.get(

                    "module"

                ),


                "问题":

                " / ".join(

                    item.get(

                        "questions",

                        []

                    )

                ),


                "回答":

                item.get(

                    "answer"

                ),


                "需确认":

                item.get(

                    "need_confirm"

                )

            })



        st.dataframe(

            pd.DataFrame(

                rag_rows

            ),

            use_container_width=True

        )



        # =====================
        # QC
        # =====================


        st.divider()


        st.subheader(

            "③ 质量检测"

        )


        st.json(

            qc

        )



        # =====================
        # Excel下载
        # =====================


        st.divider()


        st.subheader(

            "📥 下载"

        )


        with open(

            result["excel_path"],

            "rb"

        ) as f:


            st.download_button(

                label="下载RAG知识库Excel",

                data=f,

                file_name="汽车外呼RAG知识库.xlsx"

            )
