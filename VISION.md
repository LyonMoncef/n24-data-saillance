# Vision

> Document vivant. Mis à jour après chaque conversation structurante.

## Le mot "saillance"

DataSaillance fait jouer **datascience** et **saillance** — au sens cognitif : ce qui émerge spontanément du fond, ce qui devient visible parce qu'on a su le mettre en relief. Le pari est qu'un signal médical rare (le N24 chez un voyant) est *déjà présent* dans des années de données wearable accumulées par l'utilisateur, mais qu'il faut une chaîne d'analyse adéquate pour le rendre saillant.

Ce repo n'est ni un tracker de plus, ni un dashboard cosmétique : c'est la **preuve méthodologique** que la chronobiologie grand-public est possible depuis du matériel consumer, avec une documentation suffisamment rigoureuse pour discuter avec un chercheur.

## Triple objectif

1. **Scientifique** — publi en case report N=1 (style *Sleep Medicine* lettre, *JCSM* short report, ou bioRxiv preprint) + release code méthodologique (style JOSS / SoftwareX). Pas de manuscrit Nature, mais une trace publique réutilisable par d'autres patients ou chercheurs.
2. **Portfolio DataSaillance** — vitrine technique pour l'agence freelance. Le repo doit être *lisible* par un prospect non-médical : README clair, notebooks qui racontent une histoire, design cohérent avec la charte.
3. **Vulgarisation** — un notebook accessible "qu'est-ce que le N24 et comment le voir dans des données ?" destiné au grand public ou aux patients en errance diagnostique.

## Ce que ce projet n'est pas

- **Pas un produit utilisateur** — Nightfall (SamsungHealth) couvre ce rôle pour la partie visualisation grand public et Android.
- **Pas un re-parser Samsung Health *via Nightfall*** — Nightfall agrège en hourly (24 epochs/jour) ce qui dégrade IV ; ce repo consomme directement le Samsung Health raw export (CSV `movement` + JSONs `binning_data` au 1-min) pour préserver la résolution NPCRA. Le schéma parquet d'entrée reste portable, indépendant de la source.
- **Pas un dashboard cosmétique** — le dashboard Streamlit ici est *data-science angle* : contrôles paramétriques, exports figures publication, comparaisons N=1 vs cohortes publiques.
- **Pas un projet d'ingénierie cloud** — pas d'auth, pas de multi-utilisateur, pas d'API. Si un jour des données externes sont partagées, c'est via parquet anonymisé.

## Contraintes hard

### C1 — Portabilité du schéma d'entrée

Un seul format parquet en entrée, indépendant de la source (Samsung, Actiwatch, GENEActiv, CamNtech). C'est ce qui permettra à terme de comparer N=1 personnel et N=N cohorte publique sans dupliquer le pipeline d'analyse.

### C2 — Tests sur données synthétiques avant données réelles

Chaque formule NPCRA est validée sur un signal synthétique à `tau` connu (cosinor 14-21 jours, bruit gaussien, seed fixée) avant tout calcul sur données personnelles. Tolérance documentée. Cross-check possible contre `pyActigraphy` comme oracle.

### C3 — Limites assumées dès le départ

Le manque de données CamNtech raw (validation chiffrée impossible) est documenté en première intention dans `PROTOCOL.md`. Pas de claim méthodologique surdimensionné. La triangulation avec le rapport PDF CamNtech sera qualitative.

### C4 — Cohérence avec le design system DataSaillance

Notebooks Plotly et dashboard Streamlit utilisent les tokens couleur DataSaillance (teal `#0e9eb0`, amber `#d37c04`, cyan `#3be5e7`). Pas d'indigo Tailwind, pas de gradient décoratif, pas de halo. Hiérarchie typographique : Playfair Display pour les titres, Inter pour le corps.

## Phases de développement

| Phase | Contenu | Statut |
|-------|---------|--------|
| **0 — Scaffold** | docs + structure + pyproject + tests synthétiques | ✅ done (PR #1) |
| **1 — Ingestion Samsung Health raw** | parser CSV + binning JSONs → parquet portable 1-min | À venir (issue #2) |
| **2 — NPCRA personal + literature norms** | actogramme drift, IS/IV/RA fenêtres glissantes, régression tau, comparaison vs Van Someren / Ortiz-Tudela / Sack | À venir (issue #3) |
| **3 — Dashboard data-science** | Streamlit, contrôles paramétriques fenêtre/source, exports figures publication | À venir |
| **4 — Manuscrit / preprint** | rédaction case report + figures publication, soumission bioRxiv | À venir |
| **5 — Triangulation CamNtech** | intégration rapport PDF post-restitution (qualitative) | À venir (post-restitution) |
| **6 — Cohorte publique** (deferred) | NHANES PAM+LUX (CITI requis) ou MESA Sleep (CITI + cosignataire académique) — stretch goal, post-preprint | Différée |

## Questions ouvertes

- Quelle revue cible exacte pour le case report ? *Sleep Medicine* lettre vs *JCSM* short report vs preprint bioRxiv seul ?
- Quel timing pour investir dans CITI Independent Learner (~$165, 2 weekends) — maintenant pour ouvrir NHANES/MESA en parallèle, ou après preprint si la trajectoire chrono-recherche se confirme ?
- Quel format de notebook pour la vulgarisation : Jupyter exporté HTML statique sur GitHub Pages, ou article blog DataSaillance dédié ?
- Quel niveau d'anonymisation des données personnelles dans le repo public ? (probablement : pas de timestamps absolus, ramener au jour 0 = début enregistrement)
- Coauteur clinicien : qui contacter ? (médecin du sommeil actuel, équipe chronobio Hôtel-Dieu Lyon, asso française du sommeil)
