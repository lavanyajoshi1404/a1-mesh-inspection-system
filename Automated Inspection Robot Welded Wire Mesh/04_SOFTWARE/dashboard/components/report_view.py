"""Formal engineering inspection record and export controls."""
import streamlit as st

from config.settings import SOFTWARE_ROOT
from dashboard.components.workstation import (
    render_dataframe,
    render_empty_run,
    render_kv_table,
    render_page_header,
    render_section_title,
    render_status_bar,
)
from dashboard.utils.export import generate_csv_spacings, generate_json_report, generate_text_report, save_inspection_to_disk
from dashboard.utils.presentation import inspection_view_model


def render_report_view(pipeline_result=None):
    result = pipeline_result or st.session_state.get("inspection_result")
    if result is None:
        render_page_header("A-1 MESH INSPECTION REPORT", "Formal inspection record.", "NO RUN")
        render_empty_run()
        return

    vm = inspection_view_model(result)
    render_page_header(
        "A-1 MESH INSPECTION REPORT",
        f"{vm['id']}  ·  {vm['timestamp']}",
        vm["classification"],
    )

    json_data = generate_json_report(result)
    text_data = generate_text_report(result)
    csv_data = generate_csv_spacings(result)

    actions = st.columns(4, gap="small")
    with actions[0]:
        if st.button("SAVE RECORD", type="primary", use_container_width=True):
            try:
                saved = save_inspection_to_disk(result, SOFTWARE_ROOT / "data" / "results")
                st.success(f"Saved {len(saved)} record artifacts.")
            except Exception as error:
                st.error(f"Record could not be saved: {error}")
    with actions[1]:
        st.download_button("JSON REPORT", json_data, f"inspection_{vm['id']}.json", "application/json", use_container_width=True)
    with actions[2]:
        st.download_button("TEXT REPORT", text_data, f"inspection_{vm['id']}.txt", "text/plain", use_container_width=True)
    with actions[3]:
        st.download_button("SPACING CSV", csv_data, f"spacing_{vm['id']}.csv", "text/csv", use_container_width=True)

    left, right = st.columns([0.5, 0.5], gap="small")
    with left:
        with st.container(border=True):
            render_section_title("Inspection identification")
            render_kv_table(
                [
                    ("Inspection ID", vm["id"]),
                    ("Timestamp", vm["timestamp"]),
                    ("Profile", vm["profile"]),
                    ("Image / source", vm["source"]),
                    ("Acquisition", vm["source_type"]),
                ]
            )
        with st.container(border=True):
            render_section_title("Decision")
            render_kv_table(
                [
                    ("Classification", vm["classification"]),
                    ("Decision", vm["decision"]),
                    ("Reason", vm["decision_note"]),
                ]
            )
            for reason in vm["decision_reasons"]:
                st.markdown(f"<div class='evidence-note'>{reason}</div>", unsafe_allow_html=True)
        with st.container(border=True):
            render_section_title("Measurements")
            render_kv_table(
                [
                    ("Grid", vm["grid"]),
                    ("Intersections", vm["intersections"]),
                    ("Vertical spacing", f"{vm['vertical_spacing_display']} / {vm['vertical_spacing_px']}"),
                    ("Horizontal spacing", f"{vm['horizontal_spacing_display']} / {vm['horizontal_spacing_px']}"),
                    ("Calibration", vm["calibration"]),
                    ("Tolerance", vm["tolerance_display"]),
                ]
            )

    with right:
        with st.container(border=True):
            render_section_title("Findings")
            fc = vm["finding_counts"]
            st.caption(
                f"{fc['visual']} visual findings on the sample  ·  "
                f"{fc['methodology']} methodology / calibration notes  ·  "
                f"{fc['total']} total entries below"
            )
            render_dataframe(vm["findings"], height=240)
        with st.container(border=True):
            render_section_title("Limitations")
            render_dataframe(vm["limitations"], height=220)

    render_status_bar(
        [
            ("Record", vm["id"]),
            ("Classification", vm["classification"]),
            ("Profile", vm["profile_id"]),
        ]
    )
