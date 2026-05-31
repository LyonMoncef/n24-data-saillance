"""DataSaillance-themed Plotly factories for NPCRA visualizations."""

from n24sal.viz.actogram import double_plot_actogram
from n24sal.viz.coverage import coverage_heatmap
from n24sal.viz.drift import m10_phase_drift_plot
from n24sal.viz.profile import average_24h_profile
from n24sal.viz.theme import (
    AMBER,
    CYAN,
    DATASAILLANCE_COLORWAY,
    TEAL,
    apply_theme,
)

__all__ = [
    "AMBER",
    "CYAN",
    "DATASAILLANCE_COLORWAY",
    "TEAL",
    "apply_theme",
    "average_24h_profile",
    "coverage_heatmap",
    "double_plot_actogram",
    "m10_phase_drift_plot",
]
