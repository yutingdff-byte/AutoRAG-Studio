"""Reusable Streamlit UI components."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import streamlit as st


def render_page_header(title: str, subtitle: str, eyebrow: str | None = None) -> None:
    if eyebrow:
        st.caption(eyebrow)
    st.title(title)
    st.caption(subtitle)


def render_section_title(title: str) -> None:
    st.subheader(title)


def render_status_badge(label: str, status: str = "default") -> None:
    css_class = {
        "ready": "autorag-status-ready",
        "building": "autorag-status-building",
    }.get(status, "")
    st.markdown(
        f'<span class="autorag-status {css_class}">{label}</span>',
        unsafe_allow_html=True,
    )


def render_step_navigation(steps: Sequence[str]) -> None:
    items = "".join(f'<span class="autorag-step">{step}</span>' for step in steps)
    st.markdown(
        f'<div class="autorag-step-wrap">{items}</div>',
        unsafe_allow_html=True,
    )


def render_feature_card(
    title: str,
    body: str,
    tags: Iterable[str],
    status_label: str,
    status: str,
) -> None:
    with st.container(border=True):
        st.subheader(title)
        if status_label:
            st.caption(status_label)
        st.write(body)
        st.caption(" · ".join(str(tag) for tag in tags))


def render_metric_cards(metrics: Sequence[tuple[str, str | int, str]]) -> None:
    if not metrics:
        return

    columns = st.columns(len(metrics))
    for column, (label, value, help_text) in zip(columns, metrics):
        with column:
            st.metric(label, value, help=help_text or None)


def render_file_card(file_name: str, file_type: str, file_size: int | None = None, status: str = "已接收") -> None:
    size_text = ""
    if file_size is not None:
        size_text = f" · {file_size / 1024:.1f} KB"
    st.markdown(
        f"""
        <div class="autorag-file-card">
            <div class="autorag-file-name">{file_name}</div>
            <div class="autorag-file-meta">{file_type}{size_text} · {status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer(version: str | None = None) -> None:
    text = "AutoRAG-Studio"
    if version:
        text = f"{text} {version}"
    st.caption(text)
