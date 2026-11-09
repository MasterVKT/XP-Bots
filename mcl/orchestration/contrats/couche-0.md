# Couche 0 — Contrats d'orchestration

Finalisé avant code le 09/11/2026. Consommateurs : bras 1 et moteur 2.

| Élément | Contrat |
|---|---|
| Unité | contrats_orchestration |
| Responsabilité | Définir les fabriques et déploiements injectés, entrées causales et sorties par bras |
| Signature | Strategie ; FabriqueStrategie ; Deploiement ; ReceptionExterne ; MiseAJourBras ; EntreeMoteur ; SortieMoteur ; SortieEvenement |
| Entrée | Types publics des six artefacts amont gelés, horodatage et numérotation UTC explicites |
| Sortie | Valeurs immuables, collections copiées, identités et frontières vérifiées |
| Effets de bord | Aucun, aucune fabrique appelée par les types |
| Erreurs | ErreurOrchestration(ValueError) pour incohérence ; booléens exclus des entiers |

Strategie est le protocole structurel identifiant, sur_bougie(bougie) et sur_issue(issue).
Une fabrique nommée construit, plus tard en 1, une stratégie depuis ConfigurationFigee et une
table de taille de tick réduite à un symbole. Une instance distincte est requise par méthode,
symbole et bras. Aucun import de moteur de méthode. Deploiement(identifiant, mode, fabriques,
tailles_tick, longueur_empreinte) copie ses collections ; noms uniques non vides UTF-8, tailles Decimal
finies positives, mode et noms de bras viennent du journal canonique. Pas de valeur normative
recopiée. La longueur est fournie par la composition qualifiée, pas choisie par ce composant.

ReceptionExterne(nature, octets=b'', symbole=None, table=None) porte PERMISSION, CALENDRIER,
INTERRUPTION ou SNAPSHOT. Calendrier exige la vraie TableImportance ; permission/interruption
un symbole ; interruption sans octets ; snapshot accepte aussi None pour absence. Ces types
ne valident pas les formats métier : le moteur 2 passe les octets aux vrais contrôles C05/IA.
La réception réelle est l'instant du cadre EntreeMoteur, jamais une date inférée du payload.

MiseAJourBras(reponses=(), observation=None, base_utc=None, preuve=None) garde les types réels
C08, BaseReconstituee ou RefusExecution. EntreeMoteur(instant_ms, numero, nature='MINUTERIE',
ticks=(), mises_a_jour=(), receptions=()) a un numéro entier positif ; les noms de bras sont
uniques et connus. Nature TICKS exige des ticks d'un même instant de réception, MINUTERIE
n'en a pas, PERSISTANCE exige une preuve et interdit ticks, réponses et observations. Les
preuves sont donc traitées séparément des faits natifs, déjà reçus et rapprochés avant elles.
Les réponses/observations/bases futures sont refusées. Les réceptions externes restent possibles
à toute nature, notamment avant la revalidation. Le moteur 2 contrôle progression et relecture.

SortieMoteur(enregistrements, commandes, lot=None) utilise les vrais Enregistrement,
CommandeExecution et LotCoordinateur ; collections immuables. SortieEvenement(numero,
instant_ms, sorties=(), ignoree=False) étiquette chaque sortie par son bras unique ; par_bras
est une vue non modifiable, enregistrements agrège seulement les traces déjà étiquetées C09.
Une sortie ignorée ne contient ni commande ni enregistrement, pour éviter toute réémission.
Les types C08 et de calendrier sont des amonts de la feuille 0, pas des unités locales simulées.

Extension tracée du 09/11/2026, document 01 §9.2 et C11.14 : AppelCalcul(nom, arguments,
options, resultat) conserve un appel aux sept méthodes de CalculCourtier et son résultat
normalisé par appeler_calcul. Les arguments sont ceux des types publics immuables ; options
nommées uniques, résultat réel Decimal fini, type natif attendu ou RefusExecution. Une erreur
de frontière est déjà normalisée ; aucun message d'exception brut ni secret n'est enregistré.
EntreeJournalisee(entree, calculs) relie une EntreeMoteur aux suites d'AppelCalcul par bras,
sans mélanger leurs comptes. Les appels d'initialisation sont conservés séparément des cadres.
Ces deux ajouts ne modifient aucun type existant. Le bras 1 produira/lira ces traces, le moteur
2 les rattachera aux événements pour le rejeu d'incident sans interrogation du courtier.

Tests propres : test_cat1_c0_contrats.py. Les amonts sont réels ; aucun test catégorie 2 ne
simule une dépendance locale inexistante à cette feuille. Les jonctions sont testées à 1 et 2.
