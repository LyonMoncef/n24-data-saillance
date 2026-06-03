# Comment on calcule chaque point sur l'agenda ?

Document de vulgarisation — base pour un post LinkedIn grand public.
Décrit le modèle mathématique derrière la projection des courbes paramétriques
sur l'agenda du sommeil produite par `tools/oscillator_explore/agenda_overlay.py`.

---

## La question qu'on pose

Pour chaque nuit, on cherche **à quelle heure ton corps va vouloir s'endormir**.
Le modèle est censé répondre.

## L'idée centrale en une phrase

> Ton heure d'endormissement, ce soir, c'est : **un point de départ** + **une dérive régulière** + **une vague qui oscille**.

Mathématiquement, en notant `n` le numéro de la nuit (jour 0, jour 1, jour 2, ...) :

```
Heure prédite(nuit n) =  α · n  +  β  +  A · sin(2π · n / P + ψ)
                         ↑         ↑     ↑
                    dérive lente  base   vague qui zigzague
```

(le résultat est en heures, à compter d'un instant zéro qu'on a choisi —
typiquement midi du premier jour de la fenêtre.)

## Décodage de chaque ingrédient

### **α (alpha) — ta dérive quotidienne**

Combien de minutes tu te couches **plus tard chaque jour** que la veille.

- Dormeur "normal" : α ≈ 0 (tu te couches à la même heure tous les soirs)
- N24 en free-run : α ≈ +24 min/jour (chaque soir, 24 min plus tard que la veille)
- N24 cadré par le travail : α ≈ 0 (la contrainte sociale écrase le rythme)

C'est lié au fameux **τ (tau)** : ta période interne = 24h + α. Si α = 0.4h,
ton horloge biologique tourne sur des journées de **24h24** au lieu de 24h.

### **β (beta) — ton point de départ**

Juste l'heure prédite pour la toute première nuit de la fenêtre. C'est un
ajustement technique, pas une grandeur biologique.

### **A (amplitude) — la hauteur de la vague**

De combien d'heures ton endormissement peut osciller **autour de** la dérive
régulière.

- A = 1h : la vague te fait t'endormir 1h plus tôt ou 1h plus tard que ce que
  prédit la simple dérive
- A = 3h : les écarts sont 3 fois plus gros

### **P (période) — la durée d'un cycle de la vague**

Tous les combien de jours la vague revient au même point.

- P = 3 jours : un aller-retour complet en 3 jours (zigzag rapide)
- P = 12 jours : un aller-retour complet en 2 semaines (vague longue)

### **ψ (psi) — où tu démarres dans la vague**

Imagine la vague comme un ressort enroulé. ψ dit "à quel cran du ressort on
est au jour 0". Pas de signification biologique, c'est juste pour caler la
phase.

## Exemple concret : fenêtre nov-déc 2025 (régime free-run)

Le modèle a trouvé :

- **α = 0.4 h/jour** → 24 min de retard chaque jour
- **A = 2.8 h** → la vague te bouge ton endormissement de ±2h48
- **P = 3.2 jours** → un zigzag complet tous les 3 jours

Traduit en humain :

> *"Mon corps tourne sur une journée de 24h24 — donc je me couche 24 min plus
> tard chaque jour en moyenne. ET, par-dessus, je fais des micro-zigzags : un
> soir je m'endors à 21h30, deux jours après c'est plutôt 02h30, puis ça
> revient. La moyenne, elle, glisse lentement vers les heures tardives."*

C'est exactement ça qu'on voit sur l'agenda : les points zigzaguent
verticalement en haut/bas tous les 3 jours, tout en dérivant doucement vers
la droite (de plus en plus tard) au fil des semaines.

## Et la projection sur l'agenda, comment ça marche ?

Une fois qu'on a "à quelle heure depuis le repère tu vas t'endormir cette
nuit-là" (un nombre en heures, genre 380h pour la nuit n°15), on fait **deux
conversions** :

### 1. Quelle date ?

On ajoute ces 380h au repère (midi jour 0). On obtient une date + une heure
réelles (genre "le 21 avril à 18:00").

- Si l'heure est **avant 20h** → la nuit s'attache à **ce jour-là** (la nuit
  du 20 au 21).
- Si **après 20h** → la nuit s'attache au **jour suivant** (la nuit du 21
  au 22).

→ c'est ça qui détermine sur **quelle row** le point se place.

### 2. Quelle position horizontale ?

L'axe X de l'agenda va de 20h à 20h le lendemain. On regarde simplement combien
d'heures se sont écoulées depuis 20:00 la veille → ça donne un nombre entre 0
et 24 qui place le point quelque part sur la row.

Exemple : endormissement prédit à 02:30 → x = 6.5 (parce que 02:30 = 6h30
après 20:00). Endormissement à 22:00 → x = 2.

## Pourquoi le modèle "double sinusoïde" devient intéressant

Sur la fenêtre d'avril 2026, le modèle a trouvé **deux** vagues superposées :

- Une vague rapide : P=2.5 jours, A=2h
- Une vague lente : P=12 jours, A=5h (!)

C'est comme si le rythme avait **deux rythmes en même temps** : une petite
oscillation jour-à-jour, et une grosse marée de fond qui balance la phase sur
2 semaines. Sans le double modèle, on confond les deux et on estime mal τ.
Avec, on voit la structure réelle.

---

## En résumé

Chaque point sur l'agenda est le résultat d'un calcul :

1. Le modèle dit "voici à quelle heure (en chiffres) on prédit l'endormissement
   de la nuit n°15".
2. On convertit ce chiffre en (date, heure-du-jour) selon les conventions de
   l'agenda (nuit = fenêtre 20h → 20h le lendemain).
3. On place le point sur l'image.

Le **τ** te dit la vitesse de fond à laquelle ton rythme dérive. Les **A** et
**P** te disent comment ton rythme zigzague autour de cette dérive. Et la
projection sur l'agenda rend ces équations directement lisibles sur ton
calendrier de sommeil réel.

## Limites du modèle actuel (ce qu'on n'a pas encore capturé)

- **La dette de sommeil** : quand on est contraint par le travail, on cumule
  une dette en semaine qu'on rembourse le weekend. Le modèle sinusoïde simple
  rate complètement ce mécanisme (la bascule est brutale, pas oscillante).
- **La durée idéale de sommeil** : le modèle prédit l'heure de **coucher**,
  pas la durée. Or la durée dépend de la dette accumulée.
- **Les régimes mixtes** : on a testé sur 3 fenêtres pré-découpées, mais
  identifier automatiquement les transitions free-run ↔ contraint reste à
  faire.

Ces limites sont l'objet des prochaines itérations.
