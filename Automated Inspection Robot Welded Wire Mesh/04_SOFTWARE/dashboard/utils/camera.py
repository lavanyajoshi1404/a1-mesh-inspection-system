"""
Camera acquisition utilities for the A1 Mesh Inspection Dashboard.

Supports:
1. Laptop / USB Webcam (live demonstration)
2. Network / Phone Camera (via IP stream URL, e.g. MJPEG/RTSP/HTTP)

Architecture Reminder:
  CAMERA = DATA ACQUISITION
  LAPTOP = PROCESSING & INSPECTION ENGINE
  DASHBOARD = OPERATOR INTERFACE
"""

import time
from typing import List, Optional, Tuple

import cv2
import numpy as np


class CameraError(Exception):
    """Raised when camera acquisition fails."""


def test_camera_index(index: int = 0) -> bool:
    """Test if a USB/laptop webcam index is accessible."""
    try:
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW) if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(index)
        if not cap.isOpened():
            cap.release()
            return False
        ret, frame = cap.read()
        cap.release()
        return bool(ret and frame is not None and frame.size > 0)
    except Exception:
        return False


def get_available_cameras(max_indices: int = 3) -> List[int]:
    """Scan and return a list of available camera device indices."""
    available = []
    for i in range(max_indices):
        if test_camera_index(i):
            available.append(i)
    return available


def capture_frame_from_webcam(device_index: int = 0) -> Tuple[np.ndarray, str]:
    """Capture a single full-resolution frame from the selected USB webcam.

    Returns:
        (image_bgr, info_string)
    """
    cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW) if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(device_index)
    if not cap.isOpened():
        raise CameraError(
            f"Cannot connect to webcam at device index {device_index}. "
            "Please check that the USB camera is plugged in and permissions are granted."
        )

    # Attempt to request higher resolution if supported by the camera hardware
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    # Let sensor auto-exposure and white balance stabilize
    time.sleep(0.2)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None or frame.size == 0:
        raise CameraError(
            f"Webcam at index {device_index} failed to capture a valid image frame."
        )

    h, w = frame.shape[:2]
    info = f"USB Webcam (index {device_index}, {w}x{h} px)"
    return frame, info


def capture_frame_from_network(stream_url: str, timeout_seconds: int = 5) -> Tuple[np.ndarray, str]:
    """Capture a frame from an IP network stream (e.g. phone camera app).

    The user's phone must run an accessible IP camera server on the same
    local Wi-Fi network (e.g. IP Webcam app, DroidCam, or any standard MJPEG/RTSP stream).

    Returns:
        (image_bgr, info_string)
    """
    clean_url = stream_url.strip()
    if not clean_url:
        raise CameraError("No network stream URL provided. Enter a valid HTTP/RTSP camera URL.")

    # Validate protocol
    if not (clean_url.startswith("http://") or clean_url.startswith("https://") or clean_url.startswith("rtsp://")):
        raise CameraError(
            f"Invalid stream URL format: '{clean_url}'. "
            "URL should start with http://, https://, or rtsp:// (e.g. http://192.168.1.50:8080/video)."
        )

    cap = cv2.VideoCapture(clean_url)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_seconds * 1000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_seconds * 1000)

    if not cap.isOpened():
        cap.release()
        raise CameraError(
            f"Could not open network stream at {clean_url}. "
            "Check that your phone camera server is running and both laptop and phone are on the same Wi-Fi network."
        )

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None or frame.size == 0:
        raise CameraError(
            f"Connected to {clean_url} but failed to decode a valid video frame."
        )

    h, w = frame.shape[:2]
    info = f"Network Camera ({clean_url}, {w}x{h} px)"
    return frame, info
