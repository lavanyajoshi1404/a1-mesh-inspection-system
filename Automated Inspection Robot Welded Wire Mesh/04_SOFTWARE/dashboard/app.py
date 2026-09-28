"""
A-1 MESH INSPECTION SYSTEM — industrial quality inspection workstation
"""

import sys
from pathlib import Path

SOFTWARE_ROOT = Path(__file__).resolve().parent.parent
if str(SOFTWARE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOFTWARE_ROOT))

import streamlit as st

from dashboard.components.architecture import render_system_architecture
from dashboard.components.measurements_page import render_measurements_page
from dashboard.components.new_inspection_view import render_new_inspection_page
from dashboard.components.report_view import render_report_view
from dashboard.components.result_panel import render_result_panel
from dashboard.components.visualizer import render_visual_inspection


st.set_page_config(
    page_title="A-1 Mesh Inspection System",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css():
    css_path = Path(__file__).parent / "styles" / "theme.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


NAV_PAGES = [
    "New Inspection",
    "Inspection Result",
    "Visual Inspection",
    "Measurements & Findings",
    "Inspection Report",
    "Architecture",
]

PAGE_LABELS = {
    "New Inspection": "1  NEW INSPECTION",
    "Inspection Result": "2  INSPECTION RESULT",
    "Visual Inspection": "3  VISUAL INSPECTION",
    "Measurements & Findings": "4  MEASUREMENTS & FINDINGS",
    "Inspection Report": "5  INSPECTION REPORT",
    "Architecture": "6  ARCHITECTURE",
}


def init_session_state():
    if "nav_selection" not in st.session_state:
        st.session_state["nav_selection"] = "New Inspection"
    if "nav_radio_widget" not in st.session_state:
        st.session_state["nav_radio_widget"] = "New Inspection"
    if "inspection_result" not in st.session_state:
        st.session_state["inspection_result"] = None


def _clean_html(raw_html: str) -> str:
    return "".join(line.strip() for line in raw_html.splitlines() if line.strip())


def render_sidebar():
    with st.sidebar:
        st.markdown(
            _clean_html(
                """
                <div style="padding:2px 0 8px 0;border-bottom:1px solid #334155;margin-bottom:8px;">
                    <div class="sidebar-brand-title">A-1 MESH</div>
                    <div class="sidebar-brand-sub">Inspection workstation</div>
                </div>
                <div class="sidebar-section-header">Navigation</div>
                """
            ),
            unsafe_allow_html=True,
        )

        target_page = st.session_state.pop("pending_navigation", None)
        if target_page in NAV_PAGES:
            st.session_state["nav_radio_widget"] = target_page

        selected = st.radio(
            "Application Navigation",
            options=NAV_PAGES,
            format_func=lambda x: PAGE_LABELS[x],
            label_visibility="collapsed",
            key="nav_radio_widget",
        )

        if selected != st.session_state.get("nav_selection"):
            st.session_state["nav_selection"] = selected
            st.rerun()

        res = st.session_state.get("inspection_result")
        state = "ACTIVE" if res is not None else "READY"
        st.markdown(
            f"<div class='sidebar-state' style='margin-top:10px;'>SYSTEM {state}</div>",
            unsafe_allow_html=True,
        )


def main():
    load_css()
    init_session_state()
    render_sidebar()

    current_page = st.session_state.get("nav_selection", "New Inspection")
    res = st.session_state.get("inspection_result")

    if current_page == "New Inspection":
        render_new_inspection_page()
    elif current_page == "Inspection Result":
        render_result_panel(res)
    elif current_page == "Visual Inspection":
        render_visual_inspection(res)
    elif current_page == "Measurements & Findings":
        render_measurements_page(res)
    elif current_page == "Inspection Report":
        render_report_view(res)
    elif current_page == "Architecture":
        render_system_architecture()


if __name__ == "__main__":
    main()
