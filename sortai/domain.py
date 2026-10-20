from __future__ import annotations
import re
import uuid
from typing import Any

ROLES = ("collector", "recycler", "admin")
CATEGORIES: dict[str, dict[str, Any]] = {
    "pcb": {"id": "pcb", "label": "Printed circuit boards", "crate": "Crate 1", "colour": "green", "hazardous": False},
    "battery": {"id": "battery", "label": "Batteries - hazardous", "crate": "Crate 2", "colour": "red", "hazardous": True},
    "motor": {"id": "motor", "label": "Copper coils, transformers, motors", "crate": "Crate 3", "colour": "orange", "hazardous": False},
    "cable": {"id": "cable", "label": "Cables and wires", "crate": "Crate 4", "colour": "yellow", "hazardous": False},
    "display": {"id": "display", "label": "Display panels", "crate": "Crate 5", "colour": "blue", "hazardous": True},
    "plastic": {"id": "plastic", "label": "Glass and engineered plastics", "crate": "Crate 6", "colour": "purple", "hazardous": False},
    "unknown": {"id": "unknown", "label": "Unknown / Needs Review", "crate": "Review state", "colour": "grey", "hazardous": True},
}
DEMO_USERS = {
    "demo-collector": {"id": "user-collector-demo", "role": "collector", "displayName": "Demo Collector"},
    "demo-recycler": {"id": "user-recycler-demo", "role": "recycler", "displayName": "Demo Recycler"},
    "demo-admin": {"id": "user-admin-demo", "role": "admin", "displayName": "Demo Administrator"},
}

def create_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4()}"

def demo_user_from_token(token: str | None) -> dict[str, Any] | None:
    return DEMO_USERS.get(token or "")

def infer_mock(filename: str = "") -> dict[str, Any]:
    name = filename.lower()
    category = "unknown"
    patterns = (("battery", r"battery|cell|lithium|swollen"), ("pcb", r"phone|laptop|board|pcb|circuit"), ("cable", r"cable|wire|charger"), ("motor", r"motor|fan|transformer|coil"), ("display", r"display|screen|tv|monitor"), ("plastic", r"plastic|casing|glass"))
    for candidate, pattern in patterns:
        if re.search(pattern, name):
            category = candidate
            break
    confidence = 0.41 if category == "unknown" else 0.86 if category == "battery" else 0.90
    return {"category": category, "confidence": confidence, "provider": "mock", "modelVersion": "mock-v1", "inferenceMs": 3}

def apply_safety_policy(prediction: dict[str, Any]) -> dict[str, Any]:
    category = CATEGORIES.get(prediction.get("category"), CATEGORIES["unknown"])
    review_required = prediction.get("category") == "unknown" or prediction.get("confidence", 0) < 0.8 or category["hazardous"]
    if category["id"] == "battery":
        warning = "Possible battery detected. Do not dismantle, cut, crush, or mix with ordinary scrap. Follow approved battery-handling procedures and request trained review."
    elif category["id"] == "display":
        warning = "Display construction is not confirmed visually. Avoid breaking or dismantling it; request trained review for damaged or unknown displays."
    elif review_required:
        warning = "The result is uncertain. Keep the item separate from ordinary material and request human review."
    else:
        warning = "Prediction is a sorting aid, not a safety certification. Confirm the category before placing the item."
    return {**prediction, "category": category["id"], "crate": category["crate"], "colour": category["colour"], "reviewRequired": review_required, "warning": warning}

def confirmable_category(category_id: str) -> bool:
    return category_id in CATEGORIES
