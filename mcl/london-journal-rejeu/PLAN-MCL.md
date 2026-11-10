# Plan MCL — london-journal-rejeu, composant partagé C10

## 0. Périmètre

Phase 10 London, huit unités sous xpbots.rejeu.c*. Le dossier actif porte le
préfixe London car journal-rejeu est une esquisse EMA conservée, sans code ni gel.
L’arbitrage R4/R5 du 10/11/2026 précède la construction. Le composant est commun,
avec les types canoniques du noyau, les commandes du coordinateur et le moteur
événementiel existant. Le squelette EMA et les deux socles restent distincts.
L’implémentation physique, MT5, les clients IA et toute qualification réelle sont
hors phase ; les contrôles utilisent uniquement des données synthétiques.

## 1. Applicabilité

Structure connaissable : oui, C09/C10/C11, A11/A13/A14, P-11 et cahier de données.
Contrats stabilisables : oui, paramètres figés et décisions arrêtées. Exploration
nécessaire : non. MCL s’applique à ce composant pur de l’application composite.
Les frontières sont les lignes de données, conditions contractuelles, messages
externes et transactions ; elles sont fournies en mémoire. Le coût comprend huit
gates intégraux, les checkpoints après 1 et 3, les mutations et une archive de
publication. La sélection de tests ne remplace aucun gate.

## 2. Cadre et sources

Entrées : lignes CSV avec manifeste et couverture, profils et frais datés,
configuration chargée, mode de coûts, messages causaux C05/IA, fabriques de
stratégie, factures IA et autorisation éventuelle du test réservé. Sorties :
ticks validés, commandes et faits natifs, courbes de fonds propres, trades et
mesures distinctes C09, bootstrap apparié et rapports structurés. Aucun fichier,
horloge ou réseau dans ce composant. Python 3.13 et bibliothèque standard.

Autorité : spécification 02, C03/C04/C06–C11 et A11/A13–A15, identiques au robot 1
pour les sections communes ; configuration technique et IA, document 02 §6.8,
fiche de phase 10, document 03, document 05 §1.2–1.4 et cahier de données.
La skill d’expert externe est indisponible ; cette lecture remplace son apport.
La baseline est 908 tests, 30 contrôles projet et 288 de référence. Les sept
artefacts amont sont figés ; aucune modification amont n’est présumée nécessaire.
Les quinze fichiers préexistants, CSV compris malgré les attributs Git, sont
protégés par empreinte et exclus de la publication. Le cache commit-graph Git
signale un avertissement initial ; les commandes réussissent, aucun cache n’est
réécrit pour masquer ce constat.

## 3. Unités, question-test et dépendances

| Unité | Responsabilité et objets intermédiaires | Constructible seule ? | Dépendances internes |
|---|---|---|---|
| 0a types | Valeurs de données, contrats datés, trades, comptes, jours et frais IA | Oui, avec le noyau figé | Aucune |
| 0b protocole | Blocs et coûts textuels C10, seuils et bootstrap chargés | Oui, avec la configuration figée | Aucune |
| 1a ticks | Ordre natif, format, intégrité et couverture des lignes reçues | Non | 0a |
| 1b simulateur | Calculs USD et cycle natif causal sur les ticks | Non | 0a, 0b |
| 1c métriques | Mesures C09 distinctes, fréquence et rétention, fonds propres | Non | 0a, 0b |
| 1d bootstrap | Indices de blocs et estimations appariées semées | Non | 0a, 0b |
| 2 exécuteur | Périodes, portefeuilles et coutures vers le moteur unique | Non | 0a, 0b, 1a, 1b |
| 3 rapports | Critères a priori et ventilations C10/A11/A13 | Non | 0a, 0b, 1c, 1d, 2 |

La couche d’import n’est pas une feuille parce que les ticks arrivent en premier :
ses types la précèdent. Les quatre unités de profondeur 1 sont indépendantes.
Le bootstrap consomme des sommes journalières typées et le protocole, sans devoir
appeler le calcul de métriques. Les scénarios et seuils exigent les arêtes réelles
1b→0b et 1c→0b, ajoutées à l’esquisse. Aucun cycle, aucune dépendance ascendante.

## 4. Carte et coexistence

La carte impose invariant, parallèles, externes, cycles, divergence et contrats
figés stricts. Les paquets sont c0a_types, c0b_protocole, c1a_ticks,
c1b_simulateur, c1c_metriques, c1d_bootstrap, c2_executeur et c3_rapports.
Squelette.py est exclu : il devient une façade de compatibilité. Le registre
COMMUN et les deux composites désignent les mêmes nouvelles sources. La fabrique
London est composée par 2 ; elle n’est jamais importée dans l’orchestration.
Le hasard est réservé à 1d ; les sources physiques, socles historiques et avals
sont interdits. Les cartes sont analysées avant toute source puis à chaque gate.

## 5. Contrats

Les huit esquisses précèdent le code. Chaque contrat final est arrêté juste avant
sa couche et cite signatures, erreurs, bornes et suites de tests. Le gel porte sur
fiche, interface et tests. Les feuilles restent indépendantes : chacune possède
son exception de valeur ; les données et le protocole ne s’importent pas.
Les instants sont UTC en millisecondes, les montants décimaux finis, les valeurs
immuables. Booléens à la place d’entiers et prix non finis sont refusés.

Les valeurs présentes dans les exports sont chargées ; seules les valeurs C10
exclusivement textuelles sont codées une fois dans le protocole, avec contrôle de
présence normative. Les six perturbations restent nommées et explicites, un
paramètre à la fois, exécutables uniquement en rejeu et journalisées.

## 6. Frontières

Les lignes et leur manifeste sont reçus en mémoire ; l’intégrité est vérifiée
avant qu’un historique validé puisse atteindre le moteur. Les conditions de
contrat, frais et horaires ont des dates d’effet et de connaissance. Une donnée
manquante n’est jamais remplacée par zéro. Les profils synthétiques déclarés ne
prouvent pas la qualification C04 d’un compte. Une série tierce ou des conditions
actuelles appliquées au passé sont étiquetées contrefactuelles.

Le simulateur est réel dans les tests de jonction ; le coordinateur, C05, le
lecteur IA et le moteur le sont aussi. Les seuls doubles concernent sources
externes et stockage. Les fabriques contractuelles sont admises pour les tests
propres ; les jonctions représentatives utilisent le vrai London préchargé.
Les factures IA originales sont des entrées distinctes des trades et sont
réconciliées par identifiant, jamais déduites deux fois.

## 7. Construction et gates

Ordre : 0a et 0b, puis 1a/1b/1c/1d, puis 2, puis 3. Groupes parallèles au sens
des dépendances seulement ; chaque couche conserve son gate et gel séparés.
Catégorie 1 : contrat propre. Catégorie 2 : jonction réelle sur le bloc disponible.
Commandes : python tools/run_london_tests.py --artefact london_rejeu --couche ID
--categorie N. Chaque gate rejoue intégralement les deux robots, puis
python tools/verify_project.py ; rien ne change entre gate et gel.
Après 1 et après 3 : revue, gate global et checkpoint outillés. Tout défaut amont
se corrige par défigeage formel à la source ; aucun journal MCL n’est édité à la main.

## 8. Acceptation

C11.3/5/12 : délai exact, premier tick admissible, prix Bid/Ask, un ou deux
incréments tick_size selon P-11, stress Ask élargi avec Bid technique conservé,
TP limite jamais dégradé, gaps et touches SL/TP de même milliseconde selon la
séquence. Aucun prix passé n’est réutilisé pour inventer une exécution ; les
protections natives précèdent les sorties logicielles. Les frais réels déclarés
et les effets de date sont pris en compte ; la réserve g n’est pas retranchée du P&L.

C10 : blocs fixés avant lecture, préchargement limité au passé, compte neuf par
bloc et un seul compte continu, arrêts persistants, accès au test réservé gardé
avant lecture et diagnostic 2026 non renommable. Les six perturbations sont
rapportées ensemble, avec pertes et arrêts ; aucune sélection du meilleur.

Métriques : sept mesures C09 distinctes, fonds propres avec flottant et frais,
jours à zéro inclus, PF sans perte signalé non applicable, rétention N/A ou trop
faible selon la référence. Bootstrap : blocs contigus dans chaque période,
remise, concaténation et troncature, indices appariés, sorties affectées à leur
jour, réplications sans trade signalées et percentiles linéaires calculés à la main.
A13 : deux comptes complets, coûts réels réconciliés et allocations explicites,
aucune réinférence. A11 London : ventilations et limites, sans causalité inventée.

## 9. Couture

1a remplace l’analyse S1 ; 1b et 2 remplacent l’exécution et le pilote S5. S7
compose le même moteur unique, en mode simple et PAPER_AB, avec les scénarios C10
et rapports du nouveau bloc. Les anciennes interfaces nécessaires aux tests de
frontière deviennent des adaptateurs déclarés, jamais une deuxième implémentation
de simulation. Les hypothèses synthétiques et modes de compatibilité sont nommés.
Le registre des coutures et les tests de bout en bout sont mis à jour ensemble.

## 10. Vérification et coût

Au moins une mutation par unité et par couture modifiée, sur copies temporaires
hors du dépôt, copie saine d’abord et régression intégrale par variante. Une
détection exige un test fonctionnel. Une survivante réelle conduit au test exact
et au défigeage nécessaire. Mesurer un mois synthétique de ticks et rapporter les
dimensions du jeu et la durée, sans extrapolation financière.

## 11. Clôture

Gate global, rapport MCL, cartes strictes, statuts, plan, ressources, gouvernance
et portes machine. Audit bidirectionnel et couverture des skills ; rapports dans
.local/reports/ seulement. Archive exacte de l’index vérifiée, même arbre au
commit français et sur origin/master. Directeur 1.4.11, bilan et passation phase
11. Puis arrêt avant 11. Aucun historique réel ni conclusion de rentabilité.

## 12. Bilan

### 12.1 Construction réalisée le 10/11/2026

Les huit unités sont figées après leurs gates intégraux. Les checkpoints 1 et 3
sont journalisés ; le dernier global rejoue 1 038 tests des deux lignées et les
30 contrôles projet / 288 de référence, tous verts. Le composant compte 124 tests
propres : 105 catégorie 1 et 19 catégorie 2. Les 70 tests du squelette comprennent
trois nouvelles vérifications des coutures de phase 10. Par rapport aux 908 tests
initiaux, le delta de 130 comprend aussi deux gardes transverses et un cas 0d.

| Unité | Tests propres | Jonctions | Contrat réalisé |
|---|---:|---:|---|
| 0a | 16 | — | Conditions et tarifs datés, données immuables, trades et factures originales |
| 0b | 11 | — | Dates C10, référence/stress, seuils chargés, six écarts et bootstrap |
| 1a | 8 | 3 | Intégrité du lot avant exposition, ordre stable, couverture et jours à zéro |
| 1b | 18 | 3 | Livre natif, prix exécutables, délai, protections, partiels, frais et fonds propres |
| 1c | 10 | 2 | Sept mesures distinctes, rétention, fréquence, facturation et courbe économique |
| 1d | 7 | 1 | Blocs contigus, indices appariés, graine, distributions et percentiles |
| 2 | 15 | 6 | Vrai moteur unique, C05/IA, réservé gardé, continu et états A/B indépendants |
| 3 | 20 | 4 | Critères C10/A13, ventilations A11, preuves manquantes, coûts et JSON exact |

Les simulations London été/hiver utilisent le moteur réel préchargé. Le rejeu
du journal d’entrées reconstitue ses décisions et son état sans backend ni
seconde lecture des prix ; les arrivées C05/IA archivées ne sont pas réinférées.
Les tests propres des fabriques contractuelles ne valent pas portage d’un moteur
V1 ou recâblage EMA. Les rapports gardent méthodes et comptes autonomes distincts. Les cohortes de contrôle technique et de permissions externes sont aussi séparées ; une matrice neutre ne qualifie pas la matrice fondamentale. Le delta total C05 (permissions et annonces) reste calculable quand l’effet des seules permissions ne peut pas être isolé, sans attribution au LLM.

### 12.2 Coutures et coexistence

S1 délègue à 1a : manifeste externe exact, ou déclaration explicite d’une fixture
LF pour l’ancienne signature. S5 conserve les noms historiques comme façades du
simulateur et du pilote communs ; l’ancien livre et les deux anciennes boucles
de pilotage ont été retirés. Les paquets d’arrivées externes restent disponibles.
S7 compose REFERENCE par défaut, STRESS sur option, simple ou PAPER_AB ; son JSON
conserve les anciennes clés et expose le rapport NON_VALIDE_FIXTURE. L’ancien
modèle sans délai est uniquement le scénario nommé SYNTHETIQUE_S5 des frontières
de test, absent des choix CLI. Le stockage physique reste futur.

Les deux composites et le registre COMMUN pointent le même bloc `rejeu.c*`.
L’esquisse `mcl/journal-rejeu/` n’est pas modifiée. Le squelette EMA et ses socles
restent distincts ; aucune phase EMA supplémentaire n’est déclarée achevée.
Les imports réels 1b→0b et 1c→0b et les profondeurs EMA 5/6/7 sont explicites.

### 12.3 Défauts et corrections tracés

| ID | Type / gravité | Preuve et localisation | Correction | Vérification |
|---|---|---|---|---|
| P10-01 | Carte / moyenne | Profondeur du journal commun après orchestration, composite EMA | Profondeurs 5/6/7, IDs conservés | Analyse et vérification des composites |
| P10-02 | Interaction de garde / moyenne | Premier gate 0a : dates/seuils C10 textuels pris pour des copies de config | Exceptions aux seules affectations nommées de 0b ; tests négatifs de portée | Gates 0a/0b et régression |
| P10-03 | Test / faible | Somme de tiers sous Decimal 28, test 0a | Contexte contractuel 48 dans l’assertion | Corrigé avant gel 0a |
| P10-04 | Défaut amont / forte | 0d refuse l’Ask exact 1.100125 du stress | Défigeage modification, test rouge, retrait de la restriction locale de grille des cotations | Sept gates amont et checkpoint ; [ADR](../london-execution-coordinateur/DEFIGEAGE-0d-PHASE10.md) |
| P10-05 | Test / moyenne | Comparaison de trades A/B avec identités de bras différentes, première cascade 0d | Comparer les faits économiques, exiger des trades non vides et des clés distinctes | Cascade complète verte |
| P10-06 | Défaut local / forte | Classification diagnostic de toute date après mai, exécuteur 2 | Bornes exactes RESERVE/DIAGNOSTIC/PROSPECTIF | Cas de dates avant gel 2 |
| P10-07 | Omission / forte | Conditions absentes de la première archive de résultat 2 | Défigeage extension 2 et conditions datées archivées | Comparabilité des frais et gate intégral |
| P10-08 | Garde / faible | Indices littéraux 2 dans 3 confondus avec paramètres | Décomposition nommée des tuples | Garde inchangée, gate 3 |
| P10-09 | Couture / moyenne | Micro-scénarios C05 attendent un fill avant le nouveau délai | Compatibilité sans délai nommée dans leur fabrique ; nouveaux tests C10 séparés | C05/IA et régression intégrale |
| P10-10 | Défaut / forte | `all` sur zéro facture considéré comme réel, rapport A13 | Défigeage correction 3, cas rouge ; facture réelle même nulle et maintien C10 sous gel attesté | Test exact, re-gel et global verts |
| P10-11 | Tests de couture / moyenne | Premier CP3 : deux égalités JSON anciennes et ancienne alerte de stockage | Vérifier le rapport, garder les anciennes clés exactes et le nom d’alerte commun | 1 031 tests et CP3 verts |
| P10-12 | Test / faible | Remplacement d’une propriété calculée BlocC10 dans le panel de jonction | Déplacer la vraie date de début, conserver du préchargement passé | Bootstrap réel et jours à zéro |
| P10-13 | Défauts de rapport / forte | Cinq cas rouges dans 3 : corpus distincts, sous-blocs C10, voisins hétérogènes, factures hors période et snapshots optionnels | Corpus/effectifs liés ; dates C10 complètes ; six voisins du même contexte ; facture active ; comparabilité sur C05 | Tests exacts, défigeage correction 3 et re-gel |
| P10-14 | Classification / forte | Exécuteur 2 : collecte après le premier bilan C10 classée hors protocole | Prospectif prolongeable selon les effectifs ; date du premier bilan et début inchangés | Cas au 08/03/2027 rouge puis vert, défigeage 2 et gate intégral |
| P10-15 | Portée C05 / forte | Delta total C05 indisponible si le neutre n’a pas de calendrier ; cohortes et qualification à séparer | Delta permissions + annonces explicite, effet des seules permissions distinct ; cohortes par régime et empreinte ; matrice externe requise | Vrai London et C05 NO_NEW ; tests de portée, défigeage 3 et gate intégral |
| P10-16 | Complétude / forte | Ordre sans cotation après envoi : zéro position mais cycle INCONNU, résultat marqué complet | Exiger des cycles C08 terminaux en plus de l’absence de position et de la couverture | Cas réel de pilote rouge puis vert, défigeage 2 et gate intégral |
| P10-17 | Critère A13 / forte | Rétention N/A ou trop faible bloquante alors que l’obligation commence à 50 références | Exemption strictement bornée à la rétention A13 non applicable, autres critères obligatoires | Cas de portée, défigeage 3 et gate intégral |
| P10-18 | Couverture du journal / moyenne | La mutation 2 retire les fills et clôtures transmis au moteur, mais le rapprochement natif conserve le trade final ; le test de jonction 2 ne vérifiait pas l’exhaustivité du journal | Défigeage correction 2, renforcement du test de rejeu existant : toutes les réponses natives sont transmises au même instant, dans l’ordre et sans perte ; implémentation saine inchangée | Test ciblé vert sur la source saine, rouge sur la mutation ; gate et re-gel tracés |

La vérification des seuls résultats finaux ne suffit pas à prouver la fidélité
du journal d’entrée : le rapprochement C08 peut récupérer un fill perdu dans
une variante. Le test de jonction compare donc les réponses natives aux faits
transmis au moteur, avec leurs instants, avant de vérifier leur rejeu sans backend.

Un rejeu complet exige aussi des cycles natifs terminaux : un ordre INCONNU sans
position ouverte rend le résultat incomplet. Pour A13, la rétention est un critère
seulement lorsque la référence compte au moins 50 trades par méthode/symbole ;
N/A et trop faible restent décrits et sont explicitement non applicables à cette
condition, sans dispenser des journées, effectifs, coûts et autres preuves.

Le journal MCL est produit uniquement par l’outil. Les 185 fichiers contractuels
de la cohorte amont ont été comparés : 183 conservés strictement et deux fichiers
0d révisés sous l’ADR. Les 30 nouveaux portent la cohorte à 215 ; octets LF,
empreintes de gel et blobs de l’index concordent. Toutes les ressources protégées
(`config`, schémas, prompts, référence, preuves, livrables) restent intactes.
L’avertissement Git préexistant sur le cache commit-graph reste déclaré, sans
réécriture de cache ; il n’empêche pas les commandes de réussir.

### 12.4 Mesure de durée et limites de portée

Un mois synthétique du 01/06/2023 au 01/07/2023 a été rejoué avec le vrai London :
16 462 ticks, 22 journées de marché, 17 trades, compte final sans position ouverte,
5 930 enregistrements, en 45,483 secondes sous Python 3.13.0 / Windows AMD64.
Densité : quatre ticks par M15 et frontières de la fabrique, préchargement inclus,
un seul symbole EURUSD, scénario REFERENCE, mode REJEU, commissions nulles déclarées.
Empreinte des prix : `26c10ccb383075d5e9c3ee80211d3c5ca3d78a47061d179eac3945db98f09bf4`.
Le rapport est `.local/reports/phase10_benchmark_mois.json`.

La projection mécanique à densité identique sur les 2 499 jours calendaires du
continu est 3 788,701 secondes, environ 63 minutes. Elle inclut le préchargement
de la mesure et ne modélise ni volume réel de ticks, ni bootstrap, ni matrice
des méthodes/coûts/blocs/écarts. Elle ne constitue pas une capacité garantie.
L’historique complet et le journal gardés en mémoire ont aussi un coût à mesurer
sur les données réelles ; aucune rétention arbitraire n’est introduite.
Les traces MCL au premier checkpoint 3 comptabilisent 3 527,5 secondes de régressions, hors cascade amont et mutations. Cette auto-mesure n’établit aucune
supériorité statistique de MCL.

Les conditions et frais doivent être historiques et connus à l’instant simulé.
Le simulateur supporte leurs changements datés ; l’exécuteur refuse explicitement
un changement de tick_size, sa fabrique technique recevant une grille fixe.
Sans V1 comparable, la rétention reste N/A. Les jours de l’or ne remplissent pas
la cible Forex. Sans journées, effectifs, corpus humain, coûts réels, C04, gel
et journaux prospectifs attestés, aucun verdict financier positif n’est permis.
Les retours sémantiques ne mesurent pas la réussite des trades. Les analyses de
retournements et d’opportunités après veto sont bornées aux signaux journalisés ;
les effets de calendrier et de stop technique ne sont pas attribués au LLM.

### 12.5 Vérifications de clôture

La campagne finale détecte les **12 mutations sur 12**, par des tests fonctionnels
des unités ou coutures visées, sans survivante. La copie saine puis chaque
variante rejouent les **1 038 tests des deux lignées**. Les variantes couvrent les
huit unités, S1/S5/S7 et la restriction de grille 0d corrigée. Les essais antérieurs
interrompus pour corriger les rapports ou renforcer la preuve du journal ne sont pas comptés dans ce résultat ;
la campagne finale porte une empreinte unique des sources courantes.

La gouvernance courante passe **8/8**. Les 18 cartes ont été analysées et vérifiées
sans avertissement ; les huit artefacts London/amonts sont figés. Syntaxe, JSON,
liens, miroirs et contrat de gouvernance sont verts. La nouvelle exécution du
mois synthétique conserve les mêmes dimensions et confirme sa complétude après
les corrections de fin native ; le rapport de reconfirmation est séparé de la
mesure initiale, sans extrapolation aux ticks réels.

Preuves locales (ignorées par Git) : `phase10_gate_final.log`,
`mutations_rejeu_phase10.json`, `mutations_rejeu_phase10_progression.jsonl`,
`phase10_benchmark_mois_reconfirmation.json`, `phase10_gouvernance.log`,
`cartes_phase10.json`, `phase10_gels.json`, `portes_phase10.json` et
`audit_completion_phase10.json`. La publication est conditionnée à la validation
des seuls blobs préparés ; les commandes et l’arbre testé sont journalisés dans
`publication_phase10_tests.json` et `publication_phase10_gouvernance.json`.
L’export utilise `git -c core.autocrlf=false archive`, pour conserver les octets
LF de la fixture CSV sans embarquer les modifications de l’utilisateur.

Le directeur est en 1.4.11 et la [passation](../robot-london-v3/PASSATION.md)
prépare la phase 11. Aucun code de cette phase, aucune donnée réelle, aucun
appel LLM ou courtier ni qualification de rentabilité n’est inclus. Les quinze
modifications initiales sont conservées hors du commit. La clôture comprend
l’audit bidirectionnel, un commit français et le contrôle du même arbre sur
origin/master avant l’arrêt.
