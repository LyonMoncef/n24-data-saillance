# Bibliographie

> Document vivant. Toute référence ajoutée doit indiquer : pertinence pour ce projet, et tag (NPCRA / N24 / wearable-validation / actigraphie-méthodo / dataset-public / stats).

## NPCRA — formules fondatrices

- **Van Someren EJW, Swaab DF, Colenda CC, Cohen W, McCall WV, Rosenquist PB.** *Bright light therapy: improved sensitivity to its effects on rest-activity rhythms in Alzheimer patients by application of nonparametric methods.* Chronobiology International. 1999;16(4):505-518. — **Source primaire** des formules IS et IV. À citer pour toute implémentation. Tag: NPCRA.
- **Witting W, Kwa IH, Eikelenboom P, Mirmiran M, Swaab DF.** *Alterations in the circadian rest-activity rhythm in aging and Alzheimer's disease.* Biological Psychiatry. 1990;27(6):563-572. — Source historique L5/M10 et fenêtres glissantes. Tag: NPCRA.
- **Ortiz-Tudela E, Martinez-Nicolas A, Campos M, Rol MA, Madrid JA.** *A new integrated variable based on thermometry, actimetry and body position monitoring to evaluate circadian system status in humans.* PLoS Computational Biology. 2010;6(11):e1000996. — Source du CFI (Circadian Function Index). Tag: NPCRA.

## N24SWD — clinique et physiologie

- **Sack RL, Auckley D, Auger RR, Carskadon MA, Wright KP Jr, Vitiello MV, Zhdanova IV.** *Circadian rhythm sleep disorders: part II, advanced sleep phase disorder, delayed sleep phase disorder, free-running disorder, and irregular sleep-wake rhythm.* Sleep. 2007;30(11):1484-1501. — Référence clinique N24, valeurs `tau` typiques chez l'aveugle (24,3–25,5h). Tag: N24.
- **Lockley SW, Skene DJ, Arendt J, Tabandeh H, Bird AC, Defrance R.** *Relationship between melatonin rhythms and visual loss in the blind.* Journal of Clinical Endocrinology and Metabolism. 1997;82(11):3763-3770. — N24 chez l'aveugle, actigraphie + DLMO. Tag: N24.
- **Hayakawa T, Uchiyama M, Kamei Y, Shibui K, Tagaya H, Asada T, Okawa M, Urata J, Takahashi K.** *Clinical analyses of sighted patients with non-24-hour sleep-wake syndrome: a study of 57 consecutively diagnosed cases.* Sleep. 2005;28(8):945-952. — Série de cas chez le voyant — référence principale pour la rareté de la pathologie hors cécité. Tag: N24.
- **Uchiyama M, Lockley SW.** *Non-24-hour sleep-wake rhythm disorder in sighted and blind patients.* Sleep Medicine Clinics. 2015;10(4):495-516. — Revue. Tag: N24.

## Wearable consumer vs actigraphie médicale — validation

- **Smith MT, McCrae CS, Cheung J, Martin JL, Harrod CG, Heald JL, Carden KA.** *Use of actigraphy for the evaluation of sleep disorders and circadian rhythm sleep-wake disorders: an American Academy of Sleep Medicine systematic review, meta-analysis, and GRADE assessment.* Journal of Clinical Sleep Medicine. 2018;14(7):1209-1230. — Revue systématique AASM, niveau de preuve actigraphie. Tag: actigraphie-méthodo.
- **De Zambotti M, Cellini N, Goldstone A, Colrain IM, Baker FC.** *Wearable sleep technology in clinical and research settings.* Medicine and Science in Sports and Exercise. 2019;51(7):1538-1557. — Revue état de l'art wearables. Tag: wearable-validation.
- *À compléter* — recherche dirigée sur la validation Samsung Galaxy Watch / Apple Watch / Fitbit en chronobiologie 2023-2025.

## Datasets publics

- **NSRR** (National Sleep Research Resource) — `sleepdata.org`. Datasets multiples avec actigraphie : MESA Sleep (~2200 sujets, Philips Actiwatch), CFS (Cleveland Family Study), HCHS/SOL. Accès via Data Use Agreement. Tag: dataset-public.
- **UK Biobank Accelerometry Substudy** — ~100K sujets, Axivity AX3 7 jours. Accès via application research formelle. Tag: dataset-public.
- **NHANES 2011-2014** — GENEActiv wrist, sous-cohorte. Open access. Tag: dataset-public.
- *À explorer* — Zenodo / Figshare pour datasets chronobio récents (post-2023) ; recherche CamNtech MotionWatch spécifique.

## Stats et reporting

- **Bland JM, Altman DG.** *Statistical methods for assessing agreement between two methods of clinical measurement.* The Lancet. 1986;327(8476):307-310. — Référence agréement méthodes (utilisée si raw CamNtech disponible). Tag: stats.
- **Gagnier JJ, Kienle G, Altman DG, Moher D, Sox H, Riley D; CARE Group.** *The CARE guidelines: consensus-based clinical case reporting guideline development.* Headache. 2013;53(10):1541-1547. — Format reporting case report, utilisé pour ce protocole. Tag: stats.

## Logiciels et outillage

- **pyActigraphy** — https://github.com/ghammad/pyActigraphy. Implémentation Python NPCRA + HMM sleep/wake. **Utilisé comme oracle dans les tests unitaires** de `n24sal`. Tag: actigraphie-méthodo.
- **nparACT** (R) — Package historique Van Someren formules. Référence implémentation. Tag: actigraphie-méthodo.
- **GGIR** (R) — UK Biobank workflow, accelerometry processing. Référence pour GENEActiv/Axivity. Tag: actigraphie-méthodo.

## À ajouter au fil de l'eau

- Recherche dirigée post-démarrage : papers 2024-2026 sur "consumer wearable" + "circadian rhythm disorder" + "free-running"
- Format Sleep Medicine / JCSM pour case report N24 → identifier 2-3 exemples publiés post-2020
- Standards CONSORT-AI / SPIRIT-AI si modèles ML utilisés
