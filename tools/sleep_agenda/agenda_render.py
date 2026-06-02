#!/usr/bin/env python3
"""Interactive sleep agenda HTML — Centre ChronoS Bichat-Beaujon layout, fed by
the portable n24sal parquets (``sleep_intervals.parquet`` + ``activity.parquet``),
with two visual themes (``medical`` for print, ``datasaillance`` for the brand)
and a JS drag-to-select tool that emits YAML period definitions.

Window per night : 20h (J-1) → 20h (J), local time.

Origin : ported from ``SamsungHealth/tools/sleep_agenda/agenda_render.py``
(Centre ChronoS Bichat-Beaujon style by the Nightfall project), adapted here
to consume our pipeline output instead of raw Samsung CSV.

Usage::

    python tools/sleep_agenda/agenda_render.py \\
        --subject-id S001 \\
        --theme medical \\
        --out /tmp/agenda.html
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from html import escape
from pathlib import Path
from typing import Literal

import pandas as pd

NIGHT_START_HOUR = 20
MS_PER_DAY = 24 * 3600 * 1000
ThemeKind = Literal["medical", "datasaillance"]


# ───────────────────── Data loading ─────────────────────


def load_nights_from_parquet(
    sleep_path: Path,
    activity_path: Path | None,
    timezone_name: str,
) -> list[dict]:
    """Read pipeline parquets and produce per-night dicts ready for rendering.

    Each dict :
      ``{"date": "YYYY-MM-DD",          # morning date of the night J-1 → J
         "stages": [(stage_name, start_ms, end_ms), ...],
         "coverage_pct": float}         # fraction of present epochs on the 20h-20h window
    """
    sleep = pd.read_parquet(sleep_path)
    sleep["ts_local_start"] = sleep["stage_start"].dt.tz_convert(timezone_name)
    sleep["ts_local_end"] = sleep["stage_end"].dt.tz_convert(timezone_name)

    nights: dict[str, dict] = {}
    for _, row in sleep.iterrows():
        s_local = row["ts_local_start"]
        # Assign to morning of night J-1 → J : if started ≥ 20h, the morning is next day
        morning = s_local.date()
        if s_local.hour >= NIGHT_START_HOUR:
            morning = morning + dt.timedelta(days=1)
        key = morning.isoformat()
        if key not in nights:
            nights[key] = {"date": key, "stages": [], "coverage_pct": 0.0}
        stage_name = str(row.get("stage_name", "AWAKE")).upper()
        # Convert tz-aware Timestamps to UTC ms — the renderer pins all positioning
        # against a UTC-naive baseline anchored at the night's local 20h.
        s_ms = int(s_local.tz_localize(None).timestamp() * 1000)
        e_ms = int(row["ts_local_end"].tz_localize(None).timestamp() * 1000)
        nights[key]["stages"].append((stage_name, s_ms, e_ms))

    # Coverage overlay
    if activity_path is not None and activity_path.exists():
        activity = pd.read_parquet(activity_path)
        activity["ts_local"] = activity["timestamp"].dt.tz_convert(timezone_name)
        for key in list(nights.keys()):
            morning = dt.date.fromisoformat(key)
            night_start = pd.Timestamp(
                dt.datetime.combine(morning - dt.timedelta(days=1), dt.time(NIGHT_START_HOUR)),
                tz=timezone_name,
            )
            night_end = night_start + pd.Timedelta(hours=24)
            mask = (activity["ts_local"] >= night_start) & (activity["ts_local"] < night_end)
            sub = activity[mask]
            if len(sub):
                cov = float(sub["present"].mean()) if "present" in sub.columns else 1.0
            else:
                cov = 0.0
            nights[key]["coverage_pct"] = round(cov * 100.0, 1)
    else:
        for n in nights.values():
            n["coverage_pct"] = 100.0

    return sorted(nights.values(), key=lambda n: n["date"])


# ───────────────────── Themes ─────────────────────


def theme_css(theme: ThemeKind) -> str:
    if theme == "medical":
        return _MEDICAL_CSS
    if theme == "datasaillance":
        return _DATASAILLANCE_CSS
    raise ValueError(f"unknown theme: {theme!r}")


_BASE_CSS = """
  html, body { font-family: "Inter", system-ui, sans-serif; margin: 0; }
  .wrap { max-width: 1700px; margin: 24px auto; padding: 0 16px; }
  h1 { font-size: 18px; font-weight: 700; margin: 0 0 4px; letter-spacing: -0.2px; }
  .sub { font-size: 12px; margin-bottom: 16px; }
  table.agenda { width: 100%; border-collapse: collapse; font-size: 11px; table-layout: fixed; }
  table.agenda col.col-date { width: 110px; }
  table.agenda th, table.agenda td { border: 1px solid var(--line); padding: 0; vertical-align: middle; }
  table.agenda thead th { font-weight: 600; padding: 4px 4px; }
  td.date { padding: 3px 4px; font-weight: 500; font-size: 10px; text-align: center; white-space: nowrap; user-select: none; cursor: ew-resize; position: relative; }
  td.track-cell { padding: 0; }
  thead .hour-row .hours { display: grid; grid-template-columns: repeat(25, 1fr); gap: 0; }
  thead .hour-row .hours span { border-left: 1px solid var(--line); font-weight: 500; font-size: 10px; padding: 2px 0; text-align: center; box-sizing: border-box; }
  thead .hour-row .hours span:first-child { border-left: none; }
  thead .hour-row .hours span.major { font-weight: 800; }
  .track { position: relative; height: 22px;
    background: linear-gradient(to right, var(--line) 1px, transparent 1px) 0 0 / calc(100% / 24) 100% repeat-x, var(--track-bg); }
  .track::before, .track::after { content: ""; position: absolute; top: 0; bottom: 0; width: 1px; background: var(--line-strong); }
  .track::before { left: 16.667%; }  /* midnight */
  .track::after  { left: 66.667%; }  /* noon */
  .sleep { position: absolute; top: 2px; bottom: 2px; background: var(--sleep); border-radius: 1px; }
  .arr { position: absolute; top: -2px; transform: translateX(-50%); font-size: 14px; line-height: 22px; color: var(--accent); font-weight: 900; pointer-events: none; text-shadow: 0 0 2px var(--bg); }
  .legend { margin-top: 18px; padding: 12px 14px; border: 1px solid var(--line); border-radius: 6px; font-size: 12px; }
  .legend h2 { font-size: 12px; margin: 0 0 6px; }
  .legend ul { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px 16px; }
  .legend .sym { display: inline-block; width: 18px; text-align: center; font-weight: 800; color: var(--accent); }
  .legend .box { display: inline-block; width: 18px; height: 10px; background: var(--sleep); vertical-align: middle; margin-right: 4px; }
  .legend .cov-grad { display: inline-block; width: 60px; height: 10px; background: linear-gradient(to right, var(--cov-low), var(--cov-high)); border: 1px solid var(--line); vertical-align: middle; margin: 0 4px; }
  /* Coverage indicator on date cell */
  td.date::after { content: ""; position: absolute; left: 2px; right: 2px; bottom: 1px; height: 2px; background: var(--cov-color, transparent); border-radius: 1px; }
  /* Selection feedback */
  tr.selected td { background: var(--sel-bg) !important; }
  tr.selected td.date { font-weight: 700; color: var(--accent); }
  /* Selection panel */
  #sel-panel { position: fixed; top: 12px; right: 12px; padding: 12px 14px; border: 1px solid var(--line); border-radius: 6px; background: var(--bg-panel); font-size: 12px; min-width: 220px; box-shadow: 0 2px 8px rgba(0,0,0,0.12); z-index: 100; }
  #sel-panel h3 { font-size: 12px; margin: 0 0 6px; }
  #sel-panel .row { margin: 3px 0; }
  #sel-panel .row span:first-child { color: var(--mute); margin-right: 6px; }
  #sel-panel button { padding: 5px 10px; margin-top: 8px; font-size: 11px; border: 1px solid var(--accent); background: var(--accent); color: var(--bg); cursor: pointer; border-radius: 3px; }
  #sel-panel button:hover { opacity: 0.85; }
  #sel-panel button.secondary { background: transparent; color: var(--accent); }
  /* Modal */
  #snippet-modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: none; align-items: center; justify-content: center; z-index: 200; }
  #snippet-modal.open { display: flex; }
  #snippet-modal .box { background: var(--bg-panel); padding: 18px 22px; border-radius: 6px; max-width: 560px; width: 100%; border: 1px solid var(--line); }
  #snippet-modal h3 { margin: 0 0 8px; font-size: 14px; }
  #snippet-modal pre { background: var(--bg); border: 1px solid var(--line); padding: 10px; font-size: 11px; overflow: auto; white-space: pre; }
  #snippet-modal .actions { margin-top: 10px; display: flex; gap: 8px; justify-content: flex-end; }
  @media print {
    body { font-size: 10px; }
    .wrap { max-width: none; margin: 0; padding: 8px; }
    #sel-panel, #snippet-modal { display: none !important; }
    .legend { break-inside: avoid; }
    @page { size: A3 landscape; margin: 10mm; }
  }
"""

_MEDICAL_CSS = """
:root {
  --ink: #1c1f22;
  --line: #c5cdd2;
  --line-strong: #6b7780;
  --bg: #ffffff;
  --bg-panel: #fafbfc;
  --bg-row: #fafbfc;
  --track-bg: #ffffff;
  --sleep: #f0b878;
  --accent: #0e9eb0;
  --mute: #5a646c;
  --sel-bg: #e0f4f7;
  --cov-low: #f5d4d4;
  --cov-high: #c8e6c9;
}
html, body { background: var(--bg); color: var(--ink); }
table.agenda thead th { background: #f0f3f5; }
table.agenda tbody tr:nth-child(even) td { background: var(--bg-row); }
.sub { color: var(--mute); }
.legend { background: #f7f9fa; color: var(--mute); }
.legend h2 { color: var(--ink); }
""" + _BASE_CSS

_DATASAILLANCE_CSS = """
:root {
  --ink: #e8eff2;
  --line: #2e3d44;
  --line-strong: #7a9aaa;
  --bg: #191e22;
  --bg-panel: #232e32;
  --bg-row: #1e252a;
  --track-bg: #232e32;
  --sleep: #0e9eb0;
  --accent: #d37c04;
  --mute: #7a9aaa;
  --sel-bg: rgba(211, 124, 4, 0.18);
  --cov-low: #5a3030;
  --cov-high: #2e6d3a;
}
html, body { background: var(--bg); color: var(--ink); }
table.agenda thead th { background: #2a373c; }
table.agenda tbody tr:nth-child(even) td { background: var(--bg-row); }
.sub { color: var(--mute); }
.legend { background: #1f262b; color: var(--mute); border-color: var(--line); }
.legend h2 { color: var(--ink); }
""" + _BASE_CSS


# ───────────────────── Render helpers ─────────────────────


def night_start_ms_for(date_str: str) -> int:
    """ISO 'YYYY-MM-DD' (morning of night J-1 → J) → night start in ms,
    naively pinned to UTC (consistent with the ms emitted from stages above)."""
    morning = dt.date.fromisoformat(date_str)
    night_start = dt.datetime.combine(
        morning - dt.timedelta(days=1), dt.time(NIGHT_START_HOUR)
    )
    return int(night_start.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def render_night_track(stages: list[tuple[str, int, int]], night_start_ms: int) -> str:
    night_end_ms = night_start_ms + MS_PER_DAY
    blocks: list[str] = []
    arrows: list[str] = []
    bedtime_ms: int | None = None
    waketime_ms: int | None = None
    for stype, s, e in stages:
        s_clip = max(s, night_start_ms)
        e_clip = min(e, night_end_ms)
        if e_clip <= s_clip:
            continue
        if stype != "AWAKE":
            left = 100.0 * (s_clip - night_start_ms) / MS_PER_DAY
            width = 100.0 * (e_clip - s_clip) / MS_PER_DAY
            blocks.append(
                f'<div class="sleep" style="left:{left:.3f}%;width:{width:.3f}%"></div>'
            )
            if bedtime_ms is None or s_clip < bedtime_ms:
                bedtime_ms = s_clip
            if waketime_ms is None or e_clip > waketime_ms:
                waketime_ms = e_clip
    if bedtime_ms is not None:
        pct = 100.0 * (bedtime_ms - night_start_ms) / MS_PER_DAY
        arrows.append(f'<div class="arr arr-down" style="left:{pct:.3f}%">▼</div>')
    if waketime_ms is not None:
        pct = 100.0 * (waketime_ms - night_start_ms) / MS_PER_DAY
        arrows.append(f'<div class="arr arr-up" style="left:{pct:.3f}%">▲</div>')
    return "".join(blocks + arrows)


def _coverage_color(pct: float) -> str:
    """Map coverage percentage to a CSS color via a gradient endpoint blend."""
    # Linear interpolation between cov-low (CSS var) and cov-high (CSS var)
    # using inline color-mix() for clean theming support.
    pct = max(0.0, min(100.0, pct))
    return f"color-mix(in srgb, var(--cov-high) {pct:.1f}%, var(--cov-low) {100.0 - pct:.1f}%)"


def date_label(date_str: str) -> str:
    morning = dt.date.fromisoformat(date_str)
    evening = morning - dt.timedelta(days=1)
    return f"{evening.strftime('%d/%m')} → {morning.strftime('%d/%m/%y')}"


def render_html(
    nights: list[dict],
    *,
    subject_id: str,
    timezone_name: str,
    theme: ThemeKind,
    interactive: bool,
) -> str:
    nights = sorted(nights, key=lambda n: n["date"])
    hour_labels = [(NIGHT_START_HOUR + i) % 24 for i in range(25)]
    hours_band = "".join(
        f'<span class="{"major" if h in (0, 12) else ""}">{(24 if h == 0 else h)}</span>'
        for h in hour_labels
    )

    rows: list[str] = []
    for n in nights:
        ns = night_start_ms_for(n["date"])
        track = render_night_track(n["stages"], ns)
        cov = n.get("coverage_pct", 100.0)
        cov_style = f"--cov-color:{_coverage_color(cov)};"
        rows.append(
            f'<tr data-date="{n["date"]}" data-coverage="{cov:.1f}">'
            f'<td class="date" style="{cov_style}" title="coverage {cov:.1f}%">'
            f"{escape(date_label(n['date']))}</td>"
            f'<td class="track-cell"><div class="track">{track}</div></td>'
            "</tr>"
        )
    rows_html = "".join(rows)

    if nights:
        period = f"{nights[0]['date']} → {nights[-1]['date']} ({len(nights)} nuits)"
    else:
        period = "Aucune donnée"

    panel = _SELECTION_PANEL_HTML if interactive else ""
    js = _SELECTION_JS if interactive else ""

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Agenda du sommeil — {escape(subject_id)} — {escape(period)}</title>
<style>{theme_css(theme)}</style>
</head>
<body>
<div class="wrap">
  <h1>Agenda du sommeil — sujet {escape(subject_id)} · {escape(timezone_name)}</h1>
  <div class="sub">Période : {escape(period)}. Fenêtre par nuit : 20h (J-1) → 20h (J). Thème : <b>{theme}</b>. Sélection visuelle : glisser sur la colonne date.</div>
  <table class="agenda">
    <colgroup>
      <col class="col-date">
      <col class="col-track">
    </colgroup>
    <thead>
      <tr>
        <th rowspan="2">Date (soir → matin)</th>
        <th>Heures (20h → 20h)</th>
      </tr>
      <tr class="hour-row">
        <th><div class="hours">{hours_band}</div></th>
      </tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>

  <div class="legend">
    <h2>Légende</h2>
    <ul>
      <li><span class="sym">▼</span> Mise au lit</li>
      <li><span class="box"></span> Sommeil ou sieste</li>
      <li><span class="sym">▲</span> Lever</li>
      <li>Coverage : <span class="cov-grad"></span> 0% → 100%</li>
    </ul>
  </div>
</div>
{panel}
{js}
</body>
</html>
"""


_SELECTION_PANEL_HTML = """
<div id="sel-panel">
  <h3>Sélection</h3>
  <div class="row"><span>début</span><span id="sel-start">—</span></div>
  <div class="row"><span>fin</span><span id="sel-end">—</span></div>
  <div class="row"><span>nuits</span><span id="sel-count">—</span></div>
  <div class="row"><span>coverage moy.</span><span id="sel-coverage">—</span></div>
  <button id="save-btn">Save period (YAML)</button>
  <button id="reset-btn" class="secondary">Reset</button>
</div>
<div id="snippet-modal">
  <div class="box">
    <h3>YAML snippet à coller dans <code>periods.yaml</code></h3>
    <pre></pre>
    <div class="actions">
      <button id="copy-btn">Copy</button>
      <button id="close-btn" class="secondary">Close</button>
    </div>
  </div>
</div>
"""

_SELECTION_JS = """
<script>
(function() {
  const rows = Array.from(document.querySelectorAll('table.agenda tbody tr'));
  if (!rows.length) return;
  let startIdx = null, endIdx = null, dragging = false;

  function clampSel() {
    const lo = Math.min(startIdx, endIdx);
    const hi = Math.max(startIdx, endIdx);
    rows.forEach((r, i) => r.classList.toggle('selected', i >= lo && i <= hi));
    document.getElementById('sel-start').textContent = rows[lo].dataset.date;
    document.getElementById('sel-end').textContent = rows[hi].dataset.date;
    document.getElementById('sel-count').textContent = (hi - lo + 1);
    let tot = 0, n = 0;
    for (let i = lo; i <= hi; i++) {
      const c = parseFloat(rows[i].dataset.coverage);
      if (!isNaN(c)) { tot += c; n++; }
    }
    document.getElementById('sel-coverage').textContent = n ? (tot/n).toFixed(1) + '%' : '—';
  }

  rows.forEach((row, idx) => {
    const dateCell = row.querySelector('td.date');
    dateCell.addEventListener('mousedown', (e) => {
      e.preventDefault();
      startIdx = endIdx = idx;
      dragging = true;
      clampSel();
    });
    dateCell.addEventListener('mouseover', () => {
      if (!dragging) return;
      endIdx = idx;
      clampSel();
    });
  });
  document.addEventListener('mouseup', () => { dragging = false; });

  document.getElementById('reset-btn').addEventListener('click', () => {
    rows.forEach(r => r.classList.remove('selected'));
    startIdx = endIdx = null;
    ['sel-start', 'sel-end', 'sel-count', 'sel-coverage'].forEach(id => {
      document.getElementById(id).textContent = '—';
    });
  });

  document.getElementById('save-btn').addEventListener('click', () => {
    if (startIdx === null) { alert('Sélectionne une plage en glissant sur la colonne date.'); return; }
    const lo = Math.min(startIdx, endIdx);
    const hi = Math.max(startIdx, endIdx);
    const startD = rows[lo].dataset.date;
    const endD = rows[hi].dataset.date;
    let name = prompt('Nom de la période (a-z, 0-9, underscore uniquement) :', 'regime_');
    if (!name) return;
    name = name.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    const notes = prompt('Notes (optionnel) :', '') || '';
    const yaml = `  - name: ${name}\\n    start: ${startD}\\n    end: ${endD}\\n    notes: "${notes.replace(/"/g, '\\\\"')}"`;
    document.querySelector('#snippet-modal pre').textContent = yaml;
    document.getElementById('snippet-modal').classList.add('open');
  });

  document.getElementById('copy-btn').addEventListener('click', () => {
    const txt = document.querySelector('#snippet-modal pre').textContent;
    navigator.clipboard.writeText(txt).then(
      () => { document.getElementById('copy-btn').textContent = 'Copié !'; },
      () => alert('Copy échoué — sélectionne le texte manuellement.')
    );
  });
  document.getElementById('close-btn').addEventListener('click', () => {
    document.getElementById('snippet-modal').classList.remove('open');
    document.getElementById('copy-btn').textContent = 'Copy';
  });
})();
</script>
"""


# ───────────────────── CLI ─────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--subject-id", default="S001", help="Subject identifier (default S001)")
    p.add_argument(
        "--data-dir", type=Path, default=None,
        help="Override data dir (default: data/personal/<subject_id>/)",
    )
    p.add_argument("--timezone", default="Europe/Paris", help="IANA timezone (default Europe/Paris)")
    p.add_argument(
        "--theme", choices=("medical", "datasaillance"), default="medical",
        help="Visual theme — 'medical' is print-optimized (default), 'datasaillance' is dark brand mode",
    )
    p.add_argument(
        "--out", type=Path, default=None,
        help="Output HTML path (default: data/personal/<subject_id>/agenda.html)",
    )
    p.add_argument(
        "--non-interactive", action="store_true",
        help="Drop the JS selection panel (clean print export)",
    )
    args = p.parse_args(argv)

    data_dir = args.data_dir or (Path("data/personal") / args.subject_id)
    sleep_path = data_dir / "sleep_intervals.parquet"
    activity_path = data_dir / "activity.parquet"
    if not sleep_path.exists():
        print(f"ERROR: {sleep_path} not found", file=sys.stderr)
        return 1

    nights = load_nights_from_parquet(sleep_path, activity_path, args.timezone)
    html = render_html(
        nights,
        subject_id=args.subject_id,
        timezone_name=args.timezone,
        theme=args.theme,
        interactive=not args.non_interactive,
    )
    out = args.out or (data_dir / "agenda.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"OK — {len(nights)} nuits rendues (theme={args.theme}, interactive={not args.non_interactive}) → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
