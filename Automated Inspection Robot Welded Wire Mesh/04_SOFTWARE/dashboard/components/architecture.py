"""Implemented-versus-future system architecture page."""
import streamlit as st

from dashboard.components.workstation import render_page_header, render_section_title, render_status_bar


COMPUTER_VISION_PIPELINE = [
    "Image",
    "Preprocessing",
    "Wire/Grid Detection",
    "Intersection Detection",
    "Intersection Analysis",
    "Mesh Spacing Measurement",
    "Inspection Decision",
    "Dashboard / Report",
]

PROPOSED_SYSTEM_ARCHITECTURE = [
    "Welded Wire Mesh",
    "Mesh Transport / Positioning",
    "Inspection Position",
    "Camera + Illumination",
    "Image Acquisition",
    "Computer Vision",
    "Wire/Grid Detection",
    "Intersection Analysis",
    "Spacing Measurement",
    "Inspection Decision",
    "Dashboard",
    "Inspection Record",
]

FUTURE_CAPABILITIES = [
    "Physical rejection",
    "Larger labelled dataset",
    "ML / deep learning if justified by validated requirements",
    "Multi-camera inspection",
    "Industrial integration (PLC / line handshake)",
    "Remote analytics",
]


def _flow_text(steps):
    lines = []
    for index, step in enumerate(steps):
        lines.append(step)
        if index < len(steps) - 1:
            lines.append("↓")
    return "\n\n".join(lines)


def render_system_architecture():
    render_page_header(
        "COMPUTER-VISION INSPECTION SYSTEM",
        "Current inspection pipeline and proposed end-to-end production architecture.",
        "ENGINEERING OVERVIEW",
    )
    pipeline, proposed = st.columns(2, gap="small")
    with pipeline:
        with st.container(border=True):
            render_section_title("Computer-Vision Inspection Pipeline")
            st.markdown(_flow_text(COMPUTER_VISION_PIPELINE))
            st.markdown(
                "<div class='evidence-note'>Visual analysis does not certify weld strength, tensile performance, coating quality, or destructive-test outcomes.</div>",
                unsafe_allow_html=True,
            )
    with proposed:
        with st.container(border=True):
            render_section_title("Proposed System Architecture")
            st.markdown(_flow_text(PROPOSED_SYSTEM_ARCHITECTURE))
            st.caption("Mesh transport and positioning are proposed production stages, not current prototype capabilities.")
    st.markdown("### Other Future Capabilities")
    st.markdown("\n".join(f"- {item}" for item in FUTURE_CAPABILITIES))
    render_status_bar([("Scope", "Prototype workstation"), ("Mesh transport", "Proposed")])
