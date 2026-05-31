# Notes

## Known Issues

*(rien pour le moment — scaffold initial en cours)*

## Backlog

### Phase 1 — Ingestion Samsung Health raw (issue #2)
- [ ] Parser `n24sal.io.samsung` : CSV `com.samsung.health.movement.*.csv` + JSONs binning 1-min `activity_level`
- [ ] Output parquet `data/personal/S001/activity.parquet` validé par `validate_actigraphy_frame`
- [ ] Sidecar `subject_metadata.json` conforme `SubjectMetadata`
- [ ] Bonus : `sleep_intervals.parquet` (sleep_stage event-based)
- [ ] Bonus : `heart_rate.parquet` (cross-check)
- [ ] Couverture : ≥ 80% des epochs attendus sur 2023-12 → 2026-03

### Phase 2 — NPCRA notebooks sur données personnelles (issue #3)
- [ ] `notebooks/02_npcra_basics.ipynb` — cross-check formules vs pyActigraphy + normes littérature sur synthétique (pédagogique)
- [ ] `notebooks/03_personal_case.ipynb` — analyse complète données perso : overview 27 mois, actogramme double-plotté, IS/IV/RA/CFI fenêtres 14j, L5/M10 phases par jour, régression tau avec bootstrap CI 1000 iter, z-scores vs normes
- [ ] `notebooks/04_drift_episodes.ipynb` — drift rétrospectif sur épisodes 2016-2018 (hypothèse H4)
- [ ] Design tokens DataSaillance appliqués à toutes les figures Plotly

### Phase 3 — Dashboard data-science
- [ ] Streamlit avec contrôles paramétriques (fenêtre, source, version normes)
- [ ] Export figures publication direct depuis dashboard
- [ ] Design DataSaillance (teal/amber/cyan, Playfair + Inter)

### Phase 4 — Manuscrit / preprint
- [ ] Identifier revue cible (*Sleep Medicine* lettre vs *JCSM* short report vs preprint bioRxiv seul)
- [ ] Contacter coauteur clinicien (médecin du sommeil ou équipe chronobio Lyon / SFRMS)
- [ ] Geler `protocol-v1` tag avant soumission
- [ ] Section *Limitations* explicite : N=1, pas de cohorte re-dérivée, comparaison normes littérature 1990-2010

### Phase 5 — Post-restitution CamNtech
- [ ] Lecture du rapport PDF CamNtech
- [ ] Triangulation qualitative : tau / IS / RA reportés vs ceux reconstruits depuis Samsung
- [ ] Section "External corroboration" ajoutée au manuscrit

### Phase 6 — Cohorte publique (différée — stretch goal)
- [ ] CITI Independent Learner — $165, ~2 weekends, certificat 3 ans
- [ ] **Option A** : NHANES 2011-2014 PAM + PAXLUX (open access, mais 16 GB total, stream-parsing à dimensionner — pas de DUA)
- [ ] **Option B** : NSRR MESA Sleep via cosignataire institutionnel (cohort plus propre, mais dépend d'un partenariat académique)
- [ ] Pré-calculer `data/reference/healthy_controls.json` depuis sous-échantillon matched age/sex
- [ ] Notebook `05_public_comparison.ipynb` — N=1 vs distribution healthy, z-scores
- [ ] Amendement protocole + section "Updated comparison" dans revision manuscrit

### Décisions d'architecture (le "pourquoi")

- **2026-05-29** — Split du projet en deux repos : Nightfall (produit web+Android grand-public) vs n24-data-saillance (science+publi data). Raison : Nightfall a une charge prod élevée (auth multi-user, chiffrement Art.9, Android Compose) qui freinerait l'itération notebooks. Le repo science doit rester light, Plotly-only, pas de DB.
- **2026-05-29** — Consommation directe du Samsung Health raw export (CSV `com.samsung.health.movement` + JSONs `binning_data` 1-min) plutôt que via l'API Nightfall. Raison : Nightfall agrège en hourly (24 epochs/jour) ce qui dégrade IV ; les JSONs binning donnent un signal `activity_level` continu au 1-min, équivalent fonctionnel à des activity counts Actiwatch. Pas de duplication maintenance — l'export Samsung est l'interface canonique.
- **2026-05-29** — Schéma d'entrée portable (Samsung / Actiwatch / GENEActiv / CamNtech indifférencié) pour permettre comparaisons N=1 vs cohortes publiques sans dupliquer le pipeline d'analyse. La portabilité est *aussi* l'enabler pour réutilisation par d'autres patients à l'avenir.
- **2026-05-29** — Validation Bland-Altman initiale abandonnée car raw CamNtech indisponible. Remplacée par triangulation qualitative via rapport PDF (Phase 5).
- **2026-05-29** — Tests unitaires sur signal synthétique cosinor `tau` connu obligatoires avant tout calcul sur données réelles. Cross-check pyActigraphy comme oracle. Tolérance documentée.
- **2026-05-29** — **Pivot personal-first** : la comparaison à une cohorte publique re-dérivée (NHANES / MESA) est différée en Phase 6 (stretch goal). Raison : NSRR/MESA exige formation CITI Independent Learner (~$165) + potentiellement IRB ; NHANES 2011-2014 PAM est open access mais ~16 GB nécessitent infrastructure de stream-parsing (PAXLUX ambient light en bonus stratégique pour zeitgeber analysis) ; les normes publiées (Van Someren 1999, Ortiz-Tudela 2010, Witting 1990, Sack 2007, Hayakawa 2005) sont suffisantes pour un case report défensible. Cette absence est documentée explicitement dans `PROTOCOL.md` Limitation #7 et en section *Limitations* du futur manuscrit. Permet de livrer un artefact autonome en 2-3 weekends sans dépendance externe.
