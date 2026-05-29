# n24-data-saillance

> **DataSaillance — faire émerger les insights de la donnée.**
> Repo science et notebooks reproductibles pour l'analyse du trouble Non-24-Hour Sleep-Wake Disorder (N24SWD) depuis l'actigraphie consumer.

## Problem

Le trouble Non-24 (N24SWD) est documenté principalement chez l'aveugle ; les cas chez le voyant sont rares dans la littérature, peu illustrés, et systématiquement diagnostiqués via actigraphie médicale (CamNtech MotionWatch, Philips Actiwatch). Les wearables grand public (Samsung Health, Apple Watch, Fitbit) couvrent ~70% des adultes mais leur signal n'est jamais utilisé pour la chronobiologie clinique faute de méthodologie reproductible.

## Solution

Pipeline open-source et schéma d'entrée portable pour reconstruire les indicateurs NPCRA (Van Someren 1999) depuis n'importe quelle source actigraphique — Samsung Health export, Philips Actiwatch CSV, GENEActiv, CamNtech — et estimer la période circadienne libre `tau` via régression sur les phases M10 quotidiennes.

Architecture distincte du produit [Nightfall](../SamsungHealth/) (visualisation grand-public Android+Web) : `n24-data-saillance` est l'angle **data-science et publication** — notebooks Plotly, formules testées, comparaisons N=1 vs cohortes publiques (NSRR / UK Biobank / NHANES).

## Features

| Feature | Files | Commit |
|---------|-------|--------|
| Portable actigraphy schema | `src/n24sal/io/schemas.py` | — |
| Synthetic N24 fixture generator | `src/n24sal/synthetic.py` | — |
| NPCRA metrics (IS, IV, L5, M10, RA, CFI) | `src/n24sal/npcra/metrics.py` | — |
| Tau estimation (M10 phase regression) | `src/n24sal/npcra/tau.py` | — |
| Reference norms (healthy + N24 published) | `data/reference/norms.json` | — |

## Architecture

```
Nightfall export (parquet/csv)         Public cohorts (NSRR/UKB/NHANES)
        │                                      │
        ▼                                      ▼
   [ schema validation — io.schemas ]
        │
        ▼
   [ npcra.metrics ]  IS, IV, L5, M10, RA, CFI
        │
        ▼
   [ npcra.tau ]      slope on daily M10 phases → tau hours
        │
        ▼
   [ notebooks/ ]     Plotly story: actogramme drift, tau regression, NPCRA evolution
        │
        ▼
   [ dashboard/ ]     Streamlit (publication-style, data-science angle)
```

## Setup

Python ≥ 3.11. Outillage : [`uv`](https://github.com/astral-sh/uv).

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev,viz,stats]"

# Tests
pytest

# Notebooks
jupyter lab notebooks/
```

## Usage

```python
from n24sal.synthetic import generate_synthetic_actigraphy
from n24sal.npcra import interdaily_stability, intradaily_variability, l5_m10, relative_amplitude
from n24sal.npcra.tau import estimate_tau

df = generate_synthetic_actigraphy(n_days=21, tau_hours=24.7, seed=42)
activity = df["activity"].to_numpy()

print("IS:", interdaily_stability(activity, epochs_per_day=1440))
print("IV:", intradaily_variability(activity))
print("L5/M10:", l5_m10(activity, epochs_per_hour=60, epochs_per_day=1440))

tau = estimate_tau(activity, epochs_per_hour=60, epochs_per_day=1440)
print(f"Estimated tau: {tau.tau_hours:.3f}h  (R²={tau.r_squared:.2f})")
```

## Documents

- [`VISION.md`](VISION.md) — pourquoi "saillance" et le positionnement DataSaillance
- [`PROTOCOL.md`](PROTOCOL.md) — préenregistrement méthodologique style CARE
- [`BIBLIO.md`](BIBLIO.md) — bibliographie vivante
- [`HISTORY.md`](HISTORY.md) — changelog par commit
- [`NOTES.md`](NOTES.md) — known issues + backlog

## Related projects

- [Nightfall (SamsungHealth)](../SamsungHealth/) — produit Android + web pour la visualisation personnelle des données Samsung Health avec angle N24 grand-public
- [DataSaillance](../DataSaillance/) — agence / plateforme webapp, design system source
- [OpenDesign](../OpenDesign/) — méthodologie CSS partagée
