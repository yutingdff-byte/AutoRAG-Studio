import base64
import mimetypes
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from utils.config import get_config, require_config


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp"
}


MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


IMAGE_PARSE_PROMPT = """
你是汽车业务资料解析助手。

请完整识别图片中的文字、表格和关键信息，并整理为结构清晰的纯文本资料，供后续事实抽取使用。

要求：

1. 忠实保留图片中明确出现的信息，不补充、不猜测。
2. 保留品牌、车型、版本、价格、活动时间、适用范围、配置、权益、金融政策等信息。
3. 表格内容按行整理，不能只总结结论。
4. 保留不同版本之间的对应关系。
5. 保留金额、日期、单位、限制条件、备注和例外条款。
6. 无法识别的内容标记为【图片内容无法确认】，不得猜测。
7. 不生成销售话术，不进行价值转译，不判断静态或动态知识。
8. 输出纯文本，不输出Markdown代码块，不输出JSON。
""".strip()


def get_vision_model_name():

    return get_config(
        "VISION_MODEL",
        "qwen-vl-plus"
    )


def _get_source_name(file_path):

    name = getattr(
        file_path,
        "name",
        None
    )

    if name:

        return Path(
            str(name)
        ).name

    if isinstance(
        file_path,
        (str, Path)
    ):

        return Path(
            file_path
        ).name

    return "uploaded_image"


def _read_image_bytes(file_path):

    if isinstance(
        file_path,
        (str, Path)
    ):

        return Path(
            file_path
        ).read_bytes()

    if hasattr(
        file_path,
        "getvalue"
    ):

        return file_path.getvalue()

    if hasattr(
        file_path,
        "read"
    ):

        try:

            file_path.seek(
                0
            )

        except Exception:

            pass

        content = file_path.read()

        try:

            file_path.seek(
                0
            )

        except Exception:

            pass

        return content

    raise ValueError(
        "无法读取图片文件内容"
    )


def _validate_image_bytes(image_bytes, source_name):

    if not image_bytes:

        raise ValueError(
            f"图片解析失败：{source_name} 内容为空"
        )

    if len(
        image_bytes
    ) > MAX_IMAGE_SIZE_BYTES:

        raise ValueError(
            f"图片超过MVP限制：{source_name} 大于10MB"
        )

    try:

        with Image.open(
            BytesIO(
                image_bytes
            )
        ) as image:

            image.verify()

    except UnidentifiedImageError as exc:

        raise ValueError(
            f"图片文件损坏或格式无法识别：{source_name}"
        ) from exc

    except Exception as exc:

        raise ValueError(
            f"图片校验失败：{source_name}，错误原因：{exc}"
        ) from exc


def _validate_qwen_config():

    api_key = require_config(
        "QWEN_API_KEY",
        "图片解析服务"
    )

    base_url = require_config(
        "QWEN_BASE_URL",
        "图片解析服务"
    )

    return api_key, base_url


def _build_data_url(source_name, image_bytes):

    mime_type = mimetypes.guess_type(
        source_name
    )[0]

    if not mime_type:

        suffix = Path(
            source_name
        ).suffix.lower()

        if suffix == ".webp":

            mime_type = "image/webp"

        elif suffix == ".png":

            mime_type = "image/png"

        else:

            mime_type = "image/jpeg"

    encoded = base64.b64encode(
        image_bytes
    ).decode(
        "utf-8"
    )

    return f"data:{mime_type};base64,{encoded}"


def parse_image(file_path: str) -> str:

    """
    使用Qwen-VL-Plus将图片资料解析为纯文本Material。
    """

    source_name = _get_source_name(
        file_path
    )

    suffix = Path(
        source_name
    ).suffix.lower()

    if suffix and suffix not in IMAGE_EXTENSIONS:

        raise ValueError(
            f"暂不支持该图片格式：{suffix}"
        )

    image_bytes = _read_image_bytes(
        file_path
    )

    _validate_image_bytes(
        image_bytes,
        source_name
    )

    api_key, base_url = _validate_qwen_config()

    try:

        from openai import OpenAI

    except ModuleNotFoundError as exc:

        raise RuntimeError(
            "图片解析依赖 openai 未安装，请先安装 requirements.txt。"
        ) from exc

    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    data_url = _build_data_url(
        source_name,
        image_bytes
    )

    response = client.chat.completions.create(
        model=get_vision_model_name(),
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": IMAGE_PARSE_PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url
                        }
                    }
                ]
            }
        ],
        temperature=0,
        max_tokens=4096,
        stream=False
    )

    if not response.choices:

        raise RuntimeError(
            f"图片解析失败：{source_name}，视觉模型返回为空"
        )

    content = (
        response.choices[0]
        .message
        .content
        or ""
    ).strip()

    if not content:

        raise RuntimeError(
            f"图片解析失败：{source_name}，视觉模型未返回有效文本"
        )

    return "\n".join(
        [
            f"【文件来源：{source_name}】",
            f"【图片识别模型：{get_vision_model_name()}】",
            content
        ]
    )
