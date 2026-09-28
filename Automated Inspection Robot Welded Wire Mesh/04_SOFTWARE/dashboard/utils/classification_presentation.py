"""
Centralized Classification Presentation Mapping for the A-1 Mesh Inspection System.

Maps inspection classifications:
  1. OK
  2. SPACING DEFECT
  3. WELD DEFECT
  4. MULTIPLE DEFECTS
  5. REVIEW

Strictly evidence-based presentation contracts. Does NOT fabricate defects or alter core decisions.
"""

from typing import Dict, Any


CLASSIFICATION_PRESENTATION: Dict[str, Dict[str, Any]] = {
    "OK": {
        "label": "OK",
        "title": "✓ OK",
        "subtitle": "Inspection Passed",
        "description": "All analyzed wire regions conform to calibrated geometric and optical acceptance criteria.",
        "color": "#16a34a",
        "bg_color": "#f0fdf4",
        "border_color": "#16a34a",
        "icon": "✓",
        "class_name": "verdict-ok",
        "badge_class": "status-complete",
    },
    "SPACING DEFECT": {
        "label": "SPACING DEFECT",
        "title": "✕ SPACING DEFECT",
        "subtitle": "Configured spacing tolerance violated",
        "description": "Calibrated wire spacing violates configured product acceptance tolerance.",
        "color": "#dc2626",
        "bg_color": "#fef2f2",
        "border_color": "#dc2626",
        "icon": "✕",
        "class_name": "verdict-fail",
        "badge_class": "status-fail",
    },
    "WELD DEFECT": {
        "label": "WELD DEFECT",
        "title": "✕ WELD DEFECT",
        "subtitle": "Confirmed weld/intersection defect",
        "description": "Reliable optical evidence confirms defective or broken wire crossing joint.",
        "color": "#dc2626",
        "bg_color": "#fef2f2",
        "border_color": "#dc2626",
        "icon": "✕",
        "class_name": "verdict-fail",
        "badge_class": "status-fail",
    },
    "MULTIPLE DEFECTS": {
        "label": "MULTIPLE DEFECTS",
        "title": "✕ MULTIPLE DEFECTS",
        "subtitle": "More than one confirmed defect category",
        "description": "Multiple independent defect categories confirmed across spacing and weld regions.",
        "color": "#dc2626",
        "bg_color": "#fef2f2",
        "border_color": "#dc2626",
        "icon": "✕",
        "class_name": "verdict-fail",
        "badge_class": "status-fail",
    },
    "REVIEW": {
        "label": "REVIEW",
        "title": "⚠ REVIEW",
        "subtitle": "Human Verification Required",
        "description": "Evidence is incomplete, provisional, uncalibrated, visually anomalous, or product tolerance is not configured. Human verification is required.",
        "color": "#d97706",
        "bg_color": "#fffbeb",
        "border_color": "#d97706",
        "icon": "⚠",
        "class_name": "verdict-review",
        "badge_class": "status-processing",
    },
}


def get_classification_presentation(classification: str) -> Dict[str, Any]:
    """Retrieve UI presentation properties for an inspection classification.
    
    Defaults safely to REVIEW if classification is unknown or provisional.
    """
    cleaned = classification.strip().upper() if classification else "REVIEW"
    if cleaned in CLASSIFICATION_PRESENTATION:
        return CLASSIFICATION_PRESENTATION[cleaned]
    
    # Partial matching for defect combinations
    if "SPACING" in cleaned and "WELD" in cleaned:
        return CLASSIFICATION_PRESENTATION["MULTIPLE DEFECTS"]
    if "SPACING" in cleaned:
        return CLASSIFICATION_PRESENTATION["SPACING DEFECT"]
    if "WELD" in cleaned:
        return CLASSIFICATION_PRESENTATION["WELD DEFECT"]
    if "OK" in cleaned or "PASS" in cleaned:
        return CLASSIFICATION_PRESENTATION["OK"]
    
    return CLASSIFICATION_PRESENTATION["REVIEW"]
