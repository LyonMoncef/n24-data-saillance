# Notes

## Known Issues

*(rien pour le moment — scaffold initial en cours)*

## Backlog

### Phase 1 — données personnelles
- [ ] Spec du contrat d'export Nightfall → `n24-data-saillance` (colonnes parquet, sidecar JSON metadata)
- [ ] Implémenter `n24sal.io.readers.read_nightfall_export(path)` qui valide le parquet contre `ActigraphySchema`
- [ ] Premier actogramme double-plotté Plotly sur 21 jours de données réelles
- [ ] Régression `tau` initiale sur fenêtre 2026-Q1
- [ ] Comparer profil de drift sur années 2022/2023/2024/2025

### Phase 2 — cohorte publique
- [ ] Compléter Data Use Agreement NSRR pour MESA Sleep
- [ ] Adapter pyActigraphy import → schéma portable `n24sal`
- [ ] Pré-calculer `data/reference/healthy_controls.json` depuis sous-échantillon MESA
- [ ] Comparer indicateurs N=1 vs distribution healthy

### Phase 3 — notebooks publication
- [ ] `01_intro_n24.ipynb` — vulgarisation, exemple actogramme synthétique
- [ ] `02_npcra_basics.ipynb` — formules + cross-check pyActigraphy
- [ ] `03_personal_case.ipynb` — analyse complète données Moncef
- [ ] `04_public_comparison.ipynb` — N=1 vs cohorte MESA
- [ ] `05_publication_figures.ipynb` — export SVG/PDF qualité publication

### Phase 4 — dashboard
- [ ] Streamlit avec contrôles paramétriques (fenêtre, source de données)
- [ ] Export figures publication direct depuis dashboard
- [ ] Design DataSaillance (teal/amber/cyan, Playfair + Inter)

### Phase 5 — publication
- [ ] Identifier revue cible (*Sleep Medicine* lettre vs preprint bioRxiv seul)
- [ ] Contacter coauteur clinicien (médecin du sommeil ou équipe chronobio)
- [ ] Rédiger draft manuscrit
- [ ] Geler `protocol-v1` tag avant soumission

### Phase 6 — post-restitution CamNtech
- [ ] Lecture du rapport PDF CamNtech
- [ ] Triangulation qualitative : tau / IS / RA reportés vs ceux reconstruits depuis Samsung
- [ ] Section "External corroboration" ajoutée au manuscrit

### Décisions d'architecture (le "pourquoi")

- **2026-05-29** — Split du projet en deux repos : Nightfall (produit web+Android grand-public) vs n24-data-saillance (science+publi data). Raison : Nightfall a une charge prod élevée (auth multi-user, chiffrement Art.9, Android Compose) qui freinerait l'itération notebooks. Le repo science doit rester light, Plotly-only, pas de DB.
- **2026-05-29** — Pas de réimplémentation du parser Samsung Health JSON. Nightfall expose les données via export parquet/CSV au schéma portable défini ici. Évite le double maintien quand Samsung change son schéma.
- **2026-05-29** — Schéma d'entrée portable (Samsung / Actiwatch / GENEActiv / CamNtech indifférencié) pour permettre comparaisons N=1 vs cohortes publiques sans dupliquer le pipeline d'analyse.
- **2026-05-29** — Validation Bland-Altman initiale abandonnée car raw CamNtech indisponible. Remplacée par triangulation qualitative via rapport PDF + comparaison avec cohorte publique gold-standard (MESA Sleep, Actiwatch).
- **2026-05-29** — Tests unitaires sur signal synthétique cosinor `tau` connu obligatoires avant tout calcul sur données réelles. Cross-check pyActigraphy comme oracle. Tolérance documentée.
