import os


try:

    from dotenv import load_dotenv

    load_dotenv()

except ModuleNotFoundError:

    pass


def _get_streamlit_secret(name):

    try:

        import streamlit as st

        value = st.secrets.get(
            name
        )

        if value:

            return str(
                value
            )

    except Exception:

        return ""

    return ""


def get_config(name, default=""):

    value = _get_streamlit_secret(
        name
    )

    if value:

        return value

    value = os.getenv(
        name,
        ""
    )

    if value:

        return value

    return default


def require_config(name, service_name="服务"):

    value = get_config(
        name
    )

    if value:

        return value

    raise RuntimeError(
        f"{service_name}未配置：缺少{name}。请在Streamlit Secrets、系统环境变量或本地.env中配置。"
    )
