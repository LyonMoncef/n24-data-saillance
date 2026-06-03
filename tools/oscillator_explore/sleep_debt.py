#!/usr/bin/env python3
"""Sleep-duration statistics + debt accumulator D(n).

Step 1 of the sleep-debt study (see REPORT.md "Pistes / dette de sommeil") :
characterize the distribution of nightly sleep duration per regime to identify
T★ (the user's "ideal" duration). T★ is the anchor against which the daily
debt D(n) accumulates.

Hypothesis : in free-run, D(n) ≈ 0 (the body sleeps as long as it needs). In
constrained regimes, D(n) grows during weekdays and is partially repaid on
weekends — a brutal step-shaped pattern that pure sinusoids miss.

Two metrics are reported :
- ``main_duration_h`` : longest session of the night only.
- ``tst_h``           : total sleep time = main + naps. Likely better for
  debt accounting (naps are debt repayment).

Outputs (under ``data/personal/<subject>/oscillator_explore/``) :
- ``sleep_duration.json``  : per-window stats (median/mean/std/IQR/n).
- ``sleep_duration.html``  : overlaid distributions (KDE-ish histograms).

Usage::

    .venv/bin/python tools/oscillator_explore/sleep_debt.py \\
        --subject-id S001 \\
        --periods "atcf=2025-04-06:2025-07-29,recent=2026-04-01:2026-05-07,winter25=2025-11-26:2025-12-26"
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

from n24sal.sleep.per_night import main_sleep_per_night  # noqa: E402

TEAL = "#0e9eb0"
AMBER = "#d37c04"
CYAN = "#3be5e7"
MAGENTA = "#c5198d"
GREY = "#888888"


def compute_debt(
    nights: pd.DataFrame,
    t_star: float,
    *,
    gamma: float = 1.0,
    floor_at_zero: bool = True,
) -> pd.DataFrame:
    """Return ``nights`` augmented with ``debt_before_h`` and ``debt_after_h``.

    Conventions :

    - ``debt_before[n]`` is D **at bedtime of night n**, before that night's
      sleep is accounted for. Pair this with phase models : ``φ(n)`` is the
      onset of night n, so it depends on the debt the body has *already
      accumulated* when it goes to bed.
    - ``debt_after[n]``  is D **the morning after** night n, post-increment.

    Two parameters control the form :

    - ``gamma`` ∈ (0, 1]   : decay multiplier per day. ``γ=1`` = strict cumul,
      ``γ<1`` = leaky integrator (Process-S flavour). Half-life = ln 2 / −ln γ.
      With γ=0.85, half-life ≈ 4.3 nights.
    - ``floor_at_zero``    : if True, clip at 0 (no "sleep credit" allowed) —
      semantically clean for strict cumul. If False, debt can go negative,
      meaning surplus rest carries forward.

    Iteration ::

        debt_before[n] = debt_after[n−1]            (or 0 for first night)
        debt_after[n]  = γ · debt_before[n] + (T★ − TST[n])
        if floor_at_zero : debt_after[n] = max(0, ·)

    Note : γ is applied **before** the new increment is added — the previous
    debt decays first by one day, then the night's deficit/surplus is added.

    Missing nights are *not* reset.
    """
    n = len(nights)
    before = np.zeros(n)
    after = np.zeros(n)
    tst = nights["tst_h"].to_numpy()
    for i in range(n):
        prev = after[i - 1] if i > 0 else 0.0
        before[i] = prev
        new = gamma * prev + (t_star - tst[i])
        if floor_at_zero:
            new = max(0.0, new)
        after[i] = new
    out = nights.copy()
    out["debt_before_h"] = before
    out["debt_after_h"] = after
    return out


@dataclass
class DurationStats:
    label: str
    start: str | None
    end: str | None
    n_nights: int
    main_median_h: float
    main_mean_h: float
    main_std_h: float
    main_iqr_low_h: float
    main_iqr_high_h: float
    tst_median_h: float
    tst_mean_h: float
    tst_std_h: float
    tst_iqr_low_h: float
    tst_iqr_high_h: float


def _stats(label: str, start: date_ | None, end: date_ | None, nights: pd.DataFrame) -> DurationStats:
    md = nights["main_duration_h"].to_numpy()
    td = nights["tst_h"].to_numpy()
    return DurationStats(
        label=label,
        start=start.isoformat() if start else None,
        end=end.isoformat() if end else None,
        n_nights=len(nights),
        main_median_h=float(np.median(md)),
        main_mean_h=float(np.mean(md)),
        main_std_h=float(np.std(md, ddof=1)) if len(md) > 1 else float("nan"),
        main_iqr_low_h=float(np.quantile(md, 0.25)),
        main_iqr_high_h=float(np.quantile(md, 0.75)),
        tst_median_h=float(np.median(td)),
        tst_mean_h=float(np.mean(td)),
        tst_std_h=float(np.std(td, ddof=1)) if len(td) > 1 else float("nan"),
        tst_iqr_low_h=float(np.quantile(td, 0.25)),
        tst_iqr_high_h=float(np.quantile(td, 0.75)),
    )


def parse_periods(spec: str) -> list[tuple[str, date_, date_]]:
    out = []
    for chunk in spec.split(","):
        label, dates = chunk.split("=")
        s, e = dates.split(":")
        out.append((label.strip(), date_.fromisoformat(s), date_.fromisoformat(e)))
    return out


def main(argv=None) -> int:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    ap = argparse.ArgumentParser()
    ap.add_argument("--subject-id", default="S001")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--timezone", default="Europe/Paris")
    ap.add_argument(
        "--periods",
        default="atcf=2025-04-06:2025-07-29,recent=2026-04-01:2026-05-07,winter25=2025-11-26:2025-12-26",
    )
    ap.add_argument(
        "--min-duration-h",
        type=float,
        default=2.0,
        help="Drop nights with main_duration_h < this (likely Samsung session-split artefacts)",
    )
    ap.add_argument(
        "--max-duration-h",
        type=float,
        default=24.0,
        help="Drop nights with main_duration_h > this. Default 24h = hard upper "
             "bound (one full day). Long crashes (16-22h) are real, not artefacts.",
    )
    ap.add_argument(
        "--gamma",
        type=float,
        default=0.85,
        help="Leaky decay for D(n) variant (default 0.85, half-life ~4.3 nights)",
    )
    args = ap.parse_args(argv)

    data_dir = args.data_dir or (ROOT / "data" / "personal" / args.subject_id)
    sleep_path = data_dir / "sleep_intervals.parquet"
    out_dir = data_dir / "oscillator_explore"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(sleep_path)
    nights = main_sleep_per_night(df, timezone=args.timezone)
    raw_n = len(nights)
    nights = nights[
        (nights["main_duration_h"] >= args.min_duration_h)
        & (nights["main_duration_h"] <= args.max_duration_h)
    ]
    print(f"Loaded {raw_n} nights, kept {len(nights)} after filtering "
          f"[{args.min_duration_h:.1f}, {args.max_duration_h:.1f}] h")

    periods = parse_periods(args.periods)
    stats_list: list[DurationStats] = []

    # Per-window
    for label, start, end in periods:
        sub = nights[(nights.index >= start) & (nights.index <= end)]
        if sub.empty:
            print(f"  [{label}] empty after filter, skipped")
            continue
        s = _stats(label, start, end, sub)
        stats_list.append(s)
        print(f"  [{label}] n={s.n_nights}  main med={s.main_median_h:.2f}h  "
              f"tst med={s.tst_median_h:.2f}h  (IQR tst {s.tst_iqr_low_h:.1f}-{s.tst_iqr_high_h:.1f})")

    # Global
    s_global = _stats("global", nights.index.min(), nights.index.max(), nights)
    stats_list.append(s_global)
    print(f"  [global] n={s_global.n_nights}  main med={s_global.main_median_h:.2f}h  "
          f"tst med={s_global.tst_median_h:.2f}h")

    # T★ candidate = free-run TST median (winter25 is the clearest free-run window)
    free_run = next((s for s in stats_list if s.label == "winter25"), None)
    constrained = next((s for s in stats_list if s.label == "atcf"), None)
    t_star = free_run.tst_median_h if free_run else s_global.tst_median_h
    deficit = (t_star - constrained.tst_median_h) if constrained else None

    out_json = {
        "subject_id": args.subject_id,
        "filter": {"min_duration_h": args.min_duration_h, "max_duration_h": args.max_duration_h},
        "stats": [asdict(s) for s in stats_list],
        "t_star_h": t_star,
        "t_star_source": "winter25_tst_median" if free_run else "global_tst_median",
        "deficit_constrained_vs_t_star_h": deficit,
    }
    (out_dir / "sleep_duration.json").write_text(json.dumps(out_json, indent=2))
    print(f"\nT★ (ideal duration) = {t_star:.2f}h  (from {out_json['t_star_source']})")
    if deficit is not None:
        print(f"Median deficit in `atcf` regime vs T★ = {deficit:+.2f}h / night")

    # Figure : KDE-ish histograms overlayed, main vs tst, with median lines
    color_for = {
        "atcf": MAGENTA,
        "recent": AMBER,
        "winter25": TEAL,
        "global": GREY,
    }
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[
            "<b>main_duration_h</b><br><sub>longest session per night</sub>",
            "<b>tst_h</b><br><sub>total sleep time incl. naps</sub>",
        ],
        horizontal_spacing=0.08,
    )
    bins = np.arange(args.min_duration_h, args.max_duration_h + 0.5, 0.5)
    for s in stats_list:
        if s.label == "global":
            sub = nights
        else:
            sub = nights[
                (nights.index >= date_.fromisoformat(s.start))
                & (nights.index <= date_.fromisoformat(s.end))
            ]
        color = color_for.get(s.label, GREY)
        opacity = 0.35 if s.label == "global" else 0.55
        fig.add_trace(
            go.Histogram(
                x=sub["main_duration_h"], xbins=dict(start=bins[0], end=bins[-1], size=0.5),
                histnorm="probability density",
                name=f"{s.label} (n={s.n_nights})",
                marker=dict(color=color), opacity=opacity, legendgroup=s.label,
            ),
            row=1, col=1,
        )
        fig.add_vline(x=s.main_median_h, line=dict(color=color, dash="dash", width=1.5), row=1, col=1)
        fig.add_trace(
            go.Histogram(
                x=sub["tst_h"], xbins=dict(start=bins[0], end=bins[-1], size=0.5),
                histnorm="probability density",
                name=f"{s.label} (n={s.n_nights})",
                marker=dict(color=color), opacity=opacity, legendgroup=s.label, showlegend=False,
            ),
            row=1, col=2,
        )
        fig.add_vline(x=s.tst_median_h, line=dict(color=color, dash="dash", width=1.5), row=1, col=2)

    # Annotate T★ on TST panel
    fig.add_vline(
        x=t_star, line=dict(color="black", width=2), row=1, col=2,
        annotation_text=f"T★ = {t_star:.2f}h", annotation_position="top",
    )

    fig.update_layout(
        barmode="overlay",
        template="plotly_white",
        title=dict(
            text=f"<b>Sleep duration distributions per regime — {args.subject_id}</b>"
                 f"<br><sub>T★ = {t_star:.2f}h (free-run TST median)"
                 + (f" · ATCF deficit = {deficit:+.2f}h/night" if deficit is not None else "")
                 + "</sub>",
            x=0.02, xanchor="left",
        ),
        width=1100, height=520,
        legend=dict(orientation="h", y=-0.18, yanchor="top", x=0.5, xanchor="center"),
        margin=dict(t=100, l=70, r=30, b=110),
    )
    for col in (1, 2):
        fig.update_xaxes(title_text="hours", row=1, col=col,
                         tickmode="array", tickvals=list(range(int(args.min_duration_h), int(args.max_duration_h) + 1)))
        fig.update_yaxes(title_text="density" if col == 1 else None, row=1, col=col)

    out_html = out_dir / "sleep_duration.html"
    fig.write_html(str(out_html), include_plotlyjs="cdn")
    print(f"Figure → {out_html}")
    print(f"Stats  → {out_dir / 'sleep_duration.json'}")

    # ------------------------------------------------------------------
    # D(n) — debt accumulator
    # ------------------------------------------------------------------
    # Two variants computed globally to compare saturation behaviour :
    #   - strict : γ=1, max(0,·)        → unbounded cumul over 2.5y
    #   - leaky  : γ<1, no floor        → bounded, allows sleep credit
    nights_strict = compute_debt(nights, t_star, gamma=1.0, floor_at_zero=True)
    nights_leaky = compute_debt(nights, t_star, gamma=args.gamma, floor_at_zero=False)

    debt_summary_global = {
        "strict": {
            "max_h": float(nights_strict["debt_after_h"].max()),
            "mean_h": float(nights_strict["debt_after_h"].mean()),
            "p90_h": float(np.quantile(nights_strict["debt_after_h"], 0.90)),
        },
        "leaky": {
            "gamma": args.gamma,
            "max_h": float(nights_leaky["debt_after_h"].max()),
            "min_h": float(nights_leaky["debt_after_h"].min()),
            "mean_h": float(nights_leaky["debt_after_h"].mean()),
            "p90_h": float(np.quantile(nights_leaky["debt_after_h"], 0.90)),
        },
    }
    s_strict = debt_summary_global["strict"]
    s_leaky = debt_summary_global["leaky"]
    print(f"\nDebt D(n) over FULL chronology (T★={t_star:.2f}h)")
    print(f"  strict (γ=1, floor=0) : max={s_strict['max_h']:.1f}h  mean={s_strict['mean_h']:.1f}h  p90={s_strict['p90_h']:.1f}h")
    print(f"  leaky  (γ={s_leaky['gamma']:.2f}, no floor) : max={s_leaky['max_h']:.1f}h  min={s_leaky['min_h']:+.1f}h  mean={s_leaky['mean_h']:+.1f}h")
    if s_strict["max_h"] > 40:
        print("  ⚠ Strict cumul exceeds physiological plausibility (>40h).")

    fig2 = make_subplots(
        rows=len(periods), cols=1,
        shared_xaxes=False,
        vertical_spacing=0.10,
        subplot_titles=[
            f"<b>{label}</b> ({start} → {end})"
            for label, start, end in periods
        ],
        specs=[[{"secondary_y": True}] for _ in periods],
    )
    per_window_debt_summary = {}
    for row, (label, start, end) in enumerate(periods, start=1):
        win = nights[(nights.index >= start) & (nights.index <= end)]
        if win.empty:
            continue
        # LOCAL debt : reset at start of window for intra-regime dynamics.
        sub_strict = compute_debt(win, t_star, gamma=1.0, floor_at_zero=True)
        sub_leaky = compute_debt(win, t_star, gamma=args.gamma, floor_at_zero=False)
        sub = sub_strict  # use strict for the bars; both overlaid on line below
        per_window_debt_summary[label] = {
            "strict": {
                "max_h": float(sub_strict["debt_after_h"].max()),
                "mean_h": float(sub_strict["debt_after_h"].mean()),
                "end_h": float(sub_strict["debt_after_h"].iloc[-1]),
            },
            "leaky": {
                "gamma": args.gamma,
                "max_h": float(sub_leaky["debt_after_h"].max()),
                "min_h": float(sub_leaky["debt_after_h"].min()),
                "mean_h": float(sub_leaky["debt_after_h"].mean()),
                "end_h": float(sub_leaky["debt_after_h"].iloc[-1]),
            },
        }
        dates = list(sub.index)
        tst_arr = sub["tst_h"].to_numpy()
        debt_arr = sub["debt_after_h"].to_numpy()
        is_weekend = np.array([d.weekday() in (5, 6) for d in dates])
        bar_colors = [MAGENTA if w else TEAL for w in is_weekend]

        fig2.add_trace(
            go.Bar(
                x=dates, y=tst_arr,
                marker=dict(color=bar_colors, opacity=0.65),
                name="TST (weekday/weekend)" if row == 1 else None,
                showlegend=(row == 1),
                hovertemplate="%{x|%a %d %b}  TST=%{y:.2f}h<extra></extra>",
            ),
            row=row, col=1, secondary_y=False,
        )
        # Horizontal T★ line
        fig2.add_hline(y=t_star, line=dict(color="black", dash="dot", width=1),
                       row=row, col=1, secondary_y=False,
                       annotation_text=f"T★ = {t_star:.2f}h" if row == 1 else None,
                       annotation_position="top left")
        debt_leaky_arr = sub_leaky["debt_after_h"].to_numpy()
        # D_strict
        fig2.add_trace(
            go.Scatter(
                x=dates, y=debt_arr, mode="lines+markers",
                line=dict(color=AMBER, width=2.5),
                marker=dict(size=5, color=AMBER),
                name="D_strict(n) (γ=1, floor=0)" if row == 1 else None,
                showlegend=(row == 1),
                hovertemplate="%{x|%a %d %b}  D_strict=%{y:.2f}h<extra></extra>",
            ),
            row=row, col=1, secondary_y=True,
        )
        # D_leaky
        fig2.add_trace(
            go.Scatter(
                x=dates, y=debt_leaky_arr, mode="lines+markers",
                line=dict(color=CYAN, width=2.5, dash="dash"),
                marker=dict(size=5, color=CYAN),
                name=f"D_leaky(n) (γ={args.gamma:.2f})" if row == 1 else None,
                showlegend=(row == 1),
                hovertemplate="%{x|%a %d %b}  D_leaky=%{y:+.2f}h<extra></extra>",
            ),
            row=row, col=1, secondary_y=True,
        )
        # Zero line on secondary axis (helps read D_leaky going negative)
        fig2.add_hline(y=0, line=dict(color="gray", width=0.7, dash="dot"),
                       row=row, col=1, secondary_y=True)
        fig2.update_yaxes(title_text="TST (h)", row=row, col=1, secondary_y=False,
                          rangemode="tozero")
        fig2.update_yaxes(title_text="D(n) cumul (h)", row=row, col=1, secondary_y=True,
                          rangemode="tozero", color=AMBER)

    fig2.update_layout(
        template="plotly_white",
        title=dict(
            text=f"<b>Sleep debt D(n) per regime — {args.subject_id}</b>"
                 f"<br><sub>T★ = {t_star:.2f}h  ·  strict D = max(0, D[n-1] + (T★ − TST[n]))  ·  "
                 f"leaky D = γ·D[n-1] + (T★ − TST[n]) with γ={args.gamma:.2f}  ·  "
                 f"<b>reset to 0 at the start of each window</b></sub>",
            x=0.02, xanchor="left",
        ),
        width=1200, height=320 * len(periods) + 120,
        legend=dict(orientation="h", y=-0.05, yanchor="top", x=0.5, xanchor="center"),
        margin=dict(t=120, l=70, r=70, b=80),
        barmode="overlay",
    )

    out_debt_html = out_dir / "sleep_debt.html"
    fig2.write_html(str(out_debt_html), include_plotlyjs="cdn")
    print(f"Figure → {out_debt_html}")

    # Update JSON with debt summary
    out_json["debt"] = {
        "global_strict_max0": debt_summary_global,
        "per_window_local_reset": per_window_debt_summary,
    }
    (out_dir / "sleep_duration.json").write_text(json.dumps(out_json, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
