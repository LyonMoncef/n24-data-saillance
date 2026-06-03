# History

## Features

| Feature | Files | Commit |
|---------|-------|--------|
| Out-of-sample prediction test — 3 windows (D wins, MAE 4.7-6.7h, model good ~3 nights then diverges, negative bias signals exogenous events) | `tools/oscillator_explore/predict.py`, `tools/oscillator_explore/REPORT.md` | [`04a11fb`](#2026-06-03-04a11fb) |
| Sweep (γ, T★) — identifiability of hyperparams, baseline validated on ATCF (surface flat to 0.4%) | `tools/oscillator_explore/joint_sweep.py`, `tools/oscillator_explore/REPORT.md` | [`849bb95`](#2026-06-03-849bb95) |
| Joint phase+TST model — validates user's debt hypothesis on atcf (μ=+2.4h weekday/weekend) | `tools/oscillator_explore/joint_model.py`, `tools/oscillator_explore/REPORT.md` | [`39c3e79`](#2026-06-03-39c3e79) |
| Model E (φ = α·n + β + A·sin + κ·D) integrated into fit/compare/agenda + REPORT | `tools/oscillator_explore/fit.py`, `tools/oscillator_explore/compare.py`, `tools/oscillator_explore/agenda_overlay.py`, `tools/oscillator_explore/REPORT.md` | [`903dfb0`](#2026-06-03-903dfb0) |
| Leaky D(n) variant (γ=0.85) + relax max-duration cap to 24h | `tools/oscillator_explore/sleep_debt.py` | [`7633652`](#2026-06-03-7633652) |
| Sleep-debt D(n) accumulator + T★ identification per regime | `tools/oscillator_explore/sleep_debt.py` | [`2bdcfe8`](#2026-06-03-2bdcfe8) |
| EXPLAINER — oscillator model for general public (LinkedIn-ready) | `tools/oscillator_explore/EXPLAINER.md` | [`0ebd2d9`](#2026-06-03-0ebd2d9) |
| Project fitted curves onto sleep agenda (Y=date, X=hours-past-20h) | `tools/oscillator_explore/agenda_overlay.py`, `tools/oscillator_explore/REPORT.md` | [`7a350bb`](#2026-06-03-7a350bb) |
| Lomb-Scargle P-seeding + double sinusoid + AIC/BIC selection | `tools/oscillator_explore/fit.py`, `tools/oscillator_explore/compare.py`, `tools/oscillator_explore/REPORT.md` | [`9a49127`](#2026-06-03-9a49127) |
| Oscillator-on-drift phase model — exploratory fit (linear / sin / weekly / combined) on 3 regimes | `tools/oscillator_explore/fit.py`, `tools/oscillator_explore/compare.py`, `tools/oscillator_explore/REPORT.md` | [`256d918`](#2026-06-03-256d918) |
| Fix wake-aggregation bug + n24sal.sleep.main_sleep_per_night helper | `src/n24sal/sleep/per_night.py`, `tests/test_sleep_per_night.py`, `notebooks/04_regime_atcf_weekly_pattern.ipynb` | [`a0b57d3`](#2026-06-02-a0b57d3) |
| Notebook 04 — weekly pattern analysis (social entrainment leak detection) | `notebooks/04_regime_atcf_weekly_pattern.ipynb` | [`9e7d88c`](#2026-06-02-9e7d88c) |
| Interactive sleep agenda + period selection + regime side-by-side (closes #11) | `tools/sleep_agenda/agenda_render.py`, `src/n24sal/io/periods.py`, `notebooks/03_personal_case.ipynb`, `tests/test_periods.py`, `tests/test_sleep_agenda.py` | [`1572be5`](#2026-06-02-1572be5) |
| Densify Samsung ingest + present column + tau coverage filter (closes #8) | `src/n24sal/io/samsung.py`, `src/n24sal/io/schemas.py`, `src/n24sal/npcra/tau.py`, `notebooks/03_personal_case.ipynb`, `PROTOCOL.md` | [`c5245fa`](#2026-06-01-c5245fa) |
| Fix investigate_tau script (tz-aware reindex + day truncate) | `scripts/investigate_tau.py` | [`adbf89a`](#2026-06-01-adbf89a) |
| Diagnostic script for tau on real data | `scripts/investigate_tau.py` | [`ed40e87`](#2026-06-01-ed40e87) |
| Notebook 02 NPCRA basics (synthetic, executable) | `notebooks/02_npcra_basics.ipynb` | [`f7b8268`](#2026-06-01-f7b8268) |
| Notebook 03 personal case (template, no exec) | `notebooks/03_personal_case.ipynb` | [`f7b8268`](#2026-06-01-f7b8268) |
| Bootstrap tau CI via M10-phase resampling | `src/n24sal/npcra/tau.py`, `tests/test_npcra.py` | [`f7b8268`](#2026-06-01-f7b8268) |
| Viz module: actogram, drift, profile, coverage | `src/n24sal/viz/*` | [`f7b8268`](#2026-06-01-f7b8268) |
| DataSaillance Plotly theme (teal/amber/cyan) | `src/n24sal/viz/theme.py`, `tests/test_viz.py` | [`f7b8268`](#2026-06-01-f7b8268) |
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

### 2026-06-03 `04a11fb`
explore: out-of-sample prediction test — 3 windows, double sinusoid wins everywhere, MAE 4.7-6.7h, model good ~3 nights then diverges, negative bias signals exogenous events
- Première vraie validation prédictive (train/test, pas seulement R² in-sample). 3 fenêtres hors-régimes déjà étudiés, longueurs variées (30/60/90 nuits), validation sur les 10 nuits réelles suivantes.
- `tools/oscillator_explore/predict.py` — fit auto-sélection AIC parmi L, O, W, C, D (model E exclu : sa projection demande de fermer la boucle récursive D ← TST ← D). Projection forward + comparaison aux observations.
- Sortie : `prediction_<label>.html` (agenda 2-panneaux : observations fit + projection cyan dash + vraies nuits diamants ambre ; vue φ(n) à droite) + `prediction_summary.json` (paramètres, AIC, MAE, RMSE, biais, résidus per-night).
- **Résultats** :
  - **summer24** (24 nuits fit, 9 valid) : best D, R²_in=0.63, std_in=3.57h, **MAE=4.74h**, RMSE=6.23h, bias=+1.53h. Les 3 premières nuits prédites à <1h près, puis dérive massive (résidu n=5 : −13.5h !).
  - **autumn24** (56 nuits fit, 6 valid) : best D, R²_in=0.30, std_in=4.80h, **MAE=6.74h**, RMSE=9.24h, **bias=−6.74h** (énorme). Le modèle prédit trop tard, le sujet s'est couché trop tôt → événement exogène non modélisé.
  - **post-atcf** (72 nuits fit, 7 valid) : best D, R²_in=0.41, std_in=4.10h, **MAE=4.87h**, RMSE=6.47h, bias=−3.90h. Même signature que autumn24.
- **Verdict** : (a) double sinusoïde gagne partout → hypothèse user confirmée structurellement ; (b) MAE prédictif > std in-sample → modèle généralise mal ; (c) biais négatif systématique → extrapolation linéaire τ>24 trop optimiste, l'organisme est remis à l'heure régulièrement par des exogènes ; (d) portée prédictive utile ≈ **3 nuits**.
- **Implication directe** : pour étendre la portée prédictive au-delà de 3 nuits, l'enrichissement par covariables exogènes (alarmes, calendrier, lumière, activité) est nécessaire — cohérent avec la suite logique évoquée.
- REPORT.md mis à jour : nouvelle section « Validation prédictive out-of-sample » avec protocole, résultats, lectures et verdict.

### 2026-06-03 `849bb95`
explore: (γ, T★) sweep on joint model — baseline (0.85, 8.99h) validated on ATCF, surface flat to 0.4%, model has reached intrinsic floor
- Étape « passer du découvrir à l'optimiser ». Une fois le modèle E + T2 choisi (cf. `39c3e79`), on cherche à minimiser la std résiduelle en faisant varier les hyperparams `(γ, T★)` qui étaient fixés à la main à `(0.85, 8.99h)`.
- `tools/oscillator_explore/joint_sweep.py` — sweep 2D `γ ∈ {0.50..1.00 step 0.05}` × `T★ ∈ {7.00..10.00 step 0.25}` (143 cases). Pour chaque case : recalcul `D(n)`, refit (E + T2), enregistre std_φ_E, std_TST_T2, R², AIC, BIC, params. C'est un **joint NLS profilé** sur (γ, T★) avec les 9 autres params réoptimisés à chaque case.
- Sortie : heatmaps `joint_sweep_<label>.html` (2 panneaux : std_φ + std_TST, avec baseline et optima marqués) + `joint_sweep_cells.json` + `joint_sweep_summary.json`.
- **Résultats — sharpness de la surface (range_std / mean)** :
  - **atcf** (101 nuits) : **0.4%** sur φ, 4.1% sur TST → surface **plate** : (γ, T★) non identifiables séparément à cette échelle. **Baseline quasi-optimale.**
  - **recent** (37 nuits) : 39.2% sur φ → vrai pic à γ=1.00, T★=9.00h avec gain de 30%. Mais γ aux bornes + petit échantillon = artefact d'horizon limité (la dette n'a pas le temps de saturer).
  - **winter25** (29 nuits) : 7.8% sur φ, gain marginal.
- **Lecture** : (γ, T★) n'ont pas de valeur universelle stable ; l'optimum dépend de la longueur de fenêtre. Le choix pragmatique = garder `(0.85, 8.99h)` comme hyperparams biologiques fixes, validés cross-window.
- **Conclusion structurelle** : le modèle E + T2 a atteint sa **borne basse de std atteignable** sur ATCF (~4.65h sur φ, ~2.57h sur TST). Pour descendre, il faut enrichir le modèle : calendrier réel à la place de C(n) binaire lun-ven, covariables exogènes (lumière, activité), termes d'interaction (κ·D·C, λ·D²), ou state-space formel avec bruit process explicite.
- REPORT.md mis à jour : nouvelle section « Optimisation des hyperparams (γ, T★) par sweep » avec tableaux sharpness + optima vs baseline + lecture + pistes d'enrichissement.

### 2026-06-03 `0a9e65c` `39c3e79`
explore: joint phase+TST model — TST(n)=β+λ·D(n-1)-μ·C(n), validates user hypothesis on atcf (μ=2.4h weekday/weekend)
- Réponse étape finale à l'hypothèse user « la dette explose le weekend en régime contraint ». Précédemment (modèle E sur la phase seule, commit `903dfb0`) la dette n'avait pas débloqué le R² sur atcf → suspicion que le mécanisme agit sur la **durée** pas sur l'onset.
- `tools/oscillator_explore/joint_model.py` — nouvel outil qui fit en parallèle : (a) la phase via le modèle E déjà fait, (b) la durée TST via 3 variantes OLS T0/T1/T2 :
  - **T0** : `TST(n) = β_T` (constante, baseline) — 1 param
  - **T1** : `TST(n) = β_T + λ·D(n−1)` (rebound de dette seul) — 2 params
  - **T2** : `TST(n) = β_T + λ·D(n−1) − μ·C(n)` (dette + contrainte sociale) — 3 params
  où `C(n) = 1` si nuit avec alarme weekday (lun-ven matin), `0` weekend (sam-dim).
- Fits **séparés** plutôt que NLS conjoint — garde l'interprétation de chaque coefficient (λ = rebound, μ = clamp weekday) et évite les problèmes d'identifiabilité.
- AIC/BIC choisit automatiquement parmi T0/T1/T2 par fenêtre.
- **Résultats — l'hypothèse user est validée sur `atcf`** :
  - **atcf** : **T2 gagne AIC+BIC** avec R²=0.16 (vs 0.02 pour T1, 0.00 T0). **μ = +2.42h** (gigantesque) : weekend `TST ≈ 9.06 + 0.094·D`, weekday `TST ≈ 6.64 + 0.094·D`. **Effet de 2h24 d'écart weekday/weekend totalement invisible dans le modèle de phase.** λ = +0.094 modeste mais positif (rebound de dette confirmé). β_T = 9.06h proche de T★.
  - **recent** (transition) : T0 gagne, μ ≈ 0, λ ≈ 0 → fenêtre de bascule, pas de signature weekly nette (34 nuits, puissance limitée).
  - **winter25** (free-run) : T0 gagne — comme attendu en free-run sans alarme.
- Visualisation : 2 panels par fenêtre — haut = phase avec modèle E, bas = TST en barres colorées weekday/weekend avec les 3 fits T0/T1/T2 superposés et T★ horizontal en référence.
- Sortie : `joint_<label>.html` par fenêtre + `joint_summary.json` (params phase + durée).
- **Représentation correcte pour S001 en régime mixte** (résumée dans REPORT.md) :
  ```
  φ(n)    = α·n + β + A·sin(2π·n/P + ψ) + κ·D(n)
  TST(n)  = β_T + λ·D(n−1) − μ·C(n) + ε
  D(n)    = γ·D(n−1) + (T★ − TST(n))     [état partagé, leaky]
  ```
  En free-run, μ → 0 et l'équation TST se réduit à une constante ; le système se simplifie naturellement.
- 2 commits : `39c3e79` (joint_model.py), `0a9e65c` (REPORT mise à jour avec section dédiée et synthèse étendue).

### 2026-06-03 `248af2c` `35213f6` `903dfb0`
explore: model E (φ = α·n + β + A·sin(2πn/P+ψ) + κ·D(n)) — sleep-debt-as-phase-shifter
- Réponse étape 2 à l'hypothèse user « il manque la dette de sommeil ». Modèle E ajouté à `fit.py` : `φ(n) = α·n + β + A·sin(2π·n/P + ψ) + κ·D(n)` (6 params), où D = dette leaky au coucher (`debt_before_h` issu de `compute_debt` avec γ=0.85, T★=8.99h, sans plancher 0). κ unité h/h ; signe attendu : κ < 0 (plus de dette → onset plus tôt).
- D calculé sur la **chronologie complète** filtrée (durée ∈ [2, 24]h) puis sliced à la fenêtre → chaque fenêtre hérite de sa dette accumulée historique. Filtrage cohérent avec `sleep_debt.py`.
- `load_phase_series` étendu pour exposer `tst_h`, `debt_before_h`, `debt_after_h` quand `t_star_h` est passé. `FitResult` augmenté de 10 champs (t_star_h, gamma_debt, tau_debt_h, A/P/ψ_debt, kappa_debt, r2_debt, σ_debt, aic/bic_debt). `_nan_fit` mis à jour. CLI gagne `--t-star` et `--gamma-debt`.
- `compare.py` et `agenda_overlay.py` rechargent les nuits via `load_phase_series` avec T★/γ stockés dans summary.json, et superposent le modèle E (trace noir-sombre). `predict_phi` dans agenda_overlay gagne le cas "debt" : interpole D linéairement sur n_eval (cohérent physiologie : dette évolue continûment entre nuits).
- **Résultats clés** :
  - **κ négatif sur les 3 fenêtres** (−0.43, −0.22, −0.23) → sens physiologique respecté.
  - **winter25 (free-run)** : modèle E **gagne AIC ET BIC** avec R²=0.76 (vs 0.71 oscillator, 0.74 double). Surprise : on attendait κ≈0 en free-run, mais la dette y agit comme une pression homéostatique continue.
  - **recent (transition)** : R²E=0.20 << R²D=0.59. Le double sinusoïde domine ; la vague 12-jours n'est pas réductible à un terme linéaire en dette.
  - **atcf (contraint)** : R²E=0.15 < R²C=0.17. **La dette ne débloque PAS la fenêtre contrainte comme espéré.** Lecture : la dette est probablement réelle en atcf, mais elle agit sur la **durée du sommeil** (TST gonflé le weekend), pas sur l'**heure d'endormissement** (asservie à l'alarme). → motive un modèle joint phase+durée pour l'étape suivante : `TST(n) = T★ + λ·D(n−1) − μ·C(n)`.
- REPORT.md : tableau résultats avec nouvelle colonne κ + R²E, nouvelle section « Modèle E — verdict », synthèse par régime mise à jour avec colonne κ, pistes futures révisées (modèle joint, sensibilité à γ, T★ libre).
- 3 commits : `903dfb0` (fit.py), `35213f6` (compare.py + agenda_overlay.py), `248af2c` (REPORT).

### 2026-06-03 `7633652`
explore: add leaky D(n) variant (γ=0.85, no floor) + relax max-duration cap to 24h (long crashes are real)
- Feedback user : « les nuits de 22h ne sont pas des erreurs, elles existent, ne dropent pas au dessus de 16h+ ». Cap haut relevé de 16h à 24h → 784/801 nuits gardées au lieu de 767. Médianes peu changées (main 7.02→7.12, TST 8.45→8.55). Long crashes physiologiques (16-22h TST) sont des reset partiels naturels qui font BAISSER la dette strict cumulée.
- `compute_debt(nights, t_star, *, gamma=1.0, floor_at_zero=True)` étendu avec deux nouveaux paramètres : `gamma` (multiplicateur de décroissance, défaut 1.0 = strict ; ln(2)/−ln(γ) = demi-vie en nuits) et `floor_at_zero` (défaut True = plancher 0, False = crédit autorisé). Itération : `D[n] = γ·D[n-1] + (T★ − TST[n])` puis clip 0 si demandé.
- CLI `--gamma 0.85` exposé. Deux variantes computées globalement et per-window (avec reset local).
- Plot mis à jour : pour chaque fenêtre, courbe D_strict (ambre solide) + D_leaky (cyan tirets) sur axe secondaire, ligne grise pointillée à 0 pour lire les crédits leaky.
- **Constat majeur** : sur la chronologie complète 2.5 ans, leaky γ=0.85 reste **physiologiquement saine** : max=+21.7h, min=−27h (crédit après crashes), mean=+0.3h → quasi à l'équilibre. Contre 173.4h max pour la strict — confirme que γ leaky est la bonne formulation pour intégrer la dette au modèle de phase.
- JSON enrichi : `debt.global_strict_max0` + `debt.global_leaky` + `debt.per_window_local_reset.<label>.strict`/`leaky`.

### 2026-06-03 `2bdcfe8`
explore: sleep-duration stats per regime + debt D(n)=max(0, D(n-1)+(T★-TST(n)))
- Réponse à l'hypothèse utilisateur « il manque un paramètre essentiel lié à la dette de sommeil ». Étape 1 du modèle de dette : caractériser les distributions de durée pour identifier T★, puis instancier l'accumulateur D(n).
- `tools/oscillator_explore/sleep_debt.py` — nouvel outil exploratoire. Charge `main_sleep_per_night` (TST inclut les naps, indispensable pour la dette), filtre les outliers Samsung (`main_duration_h ∈ [2, 16] h` → 767/801 nuits gardées sur S001), calcule médiane/mean/std/IQR de `main_duration_h` et `tst_h` par fenêtre + global.
- **T★ identifié = 8.99h** (médiane TST en winter25 free-run), confirme l'intuition user (~8h45-9h). Médiane globale TST=8.45h → **déficit chronique de ~0.5h/nuit** moyenné sur 2.5 ans.
- Pattern de fragmentation révélé : winter25 (free-run) a `main=5.17h` mais `TST=9h` → en free-run le sommeil est très fragmenté (siestes nombreuses). ATCF (contraint) inverse : `main=5.65h`, `TST=7.45h` → moins fragmenté mais moins de sommeil total. **Conclusion : TST est la bonne métrique pour la dette, pas `main_duration_h`.**
- Déficit médian TST en `atcf` vs T★ = **+1.54h/nuit** — c'est ce qui devrait s'accumuler en dette.
- `compute_debt(nights, t_star)` ajoute `debt_before_h` (D au coucher de la nuit n, à pairer avec φ(n)) et `debt_after_h` (D au matin après la nuit), via récurrence `D[n] = max(0, D[n-1] + (T★ − TST[n]))`. Convention : pas de reset sur trous (la dette continue en réel).
- **Constat majeur** : sur la chronologie complète (2.5 ans), le cumul strict explose à D_max = **219.6h** (~9 jours de dette), mean=93h, p90=195h — non physiologique. Warning affiché : « strict max(0,·) will need γ < 1 (leaky) or a saturation cap ». Même avec reset local par fenêtre : `atcf` max=109h en 101 nuits (4.5j de dette moyenne), `recent` max=30.8h, `winter25` max=16.6h. **Confirme que γ leaky sera indispensable à l'étape suivante.**
- Sortie : `data/personal/S001/oscillator_explore/sleep_duration.html` (histogrammes overlay avec lignes médianes + repère T★) + `sleep_debt.html` (panel par fenêtre : TST en bars colorées weekday/weekend, D(n) en ligne ambre sur axe secondaire, T★ horizontal) + `sleep_duration.json` (stats + summary debt global et per-window).
- 4 tâches créées (#58-61), 3 complétées : #58 stats, #59 T★, #60 accumulator. #61 (intégration `C(n)=κ·D(n)` au modèle de phase) reste pending.

### 2026-06-03 `0ebd2d9`
docs: add EXPLAINER for the oscillator model (general-public, LinkedIn-ready)
- `tools/oscillator_explore/EXPLAINER.md` — document de vulgarisation décrivant le modèle `φ(n) = α·n + β + A·sin(2π·n/P + ψ)` en termes intelligibles pour un public non-scientifique : chaque variable décodée avec analogies (α = « dérive quotidienne en min/jour », A = « hauteur de la vague en heures », P = « durée d'un cycle en jours », β/ψ = ajustements techniques), exemple chiffré sur la fenêtre winter25 traduit en humain (« mon corps tourne sur 24h24 + micro-zigzags de ±2h48 tous les 3 jours »), explication de la projection (n, φ) → (date, heure) sur l'agenda, et exemple double-sinusoïde sur la fenêtre recent.
- Section finale « Limites du modèle actuel » qui ouvre sur la prochaine itération : (1) absence de prise en compte de la dette de sommeil — surtout en régime contraint où la bascule semaine/weekend est brutale, non-oscillante ; (2) le modèle prédit l'heure de coucher pas la durée ; (3) découpage automatique des régimes à faire.
- Base prête pour réutilisation en post LinkedIn.

### 2026-06-03 `7a350bb`
explore: project fitted curves onto sleep agenda (Y=date, X=hours-past-20h)
- Réponse à la demande utilisateur « les graphs sont pas très parlants visuellement [...] faire correspondre 1 point dans l'espace plotly vers 1 point qui a pour coordonnées Jour/Heure dans l'agenda du sommeil ».
- `tools/oscillator_explore/agenda_overlay.py` — nouveau visualiseur qui projette les fits (linear / single sin / double sin) dans l'espace visuel de l'agenda du sommeil. Mapping `(n, φ(n)) → (morning_date, x_hours_past_20h)` via `to_agenda_xy(ts) = (morning, (ts − 20h_J-1)/1h)` avec la convention `morning = ts.date() + 1 si ts.hour ≥ 20 sinon ts.date()` (cohérente avec `tools/sleep_agenda/agenda_render.py`).
- **Échantillonnage à n entier uniquement** : sampler en n fractionnaire balaie chaque row sur 24h puisque `onset_ts(n+δ) − onset_ts(n) = 24·δ h` — c'est faux visuellement (le modèle prédit 1 onset/nuit, pas un continuum). La ligne reliant 2 prédictions consécutives montre directement la dérive nuit-à-nuit. Gap inséré uniquement si la prédiction saute une nuit entière (> 1 jour de jump).
- Layout : Y=date matin (oldest top), X=[0, 24] avec ticks toutes les 2h labellés `20h, 22h, 00h, ..., 18h, 20h`, ligne pointillée à x=4 pour repère minuit. Sessions réelles dessinées en bars teal semi-transparentes (split en 2 rectangles si la session traverse 20h). Fits superposés : linear (ambre tirets), single-sin (cyan), double-sin (magenta). Onsets observés en points teal.
- Sortie : `data/personal/S001/oscillator_explore/<label>_agenda.html` par fenêtre. Sub-titre annonce AIC + BIC winner. Hauteur adaptative : `14px × n_nights + 220`.
- Vérification mathématique sur winter25 : pour P=3.2d/A=2.79h, les onsets prédits à n=0..7 zigzaguent entre x≈1.5h (21:30) et x≈6.5h (02:30) tous les ~3 jours — c'est exactement le motif sinusoïdal attendu, directement lisible.
- REPORT.md augmenté d'une section « Projection dans l'espace agenda » expliquant la convention de mapping et la raison de l'échantillonnage entier.

### 2026-06-03 `9a49127`
explore: Lomb-Scargle P-seeding + double sinusoid + AIC/BIC model selection
- Réponse à la demande utilisateur « le 7 doit être paramétrique, voit comment le déterminer sur la période justement. et creuse la double sinusoide ».
- **Lomb-Scargle remplace FFT-on-interpolated** comme méthode de seeding du paramètre P : `scipy.signal.lombscargle` opère sur les indices de nuit réels (irréguliers) sans nécessiter d'interpolation linéaire des nuits manquantes. Impact mesuré sur `atcf` : le pic dominant passe de 17.5j (artefact d'interpolation) à 2.1j (pic réel). Top-3 pics extraits, ordonnés par amplitude ; les 2 premiers (ordonnés par période) seedent le modèle double sinusoïde.
- **Modèle double sinusoïde** ajouté : `φ(n) = α·n + β + A₁·sin(2π·n/P₁+ψ₁) + A₂·sin(2π·n/P₂+ψ₂)` (8 paramètres). NLS avec bornes séparées `[1.8, window/3]` pour P₁ et `[P₁+0.5, window/2]` pour P₂ → garantit identifiabilité (P₁ < P₂). Re-tri post-fit pour cohérence.
- **AIC / BIC** calculés pour les 5 modèles (L, O, W, C, D) : `AIC = n·ln(SSR/n) + 2k`, `BIC = n·ln(SSR/n) + k·ln(n)`. Le « gagnant » est ajouté à la sortie CLI et annoté en sub-titre des plots.
- Résultats clés sur S001 : (1) `recent` 2026-04 → le double sinusoïde gagne sans ambiguïté (AIC+BIC tous deux votent « double »), révèle P₁≈2.5j/A₁≈2.1h + **P₂≈12.2j/A₂≈5.0h** (R²=0.59 vs 0.18 pour le single), et le τ révélé descend de 24.20h à **24.08h** ; (2) `winter25` → l'oscillateur simple reste préféré (BIC parcimonieux), τ=24.40h confirmé ; (3) `atcf` → AIC vote combined / BIC vote linear (désaccord = signal faible), aucun modèle ne dépasse R²=0.20.
- Plot mis à jour : panel 3 affiche maintenant le périodogramme Lomb-Scargle en log-axis (au lieu de FFT en linéaire), avec marqueurs des pics LS top-3 ET des P₁/P₂ issus du fit double, sous-titre du plot annonce « AIC winner / BIC winner ».
- REPORT.md restructuré avec section « Détermination du paramètre P » (pourquoi LS vs FFT), section « Le P=2-3j systématique : artefact ou réalité ? » (hypothèses aliasing / PRC / split de session Samsung), et pistes : autocorrélation des résidus pour valider les P_court, changepoint detection auto, `C(n)` non-linéaire type Process S de Borbely.

### 2026-06-03 `256d918`
explore: oscillator-on-drift phase model (linear / sin / weekly / combined) for 3 regimes
- Branche exploratoire `feat/oscillator-phase-model` (pas garantie d'être mergée) — test d'une hypothèse mathématique pour expliquer le « serpent qui zigzague » dans la trajectoire de phase N24, au-delà de la régression linéaire τ−24.
- `tools/oscillator_explore/fit.py` — fitter end-to-end : charge `sleep_intervals.parquet`, extrait `main_onset` par nuit via `main_sleep_per_night`, calcule `φ(n) = (onset − anchor_J0_12h) / 1h − 24·n`, puis fitte 4 modèles : (L) linéaire, (O) `α·n+β + A·sin(2π·n/P+ψ)` NLS seedé par FFT, (W) `α·n+β + ΔW·I_weekend`, (C) tout combiné. Sortie : 4-panel plotly (φ + fits, residuals lin vs best, FFT top-3 peaks, Δφ jour-à-jour) + summary.json.
- `tools/oscillator_explore/compare.py` — figure side-by-side comparant les 3 régimes sur une ligne, baseline centrée pour comparaison visuelle directe.
- `tools/oscillator_explore/REPORT.md` — analyse des résultats sur 3 fenêtres S001 : `winter25` 2025-11-26→12-26 = free-run quasi-pur (τ=24.40h, oscillation rapide P=3.2j/A=2.8h, R²=0.71), `recent` 2026-04-01→05-07 = transition (le modèle linéaire confond drift+vague → τ_lin=24.19h vs τ_osc=24.08h avec A=5.1h/P=12.3j, ΔR²=+0.39), `atcf` 2025-04-06→07-29 = contraint travail (τ=24.04h quasi-entraîné, ΔW=+2.1h significatif mais aucun modèle satisfaisant — la bascule weekend pure est trop rigide).
- Conclusions : (1) la fréquence d'oscillation n'est pas hebdomadaire fixe — P libre est nécessaire ; (2) le τ « vrai » intrinsèque se révèle uniquement sur les segments free-run (~24.4h) ; (3) le terme `C(n)` régime-travail doit être non-linéaire (saturation type Process S de Borbely appliqué à la phase) plutôt qu'une bascule binaire weekend.
- Pistes pour suite : modèle à 2 sinusoïdes (court + long), changepoint detection automatique pour découper les régimes, bootstrap CI sur (τ, A, P), comparer M10 phase vs main_onset comme indicateur de phase.

### 2026-06-02 `a0b57d3`
fix(sleep): proper per-night aggregation via sleep_id + midpoint night assignment
- `src/n24sal/sleep/per_night.py` — nouveau module `main_sleep_per_night(sleep_intervals, timezone)` qui identifie la **session sommeil principale** par nuit via grouping sur `sleep_id` (canonical Samsung), assignment par midpoint (robuste aux sessions longues qui chevauchent la frontière 20h ET aux siestes du jour suivant), longest session = main sleep, retourne `main_onset`, `main_offset`, `main_duration_h`, `n_sessions`, `tst_h` (total sleep time = somme de toutes les sessions de la nuit)
- `tests/test_sleep_per_night.py` — 8 tests couvrant empty input, only-AWAKE, single simple night, main = longest (pas first), late-afternoon-start assigned by midpoint, AWAKE excluded, multi-night sorting, custom awake_label
- `notebooks/04_regime_atcf_weekly_pattern.ipynb` — item 3 (sleep onset/wake) refactoré pour utiliser le helper ; 3 boxplots (onset / wake / main duration) + print summary incluant TST et n_sessions ; le bug "wake à 04h" résolu : les wakes weekdays restent à ~04-08h (mais c'est la donnée Samsung réelle — sleep_id split sur les éveils internes — donc TST est probablement le proxy clinique le plus fiable)
- Tests : 104 GREEN total (+8 nouveaux dans le module sleep)
- **Smoke test S001 / regime_atcf** : weekend TST median 8-10h vs weekday TST 5-7h (vs ancien bug qui mixait afternoon naps). Le pattern social entrainment + weekend catch-up est maintenant chiffrable proprement pour le manuscrit.

### 2026-06-02 `9e7d88c`
feat(notebooks): weekly pattern analysis — social entrainment leak detection
- `notebooks/04_regime_atcf_weekly_pattern.ipynb` — template paramétrable (`PERIOD_NAME` au top, défaut `regime_atcf`) qui dissèque une période sous régime travail-semaine en cinq analyses :
  1. Profile 24h activité weekday vs weekend (overlay deux courbes)
  2. Distribution M10 phase par jour-de-la-semaine (boxplot Lun-Dim)
  3. Sleep onset / wake-up par jour-de-la-semaine (depuis `sleep_intervals.parquet`, en hours-from-20h)
  4. Tau sur fenêtres 28j roulantes step 7j (courbe tau + R² sur la période)
  5. **Tau weekdays-only vs weekends-only** : régression M10 phases par sous-ensemble, bootstrap CI 500 iter
- Template sans outputs (no personal data committed)
- **Smoke-tested sur S001 / regime_atcf (101 jours, avr-juil 2025)** — finding majeur : weekdays-only tau=24.0004h R²=0.000 (entrainement social parfait), weekends-only tau=24.3127h R²=0.6484 (+18.7 min/j drift), social jet lag M10 ~6h entre semaine et weekend. Le N24 sous-jacent est invisible en analyse globale mais leak en isolation weekend — angle de discussion fort pour le case report.
- Connue limitation : Item 3 (sleep onset/wake) montre des wake-up à 04:00 en semaine, suggérant un bug d'aggregation des siestes du jour qui suit avec la nuit. À fixer en follow-up.

### 2026-06-02 `1572be5` — closes #11
feat: interactive sleep agenda + visual period selection + regime side-by-side analysis
- `tools/sleep_agenda/agenda_render.py` — port Centre ChronoS Bichat-Beaujon depuis SamsungHealth, adapté pour `sleep_intervals.parquet` + `activity.parquet`
- Deux thèmes via `--theme {medical, datasaillance}` — médical print-A3 (cellules orange `#f0b878` sur fond blanc, accent teal) vs DataSaillance dark (cellules teal sur `#191e22`, accent amber)
- Coverage overlay : barre fine colorée sous le date label, gradient rouge→vert selon % de present epochs sur la fenêtre 20h→20h
- JS vanilla drag-to-select sur la colonne date : panneau flottant live (start/end/n_nights/mean coverage), modal "Save period (YAML)" avec snippet + clipboard copy → user paste dans `periods.yaml`
- CLI multi-user-ready : `--subject-id`, `--data-dir`, `--timezone`, `--out`, `--non-interactive` (drop JS pour export print propre)
- `src/n24sal/io/periods.py` — schéma Pydantic `PeriodDef` + `PeriodsFile`, validation nom regex `^[a-z0-9_]+$`, unicité, dates ordonnées ; helpers `load_periods()` / `dump_periods()`
- `notebooks/03_personal_case.ipynb` — nouvelle section "7. Regime analysis" lit `periods.yaml` si présent, calcule NPCRA + tau bootstrap CI par période + full dataset baseline, rend un tableau comparison side-by-side
- `pyyaml>=6.0` ajouté aux dépendances base
- Tests : `tests/test_periods.py` (10 tests : Pydantic validation, YAML roundtrip, edge cases) + `tests/test_sleep_agenda.py` (7 tests : load_nights_from_parquet, rendu HTML 2 thèmes, non-interactive strip JS, CLI end-to-end). Total 95 GREEN
- **Smoke test sur S001 réelles** : agenda 843 nuits rendu en 2.7 MB (sleep_stage data remonte 2023+, > 517 jours movement). Trois régimes identifiés via la procédure :
  - full dataset (495 jours filtrés) : tau=24.417h R²=0.871
  - regime_homogeneous_2026_q2 (49 jours) : tau=**25.023h** R²=0.849 — N24 textbook
  - slice_6_months (135 jours) : tau=23.990h R²=**0.001** — confirme superposition de régimes
- Origin du renderer crédité dans le header (`SamsungHealth/tools/sleep_agenda/`)

### 2026-06-01 `c5245fa` — closes #8
feat: densify Samsung ingest + present column + tau coverage filter
- `src/n24sal/io/schemas.py` — nouveau type `GapFillStrategy` (`"none"` / `"zero_fill"`) + champ `SubjectMetadata.gap_fill_strategy` (défaut `"none"`) ; `present` ajouté aux `ACTIGRAPHY_OPTIONAL_COLUMNS` ; `validate_actigraphy_frame` rejette `present` non-booléen
- `src/n24sal/io/samsung.py` — nouvelle fonction `densify_activity(sparse, timezone, epoch_seconds)` produit grille 1-min régulière alignée aux jours locaux avec colonne `present` (bool, True où l'epoch était réellement enregistré) ; `ingest_samsung_export` densifie par défaut (param `densify=True`), `coverage_report` détecte automatiquement dense vs sparse, CLI ajoute `--no-densify` pour back-compat legacy
- `src/n24sal/npcra/tau.py` — `estimate_tau` et `bootstrap_tau_ci` acceptent `present_mask: np.ndarray | None` et `min_daily_coverage: float = 0.0` ; les jours dont `present.mean()` sur la fenêtre 24h est inférieure au seuil sont exclus de la régression M10-phase ; nouvelle helper privée `_select_valid_days`
- `notebooks/03_personal_case.ipynb` — détecte automatiquement `gap_fill_strategy == "zero_fill"` + colonne `present`, passe `present_mask` et `min_daily_coverage=0.5` à `estimate_tau`/`bootstrap_tau_ci`, affiche un warning si parquet legacy sparse
- `PROTOCOL.md` — nouvelle section "Stratégie d'imputation et de filtrage" documentant la densification + filtrage seuil + analyse de sensibilité prévue dans le manuscrit
- Tests : +8 nouveaux (densify_activity helper, no-densify legacy, coverage filtering on synthetic gaps, mismatched mask validation) ; total 86 GREEN
- **Verified on S001 real data** : 511 303 sparse → 691 200 dense epochs (480 local days, 74% present). Tau no-filter = 24.7183h R²=0.894 CI95 [24.6988, 24.7368]. Sensibilité seuil : 30%→24.67h / 50%→24.43h / 70%→24.63h, tous dans la range N24 littérature Sack 2007 (24.2-25.5h). Convergence BUGGY vs FIXED dans `scripts/investigate_tau.py` désormais 100%

### 2026-06-01 `adbf89a`
fix: investigate_tau script — tz-aware reindex + day-boundary truncate
- `.loc[ts.values] = ...` strippait la tz et faisait planter le set ; remplacé par `pd.Series(...).reindex(grid)` qui préserve l'alignement tz-aware
- Le grid `pd.date_range(start, end, freq="1min")` peut produire une longueur non-multiple de 1440 → ajout d'une troncature explicite à `n_full_days * EPOCHS_PER_DAY` avant le reshape
- Premier run avec output complet sur S001 (479 jours, 511k epochs) : **bug primaire confirmé** — BUGGY tau=22.43h vs FIXED tau=24.718h (CI95 [24.70, 24.74], R²=0.894, 480 jours utilisés). FILTER 50%/70% donnent 24.43/24.63 (cohérent). Le vrai tau est dans la range N24 publiée (Sack 2007 : 24.2-25.5h). Issue #8 mise à jour avec ces données.

### 2026-06-01 `ed40e87`
chore: diagnostic script for tau estimation on real data
- `scripts/investigate_tau.py` — compare 4 méthodes côte à côte sur `data/personal/<subject>/activity.parquet` :
  - BUGGY (comportement actuel : reshape sur série sparse)
  - FIXED (re-index dense 1-min grid avant reshape)
  - FILTER 50/70/90% (dense grid + drop des jours à coverage insuffisant)
  - Distribution stats des phases M10 par jour
- Outil de validation pour issue robust-tau (open) ; à re-runner après le fix pour confirmer convergence des méthodes
- Hardcodé subject_id=S001 par défaut, paramétrable en CLI

### 2026-06-01 `f7b8268`
feat(viz+npcra): DataSaillance viz module + bootstrap tau CI + Phase 2 notebooks
- `src/n24sal/viz/theme.py` — tokens couleur DataSaillance (teal `#0e9eb0`, amber `#d37c04`, cyan `#3be5e7`) + templates Plotly `datasaillance_dark` / `datasaillance_light` enregistrés ; helper `apply_theme(name)`
- `src/n24sal/viz/actogram.py` — `double_plot_actogram` (heatmap 2-day repeat, downsampling configurable, séparateur amber à 24h)
- `src/n24sal/viz/drift.py` — `m10_phase_drift_plot` (M10 unwrapped + régression linéaire overlay, R² affiché en légende)
- `src/n24sal/viz/profile.py` — `average_24h_profile` (moyenne + bande IQR 25–75%)
- `src/n24sal/viz/coverage.py` — `coverage_heatmap` (epochs/h par date × heure, gaps visuellement saillants)
- `src/n24sal/npcra/tau.py` — `bootstrap_tau_ci(n_iter=1000, confidence=0.95)` via resampling des paires (jour, phase M10), retourne `TauBootstrapCI` (tau, ci_low, ci_high, n_iter, n_days, confidence)
- `pyproject.toml` — `plotly>=5.18` déplacé en dépendance base (le viz module fait partie du package) ; `[viz]` extra reste pour matplotlib/seaborn/kaleido
- `notebooks/02_npcra_basics.ipynb` — pédagogique exécuté inplace (synthetic entrained vs tau=24.7h, IS/IV/RA/CFI side-by-side, tau recovery avec bootstrap CI, comparaison normes littérature)
- `notebooks/03_personal_case.ipynb` — template pour analyse perso (coverage map, actogramme full series, NPCRA fenêtres 14j glissantes, tau bootstrap, z-scores vs normes, key results à compléter par H1–H4) ; **shipped sans outputs exécutés** pour ne pas leak data perso
- Tests : 79 GREEN au total (10 viz smoke tests + 5 bootstrap tau + non-regression)
- Smoke test sur vraies données (S001, 511k epochs, 479 jours) : IS=0.093 (z=-5.27 vs healthy), RA=0.366 (z=-11.27), CFI=0.420 (z=-3.77) — signatures N24 fortes ; tau=22.43h ±0.04h CI95 = pattern **avance** (-94min/jour) à investiguer (advance type vs unwrap mis-direction)

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
