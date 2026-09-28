"""
Navigation helper for programmatic page switching across the industrial dashboard.
Synchronizes both `nav_selection` and `nav_radio_widget` in session state.
"""

import streamlit as st


def navigate_to_page(page_name: str):
    """Programmatically transition to target page and sync sidebar radio widget."""
    st.session_state["nav_selection"] = page_name
    # The sidebar radio has already been instantiated in this run.  Streamlit
    # forbids changing that widget key until the next rerun; app.render_sidebar
    # synchronizes it safely before constructing the widget on the next pass.
    st.session_state["pending_navigation"] = page_name
    st.rerun()
