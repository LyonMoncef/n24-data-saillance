"""DataSaillance design tokens + Plotly templates.

Tokens are the canonical colour palette of the DataSaillance brand
(see ``VISION.md`` constraint C4). The two templates ``datasaillance_dark``
and ``datasaillance_light`` are registered with :mod:`plotly.io.templates`
on import. Activate one via :func:`apply_theme`.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

TEAL = "#0e9eb0"
AMBER = "#d37c04"
CYAN = "#3be5e7"

_DARK = {
    "bg": "#191e22",
    "bg_panel": "#232e32",
    "text": "#e8eff2",
    "text_muted": "#7a9aaa",
    "border": "#2e3d44",
}

_LIGHT = {
    "bg": "#ffffff",
    "bg_panel": "#f4f8fa",
    "text": "#191e22",
    "text_muted": "#81868b",
    "border": "#d0dde3",
}

DATASAILLANCE_COLORWAY = [TEAL, AMBER, CYAN, "#7a9aaa", "#a87248", "#3a90a0"]


def _make_template(theme: dict) -> go.layout.Template:
    return go.layout.Template(
        layout=dict(
            paper_bgcolor=theme["bg"],
            plot_bgcolor=theme["bg_panel"],
            font=dict(family="Inter, system-ui, sans-serif", color=theme["text"], size=13),
            colorway=DATASAILLANCE_COLORWAY,
            xaxis=dict(
                gridcolor=theme["border"],
                linecolor=theme["border"],
                title_font=dict(color=theme["text_muted"]),
                tickfont=dict(color=theme["text_muted"]),
                zeroline=False,
            ),
            yaxis=dict(
                gridcolor=theme["border"],
                linecolor=theme["border"],
                title_font=dict(color=theme["text_muted"]),
                tickfont=dict(color=theme["text_muted"]),
                zeroline=False,
            ),
            title=dict(
                font=dict(family="Playfair Display, serif", color=theme["text"], size=18),
                x=0.05,
            ),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font=dict(color=theme["text"]),
                bordercolor=theme["border"],
            ),
            margin=dict(l=60, r=30, t=60, b=50),
        )
    )


pio.templates["datasaillance_dark"] = _make_template(_DARK)
pio.templates["datasaillance_light"] = _make_template(_LIGHT)


def apply_theme(name: str = "dark") -> None:
    """Set the default Plotly template to ``datasaillance_<name>``.

    Parameters
    ----------
    name
        ``"dark"`` (default) or ``"light"``.
    """
    if name not in ("dark", "light"):
        raise ValueError(f"theme must be 'dark' or 'light', got {name!r}")
    pio.templates.default = f"datasaillance_{name}"
