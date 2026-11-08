# Contrat de la couche 5a — sorties obligatoires

Statut : finalisé le 07/11/2026 avant construction, après gel de 4.
Unité : sorties_obligatoires ; consommateurs cartographiés : coordinateur 6.
Responsabilité : sélectionner les demandes de clôture obligatoires C08 pour les seules positions possédées du cycle réel.
Signature : `SortieObligatoire(cle, cause, priorite, motif=None, detail=None)` ; `PlanSorties(demandes=(), prochaine_echeance_ms=None, refus=None)` ; `evaluer_sorties(cycles, technique, profils, gardes, fondamental, instant_ms)`.
Entrée : cycles réels, export technique chargé, profils par symbole, gardes réelles, port C05 et instant de connaissance.
Sortie : une demande prioritaire par cycle ouvert ; première échéance future ; refus d'environnement si une information obligatoire manque.
Effets : aucun changement de cycle, de compte ou de réservation ; le port fondamental est la seule frontière interrogée.
Erreurs : `ErreurExecution` pour type, doublon ou instant invalide ; panne de port → refus déterministe sans supprimer les demandes temporelles ou de sécurité.

La priorité stable est : arrêt global, verrou quotidien, protection, risque après remplissage, FLATTEN, annonce HIGH, heure locale, durée, fermeture native, blackout. Les quatre dernières échéances proviennent exclusivement de la vraie couche 0e ; en cas d'égalité, cette priorité départage sans changer l'instant. Un SL/TP déjà exécuté (volume nul) écarte toute demande.

Les décisions C05 sont lues pour chaque position ouverte. Une décision `cloture_obligatoire` vaut FLATTEN uniquement pour `FUNDAMENTAL_DIRECTION/RISK_STATE_FLATTEN`, ou annonce pour `NEWS_WINDOW/ANNONCE_HIGH`. Une permission absente, périmée ou NO_NEW ne liquide pas arbitrairement une position. Un port mal formé ou une incohérence avec sa liste de clôtures bloque les entrées par `ENVIRONMENT_NOT_READY/controle_fondamental`. Aucun lecteur C05 n'est construit ici.

Une échéance native impossible à déterminer demande une clôture de sécurité `PROTECTION` avec le refus d'environnement de 0e. Sans cotation, la demande reste présente ; 4 gère l'envoi, les nouvelles tentatives et la confirmation native. L'appelant exécute les réponses natives avant cette évaluation, puis les demandes avant toute nouvelle admission. Les changements C05 sont fournis comme événements ; 6 les réévalue aussi sur les minuteries des positions.

Tests : catégorie 1, bornes de durée, horaires Londres été/hiver, fermeture native, égalités, gardes prioritaires, FLATTEN/annonce et panne C05. Catégorie 2, vrai bloc 0–5a, sortie sans cotation, protections maintenues, confirmation native avant libération de réserve, arrêt persistant après reprise.
