# Plan MCL — moteur-london

> Phase 4 du [plan London](../../docs/architecture/robot_london_v3/README.md), artefact pur
> `xpbots.london`. Sources : document 02, §6.3, spécification S02, C03, C09 et export technique figé.

## 0. Périmètre

Ce composant reçoit des bougies enrichies M15 et H1 et des issues du noyau. Il produit les résultats
techniques S02, sans coordinateur, courtier, horloge ni fichier. Il remplace la couture S3 du
[squelette](../squelette/COUTURES.md). Les conversions exécutables et la qualification C04 restent hors phase.

## 1. Applicabilité

La structure est connaissable par S02 et la cartographie approuvée ; les contrats sont stabilisables par
les exports figés ; aucun prototype n'est nécessaire. MCL est applicable, à l'échelle composant, en mode pur.
Le coût assumé est la régression intégrale à chaque couche, puis la sérialisation des niveaux dépendants.
Les signaux surveillés sont les divergences répétées et les défigeages en chaîne.

## 2. Étape 1

La finalité est d'appliquer exactement S02, avec un état par symbole et, ultérieurement, par bras. Les entrées
sont les bougies réelles de `london-donnees-temps`, les paramètres typés du noyau et une taille de tick
`Decimal` explicite par symbole. La sortie est un signal ou un refus du noyau pour chaque nouvelle M15 ; une
H1 alimente le gel sans produire de décision. Une issue `REMPLIE` signifie qu'un volume non nul est confirmé :
le noyau n'exprime pas de volume dans `Issue`. Un refus ou une expiration ne consomme aucun quota.

Le moteur emploie uniquement la bibliothèque standard et des flottants 64 bits, sans recopier les seuils.
Les comparaisons restent strictes ou inclusives selon S02. Les artefacts amont sont figés. Les arbitrages
P-03, P-07, P-09 et P-10 sont appliqués. `reference/technical.py` reste réservé aux tests comme oracle.

Le contrôle de reprise a constaté les commits `9c39d23` et `70c60d9`, les gels amont, 451 tests verts,
`verify_project.py` PASS et la carte composite verte. La branche courante est `master` après coexistence
structurée des deux lignées ; `.gitattributes` et la fixture CSV étaient déjà modifiés avant cette phase et
restent hors de son commit. Aucun échec préexistant n'a été observé.

## 3. Carte

La question-test place les paramètres et les types en feuilles : ils ne dépendent d'aucune autre unité de
cet artefact. Chaque calcul de niveau 1 consomme ces deux feuilles réelles. L'enveloppe dépend de tous les
calculs et de leurs types. Les dépendances directes sont toutes déclarées, y compris celles vers les feuilles.

| Couche | Unité | Sous-paquet | Dépend de |
|---|---|---|---|
| 0a | parametres_london | c0a_parametres | — |
| 0b | types_london | c0b_types | — |
| 1a | range_londres | c1a_range | 0a, 0b |
| 1b | gel_atr_h1 | c1b_gel_atr_h1 | 0a, 0b |
| 1c | bougie_cassure | c1c_cassure | 0a, 0b |
| 1d | stop_local | c1d_stop | 0a, 0b |
| 1e | quotas_london | c1e_quotas | 0a, 0b |
| 2 | moteur_london | c2_moteur | 0a, 0b, 1a, 1b, 1c, 1d, 1e |

Groupes parallèles : 0a ∥ 0b, puis 1a ∥ 1b ∥ 1c ∥ 1d ∥ 1e. La carte impose toutes les règles strictes,
dont la divergence. Ses interdits couvrent les entrées-sorties, les autres méthodes, le coordinateur, les
paquets en aval et `xpbots.london.squelette`, supprimé à la couture. Il n'existe aucune frontière externe
réelle à doubler. Les interdits ne sont pas des doublures.

## 4. Contrats, gates et checkpoint

Toutes les fiches sont esquissées avant le code, puis finalisées juste avant leur couche. Les interfaces et
tests de chaque couche sont gelés ensemble. Les catégories 1 et 2 suivent le document 03, §3 ; les feuilles
n'ont pas de catégorie 2. Chaque gate rejoue `python tools/run_london_tests.py` (les deux lignées) et
`python tools/verify_project.py`. Un checkpoint suit le niveau 1. Le gate global suit l'enveloppe et la
couture S3. Les mutations s'exécutent sur une copie temporaire extérieure au dépôt.

Les tests portent S02.6-1 à 8, L-01 à L-13 au niveau technique, C11.1, C11.2 et C11.4, les égalités dyadiques,
les paramètres modifiés et les oracles `london_signal` et `london_setups`. La conversion short en Ask et
l'objectif depuis l'entrée réelle seront vérifiés en phase 5. Le document 05 fournit la lecture critique M15,
la skill d'expert externe n'étant pas disponible dans cet outil.

## 5. Bilan

La phase 4 est achevée le 06/11/2026. Les huit couches sont figées ; leurs gates rejouent les deux lignées
et les ressources métier, sans test ignoré. Le journal MCL contient le checkpoint après le niveau 1, les
huit défigeages correctifs, les huit nouveaux gates et gels, puis le checkpoint de revue corrective.
Le gate global de sortie est exécuté après la couture et la mise à jour documentaire.

### 5.1 Couches, couverture et choix arrêtés

| Couche | Catégorie 1 | Catégorie 2 | Garantie principale |
|---|---:|---:|---|
| 0a | 6 | — | Bloc London typé, clés exactes, options interdites refusées, cohérence des horaires et de l'effectif |
| 0b | 6 | — | Valeurs immuables, nombres finis, taille de tick décimale positive |
| 1a | 8 | 1 | Vingt ouvertures exactes, extrêmes exacts et disponibilité maximale |
| 1b | 7 | 1 | Dernière H1 valide admissible, âge et rang exacts, disponibilité réelle |
| 1c | 10 | 1 | Cassure, corps, clôture, buffer et TR, avec bornes inclusives ou strictes de S02 |
| 1d | 4 | 1 | Trois composantes min/max, aucune troncature du stop, distance maximale incluse |
| 1e | 7 | 1 | Premier remplissage par clé, jour Londres, quotas restaurables et idempotents |
| 2 | 21 | 5 | Enveloppe causale par symbole, motifs ordonnés, propriété et non-réévaluation |
| Total | 69 | 10 | 79 tests propres à l'artefact |

Les sept décisions du briefing initial sont fixées dans les contrats suivants.

1. Le contrat 0a type toutes les clés London et consomme les paramètres communs déjà typés ; il ne recopie
   aucun seuil et refuse les trois options désactivées si elles deviennent vraies. Les tests changent des
   paramètres pour vérifier qu'ils influencent réellement les calculs.
2. Les contrats 0b et 2 reçoivent une taille de tick `Decimal` par symbole, validée puis convertie pour les
   calculs flottants. La couture S7 impose `--tick-size SYMBOLE=DECIMAL` pour chaque symbole présent ; une
   taille manquante ou incorrecte donne le code 1. C'est une hypothèse synthétique explicite du squelette,
   à remplacer par le profil C04, sans déduire la taille des décimales des prix.
3. Le protocole structurel de stratégie ajoute `sur_issue(Issue) -> None`. S4 le contrôle et transmet chaque
   issue de refus ; le moteur London n'importe ni orchestration ni exécution. Le test de conformité
   structurelle et la mutation de perte d'issue éprouvent cette frontière.
4. `StrategieLondon` crée un moteur indépendant par symbole. Chaque bras futur devra construire sa propre
   stratégie ; aucun singleton ni état partagé entre bras n'est introduit.
5. Le contrat 2 fixe l'ordre : trou actif, fenêtre ou jour inactif, préchargement et A, range, disponibilité
   du gel, largeur, position London possédée, cassure, quota, stop, puis signal. Les motifs et détails sont
   ceux de P-07 ; les diagnostics ne montrent que des mesures connues à la clôture. P-03 efface le range au
   début d'un trou et permet son recalcul après récupération lorsque ses vingt bougies sont valides.
6. Le contrat 1b applique P-09 à la dernière H1 valide close au plus tard à F et âgée d'au plus une H1, avec
   ATR positif et rang suffisant. Le contrat 2 conserve le premier gel valide, ignore ses corrections et
   les H1 suivantes, et refuse toute décision antérieure à sa disponibilité. Une version invalide peut
   encore être remplacée avant qu'un gel valide soit acquis.
7. Le contrat 1e compte seulement la première issue `REMPLIE` d'une clé. Cette nature signifie déjà un volume
   effectivement non nul, car le noyau n'expose pas de volume dans `Issue`. Refus et expirations ne comptent
   pas ; le jour Londres seul réinitialise les quotas. Le contrat 2 empêche la réémission d'une M15, le
   rattrapage, la perte d'une position à minuit et sa réouverture par un remplissage tardif après clôture.

Les tests couvrent S02.6-1 à 8 et L-01 à L-13 dans le périmètre technique, dont les rangs limites, les égalités
représentables exactement, les jours d'été et d'hiver, les changements d'heure, la causalité par préfixe et
les disponibilités tardives. `london_signal` vérifie cassure et stop ; `london_setups` vérifie l'enveloppe sans
remplissage, avec les indicateurs réels construits sur les données synthétiques. Ces fonctions restent des
oracles de test. Les aspects de conversion Ask et d'objectif depuis l'entrée exécutée attendent la phase 5.

La fabrique de journées crée des ticks avec quatorze jours au moins de préchargement, puis un range et une
cassure voulus. Elle alimente la vraie chaîne de bougies et d'indicateurs, avec un TR constant contrôlé et
sans prix réel. Les ATR M15 et H1 peuvent être distincts dans la famille synthétique documentée par la fabrique.

### 5.2 Défigeages et mutations

La campagne initiale sur copie jetable saine a exécuté 23 mutations distinctes, une ou plusieurs dans chaque
couche et dans S4/S7, chaque fois avec la suite intégrale. Vingt-deux ont été détectées. La mutation
`1a_extreme_superieur_minimum` a réellement survécu : remplacer le maximum des hauts par le minimum faisait
passer le haut observable de 101 à 100, sans faire échouer les anciens cas dont les hauts étaient identiques.
Le défigeage `correction` de 1a a ajouté `test_extremes_heterogenes_exacts_en_toute_position_du_range`, qui
vérifie exactement (H, L, W) = (101, 97, 4), successivement aux vingt positions. L'implémentation correcte du
maximum n'a pas changé. Après gate et nouveau gel, une copie saine à 532 tests a passé, puis cette mutation
rejouée a provoqué vingt échecs de sous-tests. Les 23 mutations distinctes sont donc détectées après correction :
24 exécutions mutées, réparties en 23 initiales et une reprise corrective ciblée, sans prétendre à une seconde
campagne complète de 23 mutations.

La revue a aussi trouvé des fins CRLF dans les fiches de contrats générées sous Windows. Git les aurait
normalisées en LF, ce qui aurait invalidé leurs empreintes de gel dans un checkout distant. Les huit couches
ont été formellement défigées avec nature `correction`, puis leurs fiches écrites en UTF-8 LF, passées au gate
et regelées dans l'ordre. Sept défigeages ne changent que cette représentation ; celui de 1a inclut aussi
le test adversarial. Aucun contrat gelé n'a été retouché sans défigeage. Le contrôle final compare les octets
des contrats gelés aux blobs Git préparés pour publication.

Le harnais reproductible est `tools/verifier_mutations_london_phase4.py` ; ses motifs doivent être uniques
et les variantes syntaxiquement valides. Il vérifie d'abord la copie saine et exige ensuite de vrais tests
en défaut. Les copies sont hors du dépôt et ne contiennent aucun `.env`. Les rapports détaillés de session
restent dans `.local/reports/mutations_london_phase4_passe1.json` et
`.local/reports/mutations_london_phase4_passe2.json`, non publiés ; le tableau suivant en conserve le résultat.

| Mutation | Couche | Première exécution | Après correction |
|---|---|---|---|
| `0a_effectif_range_ignore` | 0a | Détectée | Sans nouvelle modification du cas |
| `0b_largeur_additionnee` | 0b | Détectée | Sans nouvelle modification du cas |
| `1a_bougies_apres_range_lues` | 1a | Détectée | Sans nouvelle modification du cas |
| `1a_extreme_superieur_minimum` | 1a | Survivante réelle | Détectée, 20 sous-tests |
| `1b_age_exact_refuse` | 1b | Détectée | Sans nouvelle modification du cas |
| `1b_plus_ancienne_h1` | 1b | Détectée | Sans nouvelle modification du cas |
| `1c_cloture_exacte_refusee` | 1c | Détectée | Sans nouvelle modification du cas |
| `1c_corps_exact_refuse` | 1c | Détectée | Sans nouvelle modification du cas |
| `1c_egalite_buffer_admise` | 1c | Détectée | Sans nouvelle modification du cas |
| `1c_tr_exact_refuse` | 1c | Détectée | Sans nouvelle modification du cas |
| `1d_guard_minimum` | 1d | Détectée | Sans nouvelle modification du cas |
| `1d_maximum_exact_refuse` | 1d | Détectée | Sans nouvelle modification du cas |
| `1d_stop_achat_maximum` | 1d | Détectée | Sans nouvelle modification du cas |
| `1e_jour_utc_au_lieu_de_londres` | 1e | Détectée | Sans nouvelle modification du cas |
| `1e_remplissage_compte_plusieurs_fois` | 1e | Détectée | Sans nouvelle modification du cas |
| `2_disponibilite_du_gel_ignoree` | 2 | Détectée | Sans nouvelle modification du cas |
| `2_largeur_minimale_exclue` | 2 | Détectée | Sans nouvelle modification du cas |
| `2_meme_bougie_reemise` | 2 | Détectée | Sans nouvelle modification du cas |
| `2_position_possedee_ignoree` | 2 | Détectée | Sans nouvelle modification du cas |
| `2_prechargement_m15_borne_exclue` | 2 | Détectée | Sans nouvelle modification du cas |
| `2_quota_ignore` | 2 | Détectée | Sans nouvelle modification du cas |
| `S4_issue_non_transmise` | S4 | Détectée | Sans nouvelle modification du cas |
| `S7_taille_absente_admise_au_demarrage` | S7 | Détectée | Sans nouvelle modification du cas |

### 5.3 Couture et contrôles de sortie

S3 utilise désormais la fabrique de `c2_moteur` ; `src/xpbots/london/squelette.py` a été lu puis supprimé.
S4 transmet les issues de son coordinateur minimal et S7 exige les tailles de tick. Les 35 tests du
squelette passent, avec de vraies cassures d'été et d'hiver produisant des `CLOTURE` et des `INTENTION`
refusées, aucune commande d'exécution et aucun quota consommé par ces refus. Le registre des coutures
trace S3 remplacé et les extensions S4/S7. La carte interdit toute réintroduction de l'ancien segment.

La régression finale comporte 532 tests des deux lignées, sans échec, erreur ou test ignoré, contre 451 au
contrôle de reprise. Les contrôles métier totalisent 30 vérifications de projet et 288 de référence.
Le plan directeur est en version 1.4.5 ; le guide, le document 02, le suivi composite et la passation sont
alignés. Les cartes de tous les artefacts, le plan London, la gouvernance, les liens, la syntaxe et les
portes du cycle de vie sont contrôlés à la sortie. Une première suite de gouvernance a révélé `sh` absent
du PATH Windows ; elle est relancée avec le Git Bash déjà installé, sans changement de gouvernance.
La reprise de gouvernance sur une archive des fichiers préparés, sans cache du graphe local verrouillé,
a ensuite passé les huit étapes, dont les 36 tests du cycle de vie. Un premier gate global a aussi échoué sur le message accentué d’un test EMA après forçage de
`PYTHONIOENCODING=utf-8` dans la commande : le sous-processus émettait UTF-8 tandis que le test lisait
l’encodage système. Le gate a ensuite passé les 532 tests dans l’environnement Windows initial, sans retoucher ce test.

La copie de publication est extraite par `git -c core.autocrlf=false archive` de l'arbre préparé : ses
532 tests passent, ainsi que les 30 contrôles projet et les 288 contrôles de référence. L'export ordinaire
avec le réglage Windows `core.autocrlf=true` convertissait la fixture CSV en CRLF et faisait échouer son
test d'identité ; le même comportement a été reproduit sur le commit initial. Le blob CSV préparé est
identique à celui de ce commit. La modification initiale de `.gitattributes` règle déjà le cas dans le
répertoire de travail ; elle reste hors du commit de phase 4. Pour tester une autre copie Windows de cet
état publié, conserver les octets LF du CSV. Aucune fixture ni attente de test n'est modifiée pour contourner
ce comportement de l'export. Les rapports d'export de session sont dans `.local/reports/`.

| Contrôle de sortie | Résultat constaté |
|---|---|
| Gate global de moteur-london | Vert, régression de 532 tests et contrôle métier PASS |
| Gels et contrats | Huit couches figées ; 30 fichiers contractuels identiques aux blobs préparés et aux empreintes gelées |
| Cartes MCL | Treize cartes vertes, sans avertissement |
| Vérification du plan London | PASS, aucun problème |
| Ressources métier | PASS, 30 contrôles projet et 288 contrôles de référence |
| Gouvernance sur archive Git | PASS, huit étapes sur huit ; aucun cache local requis |
| Copie de publication aux octets Git exacts | 532 tests verts, contrôle métier PASS |
| Cycle de vie | JSON, syntaxe Python, liens Markdown et vérification du projet verts |
| Différences et périmètre | `git diff --check` vert ; 61 fichiers préparés rattachés, ressources protégées intactes |

### 5.4 Audit de périmètre et limites

| Exigence | Résultat et preuve |
|---|---|
| Reprise documentée avant changement | §2 : commits, branche, 451 tests, gels amont, carte et écarts initiaux |
| Sources et expert M15 | Sources du plan et S02 lues ; lecture critique du document 05 à défaut de skill externe |
| Cycle et skills | Orchestrateur, MCL, planification, London, causalité, cohérence, gouvernance, lacunes et audit |
| Carte complète et contrats avant code | Carte stricte, huit fiches, interfaces et tests contractuels gelés |
| Construction par dépendances | Journal : gates, gels, checkpoint niveau 1 et revue corrective |
| Sept choix de conception | §5.1 et contrats correspondants |
| Tests et oracles | 79 tests propres et régression intégrale des deux lignées |
| Couture S3 complète | §5.3, registre et 35 tests du squelette |
| Mutations jusqu'à détection totale | §5.2 : 23 distinctes détectées après correction tracée |
| Documents de sortie | Plan 1.4.5, document 02, guide, composite, passation phase 5 |
| Contrôles globaux et portabilité | Gate global, cartes, suite métier, gouvernance, cycle de vie et blobs préparés |
| Publication demandée | Commit français de phase 4 et push sur `master`, à vérifier dans Git |
| Contraintes et périmètre | Standard library ; ressources protégées intactes ; phase 5 non commencée |

Réciproquement, les changements de `src/xpbots/london/`, `tests/robot/moteur_london/` et de leurs outils de
fixtures réalisent l'artefact et ses preuves ; les trois segments S3/S4/S7 et les tests du squelette réalisent
la couture ; le harnais réalise les mutations ; `mcl/moteur-london/` porte carte, contrats et traçabilité ;
les six documents de suivi réalisent la sortie. Un contrôle machine rattache chacun des 61 fichiers
préparés à exactement un de ces groupes, sans fichier hors périmètre. Les deux modifications initiales étrangères à la phase
restent hors du commit. Aucune modification ne concerne les ressources métier protégées ni les dépendances.

| Identifiant | Type et gravité | Preuve et emplacement | Correction | Validation |
|---|---|---|---|---|
| P4-01 | Écart initial, information | `master`, coexistence et 451 tests au lieu de l'ancienne passation | Contexte réel conservé, deux fichiers déjà modifiés exclus du commit | Historique et contrôle de reprise |
| P4-02 | Défaut de couverture, significatif | Mutation réelle max→min en 1a survivante | Défigeage correction et test exact à vingt positions | Gate, gel et reprise ciblée détectée |
| P4-03 | Défaut de portabilité, significatif | CRLF des fiches face aux règles LF Git | Huit défigeages correction, LF et nouveaux gels | Cartes et comparaison aux blobs préparés |
| P4-04 | Environnement de test, mineur | Gouvernance : `sh` absent du PATH, puis cache local du graphe verrouillé à la copie | Git Bash installé ajouté au PATH ; suite sur archive Git sans cache local | Suite de gouvernance complète sur les fichiers préparés |
| P4-05 | Écart documentaire, mineur | Dépendances directes et disponibilité réelle du range | Document 02 aligné sur les contrats | Vérificateur du plan et carte stricte |
| P4-06 | Environnement de commande, mineur | Gate global : message UTF-8 décodé comme texte système dans un test EMA | Retrait du forçage local de PYTHONIOENCODING, sans changement de code | Gate global vert, 532 tests |
| P4-07 | Sensibilité initiale à l’export Windows, mineure | Le CSV exporté par Git avec conversion CRLF échoue à l’identité ; reproduit sur HEAD initial | Export sans conversion et contrôle de l’identité au blob ; modifications initiales préservées | Copie de publication : 532 tests et ressources métier verts |

Les tâches de construction, tests, mutation, couture et traçabilité sont couvertes par MCL et London ;
la causalité par la skill de données, les documents par la cohérence, l'environnement des contrôles par
la gouvernance, la clôture par l'audit. Aucune lacune réutilisable n'impose de créer ou d'étendre une skill.
L'expertise M15 indisponible est remplacée par le document 05 comme prévu dans la demande.

Le coordinateur du squelette refuse encore toute entrée. Les conversions exécutables, le dimensionnement,
les permissions fondamentales, l'IA, les ordres, les essais financiers et la mise en service restent à
construire selon leurs phases. Aucun succès hors ligne ne prouve une rentabilité. La phase 5 attend une
nouvelle demande et son arbitrage de coexistence ; `mcl/execution-coordinateur` est déjà occupé par EMA.
