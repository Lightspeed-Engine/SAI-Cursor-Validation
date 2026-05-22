"""Shared Mermaid / UI palette for Shufti standalone diagrams."""

from __future__ import annotations

# Dark serious infrastructure (steel / navy)
OPS_BG = "#050b14"
OPS_PANEL = "#0c1829"
OPS_EDGE = "#3b82f6"
OPS_EDGE_LABEL_BG = "#1e3a5f"
OPS_EDGE_LABEL_STROKE = "#60a5fa"
OPS_SVC_FILL = "#0f2744"
OPS_SVC_STROKE = "#38bdf8"
OPS_AUTH_FILL = "#172554"
OPS_AUTH_STROKE = "#60a5fa"
OPS_BUS_FILL = "#0b1220"
OPS_BUS_STROKE = "#64748b"
OPS_NET_FILL = "#0b1220"
OPS_NET_STROKE = "#475569"
OPS_VOL_FILL = "#0c2e2a"
OPS_VOL_STROKE = "#2dd4bf"

# Bright agent / model families (high contrast on dark bg)
FAMILY_STYLES: dict[str, tuple[str, str, str]] = {
    "anthropic": ("#fb923c", "#7c2d12", "#fff7ed"),
    "claude": ("#fb923c", "#7c2d12", "#fff7ed"),
    "openai": ("#4ade80", "#14532d", "#ecfdf5"),
    "gpt": ("#4ade80", "#14532d", "#ecfdf5"),
    "google": ("#60a5fa", "#1e3a8a", "#eff6ff"),
    "gemini": ("#60a5fa", "#1e3a8a", "#eff6ff"),
    "cursor": ("#22d3ee", "#164e63", "#ecfeff"),
    "deepseek": ("#a78bfa", "#4c1d95", "#f5f3ff"),
    "local": ("#facc15", "#713f12", "#fefce8"),
    "ollama": ("#facc15", "#713f12", "#fefce8"),
    "unknown": ("#94a3b8", "#334155", "#f8fafc"),
}

# Token heat quintiles (cold → hot)
HEAT_STYLES: list[tuple[str, str, str]] = [
    ("#0f2744", "#1e40af", "#e2e8f0"),
    ("#1e3a5f", "#2563eb", "#e2e8f0"),
    ("#1d4ed8", "#38bdf8", "#f8fafc"),
    ("#0369a1", "#0ea5e9", "#f0f9ff"),
    ("#b45309", "#f59e0b", "#fffbeb"),
]

PERF_STYLES: dict[str, tuple[str, str, str]] = {
    "green": ("#14532d", "#22c55e", "#ecfdf5"),
    "yellow": ("#713f12", "#eab308", "#fefce8"),
    "orange": ("#7c2d12", "#f97316", "#fff7ed"),
    "red": ("#7f1d1d", "#ef4444", "#fef2f2"),
}


def mermaid_init_block() -> list[str]:
    return [
        "%%{init: {",
        '  "theme": "base",',
        '  "themeVariables": {',
        '    "darkMode": true,',
        f'    "background": "{OPS_BG}",',
        f'    "primaryColor": "{OPS_SVC_FILL}",',
        '    "primaryTextColor": "#f8fafc",',
        f'    "primaryBorderColor": "{OPS_SVC_STROKE}",',
        f'    "lineColor": "{OPS_EDGE}",',
        '    "secondaryColor": "#172554",',
        '    "tertiaryColor": "#0c2e2a",',
        '    "fontFamily": "Inter,Segoe UI,sans-serif"',
        "  },",
        '  "flowchart": { "curve": "basis", "htmlLabels": true, "padding": 18, "nodeSpacing": 44, "rankSpacing": 54 }',
        "}}%%",
    ]


def infra_class_defs() -> list[str]:
    return [
        "  classDef orch fill:#1e3a5f,stroke:#60a5fa,color:#f8fafc",
        f"  classDef svc fill:{OPS_SVC_FILL},stroke:{OPS_SVC_STROKE},color:#f1f5f9",
        f"  classDef auth fill:{OPS_AUTH_FILL},stroke:{OPS_AUTH_STROKE},color:#f8fafc",
        f"  classDef bus fill:{OPS_BUS_FILL},stroke:{OPS_BUS_STROKE},color:#e2e8f0,stroke-dasharray:5 3",
        f"  classDef net fill:{OPS_NET_FILL},stroke:{OPS_NET_STROKE},color:#e2e8f0,stroke-dasharray:4 2",
        f"  classDef vol fill:{OPS_VOL_FILL},stroke:{OPS_VOL_STROKE},color:#ecfeff",
    ]


def heat_class_defs() -> list[str]:
    lines = []
    for idx, (fill, stroke, text) in enumerate(HEAT_STYLES):
        lines.append(
            f"  classDef heat{idx} fill:{fill},stroke:{stroke},color:{text}"
        )
    return lines


def family_class_defs(families: set[str]) -> list[str]:
    lines = []
    for family in sorted(families):
        fill, stroke, text = FAMILY_STYLES.get(family, FAMILY_STYLES["unknown"])
        safe = _safe_class(family)
        lines.append(f"  classDef fam_{safe} fill:{fill},stroke:{stroke},color:{text}")
    return lines


def perf_class_defs() -> list[str]:
    return [
        f"  classDef perf_{band} fill:{fill},stroke:{stroke},color:{text}"
        for band, (fill, stroke, text) in PERF_STYLES.items()
    ]


def normalize_family(raw: str | None) -> str:
    value = (raw or "unknown").lower().strip()
    for key in FAMILY_STYLES:
        if key in value:
            return key
    if "claude" in value or "anthropic" in value:
        return "anthropic"
    if "gpt" in value or "openai" in value or "o1" in value or "o3" in value:
        return "openai"
    if "gemini" in value or "google" in value:
        return "google"
    return value.split("-")[0] if value else "unknown"


def _safe_class(value: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9_]", "_", value) or "unknown"


def code_map_class_defs() -> list[str]:
    """Mermaid classDefs for Python code-map diagrams (flowchart / classDiagram)."""
    return [
        f"  classDef module fill:{OPS_SVC_FILL},stroke:{OPS_SVC_STROKE},color:#f1f5f9",
        f"  classDef pattern fill:{OPS_AUTH_FILL},stroke:{OPS_AUTH_STROKE},color:#f8fafc",
        f"  classDef symbol fill:{OPS_VOL_FILL},stroke:{OPS_VOL_STROKE},color:#ecfeff",
        "  classDef function fill:#1e3a5f,stroke:#60a5fa,color:#f8fafc",
        "  classDef method fill:#172554,stroke:#38bdf8,color:#e2e8f0",
        "  classDef classNode fill:#312e81,stroke:#a78bfa,color:#f8fafc",
    ]


def wrap_mermaid_diagram(body: str) -> str:
    """Prepend shared dark ops theme so standalone .mmd files match compose viewer."""
    stripped = body.strip()
    if stripped.startswith("%%{init"):
        return stripped + "\n"
    header = "\n".join(mermaid_init_block() + code_map_class_defs())
    return f"{header}\n{stripped}\n"
