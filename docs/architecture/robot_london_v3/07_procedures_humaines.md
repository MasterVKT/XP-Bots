# 07 — Procédures des actions humaines

Retour au [plan directeur](README.md). Les règles du projet réservent certains gestes à l'humain : ouvrir un
compte, utiliser ses identifiants, travailler sur son poste Windows, fournir ses données privées, annoter,
décider d'une mise en service ([règles du projet](../../../.agents/PROJECT_RULES.md), §4 ; skill
`xp-bots-deployment-readiness`). Ce ne sont pas des inconnues de conception : chaque geste a ci-dessous sa
procédure, son critère de vérification et le comportement prévu s'il n'est pas accompli.

Règles communes à toutes les procédures :

- Ne jamais transmettre à l'agent, ni coller dans une conversation, ni écrire dans le dépôt : mot de passe,
  identifiant de connexion du courtier, numéro de compte, clé d'API.
- Ne jamais lancer une commande fournie par l'agent sur un compte réel : vérifier d'abord, dans le terminal,
  que le compte connecté est un compte de démonstration.
- Renvoyer à l'agent les rapports produits dans `.local/reports/` après les avoir relus : ils ne doivent contenir
  aucun secret.

## H-01 — Demander la phase suivante

- **Quand** : à la fin de chaque phase et de chaque sous-étape de la phase 13.
- **Étapes** : lire le rapport d'arrêt de la phase ; demander des corrections si besoin ; sinon écrire
  « passe à la phase N » (ou « passe à la sous-étape 13.k »).
- **Vérification** : la phase suivante commence par le relevé de l'état initial (document 04, gabarit commun).
- **Si l'action manque** : l'agent reste arrêté.

## H-02 — Préparer le poste Windows

- **Quand** : avant la phase 11.
- **Prérequis** : Windows 10 ou 11 en 64 bits ; dépôt déjà présent dans `D:\PROJETS\XP-Bots`.
- **Étapes**
  1. Installer Python 3.13 en 64 bits depuis python.org, en cochant l'ajout de `python.exe` au `PATH`. Vérifier
     dans PowerShell que `python --version` affiche 3.13 et que
     `python -c "import platform; print(platform.architecture()[0])"` affiche `64bit`.
  2. Vérifier que Git for Windows est installé (Git Bash est requis par les hooks de Claude Code sous Windows,
     voir [CLAUDE.md](../../../CLAUDE.md)).
  3. Dans `D:\PROJETS\XP-Bots` : `git fetch origin`, puis se placer sur la branche de travail indiquée dans le
     dernier rapport de phase.
  4. Créer un environnement local ignoré par Git : `python -m venv .venv`, l'activer avec
     `.venv\Scripts\Activate.ps1`, puis `python -m pip install -r requirements-dev.txt`. En phase 11, installer
     aussi le fichier d'exigences Windows ajouté par l'agent (`MetaTrader5` et `tzdata`).
  5. Donner l'accès à l'agent, au choix : (a) partager le dossier du dépôt avec la session par Remote Control
     (application Claude pour ordinateur : Paramètres, Claude Code, Remote Control), l'agent demandant ensuite
     l'accès, que l'humain accepte ; (b) exécuter soi-même les commandes que l'agent fournit et lui renvoyer les
     rapports.
- **Vérification** : `python tools/verify_project.py` et `python tools/run_robot_tests.py` affichent `PASS`
  sur le poste.
- **Si l'action manque** : la phase 11 s'arrête sur question ; les phases 0 à 10 n'en dépendent pas.

## H-03 — Ouvrir le compte de démonstration Deriv MT5

- **Quand** : avant la phase 11 (D-13).
- **Étapes**
  1. Dans l'espace client Deriv, ajouter un compte MT5 de **démonstration** de type standard (marchés
     financiers), en USD.
  2. Choisir un levier de 1:100 si l'offre le permet ; sinon noter le levier imposé. Le robot relit le levier et
     refuse de démarrer s'il diffère de `account_leverage` (C04) : il faut alors un autre compte démo.
  3. Installer le terminal MetaTrader 5 proposé par Deriv et s'y connecter au serveur de démonstration indiqué ;
     les identifiants restent dans le terminal.
  4. Dans le terminal, menu Outils, Options, onglet Expert Advisors : autoriser le trading algorithmique ; activer
     le bouton « Algo Trading » de la barre d'outils. Sans lui, le paquet Python ne peut pas envoyer d'ordre de
     démonstration.
  5. Dans l'Observation du marché (clic droit, Symboles) : afficher EURUSD, GBPUSD, XAUUSD et leurs variantes
     micro si elles existent.
  6. Garder le terminal ouvert et connecté pendant les séances d'essai.
- **Vérification** : statut de connexion actif dans le terminal ; le rapport de qualification de l'agent
  (`cli_qualification`) lit le compte sans erreur de devise, de levier ni de connexion.
- **Si l'action manque** : aucune sonde ni aucun test de contrat MT5 ; la phase 11 s'arrête sur question.

## H-04 — Compiler et lancer le service MQL5 `XPBotsExport`

- **Quand** : en phase 11, après l'écriture du service par l'agent (D-12).
- **Étapes**
  1. Dans le terminal : Fichier, Ouvrir le dossier des données ; aller dans `MQL5\Services` ; y copier
     `mql5\Services\XPBotsExport.mq5` du dépôt.
  2. Ouvrir MetaEditor (touche F4), ouvrir le fichier, compiler (touche F7). Exiger zéro erreur et zéro
     avertissement ; sinon, transmettre à l'agent le journal de compilation.
  3. Dans le Navigateur du terminal, section Services : clic droit sur `XPBotsExport`, ajouter le service, puis
     le démarrer.
  4. Vérifier la présence, dans `%APPDATA%\MetaQuotes\Terminal\Common\Files\XPBots\export\v1\`, de
     `calendrier.json` (mis à jour chaque minute) et d'un fichier `seances_<symbole>.json` par symbole lié.
- **Vérification** : test de contrat de l'export (H-07) vert ; comparaison faite par l'agent avec la vue
  calendrier du terminal.
- **Si l'action manque** : calendrier absent, donc aucune nouvelle entrée (`NEWS_WINDOW`, détail
  `CALENDRIER_PERIME`) ; horaires de séance absents, donc `ENVIRONMENT_NOT_READY`.

## H-05 — Tenir le fichier des fermetures exceptionnelles

- **Quand** : avant la première séance de la phase 11, puis à chaque avis du courtier.
- **Étapes**
  1. Copier le gabarit fourni par l'agent en phase 11 vers
     `%APPDATA%\MetaQuotes\Terminal\Common\Files\XPBots\export\v1\fermetures_exceptionnelles.json`.
  2. Renseigner la date de relevé et, pour chaque fermeture ou séance réduite annoncée par Deriv (fêtes de fin
     d'année, jours fériés), le symbole, le début et la fin en UTC, et la source (lien ou date de l'avis).
     Une liste vide reste valide si la date de relevé est renseignée.
  3. Relire les avis du courtier au moins chaque semaine et mettre à jour la date de relevé.
- **Vérification** : le robot valide le fichier au démarrage ; un format invalide est refusé et journalisé.
- **Si l'action manque** : `ENVIRONMENT_NOT_READY` (C04 : aucun champ manquant ne vaut zéro).

## H-06 — Brancher le module fondamental externe sur le dossier d'échange

- **Quand** : en phase 11 (D-11).
- **Étapes**
  1. Remettre au responsable du module le contrat du [document 01](01_architecture.md), §2.1 : emplacement, un
     fichier par symbole, schéma `fundamental-permission-v1`, écriture atomique, séquence strictement
     croissante, horodatages UTC à la milliseconde, heartbeat et validité de C05.
  2. Configurer le module pour écrire dans
     `%APPDATA%\MetaQuotes\Terminal\Common\Files\XPBots\fondamental\v1\`.
  3. Lancer le module en même temps que le terminal.
- **Vérification** : sur une séance complète, le test de contrat (H-07) ne relève aucun message rejeté et aucun
  heartbeat manqué non expliqué.
- **Si l'action manque** : comportement sûr prévu : en `PAPER` et en `DEMO`, toutes les nouvelles entrées sont
  refusées (`FUNDAMENTAL_INVALID`) ; en rejeu, seul le contrôle technique explicitement nommé
  `TECHNICAL_CONTROL_NEUTRAL` reste possible.

## H-07 — Exécuter les sondes et les tests de contrat sur le poste

- **Quand** : en phase 11, marché ouvert, après H-02 à H-06.
- **Étapes**
  1. Avec l'accès (H-02, option a), l'agent exécute lui-même ; sinon, exécuter dans l'ordre les commandes qu'il
     fournit : une par sonde (S-01 à S-10, [document 01](01_architecture.md), §10), puis les tests de contrat
     avec la variable `XPBOTS_CONTRATS_MT5` à `1`.
  2. Vérifier dans le terminal que le compte connecté est le compte démo avant toute commande qui envoie un
     ordre.
  3. Renvoyer à l'agent le contenu de `.local/reports/qualification/`.
- **Vérification** : un rapport par sonde ; l'agent statue sonde par sonde avant de construire la couche
  concernée.
- **Si l'action manque** : les couches d'infrastructure ne sont pas construites ; la phase 11 s'arrête.

## H-08 — Autoriser ou non les appels d'API et fournir les clés gratuites

- **Quand** : au début de la phase 12, quand l'agent redemande l'autorisation (D-17).
- **Étapes en cas d'accord**
  1. Créer un compte gratuit Groq et un projet gratuit Google AI Studio (Gemini) ; générer une clé par service ;
     vérifier dans chaque console que l'offre est gratuite pour ce compte et relever les quotas affichés. Si la
     gratuité de Gemini n'est pas confirmée, ne pas créer de clé : la route reste désactivée (A02).
  2. Copier `.env.example` en `.env` à la racine (fichier ignoré par Git) ; renseigner `GROQ_API_KEY` et
     `GEMINI_API_KEY` ; laisser `OPENAI_API_KEY` vide et `XPBOTS_PAID_FALLBACK_ENABLED` à `0` ; renseigner
     `XPBOTS_COMMON_FILES_DIR` avec le dossier commun du terminal (`%APPDATA%\MetaQuotes\Terminal\Common\Files`).
  3. Communiquer à l'agent les quotas relevés, jamais les clés.
- **Vérification** : une requête de conformité réussie par route gratuite ; registre de budget à 0 USD de
  dépense payante.
- **En cas de refus** : comportement prévu par D-17 : service construit et testé hors ligne, laissé arrêté ;
  bras IA de `PAPER_AB` à `NEUTRAL`.

## H-09 — Fournir les données historiques de C10

- **Quand** : sous-étape 13.3 (D-14).
- **Étapes**
  1. **Ticks du courtier** : dans le terminal, menu Affichage, Symboles, onglet Ticks : choisir le symbole lié et
     un mois, demander les ticks puis les exporter en fichier ; répéter par mois et par symbole, du 02/12/2019 au
     03/11/2026, aussi loin que l'historique du courtier le permet. Noter la première date réellement
     disponible.
  2. **Si l'historique du courtier ne couvre pas toute la période** : prendre la source tierce (par exemple
     l'export de ticks Bid/Ask de Dukascopy) pour **toute** la période, sans mélanger deux historiques (C04) ; le
     rejeu est alors déclaré contrefactuel. Les ticks du courtier servent quand même à comparer les spreads sur
     leur période propre.
  3. Déposer les exports bruts dans `data/raw/exports/<source>/<SYMBOLE>/` (ignoré par Git) avec une note :
     source, fuseau d'origine, date de récupération, trous connus. L'agent les convertit au format canonique des
     [données requises](../../data/03_Donnees_Historiques_Requises_et_Validation.md), §2, dans
     `data/raw/ticks/`, avec manifeste SHA-256 (convertisseur `cli_donnees`, phase 11).
  4. **Caractéristiques datées** : pour chaque symbole lié, enregistrer la fiche Spécification du terminal (clic
     droit sur le symbole) et les frais publiés, datés ; à chaque changement connu, une nouvelle fiche.
  5. **Permissions historiques** : si le module fondamental a archivé ses messages avec `known_at`, les fournir en
     JSON Lines ; sinon, seul le contrôle technique neutre est mesurable (C10).
- **Vérification** : rapport de validation des données de l'agent vert (formats, ordre, trous, empreintes).
- **Si l'action manque** : aucun rejeu C10 ; la sous-étape 13.5 attend.

## H-10 — Fournir la spécification V1 London

- **Quand** : avant la sous-étape 13.4 (D-15).
- **Étapes**
  1. Dans `D:\PROJETS\XP-Bots-archives\2026-11-04_organisation\`, ouvrir `manifest_avant_nettoyage.json` et
     repérer l'entrée de la spécification V1 du London Breakout (dossier `livrables/`), comme le décrit le
     [registre de nettoyage](../../maintenance/NETTOYAGE_ET_MERGE.md).
  2. Copier ce seul fichier ; calculer son empreinte avec `Get-FileHash -Algorithm SHA256 <fichier>` et la
     comparer au manifeste.
  3. Le placer dans `docs/references/` du dépôt (contexte non normatif) et le commiter, ou le transmettre à
     l'agent avec son empreinte.
- **Vérification** : empreinte identique à celle du manifeste.
- **Si l'action manque** : rétention V3/V1 déclarée non applicable ; les autres critères de C10 restent évalués.

## H-11 — Annoter les 200 textes de la qualification A13

- **Quand** : sous-étape 13.6.
- **Étapes**
  1. Recevoir de l'agent une feuille CSV UTF-8 de 200 textes officiels collectés, chacun avec le texte exact
     transmis au modèle et des colonnes vides : classe d'événement, statut temporel, acteur, orientation,
     « événement matériel » (oui ou non), commentaire. Les sorties des modèles sont masquées.
  2. Annoter selon les définitions du schéma d'extraction et du prompt `fx-text-extractor-1.0`. L'échantillon
     préparé par l'agent couvre les catégories de A13.2 : décisions actuelles, décisions programmées, discours,
     négations, rappels historiques, propositions, traductions, tentatives d'injection.
  3. Faire trancher les cas douteux par une seconde lecture des sources officielles, jamais par un LLM.
  4. Rendre la feuille complétée.
- **Vérification** : 200 lignes annotées ; rapport A13 de l'agent (précision, rappel, citations vérifiées).
- **Si l'action manque** : fournisseurs `NON_QUALIFIE` ; aucun veto réel possible.

## H-12 — Décider des mises en service

- **Quand** : sous-étape 13.7, puis à chaque changement d'étape (démonstration prospective, réel).
- **Étapes**
  1. Lire la checklist go/no-go de l'agent : chaque critère de C10 et de A13, sa preuve, son verdict.
  2. Décider, puis consigner la décision (date, étape, périmètre, responsable) dans le registre de déploiement.
  3. Pour un passage en réel : ouvrir soi-même le compte réel ; le veto IA réel reste désactivé sans validation
     financière A13 ; un arrêt global ne se lève que par une nouvelle décision consignée.
- **Vérification** : décision présente au registre ; le robot refuse le mode réel sans elle.
- **Si l'action manque** : aucun passage en démonstration prospective ni en réel.
