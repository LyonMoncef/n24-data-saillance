# History

## Features

| Feature | Files | Commit |
|---------|-------|--------|
| Samsung Health raw export ingest (movement + sleep + HR + CLI) | `src/n24sal/io/samsung.py`, `tests/test_samsung_ingest.py` | [`00baccb`](#2026-06-01-00baccb) |
| Pivot personal-first (defer cohort to Phase 6) | `VISION.md`, `PROTOCOL.md`, `NOTES.md` | [`54d0306`](#2026-05-29-54d0306) |
| Gitignore local Claude Code settings | `.gitignore` | [`41b123e`](#2026-05-29-41b123e) |
| NPCRA tau estimation | `src/n24sal/npcra/tau.py`, `tests/test_npcra.py` | [`64eb5a4`](#2026-05-29-64eb5a4) |
| NPCRA metrics (IS, IV, L5, M10, RA, CFI) | `src/n24sal/npcra/metrics.py`, `tests/test_npcra.py` | [`64eb5a4`](#2026-05-29-64eb5a4) |
| Synthetic N24 cosinor fixture | `src/n24sal/synthetic.py`, `tests/test_synthetic.py` | [`64eb5a4`](#2026-05-29-64eb5a4) |
| Portable actigraphy schema (Pydantic) | `src/n24sal/io/schemas.py`, `tests/test_schemas.py` | [`64eb5a4`](#2026-05-29-64eb5a4) |
| Reference norms (healthy + N24) | `data/reference/norms.json` | [`64eb5a4`](#2026-05-29-64eb5a4) |
| Project structure + pyproject (uv) | `pyproject.toml`, `src/n24sal/`, `data/`, `tests/`, `notebooks/`, `dashboard/` | [`56663c5`](#2026-05-29-56663c5) |
| Root docs (vision, protocol CARE, biblio) | `README.md`, `VISION.md`, `PROTOCOL.md`, `BIBLIO.md`, `NOTES.md` | [`56663c5`](#2026-05-29-56663c5) |
| Repo bootstrap (gitignore) | `.gitignore` | [`b0876e3`](#2026-05-29-b0876e3) |

---

## Changelog

### 2026-06-01 `00baccb`
feat(io): Samsung Health raw export ingest (movement + sleep + HR + CLI)
- `src/n24sal/io/samsung.py` — parser de l'export Samsung Health Android (CSV `com.samsung.health.movement.*.csv` + JSONs `jsons/com.samsung.health.movement/<first-char>/<uuid>.binning_data.json` au 1-min, équivalent fonctionnel des activity counts Actiwatch)
- `read_movement(export_dir)` → DataFrame UTC tz-aware (timestamp + activity ≥ 0), déduplique sur timestamp, gère JSONs manquants gracefully
- `read_sleep_stage(export_dir)` → intervalles sommeil avec stage_name (awake/light/deep/rem) ; gestion `time_offset` UTC±HHMM → UTC absolu
- `read_heart_rate(export_dir)` → samples HR event-based, UTC tz-aware
- `coverage_report(activity, epoch_seconds)` → date range, % coverage, count + longest gap
- `ingest_samsung_export(export_dir, subject_id, output_dir, ...)` → pipeline complet : valide via `validate_actigraphy_frame`, écrit `activity.parquet` + `sleep_intervals.parquet` + `heart_rate.parquet` + `subject_metadata.json` (Pydantic) + `coverage_report.json`
- CLI : `python -m n24sal.io.samsung ingest <export_dir> --subject-id S001 --output data/personal/S001/ [--timezone Europe/Paris] [--age 38] [--sex M] [--diagnosis N24SWD] [--no-sleep] [--no-heart-rate]`
- `tests/test_samsung_ingest.py` — 20 tests GREEN avec fixture synthétique mini-export (BOM CSV + JSONs binning sharded par premier char UUID, mirror du layout réel découvert 2026-05-29) ; couvre helpers offset parsing, parsers movement/sleep/HR, déduplication, gaps coverage, pipeline complet, CLI
- Suite complète : 53 tests passed in 2.82s (33 NPCRA + 20 Samsung)

### 2026-05-29 `54d0306`
docs: pivot to personal-first roadmap (defer cohort work to Phase 6)
- `VISION.md` phases refactorées : Phase 1 = Samsung Health raw ingest (issue #2), Phase 2 = NPCRA notebooks sur données perso avec normes littérature (issue #3), Phase 6 = cohorte publique différée (stretch goal)
- `VISION.md` "Pas un re-parser Samsung Health" précisé : on consomme le raw export (CSV `movement` + JSONs `binning_data` 1-min) plutôt que via l'API Nightfall qui agrège en hourly
- `VISION.md` Questions ouvertes : ajout du dilemme timing CITI Independent Learner (~$165)
- `PROTOCOL.md` Sources de données : MESA Sleep et NHANES marqués "Différées"
- `PROTOCOL.md` Limitation #7 ajoutée : pas de cohorte healthy re-dérivée pour le case report initial, comparaison restreinte aux normes publiées 1990-2010
- `NOTES.md` backlog : 6 phases réordonnées, Phase 6 (cohorte) déplacée en fin et marquée stretch goal avec options A (NHANES open access 16 GB) et B (MESA via cosignataire académique)
- `NOTES.md` decision log : ajout entrée "Pivot personal-first" avec raisons (CITI/IRB blockers, infrastructure NHANES, suffisance des normes publiées pour case report défensible)
- Aucun changement de code — pytest 33/33 inchangé

### 2026-05-29 `41b123e`
chore: gitignore local Claude Code settings
- Ajout `.claude/settings.local.json` au `.gitignore` (settings personnels par machine, non partagés)

### 2026-05-29 `64eb5a4`
feat: NPCRA pipeline (schema, synthetic cosinor, metrics IS/IV/L5/M10/RA/CFI, tau, tests)
- Schéma portable `n24sal.io.schemas` — `SubjectMetadata` (Pydantic) + `validate_actigraphy_frame` indépendant de la source (Samsung / Actiwatch / GENEActiv / CamNtech)
- Générateur de fixture synthétique `n24sal.synthetic.generate_synthetic_actigraphy` — cosinor free-running paramétré par `tau_hours`, tz-aware, reproductible
- Implémentation NPCRA `n24sal.npcra.metrics` — `interdaily_stability`, `intradaily_variability`, `l5_m10`, `relative_amplitude`, `circadian_function_index` (formules Van Someren 1999 et Ortiz-Tudela 2010)
- Estimation tau `n24sal.npcra.tau` — `m10_phases_per_day` + `estimate_tau` via régression linéaire sur phases M10 unwrapped, retourne intervalle de confiance via `linregress`
- `data/reference/norms.json` — normes publiées healthy / N24 (Van Someren, Witting, Ortiz-Tudela, Sack, Hayakawa)
- 33 tests unitaires GREEN — `pytest -q` en 1.4s
- Tests couvrent : NaN propagation, signaux constants, comparaison N24 vs entrained, récupération de tau à ±0.2h pour synthétique tau=24.7 et tau=25.2

### 2026-05-29 `56663c5`
chore: scaffold docs (vision, protocol, biblio) and project structure
- `README.md` — landing DataSaillance avec problème/solution/architecture/setup, lien vers Nightfall
- `VISION.md` — angle "saillance" + triple objectif (publi / portfolio / vulgarisation) + phases de dev
- `PROTOCOL.md` — préenregistrement style CARE checklist, hypothèses H1-H4 figées, limites assumées (N=1, pas DLMO, raw CamNtech indisponible)
- `BIBLIO.md` — biblio living taggée (NPCRA, N24, wearable-validation, dataset-public, stats)
- `NOTES.md` — backlog 6 phases + décisions d'architecture du 2026-05-29 (split Nightfall/n24-data-saillance, schéma portable)
- `pyproject.toml` — package `n24sal` 0.0.1 uv-compatible, extras `viz`/`stats`/`dashboard`/`oracle`/`ml`/`dev`
- Structure dossiers — `src/n24sal/{io,npcra,sleep,viz,models}/`, `data/{schemas,reference,synthetic,public,personal}/`, `notebooks/`, `dashboard/`, `tests/`, `docs/figures/` (gitkeep partout où vide)

### 2026-05-29 `b0876e3`
chore: bootstrap repo with gitignore
- Initialisation du repo `n24-data-saillance` (greenfield, branche `main`)
- `.gitignore` Python + venv + dossiers de données personnelles/publiques (ignorés par défaut, `.gitkeep` exposé)
- Premier commit minimal avant scaffold complet sur branche `chore/scaffold-init`
