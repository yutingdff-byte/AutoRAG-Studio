"""Centralized Streamlit styling for AutoRAG-Studio."""

import streamlit as st


def load_global_styles() -> None:
    """Apply lightweight SaaS-style visual polish without touching business logic."""

    st.markdown(
        """
        <style>
        :root {
            --autorag-border: #e5e7eb;
            --autorag-muted: #64748b;
            --autorag-ink: #0f172a;
            --autorag-bg-soft: #f8fafc;
            --autorag-blue: #2563eb;
            --autorag-green: #059669;
            --autorag-amber: #d97706;
        }

        .block-container {
            max-width: 1180px;
            padding-top: 2.25rem;
            padding-bottom: 3rem;
        }

        .autorag-page-header {
            border-bottom: 1px solid var(--autorag-border);
            padding-bottom: 1.15rem;
            margin-bottom: 1.25rem;
        }

        .autorag-eyebrow {
            color: var(--autorag-blue);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0;
            margin-bottom: 0.35rem;
        }

        .autorag-title {
            color: var(--autorag-ink);
            font-size: 2rem;
            font-weight: 760;
            line-height: 1.2;
            margin: 0;
        }

        .autorag-subtitle {
            color: var(--autorag-muted);
            font-size: 1rem;
            line-height: 1.65;
            margin-top: 0.55rem;
            max-width: 820px;
        }

        .autorag-card {
            border: 1px solid var(--autorag-border);
            border-radius: 8px;
            padding: 1.15rem;
            background: #ffffff;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            height: 100%;
        }

        .autorag-card-title {
            color: var(--autorag-ink);
            font-size: 1.08rem;
            font-weight: 720;
            margin-bottom: 0.45rem;
        }

        .autorag-card-body {
            color: var(--autorag-muted);
            font-size: 0.94rem;
            line-height: 1.58;
            margin-bottom: 0.75rem;
        }

        .autorag-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.7rem;
        }

        .autorag-chip {
            border: 1px solid var(--autorag-border);
            border-radius: 999px;
            color: #334155;
            background: var(--autorag-bg-soft);
            font-size: 0.78rem;
            padding: 0.2rem 0.55rem;
        }

        .autorag-status {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.18rem 0.52rem;
            font-size: 0.78rem;
            font-weight: 650;
            border: 1px solid var(--autorag-border);
            color: #334155;
            background: #ffffff;
        }

        .autorag-status-ready {
            color: var(--autorag-green);
            border-color: #bbf7d0;
            background: #f0fdf4;
        }

        .autorag-status-building {
            color: var(--autorag-amber);
            border-color: #fde68a;
            background: #fffbeb;
        }

        .autorag-section-title {
            color: var(--autorag-ink);
            font-size: 1.18rem;
            font-weight: 730;
            margin: 1.4rem 0 0.55rem;
        }

        .autorag-step-wrap {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.75rem 0 1.1rem;
        }

        .autorag-step {
            border: 1px solid var(--autorag-border);
            border-radius: 999px;
            background: var(--autorag-bg-soft);
            color: #334155;
            font-size: 0.84rem;
            padding: 0.32rem 0.7rem;
        }

        .autorag-file-card {
            border: 1px solid var(--autorag-border);
            border-radius: 8px;
            padding: 0.58rem 0.72rem;
            background: #ffffff;
            margin-bottom: 0.38rem;
        }

        .autorag-file-name {
            color: var(--autorag-ink);
            font-size: 0.92rem;
            font-weight: 660;
            margin-bottom: 0.1rem;
            line-height: 1.3;
        }

        .autorag-file-meta {
            color: var(--autorag-muted);
            font-size: 0.8rem;
        }

        .autorag-footer {
            color: var(--autorag-muted);
            font-size: 0.82rem;
            border-top: 1px solid var(--autorag-border);
            margin-top: 2.3rem;
            padding-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
