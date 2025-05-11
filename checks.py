from typing import Any, Dict, List, Tuple

# ────────────────────────────────────────────────────────────
# Spec constants
# ────────────────────────────────────────────────────────────

ALLOWED_OCCLUSION = {"0%", "25%", "50%", "75%", "100%"}
ALLOWED_TRUNCATION = {"0%", "25%", "50%", "75%", "100%"}
ALLOWED_BG_COLOR = {
    "white",
    "yellow",
    "red",
    "orange",
    "green",
    "blue",
    "other",
    "not_applicable",
}

ALLOWED_BG_BY_LABEL = {
    # typical MUTCD colors (exceptions may exist)
    "construction_sign": {"orange"},  # work zone
    "traffic_control_sign": {"red", "white", "yellow"},  # stop/yield/regulatory/warning
    "information_sign": {"green", "blue", "white"},  # guidance / services
    "policy_sign": {"white", "blue", "yellow"},  # parking, bike‑lane, etc.
    "non_visible_face": {"not_applicable"},  # sign back / edge
}


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────
def _iou(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    ax1, ay1 = a["left"], a["top"]
    ax2, ay2 = ax1 + a["width"], ay1 + a["height"]
    bx1, by1 = b["left"], b["top"]
    bx2, by2 = bx1 + b["width"], by1 + b["height"]
    inter_w = max(0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    union = a["width"] * a["height"] + b["width"] * b["height"] - inter
    return inter / union if union else 0.0


# ────────────────────────────────────────────────────────────
# Individual checks (return 0‑or‑more issue dicts)
# ────────────────────────────────────────────────────────────
def check_invalid_label(box: Dict[str, Any], idx: int) -> List[Dict[str, Any]]:
    lbl = box.get("label")
    if lbl not in ALLOWED_BG_BY_LABEL.keys():
        return [
            dict(severity="error", box_id=idx, check="invalid_label", details=str(lbl))
        ]
    return []


def check_missing_attribute(box: Dict[str, Any], idx: int) -> List[Dict[str, Any]]:
    attrs = box.get("attributes", {})
    missing = [
        k for k in ("occlusion", "truncation", "background_color") if k not in attrs
    ]
    if missing:
        return [
            dict(
                severity="error",
                box_id=idx,
                check="missing_attribute",
                details=",".join(missing),
            )
        ]
    return []


def check_invalid_attr_value(box: Dict[str, Any], idx: int) -> List[Dict[str, Any]]:
    issues = []
    occ = box["attributes"].get("occlusion")
    if occ not in ALLOWED_OCCLUSION:
        issues.append(
            dict(
                severity="error",
                box_id=idx,
                check="invalid_occlusion",
                details=str(occ),
            )
        )
    trunc = box["attributes"].get("truncation")
    if trunc not in ALLOWED_TRUNCATION:
        issues.append(
            dict(
                severity="error",
                box_id=idx,
                check="invalid_truncation",
                details=str(trunc),
            )
        )
    bg = box["attributes"].get("background_color")
    if bg not in ALLOWED_BG_COLOR:
        issues.append(
            dict(
                severity="error",
                box_id=idx,
                check="invalid_background_color",
                details=str(bg),
            )
        )
    return issues


def check_bg_color_rules(box: Dict[str, Any], idx: int) -> List[Dict[str, Any]]:
    """Spec specific background color logic."""
    lbl = box["label"]
    bg = box["attributes"].get("background_color")
    allowed = ALLOWED_BG_BY_LABEL.get(lbl)
    # non_visible_face -> bg must be not_applicable
    if lbl == "non_visible_face" and bg != "not_applicable":
        return [
            dict(
                severity="error",
                box_id=idx,
                check="bg_color_mismatch",
                details="non_visible_face must have background_color = not_applicable",
            )
        ]
    # construction_signs are generally orange
    if lbl == "construction_sign" and bg != "orange":
        return [
            dict(
                severity="warning",
                box_id=idx,
                check="bg_color_mismatch",
                details="construction_sign usually orange",
            )
        ]
    if bg not in allowed:
        return [
            dict(
                severity="warning",
                box_id=idx,
                check="bg_color_mismatch",
                details=f"{lbl} usually one of {sorted(allowed)}, got {bg}",
            )
        ]
    return []


def check_size(
    box: Dict[str, Any], img_w: int | None, img_h: int | None, idx: int
) -> List[Dict[str, Any]]:
    out = []
    if box["width"] < 4 or box["height"] < 4:
        out.append(
            dict(
                severity="warning",
                box_id=idx,
                check="tiny_box",
                details=f'{box["width"]}x{box["height"]} px',
            )
        )
    if img_w and img_h:
        if (box["width"] * box["height"]) / (img_w * img_h) > 0.80:
            out.append(
                dict(
                    severity="error",
                    box_id=idx,
                    check="oversized_box",
                    details="covers >80 percent of image",
                )
            )
    return out


def check_duplicates(boxes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    issues = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if (
                boxes[i]["label"] == boxes[j]["label"]
                and _iou(boxes[i], boxes[j]) > 0.9
            ):
                issues.append(
                    dict(
                        severity="warning",
                        box_id_1=i,
                        box_id_2=j,
                        check="duplicate_box",
                        details="IoU > 0.9",
                    )
                )
    return issues


# ────────────────────────────────────────────────────────────
# Entrypoint: run all checks on a task
# ────────────────────────────────────────────────────────────
def _img_dims(task: Dict[str, Any]) -> Tuple[int | None, int | None]:
    meta = task.get("params", {}).get("attachment_metadata", {})
    return meta.get("width"), meta.get("height")


def run_checks_on_task(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    boxes = task["response"]["annotations"]
    img_w, img_h = _img_dims(task)

    issues: List[Dict[str, Any]] = []
    for idx, b in enumerate(boxes):
        issues += check_invalid_label(b, idx)
        issues += check_missing_attribute(b, idx)
        # if required attrs missing, skip further attr‑dependent checks for this box
        if any(i["check"] == "missing_attribute" for i in issues if i["box_id"] == idx):
            continue
        issues += check_invalid_attr_value(b, idx)
        issues += check_bg_color_rules(b, idx)
        issues += check_size(b, img_w, img_h, idx)

    issues += check_duplicates(boxes)
    return issues
