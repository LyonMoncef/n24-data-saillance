# Protocole — préenregistrement méthodologique

> Format inspiré de la **CARE Checklist** (CAse REport guidelines, Gagnier et al. 2013) pour les case reports cliniques, adaptée à un préenregistrement avant l'analyse complète des données.
>
> Document figé dès `tag protocol-v1` ; toute modification post-tag est tracée comme amendement avec justification.

## Titre

Reconstruction non-paramétrique du rythme circadien chez un patient voyant atteint de trouble Non-24-Hour Sleep-Wake Disorder (N24SWD) à partir d'actigraphie consumer (Samsung Galaxy Watch). Case report N=1 longitudinal 2022–2026.

## Mots-clés

Non-24-hour sleep-wake disorder · free-running rhythm · circadian period (tau) · non-parametric circadian rhythm analysis · consumer wearable · actigraphy · Samsung Health · case report.

## Hypothèses préenregistrées

| # | Hypothèse | Test prévu | Critère de rejet |
|---|-----------|-----------|------------------|
| H1 | La période circadienne libre `tau` du sujet est supérieure à 24,0h | Régression linéaire de la phase M10 sur séries continues ≥ 14 jours | tau ≤ 24,1h sur ≥ 50% des fenêtres testées |
| H2 | L'**Interdaily Stability** (IS) du sujet est inférieure à 0,40 | IS calculé sur fenêtres glissantes 14 jours | IS médian ≥ 0,40 |
| H3 | La **Relative Amplitude** (RA) du sujet est inférieure à 0,80 | RA sur profil 24h moyen, fenêtres 14 jours | RA médian ≥ 0,80 |
| H4 | Une dérive circadienne est détectable rétrospectivement dans les données 2016-2018 (avant diagnostic) | Régression M10 sur les épisodes historiques disponibles | Pas de signature de drift sur ≥ 2 épisodes |

Hypothèses primaires : H1 et H2 (signature N24 publiée). Hypothèses exploratoires : H3 et H4.

## Patient

- **ID** : sujet S001, homme, ~38 ans en 2026, voyant, freelance basé Lyon
- **Diagnostic clinique** : N24SWD confirmé par un médecin du sommeil en 2026 ; antécédents de plaintes de sommeil sur ≥ 15 ans non résolues par PSG standard
- **Traitement actuel** : (à compléter — mélatonine titrée, photothérapie ?)
- **Consentement** : auto-recherche, données collectées sur son propre matériel ; publication soumise à consentement écrit du sujet

## Sources de données

| Source | Période | Résolution | Statut |
|--------|---------|-----------|--------|
| Samsung Health export (Galaxy Watch) | 2022 — présent (continu) | 1-min epochs (steps, HR) | Exploitée |
| Samsung Health export (épisodes historiques) | 2016 — 2018 (intermittent) | variable | Exploratoire (H4) |
| CamNtech MotionWatch 8 | 3 semaines en cours (2026) | 1-min epochs + lumière | Rapport PDF uniquement ; raw inaccessible |
| Open-Meteo irradiance solaire | Croisée GPS | Horaire | Enrichissement contextuel |
| MESA Sleep via NSRR (Philips Actiwatch) | Cohorte publique | Variable | **Différée** — cf. `NOTES.md` decision log 2026-05-29 (CITI training + IRB requis) |
| NHANES 2011-2014 PAM + PAXLUX (ActiGraph GT3X+ wrist + lumière) | Cohorte publique | 1-min, 7j × ~14 000 sujets | **Différée** — open access mais infrastructure 16 GB requise, reprise en Phase 6 |

## Plan d'analyse (figé pré-données)

### Variables primaires

- **IS** (Interdaily Stability, Van Someren 1999, formule fournie dans `src/n24sal/npcra/metrics.py`)
- **IV** (Intradaily Variability, idem)
- **L5** (5h activité minimale moyennée, sur profil 24h)
- **M10** (10h activité maximale moyennée, sur profil 24h)
- **RA** (Relative Amplitude = (M10 - L5) / (M10 + L5))
- **CFI** (Circadian Function Index, Ortiz-Tudela 2010)
- **tau** (période circadienne libre, régression sur phases M10 quotidiennes)

### Fenêtres temporelles

- Fenêtre principale : 14 jours glissants, pas 1 jour
- Fenêtre étendue : 21 jours (alignement protocoles AASM 2018)
- Analyse rétrospective : agrégation par épisode continu ≥ 7 jours

### Statistiques

- Distribution des indicateurs : médiane + IQR (non-paramétrique, échantillons longitudinaux non-iid)
- Comparaison avec normes publiées (Van Someren 1999, Ortiz-Tudela 2010, Witting 1990) : intervalle de confiance bootstrap 1000 itérations
- Régression `tau` : intervalle de confiance pente bootstrap 1000 itérations ; R² ≥ 0,85 requis pour validité

### Stratégie d'imputation et de filtrage (issue #8, résolu PR à venir)

- **Densification** : la série d'activité parquet est produite sur une grille régulière 1-min alignée aux jours locaux (`Europe/Paris`), gaps imputés à `0.0`. Une colonne booléenne `present` distingue les epochs réellement enregistrés des epochs imputés. Champ `gap_fill_strategy = "zero_fill"` dans `SubjectMetadata` documente le choix. Justification : la version `"none"` (sparse) crée un misalignment journalier lors du reshape `(n_days, 1440)` (le ratio `n_epochs / 1440` n'est plus le nombre de jours réels), faussant l'estimation `tau`.
- **Filtrage par couverture journalière** : pour la régression `tau`, les jours dont la couverture (`present.mean()` sur la fenêtre 24h) est inférieure à `min_daily_coverage = 0.5` (défaut analyse principale) sont exclus de la régression M10-phase. Justification : sur un jour à faible couverture, le profil 24h moyen est presque plat, `argmax` du M10 window devient quasi-aléatoire et pollue la pente.
- **Analyse de sensibilité** : la section *Results* du manuscrit reporte `tau` aux seuils `min_daily_coverage` = 0.0, 0.3, 0.5, 0.7 pour démontrer la robustesse de la conclusion principale au choix du seuil.
- **Métriques non-tau (IS, IV, RA, CFI)** : calculées sur fenêtres glissantes 14j ; chaque fenêtre est conservée si elle contient au moins 60% des epochs attendus. Pas de filtrage `present_mask` à l'épisode interne (les fenêtres avec gaps légers restent informatives — la métrique elle-même tolère le bruit).

### Logiciels

- Implémentation Python pure : `n24sal` (ce repo), tests d'égalité contre `pyActigraphy` 0.3+ comme oracle
- Stats : `scipy`, `statsmodels`, `pingouin`
- Reproductibilité : seeds NumPy fixées dans `tests/` ; lock dependencies via `uv lock`

## Limites assumées préenregistrées

1. **N=1** : aucune généralisation au-delà du sujet. Le case report vise la documentation méthodologique reproductible, pas l'inférence populationnelle.
2. **Steps ≠ activity counts** : Samsung Health exporte des steps/min, pas des activity counts au sens Actiwatch. La conversion est documentée mais non validée numériquement faute d'enregistrement CamNtech raw simultané. Limitation citée explicitement dans toute publication.
3. **Pas de DLMO** : aucune mesure mélatonine. La phase circadienne M10 est un proxy d'acrophase d'activité, pas un proxy direct d'acrophase mélatonine. La corrélation littérature est ~0,7-0,8 ; documentée.
4. **Pas de capteur lumière personnel** : seul l'enrichissement Open-Meteo (irradiance solaire extérieure pondérée GPS outdoor) est disponible. Manque l'exposition lumineuse intérieure réelle.
5. **CamNtech raw indisponible** : seul un rapport PDF de synthèse sera obtenu après restitution. La validation chiffrée Bland-Altman initialement envisagée est remplacée par une **triangulation qualitative** : comparaison `tau` reconstruit vs `tau` estimé par le rapport PDF, et comparaison visuelle d'actogramme sur la fenêtre 3 semaines de port commun. Limitation cardinale du protocole.
6. **Auto-recherche** : le sujet est à la fois patient, opérateur de l'analyse, et auteur principal. Biais d'investigation reconnu ; mitigation : coauteur clinicien indépendant requis avant submission.
7. **Pas de cohorte healthy re-dérivée** (Phase 6 différée) : la comparaison est restreinte aux normes publiées dans la littérature (Van Someren 1999, Ortiz-Tudela 2010, Witting 1990 pour les contrôles ; Sack 2007, Hayakawa 2005 pour les N24). La re-dérivation d'une distribution populationnelle depuis un dataset public (NHANES PAM+LUX 2011-2014, MESA Sleep via NSRR) est différée à la Phase 6, conditionnée à la formation CITI Independent Learner et/ou à l'obtention d'un cosignataire institutionnel. Pour le case report initial, cette absence est explicitement énoncée en section *Limitations* du futur manuscrit, avec mention que les normes 1990-2010 datent et peuvent sous-estimer ou sur-estimer la dispersion populationnelle 2026.

## Amendements

| Date | Section | Changement | Justification |
|------|---------|-----------|---------------|
| — | — | — | — |
