# Plan MCL — orchestration commune, phase 9 London

## 0. Périmètre et applicabilité

Composant pur de l'application composite London, trois unités 0 → 1 → 2. Sa structure est
connaissable, ses contrats déterministes et ses dépendances disponibles et gelées : MCL est
applicable sans exploration métier. Il remplace S4, avec couture S5/S7 pour PAPER_AB. Le retour
de bout en bout reste assuré par le squelette. Ni C10, ni source physique, ni service distant.

## 1. Cadre et sources

Finalité : un même moteur événementiel en rejeu et en direct, avec port de stratégie injecté
(D-18) et états de compte indépendants. Entrées : ticks, réponses et observations natives,
preuves de persistance, permissions/calendrier/snapshots reçus. Sorties : commandes et C09
par bras, prochaine échéance et état pur. Python 3.13, bibliothèque standard, aucune horloge,
aucun réseau. Références métier : C08/C09/C11.10/14, A01/A03/A07/A12/A13, A14-9/17, document
02 §6.7 et fiche de phase 9. Aucun paramètre ni contrat amont n'est modifié.

## 2. Coexistence et responsabilités

L'arbitrage R4/R5 est tracé avant code dans COEXISTENCE_ROBOT1_LONDON. Le dossier orchestration
était absent ; le paquet ne contenait que la couture S4. Le bloc est commun aux deux lignées,
avec leurs socles conservés. Le noyau canonique et le coordinateur commun sont utilisés.
Les six artefacts amont sont gelés et la baseline passe 851 tests. Les quinze modifications
initiales sont enregistrées par empreinte et exclues de la publication. Aucun appel LLM/courtier.

## 3. Cartographie et question-test

| Unité | Responsabilité | Objets intermédiaires | Constructible sans les autres ? |
|---|---|---|---|
| contrats | Ports de stratégie/fabrique, déploiement, événement et sorties typés | Deploiement, EntreeMoteur, ReceptionExterne, MiseAJourBras, SortieMoteur | Oui : types des artefacts amont gelés seulement |
| bras | Composer stratégies indépendantes et coordinateur, router issues et journaliser | EtatBras, historique public de stratégie, lots du coordinateur | Non : dépend des contrats |
| moteur | Recevoir un événement commun, C03/C05, ordre C08, dispatcher les bras | état de flux, état global, journal d'entrées, sorties étiquetées | Non : dépend du bras et des contrats |

0 est la feuille relative aux unités nouvelles, et non un noyau sans dépendance du dépôt.
Les types publics C08 et de classification de calendrier sont des amonts explicites de 0.
Une profondeur ne suit donc pas le flux d'exécution. Graphe : bras → contrats ; moteur → bras,
contrats. Aucun cycle, aucun parallèle interne. Les imports directs vers chaque amont sont
déclarés, y compris les types. Aucun moteur London, EMA ou V1 n'est importé.

## 4. Carte encodée

`carte.json` impose six règles strictes : invariant, parallèles, externes, cycles, divergence
et contrats figés. Les sources c0/c1/c2 sont communes. La couture squelette.py est exclue du
dossier composant et reste hors gel. Les deux composites pointent ce bloc, sans achèvement
supplémentaire EMA. La dépendance aux données canoniques est explicite dans le composite EMA.

## 5. Contrats

Esquisses des trois fiches créées avant source ; chaque contrat est finalisé avant sa couche,
puis gelé avec interface et tests des deux catégories. Les données reçoivent un instant UTC
et un numéro stable. Une réception externe garde ses octets à l'instant réellement connu.
Les réponses, observations et preuves appartiennent à un bras explicite ; aucun mélange des
deux comptes. REFERENCE a le complément absent ; IA reçoit le lecteur réel facultatif.

## 6. Frontières externes

Les seules doublures concernent transport/calcul courtier, stockage, arrivées externes et
fabriques de stratégie contractuelles pour les tests propres ; toutes les couches internes
C03/C05/C08/IA sont réelles. Les jonctions utilisent le vrai London injecté, avec une nouvelle
instance par méthode, symbole et bras. Les transports papier indépendants et la transaction
mémoire restent ceux du squelette. Une panne de stockage interdit les entrées et laisse les
sorties. Aucun fichier, horloge, terminal ou appel distant dans le composant.

## 7. Construction

0 : contrats et types ; 1 : bras ; 2 : moteur. Deux catégories exactement : contrat propre et
jonction sur le bloc réel. Commandes : `python tools/run_london_tests.py --artefact orchestration
--couche <id> --categorie <1|2>`. À chaque gate : suite intégrale des deux robots par
`python tools/run_london_tests.py`, puis `python tools/verify_project.py`. Aucun changement
d'arbre entre gate et gel. Le contrôle Git des nouveaux fichiers précède chaque gel.

## 8. Reprise et causalité

Les stratégies sont reconstruites en rejouant leurs bougies et issues publiques, en comparant
les résultats, sans lire de champ privé ni modifier leur contrat. Les états de coordinateur
et de flux viennent de leurs exports publics. Aucun nouveau signal rétroactif au redémarrage ;
la reprise C08 garde son rapprochement natif et ses refus de préparations périmées.
Les historiques en mémoire ne sont pas arbitrairement tronqués ; leur stockage durable est
futur. Un nouveau moteur reçoit le journal complet d'entrées typées et rend les mêmes sorties,
sans réinférence. Les réceptions externes font partie de ce journal. La répétition exacte du
dernier numéro est ignorée sans réémettre de commande ; recul ou réécriture sont refusés.

## 9. Acceptation et couture

Ordre C08 : réceptions mises en mémoire, faits natifs et sorties obligatoires pour chaque
bras, puis construction unique des bougies partagées, puis signaux simultanés de toutes les
méthodes remis ensemble au coordinateur, puis preuve et revalidation avant envoi. H1 précède
M15 à clôture égale. La preuve est un événement distinct ; elle ne modifie pas un autre bras.
C11.10 : priorités et risque au compte via le coordinateur réel. C11.14 : mêmes événements,
mêmes sorties. A14-9 : risque, protections, sorties et refus du socle inchangés avec IA.
A14-17 : comptes démarrant chacun au capital configuré, positions et quotas indépendants.
La couture conserve le mode simple et ajoute PAPER_AB sur une vraie journée London ; le
moteur unique remplace la logique S4. La CLI reste une coquille de composition explicite.

## 10. Checkpoint et coût

Après le niveau 2 : revue et gate global avec checkpoint, enveloppe déjà figée. Trois gates
intégraux, au moins un gate global, campagnes de mutations et archive de publication sont
prévus. Le coût des gates est cumulatif ; les historiques de reprise consomment de la mémoire.
Ces coûts ne prouvent aucune supériorité statistique de MCL. Les évolutions éventuelles d'un
contrat gelé passent par défigeage formel ; aucun défigeage amont n'est anticipé.

## 11. Clôture

Mutations par couche et couture sur copies jetables, copie saine d'abord, suite intégrale
et détection fonctionnelle exigée. Gate global, cartes, statuts, plan, ressources, gouvernance
et portes machine. Audit bidirectionnel ; arbre préparé testé en archive, même arbre au commit
et sur origin/master. Bilan, directeur 1.4.10, passation phase 10, commit français et push.
Puis arrêt avant la phase 10. Les ressources protégées et modifications initiales restent intactes.

## 12. Bilan

Les trois couches ont été construites dans l’ordre des dépendances. Les esquisses,
puis chaque contrat final, ont précédé le code correspondant. Les suites propres
et les vrais chemins de jonction ont été exécutés avant chaque gate intégral et
chaque gel immédiat. Les six amonts restent gelés sans modification de contrat.

| Couche | Catégorie 1 | Catégorie 2 | Dernier gate avant gel |
|---|---|---|---|
| 0, contrats | 16 | Sans jonction entre nouvelles couches | 881 tests et 30 contrôles projet, 288 de référence |
| 1, bras | 16 | 3 | 886 tests et mêmes contrôles métier |
| 2, moteur | 12 | 3 | 901 tests et mêmes contrôles métier |

La couche 0 initiale avait passé 865 tests, la couche 1 initiale 879. La lecture
de l’exigence de rejeu du document 01 §9.2 a conduit à deux défigeages `extension`,
tracés par l’outil : types AppelCalcul/EntreeJournalisee en 0, port de calcul tracé
et journal de clôture en 1. Chaque extension a repassé son gate et a été regelée
avant la construction de 2. Il ne s’agit ni d’une seconde couche de calcul
financier ni d’un changement du coordinateur : CoordinateurTrace hérite de C6
sans surcharger ses comportements métier. Les erreurs du backend sont normalisées
par le vrai appeler_calcul ; le rejeu valide sa transcription hors de sa capture
d’exceptions afin qu’une divergence ne soit pas avalée.

Le gate global après couture passe 908 tests ; le checkpoint après 2 est journalisé.
Les 50 tests propres comptent 44 catégorie 1 et 6 catégorie 2. Les sept nouveaux
tests du squelette portent sa suite à 67, sans retirer de cas. Ils vérifient la CLI
PAPER_AB sur une journée, L-15 London été/hiver, le journal avec C05/IA exactement
rejoué sur backend interdit, un stop natif simultané à FLATTEN et une clôture M15,
l’indépendance des stockages, les sorties malgré une panne après fill et le refus
d’un stockage partagé. Les tests antérieurs simples et C05/IA restent verts.

Les bougies sont construites une fois et partagées par identité ; les stratégies
et comptes sont distincts. C11.10 injecte deux méthodes contractuelles à la
frontière de stratégie et utilise le vrai coordinateur : London puis EURUSD,
réservations relues et refus SYMBOL_BUSY de la seconde méthode. L’ordre de
réception des ticks explique celui des fills ; l’ordre des demandes vérifie la
priorité. Le moteur EMA historique n’est pas recâblé. Les jonctions London et les
journées A/B utilisent la vraie fabrique S02, sans doublure interne.

La reprise passe par les API publiques des stratégies, de C03, C05, du cache IA et
de C08. Elle ne consulte aucun champ privé amont. Les états et leurs scellements
sont purs ; le journal d’entrées garde tous les calculs et réceptions. Les tests
de rejeu interdisent toute méthode du backend, y compris l’état du compte, et
comparent les commandes et enregistrements complets. Les paramètres initiaux et
les résultats d’initialisation sont nécessaires à cette reproduction.

| Identifiant | Type et preuve | Correction et validation |
|---|---|---|
| P9-01 | Divergence de carte : le premier gate 0, à 862 tests, a révélé l’import préexistant du calendrier canonique par le coordinateur dans la lignée EMA | Dépendance C03 déclarée explicitement pour ce consommateur et l’orchestration ; règles strictes conservées ; nouveaux gates verts |
| P9-02 | Omission détectée à la conception de 2 : le rejeu devait inclure les calculs courtier | Deux extensions formelles 0/1 avant source 2 ; tests sur backend interdit et rejeu complet |
| P9-03 | Défauts locaux avant gel 2 : horodatage fourni deux fois à une alerte et assertion confondant ordre des fills et ordre des demandes | Horodatage dans l’enveloppe ; priorité vérifiée sur les commandes et ensemble des fills ; tests propres et gate 901 verts |
| P9-04 | Couture : mauvais objet fourni au chargeur IA par défaut, puis trois dépendances directes de S7 absentes de la carte | ConfigurationFigee réelle fournie ; dépendances 2b/3a/3b déclarées ; CLI, cartes et gate 908 verts |
| P9-05 | Fixture S2 annonçant ESPION alors qu’elle rendait des résultats London | Identifiant aligné sur la vraie stratégie enveloppée ; contrat strict conservé et anciens tests verts |

La recherche d’impact combine les usages `rg`, les sources courantes et le graphe
incrémental : six sources critiques, 175 nœuds directement changés, 586 nœuds
impactés dont la sortie de l’outil est bornée à 500, et 73 fichiers supplémentaires.
La suite intégrale des deux lignées est la preuve de non-régression ; le graphe
seul n’établit pas une couverture exhaustive.

Les commandes reproductibles sont `python tools/run_london_tests.py`,
`python tools/verify_project.py`, `python tools/verifier_plan_london.py`,
`python tools/verifier_mutations_orchestration_phase9.py --ouvriers 1`, les
commandes MCL `verifier` et `statut`, et la suite de gouvernance commune. Les
résultats courants sont conservés sous `.local/reports/`, jamais dans les preuves
historiques protégées. Le contrôle de publication extrait les seuls blobs de
l’index avec `git -c core.autocrlf=false archive` ; les quinze modifications
initiales de l’utilisateur restent intactes et hors commit.

Limites : transport et transactions papier synthétiques, remplissage au prochain
tick et frais nuls déclarés ; aucune validation C10, statistique ou de rentabilité.
Les compositions à plusieurs méthodes ou symboles utilisent des fabriques ;
l’ancienne injection d’une instance de stratégie dans S4 est conservée pour un
seul symbole, afin de respecter l’indépendance des instances.
Les historiques complets en mémoire ont un coût croissant et ne sont pas un
stockage durable. Le scellement ne constitue pas une authentification. Le service
IA, MT5, les sources physiques et la qualification restent aux phases prévues.
Le directeur est 1.4.10 et la passation prépare uniquement la phase 10, sans la
commencer. La vérification adversariale et les contrôles de publication complètent
ce bilan avant la livraison.

### Vérification adversariale et livraison

La copie saine passe les 908 tests. Les sept mutations sont toutes détectées par
des tests fonctionnels, avec suite intégrale pour chaque variante : une mutation
en 0, deux en 1, une en 2 et une pour chacune des coutures S4/S5/S7. Aucune
survivante, aucun défaut de ressource accepté comme détection. Les sources du
dépôt ne sont jamais mutées ; les copies jetables sont bornées hors du dépôt.
Les empreintes de la cohorte sources/tests/outils/exports/cartes sont vérifiées
jusqu’à la publication. Aucune correction supplémentaire du bloc gelé n’est requise.

| Mutation | Preuve fonctionnelle |
|---|---|
| 0_nature_ticks_incoherente_admise | 1 échec(s), 0 erreur(s), suite complète exécutée |
| 1_ia_branchee_en_reference | 1 échec(s), 0 erreur(s), suite complète exécutée |
| 1_rejeu_consulte_backend | 1 échec(s), 3 erreur(s), suite complète exécutée |
| 2_repetition_retraitee | 0 échec(s), 1 erreur(s), suite complète exécutée |
| S4_reponses_minuterie_perdues | 2 échec(s), 0 erreur(s), suite complète exécutée |
| S5_octets_snapshot_perdus | 9 échec(s), 0 erreur(s), suite complète exécutée |
| S7_port_ia_non_branche | 1 échec(s), 7 erreur(s), suite complète exécutée |

Une sonde complémentaire reprend les deux bras avec C05 et veto IA actifs : les
états publics restaurés, les flux et le journal restent concordants. Les 185
fichiers de contrats gelés correspondent aux empreintes MCL et aux blobs Git LF.
Les types de tâches sont couverts par MCL, planification, London, risque/exécution,
contrats IA, causalité, cohérence, gouvernance et audit ; aucune lacune réutilisable.
La skill d’expertise externe n’étant pas disponible, la lecture du document 05
§1.2–1.4 tient lieu de relecture d’expert, sans arbitrage métier improvisé.

La livraison passe par le gate global, les 17 cartes et sept statuts gelés, le
plan, les portes explicites et la gouvernance complète, puis les deux suites et
la gouvernance sur l’archive exacte de l’index. L’audit de publication exige leur
succès, l’identité des arbres testés et publiés et une nouvelle lecture distante.
Ces preuves courantes sont sous .local/reports/ ; aucune preuve historique n’est
réécrite. Le compte rendu final ne déclare la phase achevée qu’après ces contrôles.
