"""Reusable Streamlit presentation primitives for the active workstation."""
from typing import Iterable, List, Optional, Sequence, Tuple

import pandas as pd
import streamlit as st

from dashboard.utils.classification_presentation import get_classification_presentation
from dashboard.utils.nav_helper import navigate_to_page


def _clean_html(raw_html: str) -> str:
    return "".join(line.strip() for line in raw_html.splitlines() if line.strip())


def render_page_header(title: str, subtitle: str, state: str = "SYSTEM READY"):
    st.markdown(
        _clean_html(
            f"""
            <div class="page-header">
              <div>
                <div class="page-title">{title}</div>
                <div class="page-subtitle">{subtitle}</div>
              </div>
              <div class="status-badge">{state}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_section_title(title: str):
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)


def render_kv_table(rows: Sequence[Tuple[str, object]]):
    body = "".join(
        f"<tr><th>{label}</th><td>{'' if value is None else value}</td></tr>"
        for label, value in rows
    )
    st.markdown(f"<table class='kv'>{body}</table>", unsafe_allow_html=True)


def render_verdict_strip(classification: str, subtitle: str, note: str = ""):
    presentation = get_classification_presentation(classification)
    style = presentation.get("class_name", "")
    extra = f"<div class='verdict-text'>{note}</div>" if note else ""
    st.markdown(
        _clean_html(
            f"""
            <div class="verdict {style}">
              <div class="verdict-kicker">Inspection status</div>
              <div class="verdict-title">{presentation['label']}</div>
              <div class="verdict-text">{subtitle}</div>
              {extra}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_evidence_list(items: Iterable[str]):
    entries = "".join(f"<li>{item}</li>" for item in items)
    if not entries:
        return
    st.markdown(f"<ul class='evidence-list'>{entries}</ul>", unsafe_allow_html=True)


def render_status_bar(items: Sequence[Tuple[str, str]]):
    parts = "".join(f"<span>{label}: <b>{value}</b></span>" for label, value in items)
    st.markdown(f"<div class='status-bar'>{parts}</div>", unsafe_allow_html=True)


def render_dataframe(rows: List[dict], height: Optional[int] = None):
    if not rows:
        st.caption("No records for this section.")
        return
    kwargs = {"use_container_width": True, "hide_index": True}
    if height is not None:
        kwargs["height"] = height
    st.dataframe(pd.DataFrame(rows), **kwargs)


def render_empty_run(message: str = "No inspection is available. Acquire an image and run inspection."):
    st.info(message)
    if st.button("Go to New Inspection", type="primary"):
        navigate_to_page("New Inspection")
