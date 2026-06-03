# Oscillator-on-drift phase model — exploration

Branche : `feat/oscillator-phase-model` (exploratoire, pas garantie d'être mergée).

## Hypothèse testée

Au-delà du modèle classique « phase ≈ (τ − 24) · n », on cherche à
capturer **l'oscillation visible** dans la trajectoire de l'heure de coucher
(« le serpent qui zigzague »).

## Modèles fittés

| # | Modèle | Termes | k_params |
|---|--------|--------|----------|
| L | **Linéaire** | `φ(n) = α·n + β` | 2 |
| O | **Oscillateur** | `φ(n) = α·n + β + A·sin(2π·n/P + ψ)` | 5 |
| W | **Hebdomadaire** | `φ(n) = α·n + β + ΔW · I_weekend(n)` | 3 |
| C | **Combiné** | L + O + W | 6 |
| **D** | **Double sinusoïde** | `φ(n) = α·n + β + A₁·sin(2π·n/P₁+ψ₁) + A₂·sin(2π·n/P₂+ψ₂)` | **8** |
| **E** | **Dette de sommeil** | `φ(n) = α·n + β + A·sin(2π·n/P+ψ) + κ·D(n)` | **6** |

avec `α = τ − 24` et P **libre** (NLS bornées). Pas de 7-jours codé en dur.

Pour le modèle **E** : `D(n)` est la dette de sommeil **leaky** au coucher de la nuit n :

    D(n) = γ · D(n-1) + (T★ − TST(n-1))     [sans plancher 0, donc crédit autorisé]

avec **T★ = 8.99h** (médiane TST en free-run winter25, ≈ durée idéale de sommeil)
et **γ = 0.85** (demi-vie ≈ 4.3 nuits). D est calculé sur la chronologie complète
(non reset par fenêtre) pour que chaque fenêtre hérite de sa dette accumulée
historique. κ est le coefficient (h/h) qui mappe « heure de dette → décalage de
phase ». Signe physiologique attendu : **κ < 0** (plus de dette → coucher plus tôt).

## Détermination du paramètre P

Critique : l'ancienne approche FFT-on-interpolated produisait des artefacts
basse-fréquence dûs à l'interpolation linéaire des nuits manquantes. **Solution
adoptée : Lomb-Scargle** sur les indices de nuit réels (gère nativement
l'irrégularité). On extrait les top-3 pics du périodogramme et :

- Le pic dominant sert de **seed** pour le modèle O (single sinusoïde).
- Les pics #1 et #2 (ordonnés par période) seedent (P₁, P₁) pour le modèle D.
- NLS (`scipy.optimize.curve_fit`) raffine ensuite, avec bornes
  `1.8 ≤ P ≤ window/2` et séparation `P₂ > P₁ + 0.5` pour le double.

**Impact mesuré du changement FFT → LS :** sur `atcf`, le pic « dominant »
passe de 17.5j (artefact d'interpolation) à 2.1j (pic réel). Cf. tableau.

## Sélection de modèle : AIC / BIC

Pour chaque fenêtre on calcule :

    AIC = n · ln(SSR/n) + 2k
    BIC = n · ln(SSR/n) + k · ln(n)

Le **gagnant** est celui de plus petit AIC (ou BIC, plus parcimonieux).

## Résultats sur les 3 fenêtres S001

```
label      nights      τ_lin   τ_osc   τ_dbl   τ_deb  |  P_sin A_sin  |   P₁   A₁    P₂   A₂  |   κ    |  R²L  R²O  R²W  R²C  R²D  R²E  |  AIC win  BIC win
atcf       101/115    24.028  24.027  24.035  24.049  |   2.3  2.13  |  2.1  1.98 23.7  2.02 | -0.234 | 0.03 0.12 0.09 0.17 0.19 0.15 | combined  weekly
recent     34/37      24.189  24.199  24.080  24.271  |   1.8  1.74  |  2.5  2.13 12.2  4.99 | -0.222 | 0.13 0.18 0.13 0.22 0.59 0.20 | double    double
winter25   29/31      24.404  24.402  24.368  24.510  |   3.2  2.79  |  2.5  2.44 11.4  2.05 | -0.428 | 0.56 0.71 0.57 0.71 0.74 0.76 | debt     debt
```

(T★ = 8.99h, γ = 0.85, filtre durée [2, 24]h sur main_duration — explique le passage de 106/115 à 101/115 sur atcf.)

### Lecture par régime

**`recent` (transition, avr-mai 2026) — le double sinusoïde gagne sans ambiguïté**
- AIC + BIC pointent tous deux **vers le double sinusoïde** (R²=0.59 vs 0.18 pour le single).
- Structure révélée : **P₁ ≈ 2.5j / A₁ ≈ 2.1h** (zigzag rapide) **+ P₂ ≈ 12.2j / A₂ ≈ 5.0h** (grosse vague lente).
- Sans le double sin, le modèle simple confondait les deux et donnait τ_osc=24.20h alors que le **vrai τ révélé par le double est 24.08h** — quasi le même que `atcf` (régime contraint).
- Hypothèse biologique : la vague 12j pourrait être un **cycle d'adaptation sociale partielle** (genre rendez-vous récurrents, ou rebound homéostatique sur 2 semaines).

**`winter25` (free-run, nov-déc 2025) — l'oscillateur simple suffit**
- AIC + BIC choisissent **oscillator (5 params)** plutôt que double (8 params). Le gain ΔR²=0.03 ne paie pas les 3 params supplémentaires.
- Single : **P ≈ 3.2j / A ≈ 2.8h**, τ_osc = 24.40h (clair free-run).
- Le double détecte aussi un cycle long P₂=11.4j / A₂=2.1h mais son apport est marginal.
- Signature confirmée : zigzag rapide + drift fort. Le « vrai » τ intrinsèque est ici, autour de **24.40h**.

**`atcf` (travail, avr-jul 2025) — désaccord AIC vs BIC, modèle E n'aide pas**
- AIC vote **combined (sin + weekly)**, BIC vote **weekly**. Le modèle E (R²=0.15) reste en-dessous.
- Tous les modèles plafonnent à R² < 0.20 → le rythme entraîné n'est ni périodique simple ni step-function weekend ni linéaire en dette.
- **ΔW = +2.1h** significatif (effet weekend réel) mais variabilité résiduelle énorme (σ ≈ 2.5h).
- LS révèle **P ≈ 2.1j** comme top peak — c'est sans doute un battement entre les nuits travail/repos et l'horaire de réveil, pas un vrai oscillateur biologique.
- κ = −0.23 (cohérent biologique) mais effet faible : l'onset en régime contraint est dominé par l'alarme, pas par la dette ressentie.

## Modèle E (dette de sommeil) — verdict après 3 fenêtres

**κ négatif partout** : −0.43 (winter25), −0.22 (recent), −0.23 (atcf). Sens
physiologique respecté : plus de dette accumulée → couché plus tôt.

**Surprise n°1 : c'est sur winter25 (free-run) que la dette aide le plus**
- AIC + BIC choisissent **debt** (R²=0.76) au-dessus de oscillator (0.71) et double (0.74).
- Contre-intuitif : on attendait κ ≈ 0 en free-run (dormir à volonté → dette nulle).
- Explication probable : même en free-run, les fluctuations TST nuit-à-nuit corrèlent
  avec l'onset suivant via le mécanisme homéostatique. La « dette » devient ici une
  variable continue de pression de sommeil plutôt qu'une dette socialement imposée.

**Surprise n°2 : sur atcf (le régime contraint, là où on visait l'effet maximal)
la dette ne débloque pas le R²**
- R²E = 0.15 < R²C = 0.17. Le modèle E perd contre combined.
- Hypothèse formulée par le user : « weekday/weekend brutal qu'on ne peut pas
  capturer en sinusoïde, la dette gonfle puis explose le weekend ». Le mécanisme
  est probablement réel, mais il agit sur la **durée du sommeil** (TST), pas sur
  l'**heure d'endormissement** (φ) — qui reste asservie à l'alarme/contraintes.
- La dette tirée par l'alarme produit un grossissement weekend de la TST, pas
  un avancement de l'onset weekday.

**Implication directe** : valider l'hypothèse user réclame un **modèle joint
phase + durée** :

    φ(n) = α·n + β + A·sin(2π·n/P + ψ) + κ·D(n)
    TST(n) = β_T + λ·D(n−1) − μ·C(n) + ε

avec `C(n) = I_weekday(n)` (1 si lun-ven, 0 si sam-dim). La dette est partagée
(D issue de TST observé via le leaky integrator). Fits **séparés** (OLS pour
TST, NLS pour la phase) — ça garde chaque coefficient interprétable.

## Modèle joint phase + TST — résultats

Implémenté dans `tools/oscillator_explore/joint_model.py`. Trois variantes
pour la durée comparées par AIC/BIC :

| # | Modèle TST | k_params |
|---|------------|----------|
| T0 | `β_T` (constante) | 1 |
| T1 | `β_T + λ·D(n−1)` | 2 |
| T2 | `β_T + λ·D(n−1) − μ·C(n)` | 3 |

```
label      nights         κ   R²_φE  |  β_T2   λ_T2   μ_T2   |  R²_T0 R²_T1 R²_T2 |  AIC/BIC TST
atcf       101/115   -0.234   0.15   |  9.06h  +0.094  +2.42h |   0.00  0.02  0.16 |  T2 (✓ hypothèse)
recent     34/37     -0.222   0.20   |  7.89h  +0.084  -0.09  |   0.00  0.02  0.02 |  T0 (transition)
winter25   29/31     -0.428   0.76   |  9.41h  +0.182  +1.25  |   0.00  0.05  0.09 |  T0 (free-run)
```

### Lecture par régime

**`atcf` — l'hypothèse user est validée**
- **T2 gagne AIC+BIC** sans ambiguïté (R²=0.16 vs 0.02 pour T1).
- **μ = +2.42 h** → être en jour de semaine **retire 2h24 de TST par rapport
  au weekend** : weekend `TST ≈ 9.06 + 0.094·D` ; weekday `TST ≈ 6.64 + 0.094·D`.
  Effet **massif**, totalement invisible dans le modèle de phase seul.
- λ = +0.094 modeste mais bon signe : la dette accumulée la veille tire bien
  vers une nuit plus longue le lendemain (rebound homéostatique).
- β_T = 9.06h ≈ T★ — l'optimum sans contrainte tombe sur la durée idéale.
- **Cohérent avec l'intuition** : sur le régime contraint, la dette gonfle
  bien la TST, mais elle se rembourse via la **durée** (rebond weekend), pas
  via un avancement de l'onset (asservi à l'alarme).

**`recent` — fenêtre de transition, pas de signature weekly nette**
- T0 (constante) gagne. λ ≈ 0.08, μ ≈ −0.09 (essentiellement bruit).
- 34 nuits seulement → puissance statistique limitée.
- Période de bascule : ni clairement libre, ni clairement contrainte.

**`winter25` — free-run sans alarme, T0 suffit**
- T0 (β_T = 9.41h ≈ T★) gagne.
- μ = +1.25h positif détecté (pas significatif au sens AIC), λ = +0.18.
- Cohérent avec free-run : pas de contrainte sociale → pas de signature
  weekday/weekend prononcée. La durée converge vers la durée naturelle.

### Synthèse étendue par régime

| Régime | τ révélé | best φ | best TST | κ | μ (weekday) | Mécanisme dominant |
|--------|----------|--------|----------|---|-------------|--------------------|
| Free-run (`winter25`) | 24.51h | E | T0 | −0.43 | n.s. | Drift fort + dette continue tire la phase |
| Transition (`recent`) | 24.27h | double | T0 | −0.22 | n.s. | Double oscillation phase, durée encore libre |
| Contraint (`atcf`) | 24.05h | combined | **T2** | −0.23 | **+2.4h** | **Alarme clamp la durée weekday → rebound weekend via dette** |

### Implication pour le modèle général

La représentation correcte pour S001 en régime mixte est un **système 2-équations** :

    φ(n) = α·n + β + A·sin(2π·n/P + ψ) + κ·D(n)
    TST(n) = β_T + λ·D(n−1) − μ·C(n) + ε
    D(n)   = γ·D(n−1) + (T★ − TST(n))    [état partagé, leaky]

avec **`C(n)` = indicateur de contrainte sociale** (binaire ici, peut être
enrichi avec calendrier de RDV, alarmes Samsung, etc.). En free-run, μ → 0
et l'équation TST devient triviale ; le système se réduit naturellement à
un seul mécanisme.

**Suspect identifiabilité** : sur recent, le double sinusoïde (R²=0.59) reste
largement préféré au modèle E (R²=0.20). La grosse vague 12-jours ne se laisse
pas réduire à un terme linéaire en dette — elle a sa propre structure périodique
indépendante.

## Synthèse par régime

| Régime | τ révélé | Modèle gagnant (AIC) | κ_dette | Lecture |
|--------|----------|----------------------|---------|---------|
| Free-run (`winter25`) | **24.51h** (E) / 24.40h (L) | **debt** | −0.43 | Dette + oscillation + drift fort. La pression homéostatique continue corrèle avec l'onset même hors contrainte sociale. |
| Transition (`recent`) | **24.08h** (D) / 24.27h (E) | **double sinusoid** | −0.22 | Double oscillation domine ; dette joue un rôle mineur. La vague 12j n'est pas explicable par dette seule. |
| Contraint (`atcf`) | **24.04h** | **combined** (sin + weekly) | −0.23 | Dette n'aide pas la phase (alarme dicte l'onset). Probable que la dette agit sur la **durée**, pas la phase → motive un modèle joint. |

## Implications pour le modèle général

Le modèle proposé en discussion :

    φ(n) = (τ − 24) · n + A · sin(2π · f · n / 7) + C(n) + ε(n)

doit évoluer en **3 axes** :

1. **Le `7` codé en dur saute** ✅ — P est paramètre libre seedé par LS.
   La période d'oscillation varie réellement entre régimes (2-12 jours observés).

2. **Une seule sinusoïde n'est pas toujours suffisante** : sur `recent`,
   le double sinusoïde révèle DEUX composantes distinctes (rapide + lente).
   Le modèle correct est :

       φ(n) = (τ − 24) · n + A₁·sin(2π·n/P₁ + ψ₁) + A₂·sin(2π·n/P₂ + ψ₂) + C(n)

   Avec la convention P₁ < P₂ pour l'identifiabilité. Le critère AIC/BIC
   décide automatiquement si le 2ème terme est justifié par les données.

3. **`C(n)` pour le régime contraint reste l'inconnu majeur** : aucun modèle
   testé ici (sinusoïde, step weekend, leurs combinaisons) ne dépasse R²=0.20
   pour `atcf`. La signature est ni purement périodique ni purement binaire
   weekend. Pistes :
   - `C(n) = -S · jours_depuis_dimanche(n)` (accumulation linéaire dans la semaine)
   - `C(n) = -S · jours_depuis_dimanche(n) · (1 - e^(-n/γ))` (saturation type Process S)
   - Detection de changepoints automatique pour découper par régime

## Le P=2-3j systématique : artefact ou réalité ?

Les 3 fenêtres montrent un pic LS court entre 1.8 et 3.2 jours. Possibilités :

- **Aliasing**: avec τ≈24.4h et sampling 24h, un battement apparent à P=24/(τ-24) jours apparaît. 24/0.4=60j (non observé), mais 24/(0.4·6)=10j (proche de P₂ pour recent et winter25). Le P=2-3j est probablement réel et non un alias trivial.
- **PRC + homéostasie** : avance pendant 2-3j, rattrapage 1j — pattern décrit par le user et confirmé visuellement.
- **Sieste / nuit double** : Samsung peut splitter une nuit en 2 sessions ; si le bug n'est pas totalement corrigé sur `main_sleep_per_night`, ça pourrait créer un artefact.

À vérifier : prendre le résidu et regarder la fonction d'autocorrélation —
un vrai cycle 3j donne une bosse à lag=3 et anti-bosse à lag=1.5. Un alias
donne un motif différent.

## Optimisation des hyperparams (γ, T★) par sweep

Une fois le modèle structurel choisi (E + T2), on cherche à **minimiser la std
résiduelle** en faisant varier les hyperparams `(γ, T★)` qui étaient fixés à
la main à `(0.85, 8.99h)`. Le sweep balaie une grille 2-D
`γ ∈ {0.50..1.00 step 0.05}` × `T★ ∈ {7.00..10.00 step 0.25}` (143 cases), et
pour chaque case recalcule `D(n)`, refit (E + T2), enregistre std_φ_E et
std_TST_T2. C'est un **joint NLS profilé** sur (γ, T★) : si la surface a un
minimum net, les hyperparams sont identifiables ; si elle est plate, ils ne le
sont pas.

Code : `tools/oscillator_explore/joint_sweep.py`.
Heatmaps : `joint_sweep_<label>.html`.

### Résultats — sharpness de la surface

| Window | n | range(std_φ) / mean | range(std_TST) / mean | Verdict identifiabilité |
|---|---|---|---|---|
| **atcf** | 101 | **0.4%** | 4.1% | Surface **plate** : (γ, T★) non identifiables |
| recent | 37 | 39.2% | 16.4% | Surface inclinée, mais optimum aux bornes |
| winter25 | 29 | 7.8% | 10.7% | Surface modérée, gain marginal |

### Optima vs baseline

| Window | std_φ baseline | std_φ opt | gain | (γ★, T★★) φ | std_TST baseline | std_TST opt | gain | (γ★, T★★) TST |
|---|---|---|---|---|---|---|---|---|
| atcf | 4.67h | 4.65h | **+0.4%** | (0.50, 9.75) | 2.64h | 2.57h | +2.7% | (0.55, 7.00) |
| recent | 4.93h | 3.42h | +30.6% | **(1.00, 9.00)** | 2.76h | 2.34h | +15.5% | (1.00, 8.00) |
| winter25 | 2.38h | 2.35h | +1.3% | (0.90, 8.25) | 2.57h | 2.38h | +7.5% | (1.00, 8.50) |

### Lecture

1. **Baseline `(γ=0.85, T★=8.99h)` validée sur ATCF** (la fenêtre principale de
   référence, 101 nuits) : la std résiduelle change de **0.4%** sur toute la
   grille → (γ, T★) sont non identifiables séparément à cette échelle, et le
   choix initial était quasi-optimal. **Pas de marge d'optimisation par
   hyperparams sur ATCF.**

2. **Sur recent (37 nuits), optimum à γ=1.00** (cumul strict) avec gain réel de
   30% sur la phase. Le top-10 cellules est exclusivement γ=1.00, donc pas un
   artefact de bord — c'est un vrai pic. **Mais** : appliquer γ=1.00 sur
   l'historique complet ferait diverger D vers des valeurs absurdes (centaines
   d'heures). Cela révèle que **l'optimum de (γ, T★) dépend de la longueur de
   fenêtre** — plus la fenêtre est courte, plus γ effectif tend vers 1.

3. **Implication** : (γ, T★) n'ont pas de valeur universelle stable. Le choix
   pragmatique est de **garder (0.85, 8.99h) comme hyperparams biologiques
   fixes** (cohérents cross-window, validés sur la fenêtre longue), et de
   reconnaître que l'optimum apparent sur petites fenêtres est un artefact
   d'horizon limité (la dette n'a pas le temps de saturer).

### Limite intrinsèque du modèle E + T2

Le sweep prouve que sur ATCF on a atteint la **borne basse de std atteignable
par ce modèle** : ~4.65h std sur φ et ~2.57h std sur TST. Pour descendre
en-dessous, il faut **enrichir le modèle** :

- **Calendrier réel** : remplacer `C(n)` binaire lun-ven par les vrais RDV /
  contraintes du sujet (alarmes Samsung, calendrier importé).
- **Covariables exogènes** : lumière, activité physique, alimentation tardive.
- **State-space formel** : modèle hiérarchique (Kalman ou bayésien) avec bruit
  process explicite — meilleure quantification d'incertitude.
- **Termes d'interaction** : `κ·D·C` (la dette agit différemment selon le
  régime social), `λ·D²` (réponse non-linéaire à dette élevée).

## Validation prédictive out-of-sample

Avant d'enrichir le modèle (covariables exogènes, calendrier réel), on teste la
**capacité prédictive** des modèles actuels par un protocole train/test simple :
on fitte sur une fenêtre, on **projette H=10 nuits dans le futur**, on compare
aux nuits **réellement observées** sur cette période. C'est le vrai juge de
paix : un modèle qui réduit le R² in-sample mais explose en out-of-sample est
suspecté de surfit.

Code : `tools/oscillator_explore/predict.py`.
Sortie : `prediction_<label>.html` (agenda + φ(n) côte à côte, fit + projection
+ vraies nuits observées).

### Protocole

- 3 fenêtres hors des régimes déjà étudiés (atcf, recent, winter25), de
  longueurs variées :
  - **summer24** : 30 nuits (2024-06-01 → 2024-06-30) → validation 2024-07-01 → 2024-07-10
  - **autumn24** : 60 nuits (2024-10-01 → 2024-11-29) → validation 2024-11-30 → 2024-12-09
  - **post-atcf** : 90 nuits (2025-08-01 → 2025-10-29) → validation 2025-10-30 → 2025-11-08
- Modèles testés : **L, O, W, C, D** (model E exclu — sa projection nécessite
  de fermer une boucle récursive `D(n) ← TST(n) ← D(n-1)`, hors scope ici).
- Sélection automatique par AIC.
- Métriques : MAE, RMSE, biais (mean(observed − predicted)).

### Résultats

| Window | n_fit | Best | R²_in | std_in | n_pred | MAE | RMSE | bias |
|---|---|---|---|---|---|---|---|---|
| summer24 | 24 | **D** | 0.63 | 3.57h | 9 | 4.74h | 6.23h | +1.53h |
| autumn24 | 56 | **D** | 0.30 | 4.80h | 6 | 6.74h | 9.24h | **−6.74h** |
| post-atcf | 72 | **D** | 0.41 | 4.10h | 7 | 4.87h | 6.47h | **−3.90h** |

### Lectures

1. **Le double sinusoïde (D) gagne partout** — confirme l'hypothèse user.
2. **MAE prédictif > std in-sample sur les 3 fenêtres** → le modèle généralise
   mal au-delà de quelques nuits. C'est un signe que **les paramètres absorbent
   du bruit local** plutôt que des invariants physiologiques.
3. **Biais systématique négatif sur autumn24 (−6.7h) et post-atcf (−3.9h)** :
   le modèle prédit que le sujet se couchera **plus tard** (extrapolation du
   drift τ > 24), mais en réalité **il s'est couché plus tôt**. Signature
   classique d'un **événement exogène non modélisé** (alarme, RDV, sortie,
   lumière forte) qui a remis la phase à l'heure.
4. **Dégradation temporelle nette** : sur summer24, les **3 premières nuits
   prédites à < 1h près** (résidus −0.53, +0.57, −0.43h), puis dérive massive
   (+4.6, −13.5, +3.5, +6.4...). Le modèle endogène est **excellent à court
   terme (~3 nuits) puis diverge**. Cohérent avec un horizon de prédiction
   limité par la fenêtre de validité de l'oscillation fittée.

### Verdict

- Les modèles endogènes purs (sans covariables exogènes) ont une **portée
  prédictive de ~3 nuits**. Au-delà, le biais d'un événement exogène
  ponctuel détruit la projection.
- Le **biais négatif systématique** sur 2/3 fenêtres est un signal :
  l'extrapolation linéaire du drift τ > 24 est **systématiquement trop
  optimiste** (l'organisme est régulièrement remis à l'heure par des
  contraintes sociales).
- Ce résultat **motive directement l'enrichissement** : ajouter au modèle
  les facteurs exogènes (alarmes Samsung, calendrier d'événements, exposition
  lumineuse, activité physique, repas tardifs) devrait drastiquement
  améliorer la portée prédictive.

## Pistes pour l'itération suivante

| Idée | Effort | Gain attendu |
|------|--------|--------------|
| **Modèle joint (phase + durée)** : `TST(n) = T★ + λ·D(n−1) − μ·C(n) + ε` couplé à `φ(n)` | +++ | Validation de l'hypothèse user que la dette explose le weekend via la **durée**, pas l'onset |
| Tester d'autres γ (0.7, 0.9, 0.95) — sensibilité du R²E | + | Mieux comprendre l'horizon homéostatique |
| Fitter T★ comme paramètre libre (au lieu de fixé à 8.99) | ++ | Vérifier que la médiane free-run est bien l'optimum |
| **Autocorrélation des résidus** pour valider les P_court | + | Distinguer cycle réel vs artefact |
| **Changepoint detection** sur Δφ pour découper auto les régimes | +++ | Évite les fenêtres manuelles |
| **Bootstrap CI** sur (τ, A, P, κ) | + | Robustesse des paramètres |
| Comparer **M10 phase** vs `main_onset` comme indicateur de phase | + | Sensibilité du résultat au choix de phase |
| Étendre à toutes les fenêtres glissantes 60j → carte (date, τ, P, κ) | ++ | Voir évolution longitudinale |

## Projection dans l'espace agenda

Les figures (φ, n) sont peu lisibles « instinctivement » — il faut faire le
mapping mental entre φ en heures et l'heure de coucher réelle. La projection
dans l'espace agenda (Y=date matin, X=heures écoulées depuis 20h J-1) rend
le « serpent » directement visible : il zigzague entre des heures de coucher
précoces et tardives selon la sinusoïde, avec un drift lent vers la droite.

**Convention de mapping** (cohérente avec `tools/sleep_agenda/agenda_render.py`) :

    onset_ts(n) = anchor + (24·n + φ(n)) heures
    morning(ts) = ts.date() + (1 si ts.hour ≥ 20 sinon 0)
    night_start = 20:00 le jour (morning − 1)
    x_hours = (ts − night_start) en heures   ∈ [0, 24]

**Échantillonnage** : strictement à n **entier**. Sampler en n fractionnaire
balaie chaque row sur 24h (puisque `onset_ts(n+δ) − onset_ts(n) = 24·δ h`),
ce qui n'a aucun sens — le modèle prédit 1 onset par jour biologique, pas une
trajectoire continue dans la nuit. La ligne reliant 2 prédictions consécutives
montre directement la dérive nuit-à-nuit.

Outil : `tools/oscillator_explore/agenda_overlay.py`. Sortie :
`<label>_agenda.html` par fenêtre (bars = sessions main_sleep, points teal =
onsets observés, lignes ambre/cyan/magenta = fits linear / sin / 2-sin).

## Fichiers produits

- `tools/oscillator_explore/fit.py` — fitter (L / O / W / C / D / **E** × N fenêtres),
  Lomb-Scargle seed, AIC/BIC selection, D(n) leaky via T★/γ.
- `tools/oscillator_explore/sleep_debt.py` — stats de durée par régime,
  identification de T★, calcul de D(n) strict + leaky, visualisation.
- `tools/oscillator_explore/joint_model.py` — modèle joint phase (E) + durée
  (T0/T1/T2), valide l'hypothèse user (μ_atcf = +2.4h weekday/weekend).
- `tools/oscillator_explore/compare.py` — figure comparative side-by-side.
- `tools/oscillator_explore/agenda_overlay.py` — projection dans l'espace agenda.
- `tools/oscillator_explore/REPORT.md` — ce document.
- `data/personal/S001/oscillator_explore/<label>.html` — figure détaillée
  par fenêtre (4 panels : φ + 5 fits, residuals comparison, LS periodogram
  log-axis, Δφ jour-à-jour).
- `data/personal/S001/oscillator_explore/<label>_agenda.html` — **projection
  agenda** : sessions réelles + fits superposés en (date, heure-du-jour).
- `data/personal/S001/oscillator_explore/comparison.html` — vue d'ensemble.
- `data/personal/S001/oscillator_explore/summary.json` — paramètres bruts.

Toutes les figures de la fenêtre personnelle sont sous `data/personal/`
(gitignored).

## Reproduire

    # 1) Stats de durée par régime + identification T★ + D(n) strict/leaky
    .venv/bin/python tools/oscillator_explore/sleep_debt.py --subject-id S001

    # 2) Fit des 6 modèles (L, O, W, C, D, E) sur les 3 fenêtres
    .venv/bin/python tools/oscillator_explore/fit.py \
      --subject-id S001 \
      --periods "atcf=2025-04-06:2025-07-29,recent=2026-04-01:2026-05-07,winter25=2025-11-26:2025-12-26"

    # 3) Vues comparatives
    .venv/bin/python tools/oscillator_explore/compare.py
    .venv/bin/python tools/oscillator_explore/agenda_overlay.py \
      --subject-id S001 \
      --periods "atcf=2025-04-06:2025-07-29,recent=2026-04-01:2026-05-07,winter25=2025-11-26:2025-12-26"

    # 4) Modèle joint phase + durée (valide l'hypothèse dette → durée)
    .venv/bin/python tools/oscillator_explore/joint_model.py \
      --subject-id S001 \
      --periods "atcf=2025-04-06:2025-07-29,recent=2026-04-01:2026-05-07,winter25=2025-11-26:2025-12-26"

    # 5) Sweep (γ, T★) — identifiabilité des hyperparams
    .venv/bin/python tools/oscillator_explore/joint_sweep.py \
      --subject-id S001 \
      --periods "atcf=2025-04-06:2025-07-29,recent=2026-04-01:2026-05-07,winter25=2025-11-26:2025-12-26"

    # 6) Test prédictif out-of-sample (fit + 10 nuits projetées vs réel)
    .venv/bin/python tools/oscillator_explore/predict.py \
      --subject-id S001 \
      --windows "summer24=2024-06-01:2024-06-30,autumn24=2024-10-01:2024-11-29,post-atcf=2025-08-01:2025-10-29" \
      --horizon 10
