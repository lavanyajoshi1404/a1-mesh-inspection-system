"""
Vision-Based Anomaly Detection Component for the A1 Mesh Inspection Dashboard.

Presents factual, evidence-backed visual anomaly listings without fake ML scores or artificial hotspots.
"""

import pandas as pd
import streamlit as st


def render_anomaly_detection_view(pipeline_result):
    """Render the Vision-Based Anomaly Detection section with itemized evidence table."""
    st.markdown("### 3. Vision-Based Anomaly Detection")

    res = pipeline_result
    anomalies = res.anomalies

    anom_count = len([a for a in anomalies if a.status == "POTENTIALLY_ANOMALOUS"])
    review_count = len([a for a in anomalies if a.status in ("REVIEW", "INSUFFICIENT_EVIDENCE")])
    limitation_count = len([a for a in anomalies if a.status in ("UNCALIBRATED", "PROVISIONAL")])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Potential Visual Anomalies", anom_count, help="Arm mismatches requiring operator check")
    with c2:
        st.metric("Geometry Review Items", review_count, help="Missing expected crossings or boundary clipping")
    with c3:
        st.metric("Calibration Caveats", limitation_count, help="Provisional or uncalibrated axes")

    if not anomalies:
        st.success("No anomalies or review items detected in this mesh frame.")
        return

    st.markdown("#### Itemized Optical Evidence Table")

    # Format into DataFrame for clean tabular rendering
    table_data = []
    for a in anomalies:
        coords_str = f"({a.coordinates_px[0]}, {a.coordinates_px[1]}) px" if a.coordinates_px else "Full Axis"
        table_data.append({
            "#": a.id,
            "Category": a.category,
            "Location / Region": a.location,
            "Pixel Coordinates": coords_str,
            "Evaluation Status": a.status,
            "Factual Evidence": a.evidence,
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(
        "Notice: Potential visual anomalies flag local intensity/arm pattern mismatches. "
        "They do NOT claim mechanical weld strength, shear failure, or material defects."
    )
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
