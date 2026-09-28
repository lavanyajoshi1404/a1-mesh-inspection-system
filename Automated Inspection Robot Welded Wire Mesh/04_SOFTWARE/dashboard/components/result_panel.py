"""Primary operator decision workstation."""
import streamlit as st

from dashboard.components.workstation import (
    render_empty_run,
    render_evidence_list,
    render_kv_table,
    render_page_header,
    render_section_title,
    render_status_bar,
    render_verdict_strip,
)
from dashboard.utils.classification_presentation import get_classification_presentation
from dashboard.utils.nav_helper import navigate_to_page
from dashboard.utils.presentation import inspection_view_model


def render_result_panel(pipeline_result=None):
    result = pipeline_result or st.session_state.get("inspection_result")
    if result is None:
        render_page_header("INSPECTION RESULT", "Operator decision workstation.", "NO RUN")
        render_empty_run()
        return

    vm = inspection_view_model(result)
    presentation = get_classification_presentation(vm["classification"])
    render_page_header(
        "INSPECTION RESULT",
        f"{vm['id']}  ·  {vm['timestamp']}  ·  {vm['profile']}",
        vm["classification"],
    )
    render_verdict_strip(
        vm["classification"],
        presentation["subtitle"],
        vm["decision_note"],
    )

    image_col, evidence_col = st.columns([0.63, 0.37], gap="small")
    with image_col:
        with st.container(border=True):
            render_section_title("Inspection evidence")
            image = result.intersection_overlay if result.intersection_overlay is not None else result.original_image
            st.markdown("<div class='result-image'>", unsafe_allow_html=True)
            st.image(image, channels="BGR", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with evidence_col:
        with st.container(border=True):
            render_section_title("Inspection summary")
            render_kv_table(
                [
                    ("Grid", vm["grid"]),
                    ("Intersections", vm["intersections"]),
                    ("Visual findings", f"{vm['potential_anomalies']} potential anomalies"),
                    ("Spacing", f"{vm['vertical_spacing_display']} vertical"),
                    ("Vertical cal.", vm["vertical_calibration"]),
                    ("Horizontal spacing", vm["horizontal_spacing_display"]),
                    ("Tolerance", vm["tolerance_display"]),
                ]
            )
            render_section_title("Findings / evidence")
            render_evidence_list(vm["evidence_statements"])

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        if st.button("Visual inspection", use_container_width=True):
            navigate_to_page("Visual Inspection")
    with c2:
        if st.button("Measurements", use_container_width=True):
            navigate_to_page("Measurements & Findings")
    with c3:
        if st.button("Inspection report", use_container_width=True):
            navigate_to_page("Inspection Report")

    render_status_bar(
        [
            ("Decision", vm["decision"]),
            ("Classification", vm["classification"]),
            ("Calibration", vm["calibration"]),
        ]
    )
