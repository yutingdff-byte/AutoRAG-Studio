"""AutoRAG-Studio Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from pages.generate_page import render_generate_page
from pages.home_page import render_home_page
from pages.update_page import render_update_page
from ui.components import render_footer
from ui.styles import load_global_styles


APP_VERSION = "V0.8.0-dev"


def initialize_session_state() -> None:
    defaults = {
        "current_mode": "home",
        "generate_stage": "idle",
        "generate_result": None,
        "generate_input_file_count": 0,
        "generate_export_files": {},
        "update_stage": "idle",
        "update_diff_result": None,
        "update_restore_result": None,
        "update_restore_logs": [],
        "update_restore_cache": {},
        "update_restore_cache_key": "",
        "update_restore_running": False,
        "update_new_knowledge": [],
        "update_new_errors": [],
        "update_new_logs": [],
        "update_old_file_names": [],
        "update_new_file_names": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "navigation_mode" not in st.session_state:
        st.session_state.navigation_mode = st.session_state.current_mode


def sync_navigation_mode() -> None:
    st.session_state.current_mode = st.session_state.navigation_mode


def render_navigation() -> None:
    st.sidebar.title("AutoRAG-Studio")

    st.sidebar.radio(
        "工作模式",
        options=["home", "generate", "update"],
        format_func=lambda value: {
            "home": "首页",
            "generate": "新建知识库",
            "update": "更新知识库",
        }[value],
        key="navigation_mode",
        on_change=sync_navigation_mode,
    )

    st.sidebar.caption(f"AutoRAG-Studio {APP_VERSION}")
    st.sidebar.info("请勿在未经授权的公共云环境中上传客户敏感资料、未公开资料或含个人信息的数据。")


def render_current_page() -> None:
    if st.session_state.current_mode == "generate":
        render_generate_page()
    elif st.session_state.current_mode == "update":
        render_update_page()
    else:
        render_home_page()


def main() -> None:
    st.set_page_config(
        page_title="AutoRAG-Studio",
        page_icon="🚗",
        layout="wide",
    )
    initialize_session_state()
    load_global_styles()
    render_navigation()
    render_current_page()
    render_footer(APP_VERSION)


if __name__ == "__main__":
    main()
