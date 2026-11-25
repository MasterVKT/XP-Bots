# Exigences et preuves de phase 12

Cette matrice relie les 22 exigences à la construction autorisée. Les noms de tests
sont dans tests/robot/london_service_ia ; les détails et limites figurent au
[PLAN-MCL](PLAN-MCL.md). Les références sont des oracles de tests uniquement.

| ID | Exigence | Résultat ou preuve |
|---|---|---|
| E01 | Reprise et conservation des quinze fichiers, vingt ressources et 412 contrats | 0 ; bilan §5.1 ; contrôle d’intégrité et arbre Git avant/après publication |
| E02 | Service unique, coexistence R4/R5, cartes et lignée | carte.json ; COEXISTENCE_ROBOT1_LONDON ; robot/outils/lignees et cartes composites |
| E03 | Ressources, types et formats stricts | 0 : test_cat1_c0_types ; ressources inchangées, guards négatifs |
| E04 | Borne UTF-8 de l’enveloppe complète et preuves envoyées | 1a : test_cat1_c1a_tokens et test_cat2_c1a_tokens |
| E05 | Extraction stricte et citation exacte ; A14-4 | 1b : test_cat1_c1b_validation ; oracle parse_model_output |
| E06 | Notes sourcées, bornées et informatives | 1b et 3 : validation stricte et planificateur ; oracle parse_advisory_output |
| E07 | RSS officiel, causalité, corrections et dédoublonnage | 1c, 2c, 4 : normalisation, collecteur et archives SQLite |
| E08 | Coûts Decimal et bornes inclusives ; A14-14 | 1d : budget ; oracles reserve_cost_usd et budget_admits |
| E09 | Réserves inconnues, quotas et prix datés ; A14-13 | 1d, 2b et 4 : budget, routeur, reprise physique |
| E10 | Concurrence transactionnelle réelle ; A14-12 | 4 : test_cat1_c4_persistance, deux connexions et une admission |
| E11 | Trois enveloppes A08, usage, refus et outils ; A14-15 | 1e et 4 : fournisseurs, transport HTTP et clés synthétiques |
| E12 | Snapshot strict et séquence durable | 1f et 4 : oracle make_snapshot, IPC et reprise |
| E13 | Seul veto A06 causal et expiration exacte ; A14-3,5,6 | 2a : oracle build_policy_event ; 4 : couture PAPER_AB |
| E14 | Vrai calendrier D12 et mapping incomplet refusé | 2a et 4 : calendrier réel, historique et compteur perdu |
| E15 | Ordre, délais, erreurs, gratuité et payant off | 2b : routeur ; 4 : deux cas CLI payant explicite |
| E16 | Polling conditionnel, redirections et backoff RSS | 2c : collecteur et Retry-After ; 4 : transport borné |
| E17 | Priorités, horaires Londres, hypothèses et dérive | 3 : planificateur ; été/hiver, quota, douze cas fixes, tickets |
| E18 | Archives et reprise sans réinférence ; A14-11,16 | 3 et 4 : archives causales, inconnus suspendus et événements inchangés |
| E19 | Heartbeat indépendant, worker unique et collecteur séparé | 4 : test_cat2_c4_workers et test_cat2_c4_service |
| E20 | IPC atomique et pannes NEUTRAL | 4 : test_cat1_c4_http_publication et coutures lecteur réel |
| E21 | Vrai service → lecteur → London PAPER_AB ; A14-1,2,11 | 4 : test_cat2_c4_couture_ab, six séances et une avec réponse de 20 s |
| E22 | Contrats différés, mutations, docs, audit et publication | 4 : six contrats API/RSS ignorés ; bilan §5.4 ; contrôles finaux, arbre archivé testé, commit/push de phase 12 |

Les sources, interfaces et tests de chaque couche répondent à E03–E21 ; la carte,
les frontières, le journal MCL et les deux cartes composites à E02/E22. Les gardes
et leur lignée répondent à E01/E02/E11. Les bilans, plans, guide, passation et
informations de disponibilité des skills répondent à E22 et préparent uniquement
13.1. Aucun fichier préexistant étranger à la phase n'est intégré au commit.
Le bilan rapporte séparément la construction démontrée et les qualifications
physiques, sémantiques et financières qui restent différées.
