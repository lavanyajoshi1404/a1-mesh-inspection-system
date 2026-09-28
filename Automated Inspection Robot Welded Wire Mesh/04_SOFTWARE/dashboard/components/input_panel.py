"""
Input Source Selector and Capture Panel for the A1 Mesh Inspection Dashboard.

Supports:
1. Upload Image (with real dataset image preset for fast, reliable judge demos)
2. Laptop / USB Camera (live camera demonstration option)
3. Network / Phone Camera (optional network stream URL)
"""

from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
import streamlit as st

from config.settings import DATA_INPUT_DIR
from dashboard.utils.camera import (
    CameraError,
    capture_frame_from_network,
    capture_frame_from_webcam,
    get_available_cameras,
)


def render_input_panel() -> Tuple[Optional[np.ndarray], str, str, bool]:
    """Render the input source selection card and capture controls.

    Returns:
        (image_bgr, source_name, source_type, run_clicked)
    """
    st.markdown("### 1. Image Acquisition Source")

    col_source, col_ctrl = st.columns([1, 2])

    with col_source:
        source_mode = st.radio(
            "Select Input Source",
            options=["Upload Image", "Laptop / USB Camera", "Network / Phone Camera"],
            index=0,
            label_visibility="collapsed",
        )

    image_bgr: Optional[np.ndarray] = None
    source_name = "image.jpg"
    source_type = "UPLOAD"
    run_clicked = False

    with col_ctrl:
        if source_mode == "Upload Image":
            source_type = "UPLOAD"
            upload_tabs = st.tabs(["Preset Validation Image", "Upload Custom Image"])

            with upload_tabs[0]:
                st.caption("Standard competition validation image from audited development dataset:")
                preset_image_path = DATA_INPUT_DIR / "IMG_20260920_200712.jpg"

                if preset_image_path.exists():
                    st.info(f"Loaded: **{preset_image_path.name}** (12MP, 3000x4000 px, Welded Wire Mesh)")
                    source_name = preset_image_path.name
                    # Read using OpenCV
                    image_bgr = cv2.imread(str(preset_image_path), cv2.IMREAD_UNCHANGED)
                else:
                    st.warning(f"Preset image not found at {preset_image_path}")

            with upload_tabs[1]:
                uploaded_file = st.file_uploader(
                    "Upload Welded Mesh Photo (.jpg, .jpeg)",
                    type=["jpg", "jpeg"],
                    help="Upload a single photo of a welded wire mesh panel.",
                )
                if uploaded_file is not None:
                    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                    custom_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    if custom_img is not None:
                        image_bgr = custom_img
                        source_name = uploaded_file.name
                        st.success(f"Uploaded: **{source_name}** ({custom_img.shape[1]}x{custom_img.shape[0]} px)")

        elif source_mode == "Laptop / USB Camera":
            source_type = "WEBCAM"
            st.caption("Acquire live frame from connected USB camera mounted on inspection frame:")
            c1, c2 = st.columns([1, 1])
            with c1:
                cam_idx = st.number_input("Camera Device Index", min_value=0, max_value=4, value=0, step=1)
            with c2:
                capture_btn = st.button("📷 Capture Live Frame", use_container_width=True)

            if capture_btn:
                try:
                    with st.spinner("Connecting to webcam and grabbing frame..."):
                        image_bgr, info = capture_frame_from_webcam(int(cam_idx))
                        source_name = f"webcam_capture_{int(cam_idx)}.jpg"
                        st.session_state["cached_cam_frame"] = image_bgr
                        st.session_state["cached_cam_name"] = source_name
                        st.success(f"Captured: {info}")
                except CameraError as e:
                    st.error(f"[Camera Error] {e}")

            if "cached_cam_frame" in st.session_state:
                image_bgr = st.session_state["cached_cam_frame"]
                source_name = st.session_state.get("cached_cam_name", "webcam_capture.jpg")
                st.caption(f"Active frame in memory: {source_name} ({image_bgr.shape[1]}x{image_bgr.shape[0]} px)")

        else:  # Network / Phone Camera
            source_type = "NETWORK_CAMERA"
            st.caption("Acquire live frame from phone camera stream on the same local Wi-Fi:")
            stream_url = st.text_input(
                "IP Camera Stream URL",
                value="http://192.168.1.100:8080/video",
                help="Example: http://192.168.1.X:8080/video (from any phone IP camera app)",
            )
            net_btn = st.button("🌐 Connect & Grab Frame", use_container_width=True)

            if net_btn:
                try:
                    with st.spinner(f"Connecting to network camera at {stream_url}..."):
                        image_bgr, info = capture_frame_from_network(stream_url)
                        source_name = "network_phone_capture.jpg"
                        st.session_state["cached_net_frame"] = image_bgr
                        st.session_state["cached_net_name"] = source_name
                        st.success(f"Captured: {info}")
                except CameraError as e:
                    st.error(f"[Network Camera Error] {e}")

            if "cached_net_frame" in st.session_state:
                image_bgr = st.session_state["cached_net_frame"]
                source_name = st.session_state.get("cached_net_name", "network_phone_capture.jpg")
                st.caption(f"Active frame in memory: {source_name} ({image_bgr.shape[1]}x{image_bgr.shape[0]} px)")

    # Run inspection button bar
    btn_col1, btn_col2 = st.columns([1, 3])
    with btn_col1:
        run_clicked = st.button(
            "▶ RUN INSPECTION",
            type="primary",
            use_container_width=True,
            help="Execute the full deterministic inspection pipeline on the selected image.",
        )
    with btn_col2:
        if image_bgr is not None:
            st.markdown(
                f"<div style='padding-top:8px; font-size:0.88rem; color:#475569;'>"
                f"Selected Source: <b>{source_name}</b> | Resolution: <b>{image_bgr.shape[1]} × {image_bgr.shape[0]} px</b>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='padding-top:8px; font-size:0.88rem; color:#d97706;'>"
                "⚠️ No image loaded. Select a preset or capture a frame first.</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr style='margin: 16px 0;'/>", unsafe_allow_html=True)
    return image_bgr, source_name, source_type, run_clicked
