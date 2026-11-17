# Couche 0 — configuration d'application (contrat avant code)

Responsabilité pure : valider les registres et produire les gabarits, sans lire
de fichier, d'environnement, d'horloge ou de terminal. CF est la vraie
ConfigurationFigee. `analyser_registre(document, configuration, instant_ms,
qualification=False)` produit ConfigurationApplication immuable ou
ErreurApplication. Les clés inconnues, types approximatifs, placeholders,
empreintes étrangères, dates futures, symboles non liés ou doublons natifs
sont refusés. Les chemins ne désignent jamais .env ; la frontière physique
vérifie de nouveau le chemin résolu. Aucun secret n'est accepté par le schéma.

Le registre xp-deploiement-v1 contient le déploiement, mode, commit, empreintes
des deux exports, liaisons et preuves du choix C04, chemins, table S01 et preuve
de qualification référencées, historique requis, constantes d'ingénierie,
scénario fondamental, activation du veto, statut A13 et décisions datées.
Mode absent interdit ; le gabarit lit default_evaluation_mode dans CF. DEMO et
REEL refusent TECHNICAL_CONTROL_NEUTRAL. REEL exige une décision de déploiement
datée, liée au commit et aux empreintes, avec preuves C10 réservé et démo.
Le veto natif exige aussi la décision A13 liée au même gel. La qualification
en lecture seule peut inspecter l'environnement sans autoriser l'exécution.
Le type de compte réel est contrôlé à la frontière SessionMT5, jamais déduit
de ces déclarations. Un registre ne démontre pas à lui seul une validation
financière : les commandes natives contrôlent les rapports référencés.

`gabarit_registre(configuration)` contient les constantes D-09, plafonds et
cadences d'export, les chemins sans secrets et les champs inconnus null ; il
est explicitement non exécutable avant qualification. `gabarit_fermetures()`
produit le schéma D12, sans affirmer une connaissance ou validité fictive.
`parametres_export(configuration, table, liaisons, ingenierie)` produit les
octets TSV UTF-8 LF acceptés par XPBotsExport ; la table S01 réelle est
vérifiée par TableHeureServeur, les limites UTC sont des secondes exactes,
aucun offset ni DST n'est deviné. Le calendrier couvre au moins la somme
news_forward_coverage_seconds + news_calendar_max_age_seconds + cadence.
Le plafond propre au lecteur MQL5 est respecté. Un nom pouvant injecter une
ligne ou sortir du dossier d'export est refusé. Pas de copie d'un seuil métier.
`ingenierie_par_defaut()` expose une copie immuable des constantes pour borner
les lectures initiales, avant que CF et le registre puissent être chargés.

Tests : mode réel sans décision, veto non qualifié, neutralité native refusée,
empreintes et dates, typage strict et mutation d'entrée sans effet sur l'objet,
gabarits sans secret et non exécutables, TSV consommable et jonction C05 sur
l'horizon glissant. Régression intégrale avant gel 0.
