"""
Header and Pipeline Indicator Component for the A1 Mesh Inspection Dashboard.
"""

import streamlit as st


def render_header(status: str = "READY"):
    """Render the main industrial header, title, subtitle, and system status indicator."""
    status_class = {
        "READY": "status-ready",
        "PROCESSING": "status-processing",
        "COMPLETE": "status-complete",
    }.get(status, "status-ready")

    st.markdown(
        f"""
        <div class="main-header">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 class="main-title">A-1 MESH INSPECTION SYSTEM</h1>
                    <div class="main-subtitle">Automated Vision-Based Quality Inspection for Welded Wire Mesh Production</div>
                </div>
                <div>
                    <span class="status-badge {status_class}">● SYSTEM {status}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pipeline_indicator(active_step: str = "RESULT"):
    """Render a compact horizontal pipeline progress flow indicator."""
    steps = [
        ("IMAGE", "Acquisition"),
        ("PREPROCESSING", "Filter / Contrast"),
        ("GRID DETECTION", "Wire Geometry"),
        ("INTERSECTIONS", "Arm Appearance"),
        ("SPACING", "Pitch / Aperture"),
        ("ANOMALY ANALYSIS", "Optical Evidence"),
        ("DECISION", "Conservative Rules"),
        ("RESULT", "Operator Report"),
    ]

    cols = st.columns(len(steps))
    for idx, (step_name, sub) in enumerate(steps):
        is_active = (step_name == active_step) or (active_step == "RESULT")
        bg_col = "#0284c7" if is_active else "#f1f5f9"
        text_col = "#ffffff" if is_active else "#64748b"
        border_col = "#0284c7" if is_active else "#cbd5e1"
        icon = "✓" if (active_step == "RESULT" or is_active) else f"{idx+1}"

        cols[idx].markdown(
            f"""
            <div style="background:{bg_col}; border:1px solid {border_col}; border-radius:4px; padding:6px 4px; text-align:center;">
                <div style="color:{text_col}; font-size:0.7rem; font-weight:700;">{icon} {step_name}</div>
                <div style="color:{text_col}; font-size:0.62rem; opacity:0.85;">{sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
