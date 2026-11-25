# Couche 3 — planificateur

Contrat finalisé le 17/11/2026 après gel 2c, avant implémentation.
Consommateur : service. Dépend de types, validation, veto, routeur, collecteur
et registre budgétaire/noyau temporel publics ; ports transaction, horloge, calendrier mémorisé et
sélection d'archives. La couche ne contient aucune lecture disque ou réseau.

API prévue : CasDerive(case_id,dossier:bytes,attendu:bytes),
PlanificateurIA(ressources,depot,routeur,collecteur,horloge,calendrier,
*,cas_derives=(),routes_auditees=(),selectionner_evenements=None,selectionner_jobs=None),
collecter(), planifier(), executer_un(), evenements(instant_ms),
recevoir_metriques(metriques,*,decisions=()), reprendre().
Les routeur et collecteur sont les vrais types de couche2 ; les seules
doublures de test concernent HTTP, transaction, horloge et sources externes.

collecter appelle chaque feed réel admissible, archive les résultats puis
enregistre une extraction par ID nouveau frais et complet. Son ID déterministe
permet le partage EMA/London et empêche une seconde classification. Les dates
originales restent ; aucun UND/FUTURE/PARTIAL ou article déjà expiré ne devient
une annonce. La collecte et l'inférence sont exécutées par des boucles séparées
en4, aucune attente LLM n'entre dans un moteur de trading.

La priorité est article frais, briefing, journal, dérive, revue/recherche.
ZoneInfo vient de common.session_timezone, weekday() du calendrier London et
horaires de l'export. Brief et journal ont une utilité du créneau jusqu'au délai
de job exporté, sans rattrapage des créneaux passés au démarrage. Le suivi
persistent des slots empêche les doublons. Les faits du dossier sont datés et
connus : douze heures pour briefing, depuis minuit local pour journal, semaine
glissante pour revue. Aucun ancien avis IA ne remplace une preuve primaire.

Revue et cas de dérive sont des tâches logiques non urgentes, utiles jusqu'au
créneau hebdomadaire suivant. Chaque enfant JobIA possède son propre ID daté
et délai75s exporté. Aucune admission HTTP -> report au jour UTC suivant ;
une tentative réellement envoyée ne se transforme pas en nouvel appel gratuit.
Les jobs restant hors utilité sont annulés ; un démarrage ne vide pas une vieille
file en rafale. Les plafonds de chaque enfant sont ceux du registre réel2b.
Au plus un enfant de dérive en attente par fournisseur est créé ; son prochain
espacement et Retry-After sont vérifiés par l'API publique du registre commun
avant sa création, puis réadmis atomiquement par le routeur au moment d'envoyer.

Un résultat EXTRACTION ne produit un événement que via le validateur et le
constructeur2a réels, avec calendrier D12 et mapping connus à réception. Une
source calendrier absente/invalide donne zéro nouveau veto. Les preuves, hashes,
documents, résultats et instants sont archivés sans alias de dictionnaire.
Les événements gardent leur échéance originale, même après heartbeat/reprise.
GOLDEN, BRIEFING, JOURNAL et WEEKLY_REVIEW ne créent jamais de policy_event.

Les notes restent des observations. Les métriques fournies sont des agrégats
calculés par le code, strictement typés et datés, sans compte, solde, position
personnelle ou ordre. Les champs A10 et axes London A11 sont admis ; leurs chiffres
ne sont jamais remplacés par ceux d'une réponse LLM. Le dossier d'extraction
conserve ses quatre champs A05 sans prix ou portefeuille. Une métrique future
ou un champ personnel est refusé. Les IDs de preuve sont ceux réellement envoyés.

La note validée brute est conservée ; sa publication filtre les hypothèses au
plafond global mensuel. Les propositions admises deviennent des tickets versionnés
avec ID et validation_plan ; une proposition identique est dédoublonnée. La
note publiée et la note brute sont distinctes, les omissions sont des metadata
hors schéma de note. Aucun code, paramètre, modèle ou règle n'est modifié.

## Archives de métriques et de décisions

Chaque métrique exige exactement item_id, period (date ISO locale), strategy,
symbol, arm, net_pnl, trade_count, equity_drawdown, ai_cost_usd, known_at_ms,
dimensions, refusals, data_gaps. Les méthodes et symboles appartiennent aux
communs ; arm est REFERENCE ou IA. P&L signé fini et autres montants positifs
ou nuls sont des chaînes décimales ; compteurs sont des entiers naturels.
known_at n'est pas futur et period n'est pas postérieur à son jour local.
refusals est un dictionnaire de motifs/compteurs ; dimensions n'admet que
range_width_atr_h1, first_breakout_hour_london, direction, local_stop_distance,
market_cost_usd, new_signal_after_veto, blocked_winners, too_late_opportunities,
fill_ratio. Les valeurs sont scalaires explicites ; aucune donnée personnelle.
Le service ne transforme pas ces agrégats en chiffres prévus par un modèle.

Une décision exige exactement strategy, symbol, bar_close, baseline_reasons,
ai_reason, snapshot_id, arm, known_at_ms. La clôture et la connaissance sont
causales, les raisons sont textuelles ; l'identité du snapshot est conservée
comme fournie par le code (ou None), sans en inventer une autre.
L'identité de décision est dérivée du contenu canonique ; deux versions différentes
restent deux observations. Les décisions brutes ne rejoignent pas le dossier
A05. Les insertions sont atomiques et idempotentes ; un item_id métrique réutilisé
avec un autre contenu est refusé, jamais une réécriture de P&L antérieur.

Le corpus comporte zéro (manquant NON_QUALIFIE) ou exactement le nombre exporté
de cas fixes et uniques par fournisseur audité. Les dossiers et attendus passent
le validateur1b réel. Les quatre champs matériels sont comparés ; changer la
citation seule n'est pas une dérive matérielle. Plus d'un changement suspend
durablement la publication de ses vetos, y compris ceux déjà actifs, et alerte localement ; une semaine verte ne
réactive rien. Échec/API absent -> audit incomplet, jamais stabilité prétendue.
Nouveau modèle/prompt/schéma exige nouvelle qualification ; la signature
d'extraction est distincte des prompts de notes. Les sorties informatives
peuvent continuer. Ces fixtures ne qualifient ni sémantique ni finances.

reprendre ferme les RUNNING et anciennes attentes via le routeur, signale les
usages inconnus et recharge les événements déjà validés sans réinférence. Un
résultat sans preuve calendrier archivée ne permet pas d'inventer l'appariement
du passé. Le service4 suspend les nouvelles inférences si un coût ancien reste
inconnu, en maintenant heartbeat et événements non expirés.

Les sélecteurs optionnels rendent respectivement les événements actifs et les
JobIA en attente depuis SQL indexé ; le défaut de test traverse le vrai routeur
et la mémoire transactionnelle. Ils ne remplacent ni priorités, ni validation,
ni admission, ni calcul de fenêtre. Les deux catégories testent les jonctions
réelles, l'été/hiver, les limites, la reprise et la dérive persistante.

Corrigé le 25/11/2026 (défigeage correction A12/A13) : evenements filtre les
fournisseurs suspendus au moment de la publication, y compris avec sélecteur
SQL, sans supprimer ou réécrire leurs preuves archivées. Reprise et heartbeat
ne réactivent pas un événement dont la fenêtre est encore ouverte. Les sorties
informatives continuent. Les deux causes, changement de modèle et dérive,
sont vérifiées sur un veto construit avant la suspension.
