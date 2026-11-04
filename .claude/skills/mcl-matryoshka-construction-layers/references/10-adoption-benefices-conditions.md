# 10 — Adopter MCL en équipe, bénéfices et conditions

Source : III.15, III.16, III.17. À lire quand l'utilisateur veut introduire MCL dans une équipe, convaincre,
ou décider s'il s'engage.

## Sommaire
1. Désir, connaissance, capacité, renforcement
2. La séquence d'adoption et les trois profils d'entrée
3. Quatre objections prévisibles
4. Ce que MCL apporte au praticien (six bénéfices)
5. Ce qui conditionne le bénéfice (quatre conditions)

---

## 1. Les quatre leviers

Le déficit d'adoption d'une méthode est presque jamais un déficit de connaissance : c'est un déficit de
**désir** (pourquoi changer ce qui livre déjà) et de **capacité** (comment tenir le protocole sous pression).

- **Désir.** Trois vérités à établir d'emblée :
  1. rien de la **cadence de livraison** ne change (tranches, sprint, démo restent ; ce qui change est la
     construction *dans* la tranche) ;
  2. les premiers bénéfices sont **développeur** : échec au gate localisé au dernier delta (fin de la chasse chez
     soi du bug de quelqu'un d'autre), moins de doublures à écrire, des suites qui survivent au refactoring ;
  3. l'entrée se fait par un **pilote volontaire** à l'échelle d'une tranche, où les étapes 1 à 4 tiennent en
     minutes. **Jamais par mandat** : l'adoption imposée fabrique du rejet durable.
- **Connaissance.** Le document de référence, plus une progression pour les nouveaux venus (Partie V, absente
  de la source). Pour les praticiens confirmés, le discours change : l'échafaudage cognitif ne leur apporte
  rien ; la vérification mécanique et la coordination, si.
- **Capacité.** Portée par l'outillage, dans cet ordre : carte encodée et gate en mode **warn** d'abord
  (apprendre les signaux sans bloquer), puis **strict** règle par règle ; baseline et cliquet sur l'existant ;
  checkpoints adossés aux rituels existants (rétrospective, refinement) ; rôles de gouvernance introduits au fil
  de l'extension, le gardien étant d'abord l'initiateur du pilote.
- **Renforcement.** Les traces rendent le bénéfice visible (historique des défigeages, métriques du gate :
  `mcl.py rapport`). Réalisme : l'adhérence aux protocoles stricts **non outillés** s'effondre en pratique ;
  ici la discipline est portée par l'enforcement plutôt que par la volonté. **N'exiger en strict que ce que le
  build vérifie.**

## 2. La séquence

Pilote sur une tranche avec un binôme volontaire → warn sur le périmètre pilote → extension par flux → strict
progressif → échelles supérieures (composant, puis composite pour les systèmes neufs). **Jamais l'inverse.**

Profils d'entrée :
- **Solo** : le pilote est soi-même ; le warn est inutile ; les traces suffisent.
- **Équipe de quatre à dix** : pilote en binôme, puis extension par tranches.
- **Organisation** : pilote par équipe-flux, gardien institutionnel, warn-then-strict par service, baseline par
  dépôt.

## 3. Quatre objections prévisibles

| Objection | Réponse |
|---|---|
| « Le gel, c'est rigide. » | Le gel porte sur le contrat ; l'implémentation reste révisable sous harnais. |
| « Le gate, c'est du flicage. » | Il protège l'auteur : la localisation au dernier delta travaille pour lui. |
| « Encore une méthode. » | La cadence ne change pas ; ce qui change est la construction dans la tranche. |
| « Nos couches ne sont pas vos couches. » | Exact : ici une couche est une profondeur de dépendance dans la tranche, pas une strate technique, et jamais un découpage d'équipe. |

## 4. Ce que MCL apporte au praticien

1. **Un ordre de construction, là où l'architecture n'en donnait pas** : Clean, Onion, Hexagonal disent où
   placer chaque chose, aucune ne dit par quoi commencer un lundi matin ; MCL donne la direction et un critère
   de passage à chaque couche.
2. **Un protocole dont les pièces se tiennent** : la carte de l'étape 4 sert quatre fois (plan de construction,
   règle de build, liste des consommateurs pour tout arbitrage, repérage des groupes parallélisables) ; le gel
   sert trois fois (localisation des défauts, révision sous harnais, base de l'extension additive). La
   cartographie ne se paie qu'une fois.
3. **Un savoir d'expert devenu procédure** : un junior peut suivre le protocole dès la première semaine ; sa
   production est vérifiable étape par étape plutôt qu'à la livraison.
4. **Une architecture que le build défend** : plus de dérive silencieuse entre schéma et code, plus de
   discussion en revue sur un import qui n'aurait pas dû exister ; le build tranche.
5. **Des traces qui répondent aux questions** : « pourquoi ce contrat a-t-il changé », « où en est la dette »,
   « combien de fois avons-nous cassé la couche 2 », sans reconstitution après coup.
6. **Une couverture des cas qui font décrocher les autres** : machines à états, domaines événementiels, grands
   domaines à contextes multiples, dépendances circulaires, applications entières.

## 5. Ce qui conditionne le bénéfice

1. **L'artefact doit passer le test d'applicabilité** ; sur un artefact exploratoire, carte fictive et
   défigeages en chaîne. Sonder d'abord.
2. **L'économie de doublures dépend de la topologie** : pleine sur logique interne dominante ; marginale sur un
   service d'intégration fait surtout de frontières externes.
3. **Le contrat spéculatif reste le risque propre de la méthode** (trois remparts + checkpoint ; risque
   structurellement plus élevé qu'en approche pilotée par le consommateur réel).
4. **Le gate a un prix qui croît** (quadratique en nombre de couches ; le régime à deux vitesses le contient sans
   le supprimer ; sur une application en couches globales il devient prohibitif — raison de plus pour le
   composite).
