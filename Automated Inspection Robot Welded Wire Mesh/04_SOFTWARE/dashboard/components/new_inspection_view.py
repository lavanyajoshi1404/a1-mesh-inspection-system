"""Acquisition workstation: source image, profile, run inspection."""
import cv2
import numpy as np
import streamlit as st

from config.settings import DATA_INPUT_DIR
from core.mesh_spacing import STANDARD_PROFILES
from dashboard.components.workstation import (
    render_page_header,
    render_section_title,
    render_status_bar,
)
from dashboard.utils.camera import CameraError, capture_frame_from_network, capture_frame_from_webcam
from dashboard.utils.nav_helper import navigate_to_page
from dashboard.utils.pipeline_runner import run_inspection_pipeline


def render_new_inspection_page():
    render_page_header(
        "A-1 MESH INSPECTION",
        "Automated Vision-Based Quality Inspection",
        "SYSTEM READY",
    )

    image_bgr, source_name, source_type = None, "image.jpg", "UPLOAD"
    left, right = st.columns([0.68, 0.32], gap="small")

    with right:
        with st.container(border=True):
            render_section_title("Acquisition")
            source_mode = st.radio(
                "Input source",
                ["Validation Image", "Upload Image", "USB Camera", "Network Camera"],
            )
            profile_id = st.selectbox(
                "Reference profile",
                list(STANDARD_PROFILES),
                format_func=lambda key: f"{key} — {STANDARD_PROFILES[key].name}",
            )

            if source_mode == "Validation Image":
                path = DATA_INPUT_DIR / "IMG_20260920_200712.jpg"
                if path.exists():
                    image_bgr, source_name = cv2.imread(str(path), cv2.IMREAD_COLOR), path.name
                    st.caption(source_name)
                else:
                    st.error("The standard validation image is unavailable.")
            elif source_mode == "Upload Image":
                upload = st.file_uploader("Mesh image", type=["jpg", "jpeg", "png"])
                if upload:
                    decoded = cv2.imdecode(np.frombuffer(upload.getvalue(), dtype=np.uint8), cv2.IMREAD_COLOR)
                    if decoded is None:
                        st.error("The uploaded file could not be decoded as an image.")
                    else:
                        image_bgr, source_name = decoded, upload.name
            elif source_mode == "USB Camera":
                source_type = "WEBCAM"
                index = st.number_input("Camera index", 0, 4, 0, 1)
                if st.button("Capture USB frame", use_container_width=True):
                    try:
                        image_bgr, _ = capture_frame_from_webcam(int(index))
                        source_name = f"webcam_capture_{int(index)}.jpg"
                        st.session_state["acquired_image"] = (image_bgr, source_name, source_type)
                    except CameraError as error:
                        st.error(str(error))
                cached = st.session_state.get("acquired_image")
                if cached and image_bgr is None:
                    image_bgr, source_name, source_type = cached
            else:
                source_type = "NETWORK_CAMERA"
                url = st.text_input("Camera stream URL", placeholder="rtsp:// or http:// camera URL")
                if st.button("Capture network frame", use_container_width=True):
                    try:
                        image_bgr, _ = capture_frame_from_network(url)
                        source_name = "network_capture.jpg"
                        st.session_state["acquired_image"] = (image_bgr, source_name, source_type)
                    except CameraError as error:
                        st.error(str(error))
                cached = st.session_state.get("acquired_image")
                if cached and image_bgr is None:
                    image_bgr, source_name, source_type = cached

            render_section_title("Inspection")
            if st.button("RUN INSPECTION", type="primary", use_container_width=True):
                if image_bgr is None:
                    st.error("Select, upload, or capture a valid image before running inspection.")
                else:
                    try:
                        with st.spinner("Running inspection pipeline…"):
                            st.session_state["inspection_result"] = run_inspection_pipeline(
                                image_bgr,
                                source_name,
                                source_type,
                                STANDARD_PROFILES[profile_id],
                            )
                        navigate_to_page("Inspection Result")
                    except Exception as error:
                        st.error(f"Inspection could not complete: {error}")

    with left:
        with st.container(border=True):
            render_section_title("Source image")
            if image_bgr is None:
                st.info("No source image selected. This page shows acquisition only.")
            else:
                st.markdown("<div class='workspace-image'>", unsafe_allow_html=True)
                st.image(
                    cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB),
                    caption=f"{source_name}  ·  {image_bgr.shape[1]} × {image_bgr.shape[0]} px",
                    use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

    render_status_bar(
        [
            ("State", "READY"),
            ("Image", "Loaded" if image_bgr is not None else "Not loaded"),
            ("Profile", f"{profile_id} selected"),
        ]
    )
