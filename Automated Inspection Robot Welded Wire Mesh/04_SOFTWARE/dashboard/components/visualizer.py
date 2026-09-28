"""Single-image visual evidence workspace."""
import streamlit as st

from dashboard.components.workstation import (
    render_empty_run,
    render_kv_table,
    render_page_header,
    render_section_title,
    render_status_bar,
)
from dashboard.utils.presentation import inspection_view_model, visual_mode_evidence


def render_visual_inspection(pipeline_result=None):
    result = pipeline_result or st.session_state.get("inspection_result")
    if result is None:
        render_page_header("VISUAL INSPECTION", "One evidence rendering at a time.", "NO RUN")
        render_empty_run()
        return

    vm = inspection_view_model(result)
    render_page_header(
        "VISUAL INSPECTION",
        f"{vm['id']}  ·  {vm['classification']}  ·  {vm['grid']}",
        "EVIDENCE",
    )

    selected = st.radio(
        "Visualization mode",
        ["ORIGINAL", "GRID", "INTERSECTIONS", "HEATMAP", "SPACING"],
        horizontal=True,
    )
    images = {
        "ORIGINAL": result.original_image,
        "GRID": result.grid_overlay,
        "INTERSECTIONS": result.intersection_overlay,
        "HEATMAP": result.heatmap_overlay,
        "SPACING": result.spacing_overlay,
    }
    panel = visual_mode_evidence(result, selected)

    image_col, detail_col = st.columns([0.73, 0.27], gap="small")
    with image_col:
        with st.container(border=True):
            render_section_title(f"{selected} view")
            image = images[selected] if images[selected] is not None else result.original_image
            st.markdown("<div class='workspace-image'>", unsafe_allow_html=True)
            st.image(image, channels="BGR", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with detail_col:
        with st.container(border=True):
            render_section_title("Evidence")
            render_kv_table(panel["rows"])
            for note in panel["notes"]:
                st.markdown(f"<div class='evidence-note'>{note}</div>", unsafe_allow_html=True)

    render_status_bar(
        [
            ("Mode", selected),
            ("Intersections", vm["intersections"]),
            ("Visual findings", str(vm["potential_anomalies"])),
        ]
    )
