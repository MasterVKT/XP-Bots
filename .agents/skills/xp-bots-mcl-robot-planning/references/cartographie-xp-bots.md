# Cartographie MCL proposée pour XP-Bots

Statut : **hypothèse dérivée** des spécifications 3.1.0 et de la stack « robot de trading » de
`.agents/skills/mcl-matryoshka-construction-layers/references/09-stacks-composite-positionnement.md` (section 2).
Elle accélère la phase 1 ; elle ne la remplace pas. Chaque unité repasse la question-test et `mcl.py analyser`
tranche les profondeurs réelles. Les noms d'unités sont des identifiants de carte, pas des noms de code imposés.

## 1. Squelette du mode composite (outside-in, hors protocole MCL)

Chemin minimal de bout en bout, en code de production destiné à durer et déployable dès le départ :

```
ticks rejoués (fixture) -> bougie M15 -> stratégie neutre (NO_SETUP) -> coordinateur (refus explicite)
-> exécution papier -> journal C09 (motif de refus)
```

- Sa CI est son gate : suite du robot plus `python tools/verify_project.py`.
- Chaque composant ci-dessous est un artefact de chair distinct (`mcl/<artefact>/`), branché en remplaçant le
  segment minimal correspondant ; modifier un contrat du squelette est un changement de contrat tracé.
- Ordre de livraison (niveau produit) : section « Ordre de construction et de qualification » du guide
  d'implémentation. Ordre de construction à l'intérieur d'un artefact : uniquement le graphe de dépendances.

## 2. Artefacts, unités candidates et frontières

### A. `london-donnees-temps` — temps, bougies et indicateurs (C03)

| Unité | Responsabilité | Dépend de | Couche proposée |
|---|---|---|---|
| `Instant` | Représenter un horodatage UTC à la milliseconde avec ordre stable des égalités | — | 0 |
| `Tick`, `Bougie` | Représenter un tick Bid/Ask et une bougie Bid OHLC d'intervalle `[T, T+durée)` | `Instant` | 0 |
| `parametres_techniques` | Charger et valider le bloc `common` de `config/parametres_figes_v3.json` | — | 0 |
| `sessions_londres` | Calculer fenêtres, jours Londres, jour UTC et blackout de rollover via `Europe/London` | `Instant`, `parametres_techniques` | 1a |
| `constructeur_bougies` | Agréger les ticks en M15 et H1 clôturées, rattacher le tick de frontière, signaler les trous | `Tick`, `Bougie` | 1b |
| `indicateurs` | Calculer EMA (graine SMA), RSI et ATR Wilder, TR et `A_t` = ATR de t−1 | `Bougie` | 1c |
| `etat_indicateurs` | Précharger 1 000 M15 et 300 H1, persister les états récursifs, reprendre au redémarrage | `indicateurs`, `stockage` | 2 |

Frontières : flux de ticks du courtier, horloge, stockage d'état. Doublures : flux rejoué depuis fixture,
horloge contrôlée, stockage en mémoire.

### B. `moteur-ema` — méthode S01

| Unité | Responsabilité | Dépend de | Couche proposée |
|---|---|---|---|
| `parametres_ema` | Charger et valider le bloc `ema` de la configuration figée | — | 0 |
| `tendance_ema` | Évaluer l'ordre EMA15/25/50 et la pente EMA50 sur 4 bougies (S01.1) | `parametres_ema` | 1a |
| `bougie_reprise` | Tester la bougie de reprise : corps directionnel, RSI, clôture dans les 35 % favorables, TR (S01.3) | `parametres_ema` | 1b |
| `stop_objectif_ema` | Calculer buffer, `B_SL`, refus au-delà de 2,50 A et multiple 1,5 (S01.4) | `parametres_ema` | 1c |
| `machine_etats_ema` | Gérer armement, contact, repli de 1 à 8 bougies, cooldown, position possédée, compteur journalier (S01.2) | `tendance_ema`, `bougie_reprise` | 2 |
| `moteur_ema` | À chaque clôture admissible, produire un signal (sens, `B_SL`, référence d'ATR) ou un motif technique, puis appliquer l'issue reçue (fill ou refus définitif) à l'état | `machine_etats_ema`, `stop_objectif_ema` | 3 |

La machine à états forme une composante fortement connexe : la condenser en une couche et la faire croître
transition par transition (référence MCL 03, systèmes non-flux). Types de bougie, sessions et indicateurs
viennent de l'artefact A, déjà figé. Permissions fondamentales, veto IA, cotation et dimensionnement sont
appliqués par le coordinateur au point d'insertion A07 : le moteur reste indépendant et ne connaît que l'issue.

### C. `moteur-london` — méthode S02

| Unité | Responsabilité | Dépend de | Couche proposée |
|---|---|---|---|
| `parametres_london` | Charger et valider le bloc `london` | — | 0 |
| `range_londres` | Construire le range des 20 M15 de 02:00 à 06:45 Londres et sa validité (S02.1) | `parametres_london` | 1a |
| `gel_atr_h1` | Figer `A_H1` à 07:00 avec son heure réelle de disponibilité (S02.1) | `parametres_london` | 1b |
| `bougie_cassure` | Tester cassure, buffer, corps 40 %, clôture 65 % et TR (S02.3) | `parametres_london` | 1c |
| `stop_local_london` | Calculer le stop à trois composantes et le multiple 2 (S02.4) | `parametres_london` | 1d |
| `quotas_london` | Compter deux entrées par jour et une par sens au premier fill non nul (S02.4) | `parametres_london` | 1e |
| `moteur_london` | Combiner range admissible, fenêtre 08:00–11:00, cassure, stop et quotas ; appliquer l'issue reçue sans consommer le quota sur un refus | unités 1a à 1e | 2 |

### D. `execution-coordinateur` — C06 à C09

| Unité | Responsabilité | Dépend de | Couche proposée |
|---|---|---|---|
| `profil_instrument`, `cotation`, `intention` | Types : caractéristiques C04, cotation Bid/Ask, clé d'intention persistante (C08) | — | 0 |
| `garde_cotation` | Contrôler âge, croisement, plafond de spread, écart d'entrée et TTL (C06) | `cotation` | 1a |
| `prix_executables` | Convertir `B_SL`, choisir E et calculer TP avec arrondis au tick (C06) | `cotation`, `profil_instrument` | 1b |
| `gardes_compte` | Suivre base quotidienne UTC et pic de fonds propres, arrêts persistants (C07) | `stockage` | 1c |
| `risque_all_in` | Calculer la perte pessimiste et les frais pour un volume (C07) | `prix_executables`, `calcul_courtier` | 2 |
| `registre_reservations` | Réserver et libérer le risque de façon atomique et persistante (C07, C08) | `intention`, `stockage` | 2 |
| `dimensionnement` | Retenir le plus grand volume admissible sous les cinq contraintes (C07) | `risque_all_in`, `registre_reservations`, `gardes_compte` | 3 |
| `arbitrage` | Appliquer priorités LONDON avant EMA puis ordre des symboles, une position par sous-jacent (C08) | `registre_reservations` | 3 |
| `cycle_ordre` | Envoyer l'ordre protégé, gérer accusé ambigu, rapprochement, fill partiel, protections (C08) | `dimensionnement`, `execution_courtier` | 4 |
| `sorties_obligatoires` | Déclencher la première échéance de sortie et les clôtures prioritaires (C08) | `cycle_ordre`, `sessions_londres` | 5 |
| `coordinateur` | Ordonner les traitements de C08 (fondamental et calendrier, puis contexte IA au point A07, puis cotation, stop, taille et marge) et journaliser chaque décision (C09) | toutes les unités ci-dessus, `permissions`, `contexte_ia`, `journal` | 6 |

Frontières : exécution du courtier, fonctions de calcul du courtier, horloge, stockage et journal. Doublures :
courtier simulé déterministe (accusés, refus, fills partiels, timeouts scénarisés), stockage en mémoire.

### E. `controles-fondamentaux` — C05

| Unité | Responsabilité | Dépend de | Couche proposée |
|---|---|---|---|
| `message_permission` | Valider un message `fundamental-permission-v1` et ses heures | `Instant` | 1a |
| `etat_permissions` | Conserver la dernière permission valide par symbole, séquence et expiration | `message_permission` | 2 |
| `garde_annonces` | Contrôler fraîcheur et couverture du calendrier, fenêtres HIGH par devise | `Instant` | 1b |
| `permissions` | Combiner direction, état de risque et annonces en autorisation ou motif de refus | `etat_permissions`, `garde_annonces` | 3 |

Frontières : fournisseur fondamental externe, calendrier d'annonces, horloge. Doublures : messages et
calendriers scénarisés avec `known_at`.

### F. `contexte-ia` — lecture du snapshot (A07, A10, A12)

| Unité | Responsabilité | Dépend de | Couche proposée |
|---|---|---|---|
| `snapshot` | Valider schéma, hash canonique, taille, séquence, âge et horodatages | `Instant` | 1 |
| `cache_vetos` | Conserver les vetos validés jusqu'à leur échéance propre, au redémarrage compris | `snapshot`, `stockage` | 2 |
| `contexte_ia` | Rendre `BLOCK` ou `NEUTRAL` pour un symbole et un instant, jamais `ALLOW` | `cache_vetos` | 3 |

Frontière : fichier d'IPC du snapshot. Comparaison : `overlay_decision` de `reference/llm_contracts.py`.

### G. `service-ia` — A04 à A11

Unités candidates : collecte RSS et normalisation (A04), borne de tokens (A09), validateur de sortie (A05),
constructeur d'événement de veto (A06), registre de budget transactionnel (A09), routeur de fournisseurs
(A08), écrivain atomique de snapshot (A10), planificateur des travaux (A09), point d'entrée du service.
Frontières : API Groq, Gemini et OpenAI, flux RSS officiels, SQLite, système de fichiers, horloge ; aucune
inférence locale. Comparaison : `reference/llm_contracts.py`.

### H. `journal-rejeu` — C09, C10, A13

Unités candidates : enregistrements du journal (C09), simulateur d'exécution de référence et de stress (C10),
métriques (espérance, profit factor, drawdown de fonds propres, rétention, fréquence), bootstrap de blocs,
exécuteur de deux portefeuilles A/B. Le simulateur implémente le port d'exécution : le même moteur de décision
sert au rejeu et à la plateforme.

## 3. Affectation des cas d'acceptation

| Cas | Artefact | Catégorie de test |
|---|---|---|
| C11.1 bougie future sans effet, H1 partielle invisible | A, puis B et C | 1 puis 2 |
| C11.2 égalités : spread au plafond, TTL, fin de fenêtre, EMA égales | D, B, C | 1 |
| C11.3 tick de frontière | A | 1 |
| C11.4 changement d'heure, jours UTC et Londres, aucun dimanche | A, B, C | 1 et 2 |
| C11.5 Ask d'entrée et Bid de sortie, spread compté une fois | D | 1 |
| C11.6 volume minimal au-delà du budget refusé | D | 1 |
| C11.7 frais non linéaires, réserve, marge cumulée, positions externes, micro | D | 1 et 2 |
| C11.8 permissions expirées, futures, incompatibles ; FLATTEN prioritaire | E, puis D | 1 puis 2 |
| C11.9 annonce : début inclus, fin exclue ; calendrier révisé | E | 1 |
| C11.10 signaux simultanés des deux robots | D avec B et C | 2 |
| C11.11 fill partiel, timeout ambigu, redémarrage, position inconnue | D | 1 et 2 |
| C11.12 gap au stop, SL et TP simultanés, flux absent à la sortie | D et H | 2 |
| C11.13 arrêts quotidiens et globaux, durée maximale | D | 1 et 2 |
| C11.14 égalité moteur de référence et robot de plateforme | H avec B ou C | 2 |
| S01.6 | B | 1 et 2 |
| S02.6 | C | 1 et 2 |
| A14 | F et G, insertion dans B et C | 1 et 2 |

## 4. Gate de chaque couche

- Catégorie 1 : tests du contrat propre de la couche, frontières externes doublées.
- Catégorie 2 : jonction de la couche sur le bloc réel `{0 → k}`, chemins représentatifs, sans doublure interne.
- Régression intégrale : toute la suite du robot, puis `python tools/verify_project.py`.
- Commande : `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/<artefact> gate --couche <id> --unitaire "<cat. 1>" --integration "<cat. 2>" --regression "<suite intégrale>"`,
  puis `figer --couche <id>` sans rien modifier entre les deux.
