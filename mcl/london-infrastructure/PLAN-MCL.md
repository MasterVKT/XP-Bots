# Infrastructure commune — phase 11 London

## 0. Périmètre
Frontières physiques C03 à C09, D11/D12 et A10, SDK 5.0.6231 injecté.
Source MQL5 export seule, sans décision ni ordre. Pas de service IA ni de qualification réelle.

## 1. Applicabilité
Structure connue, contrats stabilisables, dépendances identifiables : MCL applicable.
Les nombreuses frontières imposent des tests de fidélité différés en 13.1 ;
les fixtures et gates hors ligne prouvent les contrats logiciels, pas le courtier.

## 2. Cadre et objets intermédiaires
Configuration qualifiée, fichiers et structures SDK deviennent profils, ticks,
observations et réponses publiques. Une transaction durable précède l’entrée ;
les protections et clôtures C08 restent immédiates. L’assemblage est le seul import SDK.
Le registre de coexistence consigne R4/R5. L’esquisse EMA demeure historique.
Les feuilles répondent oui à la question « testable sans les autres unités » ;
session nécessite les types, chaque adaptateur nécessite session, courtier les
quatre adaptateurs et assemblage le courtier et les frontières physiques.

## 3. Carte et groupes parallèles
| Couche | Unité | Dépendances directes |
|---|---|---|
| 0a | types | noyau, execution |
| 0b | horloge | horloge |
| 0c | sqlite | sqlite, fichiers |
| 0d | journal | fichiers, noyau |
| 0e | snapshot | fichiers |
| 0f | ticks | fichiers |
| 0g | controles | fichiers |
| 0h | verrou | fichiers, verrou-systeme |
| 1 | session | types, fichiers |
| 2a | specifications | session, types, noyau, execution |
| 2b | flux | session, types, noyau |
| 2c | calculs | session, types, noyau, execution |
| 2d | execution_mt5 | session, types, horloge, noyau, execution, taches |
| 3 | courtier | specifications, flux, calculs, execution_mt5, session, types, horloge, noyau, execution |
| 4 | assemblage | horloge, sqlite, journal, snapshot, ticks, controles, verrou, courtier, session, types, noyau, sdk, fichiers |

Les huit feuilles 0a à 0h sont parallèles ; 2a à 2d le sont après 1. La feuille 0h a été ajoutée lors de la conception de l’assemblage : le verrou de processus est indépendant du courtier. Cette précision de la carte ne modifie aucun contrat métier ni aucun amont gelé.
Chaque groupe conserve des gates et gels individuels, sans dépendance cachée.

## 4. Contrats, frontières et gates
Contrats finalisés par couche avant code. Fichiers et SQLite temporaires réels,
horloge externe déterministe et faux SDK conforme : aucune doublure interne.
Gate : catégories propres, jonction réelle, suite intégrale des deux robots et
verify_project. Checkpoints après profondeur 1 et 3, gate global après enveloppe.
Tests de contrat MT5 présents dès chaque couche, ignorés sauf activation 13.1.
Les constantes sont confrontées au texte officiel de la roue épinglée ; les
résultats et last_error restent distincts. Aucun secret n’est journalisé.

## 5. Bilan de construction et de validation

Les quinze unités de la carte sont figées. Les huit feuilles physiques sont
indépendantes ; la session 1 précède les quatre adaptateurs 2a à 2d, puis le
courtier 3 et l’assemblage 4. La feuille 0h a été extraite avant la construction
de l’assemblage pour représenter le verrou de processus comme une responsabilité
indépendante. La carte reste stricte et ne présente aucune divergence. Le SDK
est injecté par la seule enveloppe ; aucun composant ne l’importe au chargement.

Les décisions de l’assemblage sont conservées dans
[DECISIONS-ASSEMBLAGE.md](DECISIONS-ASSEMBLAGE.md). Le chemin du dossier d’échange
est celui de `terminal_info.commondata_path`, complété par `Files`, puis contrôlé
contre le chemin déclaré. Les noms et fichiers sont confinés ; les lectures
sont bornées et leurs réceptions datées après retour. Les producteurs externes
doivent publier atomiquement et conserver leurs versions. Un état lié au compte
qui disparaît n’est pas recréé comme un compte neuf ; session, base et verrou
restent possédés tant qu’une tâche native est active.

Les corrections ont été faites à leur source, avec défigeage et revalidation
tracés. En 0a, les champs structurés du tableau natif ont priorité sur les
attributs Python homonymes, notamment `flags`. Le journal 0d accepte les deux
bras explicitement nommés en PAPER_AB, sans élargir l’identité du déploiement.
Les nouvelles qualifications et leur consommation ont révélé les besoins
communs décrits dans les bilans d’exécution, d’orchestration et de rejeu ; les
adaptateurs ne réécrivent pas leurs règles.

La correction [P11-20](CORRECTION-HORODATAGE-SDK-UTC.md) distingue la convention
des ticks SDK de celle des exports D12. C04 exige le choix qualifié S-01 `UTC`
ou `SERVEUR_S01`. Le courtier le transmet au flux et à la cotation défensive.
La table serveur reste utilisée pour les sources qui lui sont effectivement
liées ; aucun offset n’est déduit pour rendre une donnée acceptable. Les
signatures de reprise engagent ce choix et refusent une réinterprétation du
curseur. Les tests réels du bloc C04/C05/C08/SQLite exercent séparément les deux
conventions avec D12 à +2 h, entrée après deux COMMITs, reprise sans doublon et
clôture FLATTEN sur cotation fraîche. Les faits financiers de ces fixtures sont
explicitement en heure serveur S-01.

Les gates et gels individuels sont enregistrés dans `journal.jsonl`. Les
checkpoints de construction sont suivis du CP4 de revalidation P11-20, sur
1403 tests des deux lignées : 1389 réussis et 14 contrats
physiques différés. Les ressources passent leurs 30 contrôles projet et
288 contrôles de référence. L’infrastructure comprend 183 cas
(158 de catégorie 1, 25 de catégorie 2, contrats physiques
différés inclus). Les deux catégories utilisent les composants internes réels,
un faux SDK, une horloge externe et des fichiers/SQLite temporaires réels.

Les cinq sources MQL5 exportent seulement calendrier et séances. Leur convention
de modules et leurs formats ont été relus et testés en Python. `mcl.py` ne parse
pas MQL5 ; la compilation, les fonctions du terminal et les garanties propres
au poste ne sont pas démontrées par ces contrôles. Aucun terminal, identifiant,
ordre de courtier ni API distante n’a été utilisé. Les fixtures ne qualifient
aucun compte et ne prouvent aucun résultat financier.

### Contrats physiques différés

Les 14 tests suivants sont écrits mais restent ignorés pendant cette
phase. Leur activation relève de 13.1 après les actions humaines et sondes
requises, sur terminal de démonstration, avec `XPBOTS_CONTRATS_MT5=1`. Le guide
[LONDON_M15](../../docs/exploitation/LONDON_M15.md) précise les prérequis et les
incidents. Une réussite du faux SDK ne remplace pas cette confrontation.

| Couche | Test différé en 13.1 | Fichier |
|---|---|---|
| 0a | `test_structures_scalaires_et_table_qualifiee_s01` | [source](../../tests/robot/london_infrastructure/test_cat1_c0a_contrat_physique.py) |
| 0b | `test_utc_monotone_et_derivation_mesurable_sur_poste` | [source](../../tests/robot/london_infrastructure/test_cat1_c0b_contrat_physique.py) |
| 0c | `test_wal_commit_et_reouverture_du_fichier_windows` | [source](../../tests/robot/london_infrastructure/test_cat1_c0c_contrat_physique.py) |
| 0d | `test_projection_canonique_et_remplacement_windows` | [source](../../tests/robot/london_infrastructure/test_cat1_c0d_contrat_physique.py) |
| 0e | `test_racine_common_files_et_lecture_fermee_du_snapshot` | [source](../../tests/robot/london_infrastructure/test_cat1_c0e_contrat_physique.py) |
| 0f | `test_jeu_mensuel_reel_et_deux_empreintes` | [source](../../tests/robot/london_infrastructure/test_cat1_c0f_contrat_physique.py) |
| 0g | `test_dossiers_d11_d12_reels_sans_ecriture` | [source](../../tests/robot/london_infrastructure/test_cat1_c0g_contrat_physique.py) |
| 1 | `test_attachement_versions_racine_et_type_compte_demo` | [source](../../tests/robot/london_infrastructure/test_cat1_c1_contrat_physique.py) |
| 2a | `test_profils_du_compte_et_symboles_lies_concordent_aux_preuves` | [source](../../tests/robot/london_infrastructure/test_cat1_c2a_contrat_physique.py) |
| 2b | `test_occurrences_recentes_concordent_au_tableau_natif` | [source](../../tests/robot/london_infrastructure/test_cat1_c2b_contrat_physique.py) |
| 2c | `test_profit_marge_et_positions_en_lecture_seule` | [source](../../tests/robot/london_infrastructure/test_cat1_c2c_contrat_physique.py) |
| 2d | `test_tickets_volume_et_protections_du_compte_demo_sans_envoi` | [source](../../tests/robot/london_infrastructure/test_cat1_c2d_contrat_physique.py) |
| 3 | `test_composition_qualifiee_et_releve_courant_sans_emission` | [source](../../tests/robot/london_infrastructure/test_cat1_c3_contrat_physique.py) |
| 4 | `test_ressources_et_courtier_en_paper_sur_le_seul_compte_demo` | [source](../../tests/robot/london_infrastructure/test_cat1_c4_contrat_physique.py) |

### Revue des sources MQL5

| Source MQL5 | Empreinte SHA-256 | Revue et limite |
|---|---|---|
| [XPBotsExport.mq5](../../mql5/Services/XPBotsExport.mq5) | `adf227fbf1b0ded86aad96a683602382d19547864066331404f16ccb409dec50` | Service OnStart, verrou exclusif, controles de serveur, cadences monotones et fermeture ; aucun ordre ni reseau. Compilation et terminal non vérifiés. |
| [Atomic.mqh](../../mql5/Services/XPBotsExport/Atomic.mqh) | `9b0ffc33ff4da777425dae1f043a3bc066e54ad300e01a4d63bd481d4e474d4e` | Racine FILE_COMMON, noms confines, JSON echappe, UTF8 sans NUL, flush/close/move, reservation de version durable avant publication, refus du ledger absent pour publication existante. Compilation et terminal non vérifiés. |
| [TimeTable.mqh](../../mql5/Services/XPBotsExport/TimeTable.mqh) | `9ebdcca9a809f698dc92c8ed92e219c28e30a0bcfcf1800e0f84e8312cf75c1b` | TSV borne, UTF8 aller-retour, LF, segments ordonnes sans chevauchement ; conversion inverse unique, aucune deduction de decalage. Compilation et terminal non vérifiés. |
| [Calendar.mqh](../../mql5/Services/XPBotsExport/Calendar.mqh) | `481978abff958d2baa9ce7671b160085680acae46141bc690dbee47eb57f7a09` | Fenetre UTC couverte, conversions qualifiees, erreurs natives refusees, HIGH date seulement, pays/devise et IDs verifies, plage demi-ouverte, version reservee avant ecriture. Compilation et terminal non vérifiés. |
| [Sessions.mqh](../../mql5/Services/XPBotsExport/Sessions.mqh) | `68202715cb3c6617b3cd16e6189e536a6ff7c43e09f2354687efb67d12177325` | Cotation et negociation separees sur sept jours, erreurs natives distinguees de fin de liste, symbole synchronise, version monotone. Compilation et terminal non vérifiés. |

### Mutations et coutures

La copie saine passe la suite intégrale. Les 38 mutations de la phase
sont toutes détectées par une suite complète par variante : 32 couches nouvelles
ou modifiées, coutures S1 en direct, S6 et S7, contrôle de source MQL5 et deux
pertes distinctes de propagation du choix UTC. Une garde d’architecture seule
n’est pas acceptée comme preuve de comportement. La mutation MQL5 est un contrôle
de source non compilée, explicitement distingué des mutations Python. Les sources
du dépôt ne sont pas mutées et l’empreinte de la copie est restaurée après chaque
variante. Le détail des cas apparaît au bilan des points d’entrée.

Les coutures S1 en direct et S6 utilisent cette infrastructure ; S7 compose les
commandes physiques. Les 70 tests du squelette sont conservés et les entrées
historiques EMA restent distinctes. Les essais de panne, de persistance et de
reprise emploient les mêmes composants que la boucle directe. La qualification
physique reste en 13.1 et le service IA est une phase distincte, non commencée.
