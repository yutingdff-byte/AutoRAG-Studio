"""Streamlit UI helpers for persisted Excel task recovery."""

from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

from storage.task_store import (
    PersistedTask,
    TaskExpiredError,
    TaskNotFoundError,
    TaskStoreError,
    load_excel_files,
)


LOCAL_STORAGE_KEY = "autorag_last_recovery_token"
COOKIE_NAME = "autorag_last_recovery_token"
COOKIE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def _cookie_value(name: str) -> str:
    try:
        value = st.context.cookies.get(name, "")
    except Exception:
        return ""
    return str(value or "")


def install_auto_restore_script() -> None:
    """Migrate the old localStorage token to a first-party cookie if needed."""

    components.html(
        f"""
        <script>
        (() => {{
          try {{
            const token = window.localStorage.getItem({LOCAL_STORAGE_KEY!r});
            if (!token) return;
            const cookie = `${{{json.dumps(COOKIE_NAME)}}}=${{encodeURIComponent(token)}}; Max-Age={COOKIE_MAX_AGE_SECONDS}; Path=/; SameSite=Lax`;
            try {{
              window.parent.document.cookie = cookie;
            }} catch (err) {{
              document.cookie = cookie;
            }}
          }} catch (err) {{
            console.debug("AutoRAG recovery token unavailable", err);
          }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def remember_recovery_token(token: str) -> None:
    token_json = json.dumps(token)
    cookie_name_json = json.dumps(COOKIE_NAME)
    components.html(
        f"""
        <script>
        (() => {{
          try {{
            const token = {token_json};
            window.localStorage.setItem({LOCAL_STORAGE_KEY!r}, token);
            const cookie = `${{{cookie_name_json}}}=${{encodeURIComponent(token)}}; Max-Age={COOKIE_MAX_AGE_SECONDS}; Path=/; SameSite=Lax`;
            try {{
              window.parent.document.cookie = cookie;
            }} catch (err) {{
              document.cookie = cookie;
            }}
          }} catch (err) {{
            console.debug("AutoRAG recovery token save failed", err);
          }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def clear_recovery_token() -> None:
    cookie_name_json = json.dumps(COOKIE_NAME)
    components.html(
        f"""
        <script>
        (() => {{
          try {{
            window.localStorage.removeItem({LOCAL_STORAGE_KEY!r});
            const expireRoot = `${{{cookie_name_json}}}=; Max-Age=0; Path=/; SameSite=Lax`;
            const expireHere = `${{{cookie_name_json}}}=; Max-Age=0; SameSite=Lax`;
            try {{
              window.parent.localStorage.removeItem({LOCAL_STORAGE_KEY!r});
            }} catch (err) {{}}
            try {{
              window.parent.document.cookie = expireRoot;
              window.parent.document.cookie = expireHere;
            }} catch (err) {{
              document.cookie = expireRoot;
              document.cookie = expireHere;
            }}
          }} catch (err) {{
            console.debug("AutoRAG recovery token clear failed", err);
          }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def restore_task_to_session(token: str) -> PersistedTask:
    task, files = load_excel_files(token)
    st.session_state.recovered_task = task.to_public_dict()
    st.session_state.recovered_export_files = files
    st.session_state.recovered_token = token
    st.session_state.recovered_error = ""
    return task


def _render_downloads(files: dict[str, dict], key_prefix: str) -> None:
    static_file = files.get("static")
    dynamic_file = files.get("dynamic")
    if static_file:
        st.download_button(
            "下载车型配置知识库",
            data=static_file["data"],
            file_name=static_file["file_name"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key_prefix}_static",
            use_container_width=True,
        )
    if dynamic_file:
        st.download_button(
            "下载价格政策知识库",
            data=dynamic_file["data"],
            file_name=dynamic_file["file_name"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key_prefix}_dynamic",
            use_container_width=True,
        )


def render_persisted_task_notice(task: PersistedTask | dict, token: str, key_prefix: str) -> None:
    expires_at = task.expires_at if isinstance(task, PersistedTask) else task.get("expires_at", "")
    st.success("Excel 已保存到当前任务存储。")
    st.caption(f"有效期至：{expires_at}")
    st.code(token, language="text")
    st.caption("请妥善保存恢复码。恢复码等同于下载凭证，不要发给无关人员。")
    st.caption("当前未接入外部对象存储；请及时下载 Excel。刷新、关闭网页或 app 重启后不保证恢复。")
    remember_recovery_token(token)


def render_recovery_sidebar() -> None:
    install_auto_restore_script()

    cookie_token = _cookie_value(COOKIE_NAME)
    if cookie_token and st.session_state.get("recovered_token") != cookie_token:
        try:
            restore_task_to_session(cookie_token)
            remember_recovery_token(cookie_token)
        except (TaskExpiredError, TaskNotFoundError, TaskStoreError) as exc:
            st.session_state.recovered_error = str(exc)

    with st.sidebar.expander("恢复已保存任务", expanded=bool(st.session_state.get("recovered_task"))):
        st.caption("同一浏览器会自动尝试恢复最近一次任务；换电脑时可输入恢复码。当前未接入外部对象存储时，不保证 app 重启后恢复。")
        with st.form("manual_task_recovery_form"):
            token = st.text_input("恢复码", type="password")
            submitted = st.form_submit_button("恢复任务", use_container_width=True)
        if submitted:
            try:
                task = restore_task_to_session(token)
                remember_recovery_token(token)
                st.success(f"已恢复 {task.mode} 任务。")
            except (TaskExpiredError, TaskNotFoundError, TaskStoreError) as exc:
                st.error(str(exc))

        error_text = st.session_state.get("recovered_error")
        if error_text:
            st.warning(error_text)

        task = st.session_state.get("recovered_task")
        files = st.session_state.get("recovered_export_files") or {}
        if task and files:
            mode_label = "新建知识库" if task.get("mode") == "generate" else "更新知识库"
            st.markdown(f"**已恢复：{mode_label}**")
            st.caption(f"完成时间：{task.get('completed_at', '')}")
            st.caption(f"有效期至：{task.get('expires_at', '')}")
            _render_downloads(files, "recovered_task_download")

        if st.button("清除本机任务记录", use_container_width=True):
            clear_recovery_token()
            st.session_state.recovered_task = None
            st.session_state.recovered_export_files = {}
            st.session_state.recovered_token = ""
            st.session_state.recovered_error = ""
            st.info("已清除本机自动恢复记录。任务存储中的文件不会被立即删除。")
