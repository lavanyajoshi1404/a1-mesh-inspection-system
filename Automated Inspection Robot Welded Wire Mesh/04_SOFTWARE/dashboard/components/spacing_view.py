"""
Mesh Spacing Analysis Component for the A1 Mesh Inspection Dashboard.

Displays:
- Vertical Spacing (between horizontal wires along Y)
- Horizontal Spacing (between vertical wires along X)
- Pitch Statistics (Mean, Min, Max)
- Calibration Status (PROVISIONAL / UNCALIBRATED)
- Reference Profile Comparison & Tolerance Status
"""

import pandas as pd
import streamlit as st

from core.mesh_spacing import (
    STANDARD_PROFILES,
    compare_against_profile,
)


def render_spacing_analysis_view(pipeline_result):
    """Render the wire spacing analysis, interval tables, and profile comparison."""
    st.markdown("### 4. Wire Spacing & Aperture Analysis")

    res = pipeline_result
    spacing_res = res.spacing_result

    # Top summary metrics
    v_spacings = spacing_res.vertical_spacings
    h_spacings = spacing_res.horizontal_spacings

    v_mm_vals = [s.measured_spacing for s in v_spacings if s.measured_spacing is not None]
    h_px_vals = [s.pixel_spacing for s in h_spacings]
    v_px_vals = [s.pixel_spacing for s in v_spacings]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        v_mean_str = f"{spacing_res.mean_vertical_spacing_mm:.2f} mm" if spacing_res.mean_vertical_spacing_mm else "N/A"
        st.metric(
            "Vertical Mean Pitch",
            v_mean_str,
            f"{spacing_res.mean_vertical_spacing_px:.1f} px (PROVISIONAL)",
        )
    with c2:
        if v_mm_vals:
            st.metric("V-Pitch Min / Max", f"{min(v_mm_vals):.2f} / {max(v_mm_vals):.2f} mm")
        else:
            st.metric("V-Pitch Min / Max", "N/A")
    with c3:
        h_mean_str = f"{spacing_res.mean_horizontal_spacing_px:.1f} px"
        st.metric(
            "Horizontal Mean Pitch",
            h_mean_str,
            "UNCALIBRATED",
        )
    with c4:
        if h_px_vals:
            st.metric("H-Pitch Min / Max", f"{min(h_px_vals):.1f} / {max(h_px_vals):.1f} px")
        else:
            st.metric("H-Pitch Min / Max", "N/A")

    # Spacing Interval Tables
    tab_vert, tab_horiz, tab_profile = st.tabs([
        "Vertical Spacings (Along Y)",
        "Horizontal Spacings (Along X)",
        "Product Profile Comparison",
    ])

    with tab_vert:
        v_data = []
        for s in v_spacings:
            mm_str = f"{s.measured_spacing:.2f}" if s.measured_spacing is not None else "None"
            cal_str = f"{s.calibration_used:.1f} px/mm" if s.calibration_used else "None"
            v_data.append({
                "Interval": f"V{s.index} (Wires {s.wire_index_1} → {s.wire_index_2})",
                "Start Y (px)": s.wire_position_1_px,
                "End Y (px)": s.wire_position_2_px,
                "Pixel Spacing": f"{s.pixel_spacing:.2f} px",
                "Measured Spacing": f"{mm_str} mm",
                "Calibration Scale": cal_str,
                "Calibration Status": s.calibration_status,
                "Midpoint (px)": s.location_px,
            })
        if v_data:
            st.dataframe(pd.DataFrame(v_data), use_container_width=True, hide_index=True)
        else:
            st.info("No vertical spacing intervals detected.")

    with tab_horiz:
        h_data = []
        for s in h_spacings:
            mm_str = f"{s.measured_spacing:.2f}" if s.measured_spacing is not None else "Uncalibrated"
            h_data.append({
                "Interval": f"H{s.index} (Wires {s.wire_index_1} → {s.wire_index_2})",
                "Start X (px)": s.wire_position_1_px,
                "End X (px)": s.wire_position_2_px,
                "Pixel Spacing": f"{s.pixel_spacing:.2f} px",
                "Measured Spacing": mm_str,
                "Calibration Status": s.calibration_status,
                "Midpoint (px)": s.location_px,
                "Engineering Note": s.notes,
            })
        if h_data:
            st.dataframe(pd.DataFrame(h_data), use_container_width=True, hide_index=True)
        else:
            st.info("No horizontal spacing intervals detected.")

    with tab_profile:
        st.markdown("#### Comparison Against A-1 Reference Product Profiles")
        st.caption(
            "Reference specifications from A-1 Fence product catalog. "
            "Per engineering rules, acceptance tolerances are NOT invented; they remain unconfigured."
        )

        selected_pid = st.selectbox(
            "Select Reference Product Profile",
            options=list(STANDARD_PROFILES.keys()),
            format_func=lambda k: f"{k} — {STANDARD_PROFILES[k].name}",
            index=0,
        )

        profile = STANDARD_PROFILES[selected_pid]
        comp = compare_against_profile(spacing_res, profile)

        st.markdown(
            f"**Selected Profile:** `{profile.profile_id}` — {profile.name}  \n"
            f"**Nominal Aperture:** {profile.nominal_vertical_spacing_mm} mm (V) × {profile.nominal_horizontal_spacing_mm} mm (H)  \n"
            f"**Configured Tolerance:** Vertical: `{profile.vertical_tolerance_mm}` | Horizontal: `{profile.horizontal_tolerance_mm}`  \n"
            f"**Status:** `NO TOLERANCE CONFIGURED`"
        )

        comp_data = []
        for c in comp.comparisons:
            meas_str = f"{c.measured_spacing_mm:.2f} mm" if c.measured_spacing_mm is not None else "Uncalibrated"
            nom_str = f"{c.nominal_spacing_mm:.2f} mm" if c.nominal_spacing_mm is not None else "N/A"
            dev_str = f"{c.deviation_mm:+.2f} mm" if c.deviation_mm is not None else "N/A"
            comp_data.append({
                "Axis": c.axis.upper(),
                "Index": c.index,
                "Measured": meas_str,
                "Nominal Ref": nom_str,
                "Deviation": dev_str,
                "Tolerance": "Unconfigured (None)",
                "Compliance Status": c.status,
                "Observation Notes": c.notes,
            })

        st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)
        st.warning(
            "Compliance Rule: Deviation from nominal is NOT classified as a confirmed spacing defect "
            "because no validated production tolerance is configured for this prototype sample."
        )

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
