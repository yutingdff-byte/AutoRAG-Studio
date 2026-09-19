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

PREPROCESS_QUALITY_STEPS = (95, 90, 85, 80, 75, 70)
PREPROCESS_MAX_SIDE_STEPS = (6000, 5000, 4096, 3500, 3000, 2500, 2000, 1600, 1200, 1000, 800)


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
9. 如果图片是单列配置表，不得自行拆成多个版本；只有表头明确出现多个版本时才输出版本差异。
10. 对金融、质保、保养、权益、活动等高风险信息，如果图片没有明确金额、期限或条件，只能写【图片内容无法确认】，不得补充行业常识或示例政策。
11. 专有系统名称必须逐字保留，例如 HUAWEI HiCar、ICCOA Carlink、CarPlay、Android Auto 不得互相替换。
12. 参数数值必须逐字抄录，不得近似、改写或凭图片印象修正。
13. 动力、发动机、变速箱等参数必须保持“参数名称-数值-单位”的原始对应关系；不得把发动机最大扭矩、变速箱类型或营销描述推断成“变速箱最大扭矩/扭矩容量/承载扭矩”。只有图片明确出现该参数名称和数值时，才可输出对应内容。
14. 后备箱、行李箱、储物空间、容积等空间参数必须保持“参数名称-数值/范围-单位-条件”的原始对应关系；如果图片标题或图片下方说明给出容积范围，必须逐字保留完整范围和条件，不得改写成单一容积、未放倒容积或自行估算值。
15. 对图片中展示行李箱、座椅放倒、储物空间等场景但数字说明不清晰的内容，只能写【图片内容无法确认】；不得根据图片画面、常见车型参数或相邻配置表补充后备箱/行李箱容积。
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


def _open_image_copy(image_bytes, source_name):

    if not image_bytes:

        raise ValueError(
            f"图片解析失败：{source_name} 内容为空"
        )

    try:

        with Image.open(
            BytesIO(
                image_bytes
            )
        ) as image:

            image.load()
            return image.copy()

    except UnidentifiedImageError as exc:

        raise ValueError(
            f"图片文件损坏或格式无法识别：{source_name}"
        ) from exc

    except Exception as exc:

        raise ValueError(
            f"图片校验失败：{source_name}，错误原因：{exc}"
        ) from exc


def _save_jpeg(image, quality: int) -> bytes:
    output = BytesIO()
    image.save(
        output,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )
    return output.getvalue()


def _to_rgb(image):
    if image.mode in {"RGB", "L"}:
        return image.convert("RGB")

    background = Image.new(
        "RGB",
        image.size,
        (255, 255, 255),
    )

    if image.mode in {"RGBA", "LA"}:
        alpha = image.convert("RGBA").split()[-1]
        background.paste(
            image.convert("RGBA"),
            mask=alpha,
        )
        return background

    return image.convert("RGB")


def _resize_to_max_side(image, max_side: int):
    width, height = image.size
    longest = max(width, height)
    if longest <= max_side:
        return image.copy()

    ratio = max_side / longest
    new_size = (
        max(1, int(width * ratio)),
        max(1, int(height * ratio)),
    )
    return image.resize(
        new_size,
        Image.Resampling.LANCZOS,
    )


def _prepare_image_bytes_for_model(image_bytes, source_name):
    image = _open_image_copy(
        image_bytes,
        source_name,
    )

    if len(image_bytes) <= MAX_IMAGE_SIZE_BYTES:
        return image_bytes, None

    rgb_image = _to_rgb(image)

    for quality in PREPROCESS_QUALITY_STEPS:
        compressed = _save_jpeg(
            rgb_image,
            quality,
        )
        if len(compressed) <= MAX_IMAGE_SIZE_BYTES:
            return compressed, "image/jpeg"

    for max_side in PREPROCESS_MAX_SIDE_STEPS:
        resized = _resize_to_max_side(
            rgb_image,
            max_side,
        )
        for quality in PREPROCESS_QUALITY_STEPS:
            compressed = _save_jpeg(
                resized,
                quality,
            )
            if len(compressed) <= MAX_IMAGE_SIZE_BYTES:
                return compressed, "image/jpeg"

    raise ValueError(
        f"图片超过MVP限制：{source_name} 预处理后仍大于10MB"
    )


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


def _build_data_url(source_name, image_bytes, mime_type=None):

    mime_type = mime_type or mimetypes.guess_type(
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

    prepared_bytes, prepared_mime_type = _prepare_image_bytes_for_model(
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
        prepared_bytes,
        prepared_mime_type,
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
