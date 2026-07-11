from docx import Document
import os



def parse_docx(file):

    """
    Word文档解析器


    支持：

    1. 本地路径

    "test.docx"


    2. Streamlit上传文件对象


    返回：

    str文本

    """



    try:


        # =====================
        # 判断输入类型
        # =====================


        if isinstance(file, str):

            doc = Document(
                file
            )

            file_name = os.path.basename(
                file
            )


        else:

            doc = Document(
                file
            )

            file_name = file.name



        texts = []



        # =====================
        # 文件来源
        # =====================

        texts.append(

            f"【文件来源：{file_name}】"

        )



        # =====================
        # 读取正文
        # =====================


        for paragraph in doc.paragraphs:


            text = paragraph.text.strip()


            if text:


                texts.append(
                    text
                )



        # =====================
        # 读取表格
        # =====================


        for index, table in enumerate(doc.tables):


            texts.append(

                f"\n【表格 {index+1}】"

            )


            for row in table.rows:


                row_data = []


                for cell in row.cells:


                    value = cell.text.strip()


                    row_data.append(
                        value
                    )



                # 过滤空行

                if any(row_data):


                    texts.append(

                        " | ".join(row_data)

                    )



        return "\n".join(texts)



    except Exception as e:


        raise Exception(

            f"Word解析失败: {str(e)}"

        )




# =====================
# 本地测试
# =====================

if __name__ == "__main__":


    result = parse_docx(
        "test.docx"
    )


    print(result)
