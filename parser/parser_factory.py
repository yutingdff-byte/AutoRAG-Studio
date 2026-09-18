import os


from parser.docx_parser import parse_docx
from parser.excel_parser import parse_excel
from parser.image_parser import IMAGE_EXTENSIONS, parse_image
from parser.pdf_parser import parse_pdf
from parser.zip_image_parser import ZIP_EXTENSIONS, parse_zip_images



def parse_file(file):

    """
    文件解析统一入口


    输入：

    file:
        本地文件路径
        或 Streamlit UploadedFile


    输出：

    str:
        统一文本内容


    """



    try:


        # =====================
        # 获取文件名
        # =====================


        if isinstance(file, str):

            filename = os.path.basename(
                file
            )


        else:

            filename = file.name



        filename_lower = filename.lower()



        # =====================
        # 文件类型判断
        # =====================


        if filename_lower.endswith(
            ".docx"
        ):


            return parse_docx(
                file
            )



        elif filename_lower.endswith(
            ".xlsx"
        ) or filename_lower.endswith(
            ".xls"
        ):


            return parse_excel(
                file
            )



        elif filename_lower.endswith(
            ".pdf"
        ):


            return parse_pdf(
                file
            )


        elif os.path.splitext(
            filename_lower
        )[1] in IMAGE_EXTENSIONS:


            return parse_image(
                file
            )

        elif os.path.splitext(
            filename_lower
        )[1] in ZIP_EXTENSIONS:


            return parse_zip_images(
                file
            )



        elif filename_lower.endswith(
            ".txt"
        ):


            # TXT暂时内置处理

            if isinstance(file, str):

                with open(
                    file,
                    "r",
                    encoding="utf-8"
                ) as f:


                    return (
                        f.read()
                    )


            else:


                return (
                    file.read()
                    .decode(
                        "utf-8"
                    )
                )



        else:


            raise Exception(

                f"暂不支持的文件类型: {filename}"

            )



    except Exception as e:


        raise Exception(

            f"文件解析失败: {str(e)}"

        )
