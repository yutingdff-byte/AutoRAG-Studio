from openpyxl import Workbook
from openpyxl.styles import Font, Alignment


# ==========================
# Sheet格式化
# ==========================

def format_sheet(ws):

    # 冻结首行
    ws.freeze_panes = "A2"


    # 自动筛选
    if ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions


    # 表头样式
    for cell in ws[1]:

        cell.font = Font(
            bold=True
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )


    # 内容换行
    for row in ws.iter_rows():

        for cell in row:

            cell.alignment = Alignment(
                wrap_text=True,
                vertical="top"
            )


    # 列宽
    width_config = {

        "A":12,
        "B":15,
        "C":20,
        "D":15,
        "E":18,
        "F":40,
        "G":15,
        "H":55,
        "I":25,
        "J":20,
        "K":15,
        "L":12,
        "M":35

    }


    for col,width in width_config.items():

        ws.column_dimensions[col].width = width



# ==========================
# Facts fallback车辆信息
# ==========================

def extract_vehicle_info(facts_data):

    """
    兼容旧版本

    如果Step2没有输出：
    brand / vehicle / year

    从facts中尝试提取
    """


    result = {

        "brand":"",
        "model":"",
        "year":""

    }


    facts = facts_data.get(
        "facts",
        []
    )


    for fact in facts:


        category = fact.get(
            "category",
            ""
        )


        content = fact.get(
            "content",
            ""
        )


        vehicle = fact.get(
            "vehicle",
            ""
        )


        # 新Step1结构

        if vehicle:

            if vehicle not in [
                "全系",
                "品牌级",
                "需确认"
            ]:

                result["model"] = vehicle



        # 品牌信息

        if "品牌" in category:

            result["brand"] = content



        # 年款

        if "年款" in category:

            result["year"] = content



    return result



# ==========================
# 回答类型中文化
# ==========================

def translate_answer_type(value):

    mapping = {

        "fact_answer":"事实回答",

        "sales_translation":"销售转译",

        "need_confirm":"需确认"

    }


    return mapping.get(
        value,
        value
    )



# ==========================
# 风险等级中文化
# ==========================

def translate_risk(value):

    mapping = {

        "error":"错误",

        "warning":"警告"

    }


    return mapping.get(
        value,
        value
    )


# ==========================
# Excel生成
# ==========================

def generate_excel(

        facts_data,

        rag_data,

        qc_data,

        output_path

):


    fallback_vehicle = extract_vehicle_info(
        facts_data
    )


    wb = Workbook()


    # 删除默认Sheet

    ws = wb.active

    ws.title = "RAG知识表"



    # ==================================================
    # Sheet1 RAG知识表
    # ==================================================


    ws.append(

        [

            "RAG编号",

            "品牌",

            "车型",

            "年款",

            "知识模块",

            "用户问题",

            "回答类型",

            "标准回答",

            "事实引用",

            "适用范围",

            "是否需人工确认",

            "置信度",

            "风险提示"

        ]

    )



    module_order = {


        "价格":1,

        "价格信息":1,


        "品牌车型":2,

        "车型信息":2,

        "车型定位":2,


        "版本选择":3,

        "版本信息":3,


        "空间":4,

        "空间信息":4,


        "外观尺寸":5,

        "尺寸信息":5,


        "内饰与舒适":6,

        "舒适":6,

        "舒适配置":6,


        "续航":7,

        "续航信息":7,


        "补能":8,

        "补能信息":8,


        "智能驾驶":9,

        "智驾":9,

        "智驾信息":9,


        "售后质保":10,

        "质保":10,

        "售后信息":10,


        "交付与库存":11,

        "库存交付":11,


        "试驾与权益":12,

        "权益政策":12


    }



    priority_map = {


        "高":1,

        "中":2,

        "低":3

    }



    rag_list = sorted(

        rag_data.get(

            "rag_knowledge",

            []

        ),

        key=lambda x:(


            module_order.get(

                x.get(

                    "module",

                    ""

                ),

                99

            ),


            priority_map.get(

                x.get(

                    "faq_priority",

                    "低"

                ),

                3

            )

        )

    )



    for item in rag_list:



        # ==========================
        # Step2优先
        # Facts fallback
        # ==========================


        brand = (

            item.get(

                "brand",

                ""

            )

            or

            fallback_vehicle.get(

                "brand",

                ""

            )

        )



        vehicle = (

            item.get(

                "vehicle",

                ""

            )

            or

            fallback_vehicle.get(

                "model",

                ""

            )

        )



        year = (

            item.get(

                "year",

                ""

            )

            or

            fallback_vehicle.get(

                "year",

                ""

            )

        )



        guardrails = item.get(

            "guardrails",

            []

        )


        if guardrails:

            risk_text = "\n".join(

                guardrails

            )

        else:

            risk_text = "无"



        questions = item.get(

            "questions",

            []

        )


        if not isinstance(

            questions,

            list

        ):

            questions = [

                questions

            ]



        fact_refs = item.get(

            "fact_refs",

            []

        )


        if not isinstance(

            fact_refs,

            list

        ):

            fact_refs = [

                fact_refs

            ]



        ws.append(

            [

                item.get(

                    "rag_id",

                    ""

                ),


                brand,


                vehicle,


                year,


                item.get(

                    "module",

                    ""

                ),


                "\n".join(

                    questions

                ),


                translate_answer_type(

                    item.get(

                        "answer_type",

                        ""

                    )

                ),


                item.get(

                    "answer",

                    ""

                ),


                ",".join(

                    fact_refs

                ),


                item.get(

                    "适用范围",

                    ""

                ),


                item.get(

                    "need_confirm",

                    ""

                ),


                item.get(

                    "confidence",

                    ""

                ),


                risk_text

            ]

        )


    # ==================================================
    # Sheet2 信息缺口清单
    # ==================================================


    ws2 = wb.create_sheet(

        "信息缺口清单"

    )


    ws2.append(

        [

            "缺口编号",

            "缺口类型",

            "缺失内容",

            "影响模块",

            "影响程度",

            "说明"

        ]

    )



    for index,item in enumerate(

        rag_data.get(

            "info_gaps",

            []

        )

    ):


        # 新格式

        if isinstance(

            item,

            dict

        ):


            ws2.append(

                [

                    item.get(

                        "gap_id",

                        f"G{index+1:03}"

                    ),


                    item.get(

                        "gap_type",

                        ""

                    ),


                    item.get(

                        "missing_content",

                        ""

                    ),


                    item.get(

                        "impact_module",

                        ""

                    ),


                    item.get(

                        "impact_level",

                        ""

                    ),


                    item.get(

                        "description",

                        ""

                    )

                ]

            )


        # 兼容旧格式

        else:


            ws2.append(

                [

                    f"G{index+1:03}",

                    "",

                    item,

                    "",

                    "",

                    ""

                ]

            )





    # ==================================================
    # Sheet3 人工确认事项
    # ==================================================


    ws3 = wb.create_sheet(

        "人工确认事项"

    )


    ws3.append(

        [

            "确认编号",

            "确认事项",

            "确认原因",

            "关联模块",

            "影响范围",

            "优先级"

        ]

    )



    for index,item in enumerate(

        rag_data.get(

            "confirm_items",

            []

        )

    ):



        # 新格式

        if isinstance(

            item,

            dict

        ):


            ws3.append(

                [

                    item.get(

                        "confirm_id",

                        f"C{index+1:03}"

                    ),


                    item.get(

                        "item",

                        ""

                    ),


                    item.get(

                        "reason",

                        ""

                    ),


                    item.get(

                        "module",

                        ""

                    ),


                    item.get(

                        "impact_scope",

                        ""

                    ),


                    item.get(

                        "priority",

                        ""

                    )

                ]

            )


        # 兼容旧格式

        else:


            ws3.append(

                [

                    f"C{index+1:03}",

                    item,

                    "",

                    "",

                    "",

                    ""

                ]

            )





    # ==================================================
    # Sheet4 质检报告
    # ==================================================


    ws4 = wb.create_sheet(

        "质检报告"

    )


    ws4.append(

        [

            "检查项",

            "结果"

        ]

    )



    summary = qc_data.get(

        "summary",

        {}

    )



    ws4.append(

        [

            "总体结果",

            qc_data.get(

                "overall_result",

                ""

            )

        ]

    )



    ws4.append(

        [

            "RAG总数",

            summary.get(

                "total_rag",

                0

            )

        ]

    )



    ws4.append(

        [

            "通过数量",

            summary.get(

                "pass",

                0

            )

        ]

    )



    ws4.append(

        [

            "警告数量",

            summary.get(

                "warning",

                0

            )

        ]

    )



    ws4.append(

        [

            "错误数量",

            summary.get(

                "error",

                0

            )

        ]

    )



    ws4.append([])



    # 覆盖检查

    ws4.append(

        [

            "覆盖模块",

            "覆盖状态"

        ]

    )



    coverage = qc_data.get(

        "coverage_check",

        {}

    )



    if isinstance(

        coverage,

        dict

    ):


        for module,status in coverage.items():


            ws4.append(

                [

                    module,

                    status

                ]

            )



    ws4.append([])



    # 问题列表

    ws4.append(

        [

            "问题类型",

            "风险等级",

            "问题说明",

            "处理建议"

        ]

    )



    for issue in qc_data.get(

        "issues",

        []

    ):


        if isinstance(

            issue,

            dict

        ):


            ws4.append(

                [

                    issue.get(

                        "issue_type",

                        ""

                    ),


                    translate_risk(

                        issue.get(

                            "risk_level",

                            ""

                        )

                    ),


                    issue.get(

                        "description",

                        ""

                    ),


                    issue.get(

                        "suggestion",

                        ""

                    )

                ]

            )





    # ==================================================
    # 格式化 & 保存
    # ==================================================


    for sheet in wb.worksheets:


        format_sheet(

            sheet

        )



    wb.save(

        output_path

    )