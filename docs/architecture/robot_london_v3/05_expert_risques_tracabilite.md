# 05 — Regard d'expert M15, risques et traçabilité

Retour au [plan directeur](README.md).

## 1. Lecture d'expert M15

Lecture appliquée par la skill `anthropic-skills:expert-scalper-m15` (scalpeur M15 sur paires majeures, analyse
descendante, risque d'abord). Elle sert à **éprouver l'implémentation** et à **choisir ce qu'il faut mesurer**.
Les règles V3 figées prévalent : aucune remarque ci-dessous ne modifie une règle, un seuil ou un coût. Une idée
d'amélioration devient au plus une hypothèse de recherche versionnée (A11 : trois par mois au plus pour tout le
projet, testée hors marché, jamais sur le test réservé).

### 1.1 S02 face au setup discrétionnaire « London Open Breakout »

| Élément | Pratique discrétionnaire courante | Règle V3 figée | Conséquence pour le robot |
|---|---|---|---|
| Range de référence | Range asiatique, éviter les ranges trop larges ou trop étroits en pips | `[02:00, 07:00)` Londres, largeur normalisée par l'ATR H1 figé (`range_min_h1_atr`, `range_max_h1_atr`) | Normalisation systématique ; rapport A11 par tranches de W/A_H1 |
| Déclencheur | Clôture M15 franche hors du range (corps, pas mèche) | Clôture au-delà du niveau plus buffer, corps et position de clôture minimaux, fenêtre 08:00–11:00 Londres | Prédicats exacts ; mesurer l'heure de première cassure |
| Entrée | Au close ou sur retest | Au marché après la clôture, TTL de 5 s, aucun retest, aucun ordre stop en attente | Aucune logique de retest ni d'ordre en attente |
| Stop | Autre côté de la borne cassée plus quelques pips | Stop local à trois composantes (bougie, intérieur du range, plancher ATR) | Stops plus proches, possiblement plus souvent touchés : journaliser la composante contraignante |
| Objectif | Hauteur du range ou niveau H1 | 2 D depuis l'entrée réelle | Objectif fixe, aucune sortie partielle |
| Gestion | Break-even, partiel, trailing | Interdits | Ne jamais les ajouter |
| Sortie temporelle | Quelques bougies sans progression | `max_position_wallclock_seconds` ou 12:00 Londres | Cohérent |
| Biais de plus haute unité | Biais H4 ou D1 | Aucun filtre directionnel ; la direction relève du fondamental externe (C05) | Mesurer l'effet propre du fondamental (exigé par C10) |
| Fausse première cassure | Attendre le piège puis l'impulsion opposée | Non filtrée | Taux de retournement après première cassure dans le rapport A11 ; hypothèse de recherche possible |
| Annonces | Rester à plat autour des publications majeures | Fenêtre HIGH `[N − 900 s, N + 900 s)`, clôture à N − 900 s | La table d'importance du calendrier détermine la couverture réelle |
| Spread | Un élargissement anormal signale une fuite de liquidité | Plafonds absolus par symbole | Spread journalisé à chaque tentative |
| Corrélation EURUSD et GBPUSD | Ne pas empiler deux positions corrélées | Deux positions possibles, réserve totale bornée par `account_max_initial_reserved_risk_fraction` | Exposition connue ; rapport des trades simultanés ; aucune règle ajoutée |
| Lundi matin, vendredi | Prudence | Aucun filtre | Ventilation par jour de semaine |
| Score de confluence | Grille A+ à C | Interdit (« pas de score de confluence ») | Ne jamais introduire de score |
| Risque | 0,5 à 1 % par trade | `risk_fraction_per_entry`, sans martingale ni augmentation après perte | Aligné |

### 1.2 Pièges d'exécution à instrumenter

1. **Ouverture de Londres** : le spread peut s'élargir à 08:00 et autour des publications européennes ; compter
   les refus `SPREAD_CAP` par heure locale.
2. **Calendrier** : publications britanniques à 07:00 Londres (avant la fenêtre), européennes et allemandes entre
   08:00 et 10:00 Londres (dans la fenêtre) ; seule la table d'importance HIGH décide du blocage : la faire
   relire par l'humain au moment de D-12.
3. **Banques centrales** : une décision de la BoE à 12:00 Londres ouvre la fenêtre à 11:45 et ferme GBPUSD plus
   tôt (scénario L-14) ; une décision BCE à 13:15 heure de Paris tombe à 12:15 Londres, après la sortie forcée.
4. **Lundi** : le range du lundi se forme après la réouverture du dimanche soir ; la validité de ses bougies
   (couverture, au moins un Bid) est contrôlée comme les autres jours.
5. **Jours fériés britanniques et fêtes de fin d'année** : marché ouvert mais liquidité réduite ; aucune règle
   ajoutée ; les séances natives du courtier et la validité des données font foi.
6. **Glissement au stop** sur une cassure rapide : la réserve g dimensionne, elle ne garantit rien (C07) ;
   comparer le glissement réel de démonstration au modèle C10.
7. **Volume minimal à 100 USD** : avec 1 000 unités, la plupart des stops dépassent le budget (S02.5) ; la
   disponibilité réelle de contrats micro sur le compte standard est décisive (phase 13.1).

### 1.3 Diagnostics attendus du rapport A11 London

Par symbole, sur les seuls journaux du robot : performance et effectifs par tranche de W/A_H1, par heure de
première cassure, par sens, par composante contraignante du stop, par jour de semaine ; coût par trade ;
nouveaux signaux après un veto ; gagnants bloqués et opportunités devenues tardives ; ratio de remplissage ;
taux de retournement après première cassure ; refus par motif et par heure. Les gains déjà dus à la garde
d'annonces ou au stop technique ne sont pas attribués au LLM.

### 1.4 Garde-fous

Le scalping de change est une activité à haut risque. Ce plan est de l'ingénierie et de l'analyse technique
éducative, pas un conseil financier ; il ne promet aucune rentabilité. Toute stratégie passe par le rejeu, la
démonstration prospective, puis une décision humaine. Rester sans position est un résultat légitime ; aucune
logique de martingale, de revanche ou d'augmentation du risque après pertes n'est admise.

## 2. Registre des risques

| Id | Risque | Effet | Traitement | Phase |
|---|---|---|---|---|
| R-01 | Base horaire des ticks MT5 ambiguë (UTC ou heure du serveur) | Bougies et sessions décalées, décisions fausses | Table de conversion versionnée (document 08, §5) dès la phase 11 ; sonde S-01 ; refus du flux non qualifié | 11, 13.1 |
| R-02 | `order_send` bloquant, appels concurrents non garantis | Accusé ambigu, rapprochement retardé | Exécutant dédié avec délai dès la phase 11 ; sonde S-06 ; repli documenté | 11, 13.1 |
| R-03 | Paquet Python sans calendrier ni horaires de séance | Garde d'annonces et garde de fermeture native impossibles | D-12 : service MQL5 d'export ; risque résiduel : code MQL5 non compilable dans le conteneur, contrôlé par revue en phase 11, puis compilation et test de contrat sur le poste en 13.1 | 7, 11, 13.1 |
| R-04 | SL non attachable à l'entrée chez le courtier | Profil non prêt pour V3 (C06) | Sonde S-02 ; aucun contournement par pose différée ; décision humaine | 13.1 |
| R-05 | Contrats micro indisponibles sur le compte standard | Presque tous les signaux refusés (`MIN_VOLUME_OR_RISK_REJECT`) | Qualification 13.1 ; verdict « compte incompatible » sans déformer le risque | 13.1 |
| R-06 | Historique de ticks du courtier trop court | Validation C10 impossible sur le symbole exact | D-14 : source tierce déclarée contrefactuelle | 13.3 |
| R-07 | Rejeu Python lent sur sept ans de ticks | Protocole C10 long | Mesure en phase 10 ; optimisation à comportement constant | 10, 13.5 |
| R-08 | Contamination du test réservé | Validation sans valeur | Verrou du test réservé, ouverture unique journalisée après gel | 10, 13.5 |
| R-09 | Ambiguïtés de spécification tranchées implicitement | Défigeages en chaîne | Arbitrages P-01 à P-12 en phase 0 | 0 |
| R-10 | Règles V1 absentes du dépôt | Rétention non calculable | D-15 : l'humain fournit la V1 avant 13.4 ; sinon rétention N/A déclarée | 13.4 |
| R-11 | Quotas ou gratuité des API modifiés, appels non autorisés | Complément IA indisponible | Neutralité A12, autorisation redemandée en sous-étape 13.6 (D-17), qualification A13, route payante désactivée | 12, 13.6 |
| R-12 | Composants Windows non testables dans le conteneur, sans intégration continue distante (D-10 non autorisée) | Défauts propres à Windows découverts en sous-étape 13.1 seulement | Tests de contrat sur le poste, preuves consignées ; D-10 peut être redemandée | 1, 13.1 |
| R-13 | Conditions du courtier modifiées dans le temps | Risque ou coûts faux | Relecture C04 avant chaque ordre, profils datés | 11, 13 |
| R-14 | Disponibilité humaine (annotation, surveillance de démonstration) | Retard de validation | Sous-étapes 13.x séparées, chacune avec son point d'arrêt | 13 |
| R-15 | Divergences répétées ou défigeages en chaîne | Carte MCL fausse | Suspendre, sonder, re-cartographier, informer l'humain | 2 à 12 |
| R-16 | Module fondamental externe qui n'écrit pas de façon atomique ou réutilise une séquence | Permissions rejetées, entrées bloquées | Lecture tolérante (rejet journalisé, état inchangé) ; règles d'écriture remises au fournisseur ; test de contrat avec le vrai module | 11, 13.1 |
| R-17 | Calendrier historique exporté après coup | Fuite d'information dans les rejeux C10 | Approximation déclarée (données §4) ; collecte prospective des versions dès la sous-étape 13.1 | 13.1, 13.3 |
| R-18 | Infrastructure figée sur des contrats que le réel contredit (comportement de MT5, de Windows ou du terminal différent du document 08) | Défaut découvert après le gel de la phase 11 | Contrats établis par l'examen du paquet officiel ; faux module comparé au document 08 par un test ; sondes et tests de contrat en 13.1 avant toute séance ; défigeage « correction » de la seule couche concernée, test qui capture le cas, régression intégrale ; aucune séance de démonstration avant la fin de 13.1 | 11, 13.1 |

## 3. Coûts et garanties de MCL

- **Coûts annoncés** : retour produit tardif hors composite (compensé ici par le squelette de la phase 1) ; coût
  du gate croissant avec le nombre de couches (régression intégrale à chaque gel, d'où des tests rapides et des
  fixtures petites) ; sérialisation entre couches dépendantes (groupes parallèles signalés dans le
  document 02) ; risque de contrat spéculatif (contrats minimaux, finalisés au début de chaque couche) ;
  bénéfice dégradé pour `infrastructure` et `service-ia`, dominés par leurs frontières externes.
- **Garantie donnée** : à tout instant, le bloc `{0 → k}` de chaque artefact est testé, intégré et stable, et le
  squelette reste déployable et vert.
- **Garanties non données** : rentabilité ; comportement réel du courtier avant la sous-étape 13.1 ; qualité
  sémantique des modèles avant A13 ; chemin de bout en bout sur la vraie plateforme avant la sous-étape 13.1 (la
  répétition générale de la phase 11 l'exerce contre le faux module seulement). MCL n'est pas présentée comme
  statistiquement supérieure à une autre approche : c'est une discipline de construction.

## 4. Matrice de traçabilité spécification → plan

Vue par section ; le [document 06](06_verification_exhaustive.md) la détaille exigence par exigence (155 lignes),
confronte chaque consigne de la skill d'expert à un choix de conception (71 consignes) et se contrôle par
`python tools/verifier_plan_london.py`.

| Section | Contenu | Artefacts et couches | Phases | Cas |
|---|---|---|---|---|
| C01 | Statut, compte, risque | `noyau` 0c ; `points-entree` 2 | 2, 11 | Refus des modes non autorisés |
| C02 | Configuration normative | `noyau` 0c ; `moteur-london` 0a | 2, 4 | Garde de configuration figée |
| C03.1–C03.2 | Horodatage, intervalles, tick de frontière | `noyau` 0a ; `london-donnees-temps` 1a | 2, 3 | C11.3 |
| C03.3 | Europe/London, jours locaux, jour UTC de perte | `london-donnees-temps` 0b ; `execution-coordinateur` 1b | 3, 5 | C11.4 |
| C03.4–C03.7 | Bougies closes, validité, trous, préchargement, reprise | `london-donnees-temps` 1c, 2a, 2b, 3 | 3 | C11.1, P-01 à P-03, P-10 |
| C03.8–C03.12 | Récurrences, A_t, précision, arrondis | `london-donnees-temps` 1b ; `noyau` 0b ; `execution-coordinateur` 0d | 2, 3, 5 | Oracles `wilder`, `rounded_levels` |
| C04 | Instruments, compte, fonctions du courtier, liaison des symboles | `noyau` 1b ; `infrastructure` 2a, 2c ; `points-entree` 1c | 2, 11, 13.1 | C11.7 |
| C05 | Permissions externes et annonces | `controles-fondamentaux` 0 à 3 ; `execution-coordinateur` 0b, 5a ; `infrastructure` 0g ; service MQL5 | 5, 7, 11 | C11.8, C11.9 |
| C06 | Entrée, spread, stop et objectif exécutables | `execution-coordinateur` 0c, 0d | 5 | C11.2, C11.5, S02.6-6 |
| C07 | Dimensionnement, réserves, gardes | `execution-coordinateur` 1b, 1c, 2a, 3 | 5 | C11.6, C11.7, C11.13 |
| C08 | Ordres, conflits, sorties, redémarrage | `execution-coordinateur` 2b, 4, 5a, 5b, 6 ; `orchestration` 2 | 6, 9 | C11.10 à C11.13 |
| C09 | Journal et mesures | `noyau` 2 ; `infrastructure` 0d ; `journal-rejeu` 1c, 3 | 2, 10, 11 | Motifs (P-07, P-08) |
| C10 | Plan d'évaluation | `journal-rejeu` 0b, 1b, 1c, 1d, 2, 3 ; `donnees-historiques` ; `moteur-london-v1` | 10, 13.3 à 13.5 | P-11, verrou du test réservé, rétention V3/V1 |
| C11 | Cas d'acceptation communs | Tous | 2 à 13.2 | Document 03, §5.1 |
| S02.1 | Range et analyse H1 | `moteur-london` 1a, 1b, 2 | 4 | S02.6-1, S02.6-2 |
| S02.2 | Fenêtre de déclenchement | `london-donnees-temps` 0b ; `moteur-london` 2 ; `execution-coordinateur` 0e | 3, 4, 5 | S02.6-3 |
| S02.3 | Bougie de cassure | `moteur-london` 1c | 4 | S02.6-4, S02.6-5 |
| S02.4 | Stop, objectif, quotas | `moteur-london` 1d, 1e, 2 | 4 | S02.6-6 à S02.6-8 |
| S02.5 | Exemple chiffré | `moteur-london` 1d ; `execution-coordinateur` 0d, 2a, 3 | 4, 5 | Scénario L-01 |
| S02.6 | Acceptation spécifique | `moteur-london`, `execution-coordinateur` | 4 à 6 | Document 03, §5.2 |
| A01–A02 | Portée, configuration et fournisseurs IA | `noyau` 0c ; `service-ia` | 2, 12 | — |
| A03 | Architecture et chemin d'exécution | Principe 2 du document 01 ; cartes | Toutes | A14-1 |
| A04–A06 | Données, extraction, veto | `service-ia` 1a, 0c, 1b, 2a ; export MQL5 du calendrier pour l'appariement A06 | 11, 12 | A14-3 à A14-6 |
| A07 | Insertion London | `execution-coordinateur` 6 ; `moteur-london` 2 ; `orchestration` 2 | 6, 9 | A14-10, L-15 |
| A08–A09 | Appels API, routeur, budget | `service-ia` 1c, 1d, 2b, 3 | 12 | A14-12 à A14-15 |
| A10 | Cache, IPC, journal, reprise | `contexte-ia` 1, 2 ; `service-ia` 2c ; `infrastructure` 0e | 8, 11, 12 | A14-16 |
| A11 | Recherche, audit, journal | `journal-rejeu` 3 ; `service-ia` 3 | 10, 12 | Diagnostics du §1.3 |
| A12 | Pannes et états | `contexte-ia` 3 ; `execution-coordinateur` 0b | 5, 8 | A14-8 |
| A13 | Validation sémantique et financière | `journal-rejeu` 2, 3 ; sous-étapes 13.6 et 13.7 | 10, 13 | A14-17 |
| A14 | Cas d'acceptation IA | `contexte-ia`, `service-ia`, `orchestration`, `journal-rejeu` | 8 à 12 | Document 03, §5.3 |
| A15, R | Sources et limites | Contexte, non normatif pour le code | — | — |
