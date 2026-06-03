#!/usr/bin/env python3
"""(γ, T★) sweep on the joint phase+TST model — minimise residual std.

For each (γ, T★) cell we recompute the leaky debt D(n), refit (E + T2),
and record the residual std of φ (model E) and TST (model T2). We also
record R² and AIC/BIC. The output is a heatmap per window and a
per-window optimum.

This is a **post-hoc identifiability check** : (γ, T★) were chosen by
hand (0.85, 8.99h). Sweeping shows whether the residual variance has a
sharp minimum somewhere else, or whether the surface is flat (= γ/T★
are not well-identified at our sample size).

Usage::

    .venv/bin/python tools/oscillator_explore/joint_sweep.py \\
        --subject-id S001 \\
        --periods "atcf=2025-04-06:2025-07-29,recent=2026-04-01:2026-05-07,winter25=2025-11-26:2025-12-26" \\
        --gamma-grid "0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90,0.95,1.00" \\
        --t-star-grid "7.00,7.25,7.50,7.75,8.00,8.25,8.50,8.75,9.00,9.25,9.50,9.75,10.00"
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date as date_
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fit import parse_periods  # noqa: E402
from joint_model import fit_joint_window  # noqa: E402

TEAL = "#0e9eb0"
AMBER = "#d37c04"
MAGENTA = "#c5198d"
DARK = "#2a2a2a"


@dataclass
class SweepCell:
    period_label: str
    gamma: float
    t_star_h: float
    n_used: int
    # phase model E
    r2_phase_E: float
    std_phi_E_h: float
    rss_phi_E: float
    aic_phase_E: float
    bic_phase_E: float
    kappa: float
    tau_h: float
    P_days: float
    A_h: float
    # TST model T2
    r2_T2: float
    std_tst_T2_h: float
    rss_T2: float
    aic_T2: float
    bic_T2: float
    beta_T2: float
    lambda_T2: float
    mu_T2: float
    best_tst_aic: str


def _std_from_r2(r2: float, y: np.ndarray) -> float:
    """std of residuals = sqrt((1 - R²) · var(y))."""
    if not np.isfinite(r2):
        return float("nan")
    s = float(np.std(y, ddof=0))
    inside = max(0.0, 1.0 - r2)
    return s * float(np.sqrt(inside))


def sweep_window(
    sleep_path: Path, timezone: str, label: str, start: date_, end: date_,
    gamma_grid: list[float], t_star_grid: list[float],
) -> list[SweepCell]:
    cells: list[SweepCell] = []
    # baseline std of phi and tst (independent of γ, T★) needed to convert R² → std
    # — we get it by computing it once via load_phase_series at any (γ, T★)
    for gamma in gamma_grid:
        for t_star in t_star_grid:
            fit, series = fit_joint_window(
                sleep_path, timezone, label, start, end,
                t_star_h=t_star, gamma_debt=gamma,
            )
            if series is None or series.empty or "tst_h" not in series.columns:
                cells.append(SweepCell(
                    period_label=label, gamma=gamma, t_star_h=t_star, n_used=0,
                    r2_phase_E=float("nan"), std_phi_E_h=float("nan"),
                    rss_phi_E=float("nan"), aic_phase_E=float("nan"),
                    bic_phase_E=float("nan"), kappa=float("nan"),
                    tau_h=float("nan"), P_days=float("nan"), A_h=float("nan"),
                    r2_T2=float("nan"), std_tst_T2_h=float("nan"),
                    rss_T2=float("nan"), aic_T2=float("nan"), bic_T2=float("nan"),
                    beta_T2=float("nan"), lambda_T2=float("nan"),
                    mu_T2=float("nan"), best_tst_aic="?",
                ))
                continue

            n = len(series)
            phi = series["phi_h"].to_numpy()
            tst = series["tst_h"].to_numpy()
            std_phi = _std_from_r2(fit.r2_phase_E, phi)
            std_tst = _std_from_r2(fit.r2_T2, tst)
            rss_phi = float(n * std_phi ** 2) if np.isfinite(std_phi) else float("nan")
            rss_tst = float(n * std_tst ** 2) if np.isfinite(std_tst) else float("nan")

            cells.append(SweepCell(
                period_label=label, gamma=gamma, t_star_h=t_star, n_used=n,
                r2_phase_E=fit.r2_phase_E, std_phi_E_h=std_phi,
                rss_phi_E=rss_phi, aic_phase_E=fit.aic_phase_E,
                bic_phase_E=fit.bic_phase_E, kappa=fit.kappa_debt,
                tau_h=fit.tau_debt_h, P_days=fit.period_debt_days,
                A_h=fit.amplitude_debt_h,
                r2_T2=fit.r2_T2, std_tst_T2_h=std_tst,
                rss_T2=rss_tst, aic_T2=fit.aic_T2, bic_T2=fit.bic_T2,
                beta_T2=fit.beta_T2_h, lambda_T2=fit.lambda_T2,
                mu_T2=fit.mu_T2_h, best_tst_aic=fit.best_tst_aic,
            ))
    return cells


def _grid_matrix(cells: list[SweepCell], field: str,
                 gamma_grid: list[float], t_star_grid: list[float]) -> np.ndarray:
    """Build a 2-D matrix indexed by (γ row, T★ col) from the sweep cells."""
    Z = np.full((len(gamma_grid), len(t_star_grid)), float("nan"))
    by_key = {(round(c.gamma, 4), round(c.t_star_h, 4)): c for c in cells}
    for i, g in enumerate(gamma_grid):
        for j, t in enumerate(t_star_grid):
            c = by_key.get((round(g, 4), round(t, 4)))
            if c is not None:
                Z[i, j] = getattr(c, field)
    return Z


def plot_heatmap(
    label: str, cells: list[SweepCell],
    gamma_grid: list[float], t_star_grid: list[float],
    baseline: tuple[float, float] | None,
    out_path: Path,
) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    Z_phi = _grid_matrix(cells, "std_phi_E_h", gamma_grid, t_star_grid)
    Z_tst = _grid_matrix(cells, "std_tst_T2_h", gamma_grid, t_star_grid)
    Z_aic_phi = _grid_matrix(cells, "aic_phase_E", gamma_grid, t_star_grid)
    Z_aic_tst = _grid_matrix(cells, "aic_T2", gamma_grid, t_star_grid)

    # Find optima
    def _argmin(Z):
        if not np.isfinite(Z).any():
            return None
        i, j = np.unravel_index(np.nanargmin(Z), Z.shape)
        return float(gamma_grid[i]), float(t_star_grid[j]), float(Z[i, j])

    opt_phi = _argmin(Z_phi)
    opt_tst = _argmin(Z_tst)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            f"<b>std(φ − model E)</b>  [h]"
            + (f"  ·  min = {opt_phi[2]:.3f}h @ γ={opt_phi[0]:.2f} T★={opt_phi[1]:.2f}" if opt_phi else ""),
            f"<b>std(TST − T2)</b>  [h]"
            + (f"  ·  min = {opt_tst[2]:.3f}h @ γ={opt_tst[0]:.2f} T★={opt_tst[1]:.2f}" if opt_tst else ""),
        ),
        horizontal_spacing=0.12,
    )

    fig.add_trace(
        go.Heatmap(
            z=Z_phi, x=t_star_grid, y=gamma_grid,
            colorscale="Viridis", reversescale=True,
            colorbar=dict(title="std φ (h)", x=0.46, len=0.85),
            hovertemplate="γ=%{y:.2f}  T★=%{x:.2f}h  std=%{z:.3f}h<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Heatmap(
            z=Z_tst, x=t_star_grid, y=gamma_grid,
            colorscale="Cividis", reversescale=True,
            colorbar=dict(title="std TST (h)", x=1.02, len=0.85),
            hovertemplate="γ=%{y:.2f}  T★=%{x:.2f}h  std=%{z:.3f}h<extra></extra>",
        ),
        row=1, col=2,
    )

    # Mark baseline (γ=0.85, T★=8.99 in the standard pipeline)
    if baseline is not None:
        g0, t0 = baseline
        for col in (1, 2):
            fig.add_trace(
                go.Scatter(x=[t0], y=[g0], mode="markers",
                           marker=dict(symbol="x", size=14, color="white",
                                       line=dict(color="black", width=2)),
                           showlegend=False,
                           hovertemplate=f"baseline γ={g0:.2f} T★={t0:.2f}h<extra></extra>"),
                row=1, col=col,
            )
    # Mark optima
    if opt_phi is not None:
        fig.add_trace(
            go.Scatter(x=[opt_phi[1]], y=[opt_phi[0]], mode="markers",
                       marker=dict(symbol="star", size=16, color=AMBER,
                                   line=dict(color="black", width=1)),
                       showlegend=False,
                       hovertemplate=f"phase optimum<extra></extra>"),
            row=1, col=1,
        )
    if opt_tst is not None:
        fig.add_trace(
            go.Scatter(x=[opt_tst[1]], y=[opt_tst[0]], mode="markers",
                       marker=dict(symbol="star", size=16, color=AMBER,
                                   line=dict(color="black", width=1)),
                       showlegend=False,
                       hovertemplate=f"TST optimum<extra></extra>"),
            row=1, col=2,
        )

    fig.update_xaxes(title_text="T★  (h)", row=1, col=1)
    fig.update_yaxes(title_text="γ  (leak)", row=1, col=1)
    fig.update_xaxes(title_text="T★  (h)", row=1, col=2)
    fig.update_yaxes(title_text="γ  (leak)", row=1, col=2)

    fig.update_layout(
        title=dict(text=f"<b>(γ, T★) sweep — {label}</b><br>"
                        f"<sub>baseline = ✕ (γ=0.85, T★=8.99h)  ·  optimum = ★</sub>",
                   x=0.02, xanchor="left"),
        template="plotly_white",
        width=1200, height=560,
        margin=dict(t=110, l=70, r=80, b=80),
    )
    fig.write_html(str(out_path), include_plotlyjs="cdn")


# ============================================================================
# CLI
# ============================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject-id", default="S001")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--timezone", default="Europe/Paris")
    ap.add_argument("--periods", required=True,
                    help='"label1=YYYY-MM-DD:YYYY-MM-DD,label2=..."')
    ap.add_argument("--gamma-grid", default="0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90,0.95,1.00")
    ap.add_argument("--t-star-grid", default="7.00,7.25,7.50,7.75,8.00,8.25,8.50,8.75,9.00,9.25,9.50,9.75,10.00")
    ap.add_argument("--baseline-gamma", type=float, default=0.85)
    ap.add_argument("--baseline-t-star", type=float, default=8.99)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args(argv)

    data_dir = args.data_dir or (ROOT / "data" / "personal" / args.subject_id)
    sleep_path = data_dir / "sleep_intervals.parquet"
    out_dir = args.out_dir or (data_dir / "oscillator_explore")
    out_dir.mkdir(parents=True, exist_ok=True)

    gamma_grid = [float(s) for s in args.gamma_grid.split(",")]
    t_star_grid = [float(s) for s in args.t_star_grid.split(",")]
    periods = parse_periods(args.periods)
    baseline = (args.baseline_gamma, args.baseline_t_star)

    all_cells: list[SweepCell] = []
    per_window_summary = []

    for label, start, end in periods:
        print(f"[sweep] {label}  {start} → {end}  ({len(gamma_grid)}×{len(t_star_grid)} cells)…")
        cells = sweep_window(
            sleep_path, args.timezone, label, start, end,
            gamma_grid, t_star_grid,
        )
        all_cells.extend(cells)

        # heatmap
        plot_heatmap(
            label, cells, gamma_grid, t_star_grid, baseline,
            out_dir / f"joint_sweep_{label}.html",
        )

        # baseline cell : nearest grid point to (baseline_gamma, baseline_t_star)
        # (baseline T★ = 8.99 is not exactly on the default 0.25-step grid)
        def _nearest(g, t):
            if not cells:
                return None
            return min(
                cells,
                key=lambda c: (c.gamma - g) ** 2 + ((c.t_star_h - t) / 4.0) ** 2,
            )
        base = _nearest(*baseline)
        finite_cells = [c for c in cells if np.isfinite(c.std_phi_E_h)]
        opt_phi = min(finite_cells, key=lambda c: c.std_phi_E_h) if finite_cells else None
        finite_cells_tst = [c for c in cells if np.isfinite(c.std_tst_T2_h)]
        opt_tst = min(finite_cells_tst, key=lambda c: c.std_tst_T2_h) if finite_cells_tst else None

        per_window_summary.append({
            "label": label,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "baseline_gamma": baseline[0],
            "baseline_t_star_h": baseline[1],
            "baseline_std_phi_h": base.std_phi_E_h if base else None,
            "baseline_std_tst_h": base.std_tst_T2_h if base else None,
            "baseline_r2_phi_E": base.r2_phase_E if base else None,
            "baseline_r2_T2": base.r2_T2 if base else None,
            "opt_phase_gamma": opt_phi.gamma if opt_phi else None,
            "opt_phase_t_star_h": opt_phi.t_star_h if opt_phi else None,
            "opt_phase_std_h": opt_phi.std_phi_E_h if opt_phi else None,
            "opt_phase_r2": opt_phi.r2_phase_E if opt_phi else None,
            "opt_phase_kappa": opt_phi.kappa if opt_phi else None,
            "opt_tst_gamma": opt_tst.gamma if opt_tst else None,
            "opt_tst_t_star_h": opt_tst.t_star_h if opt_tst else None,
            "opt_tst_std_h": opt_tst.std_tst_T2_h if opt_tst else None,
            "opt_tst_r2": opt_tst.r2_T2 if opt_tst else None,
            "opt_tst_lambda": opt_tst.lambda_T2 if opt_tst else None,
            "opt_tst_mu": opt_tst.mu_T2 if opt_tst else None,
        })

    # Dump all cells + summary
    (out_dir / "joint_sweep_cells.json").write_text(
        json.dumps([asdict(c) for c in all_cells], indent=2)
    )
    (out_dir / "joint_sweep_summary.json").write_text(
        json.dumps(per_window_summary, indent=2)
    )

    # Print short table
    print("\n=== Sweep summary ===")
    for s in per_window_summary:
        gain_phi = (
            (s["baseline_std_phi_h"] - s["opt_phase_std_h"]) / s["baseline_std_phi_h"] * 100
            if s["baseline_std_phi_h"] and s["opt_phase_std_h"] else float("nan")
        )
        gain_tst = (
            (s["baseline_std_tst_h"] - s["opt_tst_std_h"]) / s["baseline_std_tst_h"] * 100
            if s["baseline_std_tst_h"] and s["opt_tst_std_h"] else float("nan")
        )
        print(
            f"{s['label']:>10s}  "
            f"φ base std={s['baseline_std_phi_h']:.3f}h → "
            f"opt {s['opt_phase_std_h']:.3f}h "
            f"(γ={s['opt_phase_gamma']:.2f} T★={s['opt_phase_t_star_h']:.2f}) "
            f"gain={gain_phi:+.1f}%  ·  "
            f"TST base std={s['baseline_std_tst_h']:.3f}h → "
            f"opt {s['opt_tst_std_h']:.3f}h "
            f"(γ={s['opt_tst_gamma']:.2f} T★={s['opt_tst_t_star_h']:.2f}) "
            f"gain={gain_tst:+.1f}%"
        )
    print(f"\nHeatmaps + JSON → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
