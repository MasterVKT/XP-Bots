# Couche 3 — composition du courtier MT5

Contrat finalisé le 14/11/2026, avant code, sur les quatre adaptateurs réels
gelés. Le checkpoint CP2 est validé. Les parents session, types et horloge
sont déclarés dans la carte avant l'implémentation de cette composition.

CourtierMT5(session,commun,table,liaisons,horloge,instant_ms,*,qualification,
departs_ticks_utc_ms,depuis_historique_compte_utc_ms,seances_max_age_ms,
fermetures_max_age_ms,max_jours_horaires,ecart_horloges_max_ms,taille_lot,
max_ticks_lot,longueur_empreinte,max_taches_natives,etat=None) construit une
seule instance réelle de SpecificationsMT5, FluxMT5, ExecutionMT5 et CalculsMT5.
Tous partagent la session, la table qualifiée et les liaisons fixes injectées.
Pas d'import SDK, d'horloge physique directe, de fichier ni de nouvelle règle
de risque. Les callbacks de calcul sont ceux des instances publiques réelles :
preuve et profil de specifications ; proprietaire et flux_externe d'execution.
La composition n'inspecte aucun attribut privé d'un composant enfant.
P11-20 : `specifications.convention_ticks(historique)` fournit la convention
qualifiée C04 explicite, propagée à FluxMT5 et ExecutionMT5. Le décalage D12
ne détermine pas celui du flux SDK ; aucun choix manquant n'est remplacé par
un défaut dans cette composition.

Les propriétés publiques specifications, calculs et execution exposent les
composants réels nécessaires à la coquille. profil_compte(t),
convertir_serveur(texte), recevoir_exports(t,*,seances,fermetures) délèguent
aux API 2a ; actualiser_instant(t) lie le port de calcul à l'événement courant.
Les instants sont monotones ; une reprise future, une configuration étrangère,
un état partiel ou un schéma différent sont refusés avant toute émission.

lire_marche() date d'abord la demande, consulte les preuves S08 courantes et
le vrai flux 2b, puis date la connaissance après le retour SDK par HorlogeSysteme.
Le LotMarcheMT5 public expose instant_ms, ticks, couvertures, erreurs et a_jour.
Les ticks gardent fournisseur, numéro, prix et occurrences, mais leur réception
est la fin de la lecture physique. La couverture reste celle réellement prouvée
par 2b, sans prolongement jusqu'au nouvel instant de réception. Une preuve
S08 expirée rend un lot bloquant, sans couverture inventée. La qualification
structurelle historique sert seulement à construire les callbacks et les
curseurs ; elle n'est jamais publiée comme une qualification courante.

collecter(), observer(*,depuis_flux_ms=None), preparer_entrees(commandes,t),
autoriser_entrees(preuve), soumettre_defenses(commandes,t) délèguent à 2d.
Les deux lectures physiques synchronisent ensuite l'instant du port de calcul
avec leur réception réelle. La preuve native reste celle du COMMIT physique,
aucune traduction d'une preuve du cœur n'autorise directement un order_send.
fermer(attente_ms) joint seulement les tâches natives, sans fermer une session
appartenant à l'assemblage et sans tuer une tâche inconnue.

exporter_etat() rend exactement schema=xp-courtier-mt5-v1, dernier_ms,
specifications, flux et execution. Chaque état enfant est l'export public réel ;
aucun journal n'est dupliqué et les fraîcheurs ne sont jamais renouvelées par
le redémarrage. La restauration des commandes reste inconnue jusqu'au
rapprochement du processus courant. Elle ne retransmet aucune entrée.

Catégorie 1 : câblage des vrais composants, validation d'état, horloges de
réception, S08 expirée, lecture et reprise sans doublon ni rafraîchissement.
Catégorie 2 : coordinateur et calculs natifs sur cette composition, réception
des exports, flux réel 2b, persistance et reprise du bloc réel ; seul le SDK
est doublé. Aucun ordre ni terminal réel pendant les gates.
La jonction P11-20 exerce séparément UTC et SERVEUR_S01 avec une table D12
à +2 h : tick fournisseur normalisé, entrée après deux COMMITs, reprise du
curseur sans doublon, puis clôture FLATTEN sur la cotation fraîche du SDK.
Les faits financiers de la fixture sont explicitement en heure serveur S01.
