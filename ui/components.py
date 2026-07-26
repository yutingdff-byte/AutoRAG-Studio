"""Reusable Streamlit UI components."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import streamlit as st


def render_page_header(title: str, subtitle: str, eyebrow: str | None = None) -> None:
    eyebrow_html = f'<div class="autorag-eyebrow">{eyebrow}</div>' if eyebrow else ""
    st.markdown(
        f"""
        <div class="autorag-page-header">
            {eyebrow_html}
            <h1 class="autorag-title">{title}</h1>
            <div class="autorag-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(title: str) -> None:
    st.markdown(
        f'<div class="autorag-section-title">{title}</div>',
        unsafe_allow_html=True,
    )


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
    tag_html = "".join(f'<span class="autorag-chip">{tag}</span>' for tag in tags)
    status_class = {
        "ready": "autorag-status-ready",
        "building": "autorag-status-building",
    }.get(status, "")
    st.markdown(
        f"""
        <div class="autorag-card">
            <div class="autorag-card-title">{title}</div>
            <span class="autorag-status {status_class}">{status_label}</span>
            <div class="autorag-card-body">{body}</div>
            <div class="autorag-chip-row">{tag_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def render_footer(version: str) -> None:
    st.markdown(
        f'<div class="autorag-footer">AutoRAG-Studio {version}</div>',
        unsafe_allow_html=True,
    )
