"""Catalog of Israeli financing bodies (banks, non-bank financiers, and
insurance companies) used to populate the financing-tab dropdown.

Sourced from the Maakav project sponsor's master list (May 2026). Grouped
by ``kind`` so the UI can render an ``<optgroup>`` per group.
"""

from typing import TypedDict


class FinancingBody(TypedDict):
    key: str  # stable English-ish slug; safe for storage
    label: str  # Hebrew label for display
    kind: str  # "bank" | "non_bank" | "insurance"


FINANCING_BODIES: list[FinancingBody] = [
    # ── Banks (בנקאים) ──────────────────────────────────────
    {"key": "leumi", "label": "לאומי", "kind": "bank"},
    {"key": "hapoalim", "label": "הפועלים", "kind": "bank"},
    {"key": "discount", "label": "דיסקונט", "kind": "bank"},
    {"key": "jerusalem", "label": "ירושלים", "kind": "bank"},
    {"key": "mizrahi", "label": "מזרחי", "kind": "bank"},
    # ── Non-bank financiers (חוץ בנקאים) ────────────────────
    {"key": "tov_capital", "label": "טוב קפיטל", "kind": "non_bank"},
    {"key": "mavlul", "label": "מבלול", "kind": "non_bank"},
    {"key": "roni_capital", "label": "רוני קפיטל", "kind": "non_bank"},
    {"key": "epsom_capital", "label": "אפסום קפיטל", "kind": "non_bank"},
    {"key": "arnon_capital", "label": "ארנון קפיטל", "kind": "non_bank"},
    {"key": "credit_360", "label": "קרדיט 360", "kind": "non_bank"},
    {"key": "ardamor", "label": "ארדמייר", "kind": "non_bank"},
    {"key": "yesodot", "label": "יסודות", "kind": "non_bank"},
    {"key": "building_capital", "label": "בילדינג קפיטל", "kind": "non_bank"},
    {"key": "phoenix_capital", "label": "הפניקס", "kind": "non_bank"},
    # ── Insurance companies (חברות ביטוח) ────────────────────
    {"key": "clal", "label": "כלל", "kind": "insurance"},
    {"key": "phoenix", "label": "הפניקס", "kind": "insurance"},
    {"key": "shlomo", "label": "שלמה", "kind": "insurance"},
    {"key": "ayalon", "label": "איילון", "kind": "insurance"},
]


KIND_LABELS: dict[str, str] = {
    "bank": "בנקאים",
    "non_bank": "חוץ בנקאים",
    "insurance": "חברות ביטוח",
}


def grouped_payload() -> dict:
    """Shape for the GET /setup/financing/bodies endpoint."""
    groups: dict[str, list[FinancingBody]] = {}
    for body in FINANCING_BODIES:
        groups.setdefault(body["kind"], []).append(body)
    return {
        "groups": [
            {
                "kind": kind,
                "label": KIND_LABELS.get(kind, kind),
                "bodies": groups.get(kind, []),
            }
            for kind in ("bank", "non_bank", "insurance")
        ],
    }
