import os

from pypdf import PdfReader



def parse_pdf(file):

    """
    PDF文档解析器


    支持：

    1. 本地文件路径

    2. Streamlit上传文件对象


    输出：

    str文本

    """



    try:


        # =====================
        # 获取文件名称
        # =====================


        if isinstance(file, str):

            file_name = os.path.basename(
                file
            )

        else:

            file_name = file.name



        texts = []


        texts.append(
            f"【文件来源：{file_name}】"
        )



        # =====================
        # 创建PDF读取对象
        # =====================


        reader = PdfReader(
            file
        )



        # =====================
        # 遍历页面
        # =====================


        for index, page in enumerate(
            reader.pages
        ):


            texts.append(

                f"\n【第{index + 1}页】"

            )


            content = page.extract_text()



            if content:


                texts.append(

                    content.strip()

                )


            else:


                texts.append(

                    "[该页面未提取到文本]"

                )



        return "\n".join(texts)



    except Exception as e:


        raise Exception(

            f"PDF解析失败: {str(e)}"

        )





# =====================
# 本地测试
# =====================

if __name__ == "__main__":


    result = parse_pdf(

        "test.pdf"

    )


    print(result)