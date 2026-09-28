"""Engineering measurement and finding tables for a completed inspection."""
import streamlit as st

from dashboard.components.workstation import (
    render_dataframe,
    render_empty_run,
    render_kv_table,
    render_page_header,
    render_section_title,
    render_status_bar,
)
from dashboard.utils.presentation import inspection_view_model


def render_measurements_page(pipeline_result=None):
    result = pipeline_result or st.session_state.get("inspection_result")
    if result is None:
        render_page_header("MEASUREMENTS & FINDINGS", "Traceable metrology record.", "NO RUN")
        render_empty_run()
        return

    vm = inspection_view_model(result)
    render_page_header(
        "MEASUREMENTS & FINDINGS",
        f"{vm['id']}  ·  {vm['source']}",
        vm["decision"],
    )

    c1, c2 = st.columns(2, gap="small")
    with c1:
        with st.container(border=True):
            render_section_title("Image / processing")
            render_kv_table(
                [
                    ("Source dimensions", vm["image"]),
                    ("Processed dimensions", vm["processing"]),
                    ("Scale", f"{vm['resize_scale']:.3f}"),
                    ("Otsu threshold", vm["otsu"]),
                    ("Acquisition", vm["source_type"]),
                ]
            )
        with st.container(border=True):
            render_section_title("Grid")
            render_kv_table(
                [
                    ("Horizontal wires", vm["num_horizontal"]),
                    ("Vertical wires", vm["num_vertical"]),
                    ("Angle deviation H", vm["angle_h"]),
                    ("Angle deviation V", vm["angle_v"]),
                    ("Intersection completeness", f"{vm['intersections']}  ({vm['completeness']})"),
                ]
            )
        with st.container(border=True):
            render_section_title("Intersections")
            render_kv_table(
                [
                    ("Total analyzed", vm["num_analyzed"]),
                    ("Normal", vm["num_normal"]),
                    ("Potentially anomalous", vm["potential_anomalies"]),
                    ("Insufficient evidence", vm["insufficient_evidence"]),
                ]
            )

    with c2:
        with st.container(border=True):
            render_section_title("Spacing")
            render_kv_table(
                [
                    ("Vertical", f"{vm['vertical_spacing_display']}  ({vm['vertical_spacing_px']})"),
                    ("Horizontal", f"{vm['horizontal_spacing_display']}  ({vm['horizontal_spacing_px']})"),
                    ("Vertical calibration", vm["vertical_calibration"]),
                    ("Horizontal calibration", vm["horizontal_calibration"]),
                    ("Profile", vm["profile"]),
                    ("Tolerance", vm["tolerance_display"]),
                ]
            )
            render_dataframe(vm["spacing_rows"], height=168)
            render_dataframe(vm["calibration_rows"], height=108)
        with st.container(border=True):
            render_section_title("Findings")
            fc = vm["finding_counts"]
            st.caption(
                f"{fc['visual']} visual findings on the sample  ·  "
                f"{fc['methodology']} methodology / calibration notes  ·  "
                f"{fc['total']} total entries below"
            )
            render_dataframe(vm["findings"], height=220)

    render_status_bar(
        [
            ("Classification", vm["classification"]),
            ("Spacing status", vm["spacing_status"]),
            ("Intersection status", vm["intersection_status"]),
        ]
    )
