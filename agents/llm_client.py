from openai import OpenAI
from httpx import Timeout

from utils.config import get_config, require_config


def get_llm_timeout():

    connect_timeout = float(
        get_config(
            "LLM_CONNECT_TIMEOUT_SECONDS",
            "10"
        )
    )

    read_timeout = float(
        get_config(
            "LLM_READ_TIMEOUT_SECONDS",
            "600"
        )
    )

    return Timeout(
        connect=connect_timeout,
        read=read_timeout,
        write=60.0,
        pool=60.0
    )


def get_client():

    return OpenAI(
        api_key=require_config(
            "DEEPSEEK_API_KEY",
            "DeepSeek文本模型"
        ),
        base_url=get_config(
            "DEEPSEEK_BASE_URL",
            "https://api.deepseek.com"
        ),
        timeout=get_llm_timeout(),
        max_retries=int(
            get_config(
                "LLM_MAX_RETRIES",
                "0"
            )
        )
    )


def describe_llm_exception(exc, model):

    cause = getattr(
        exc,
        "__cause__",
        None
    )

    request = getattr(
        exc,
        "request",
        None
    )

    return {
        "exception_class": f"{exc.__class__.__module__}.{exc.__class__.__name__}",
        "exception_message": str(
            exc
        ),
        "cause_class": (
            f"{cause.__class__.__module__}.{cause.__class__.__name__}"
            if cause
            else ""
        ),
        "cause_message": str(
            cause
        ) if cause else "",
        "http_status": getattr(
            exc,
            "status_code",
            ""
        ),
        "request_endpoint": str(
            getattr(
                request,
                "url",
                ""
            )
        ) if request else "",
        "model": model,
        "timeout": str(
            get_llm_timeout()
        ),
        "max_retries": int(
            get_config(
                "LLM_MAX_RETRIES",
                "0"
            )
        )
    }


def call_llm(system_prompt, user_content):

    try:

        client = get_client()
        model = get_config(
            "DEEPSEEK_MODEL",
            "deepseek-v4-flash"
        )

        request_args = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            "temperature": 0.2,
            "max_tokens": 64000,
            "response_format": {
                "type": "json_object"
            }
        }
        stream_threshold = int(
            get_config(
                "LLM_STREAM_THRESHOLD_CHARS",
                "8000"
            )
        )
        use_stream = len(
            str(
                user_content or ""
            )
        ) >= stream_threshold

        if use_stream:

            response = client.chat.completions.create(
                **request_args,
                stream=True
            )
            content_parts = []
            finish_reason = ""

            for chunk in response:

                choices = getattr(
                    chunk,
                    "choices",
                    None
                ) or []
                if not choices:
                    continue

                choice = choices[0]
                delta = getattr(
                    choice,
                    "delta",
                    None
                )
                chunk_content = getattr(
                    delta,
                    "content",
                    None
                ) if delta else None
                if chunk_content:
                    content_parts.append(
                        chunk_content
                    )

                if getattr(
                    choice,
                    "finish_reason",
                    None
                ):
                    finish_reason = choice.finish_reason

            content = "".join(
                content_parts
            )
            if not content:
                print("LLM返回为空")
                return None

            print("======================")
            print("DeepSeek调用完成")
            print("transport: stream")
            print("finish_reason:", finish_reason)
            print("======================")

            return content

        response = client.chat.completions.create(
            **request_args,
            stream=False
        )


        if not response.choices:
            print("LLM返回为空")
            return None


        content = response.choices[0].message.content


        print("======================")
        print("DeepSeek调用完成")
        print(
            "finish_reason:",
            response.choices[0].finish_reason
        )

        if response.usage:
            print(
                "Token:",
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )

        print("======================")


        return content


    except Exception as e:

        print("======================")
        print("调用DeepSeek失败")
        diagnostics = describe_llm_exception(
            e,
            get_config(
                "DEEPSEEK_MODEL",
                "deepseek-v4-flash"
            )
        )
        for key, value in diagnostics.items():
            print(
                f"{key}: {value}"
            )
        print("======================")


        return None
