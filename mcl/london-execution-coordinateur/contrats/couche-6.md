# Contrat de couche 6 — coordinateur de compte

Statut : finalisé le 07/11/2026 avant construction ; toutes les dépendances sont figées.
Unité : coordinateur ; consommateurs : couture S4, orchestration et infrastructure futures.
Responsabilité : ordonner C08 sur un compte unique partagé par les deux méthodes, préserver intention, ressources et causalité, préparer puis autoriser une seule entrée protégée.
Signature : `TentativeCotation(instant_ms, cause, bid=None, ask=None, fournisseur_ms=None, reception_ms=None)` ; `DossierIntention(cle, signal, statut=EN_ATTENTE_COTATION, derniere_cause=None, tentatives=(), issue=None)` ; `EtatCoordinateur(reprise=EtatReprise(), intentions=(), preparations=(), transmises=(), revision=0, dernier_ms=0, demarrage_valide=False, exclusivites=())` ; `LotCoordinateur(etat, commandes=(), issues=(), traces=(), compte=None)` avec propriété `preparations` ; `CoordinateurCompte(technique, deploiement, profils, profil_compte, port, fondamental, instant_ms, *, longueur_empreinte, contexte=None, mode=None, etat=None, observation=None, base_utc=None)`.
Entrée : export chargé, profils C04, port de calcul, C05 obligatoire, contexte mémoire facultatif, compte rapproché et base UTC, événements explicitement horodatés.
Sortie : lots purs comprenant état à persister, commandes autorisées, préparations d'entrée conditionnelles, issues réelles et traces ; prochaine minuterie active.
Effets : état mémoire ; calculs par 1a et lectures des ports mémoire C05/IA seulement. Aucun fichier, ordre, API, LLM ou horloge.
Erreurs : `ErreurExecution` pour trame ou progression invalide ; refus C09 pour garde ou information absente. La composition doit fournir une longueur d'empreinte D-08 ; aucun identifiant de compte n'est journalisé.

## Événements et admission

`traiter(instant_ms, *, signaux=(), cotations=(), reponses=(), observation=None, base_utc=None)` intègre d'abord les réponses natives et rapprochements, puis le compte et les clôtures obligatoires, puis les nouvelles intentions. Pour une même clôture, 2b impose London avant EMA, puis l'univers chargé ; chaque candidat relit le registre après la réservation précédente. Une clé déjà connue n'est jamais une nouvelle entrée. Les types EMA se convertissent par 0a avant cet appel.

Les limites techniques de la méthode sont celles du signal produit par son moteur réel ; aucune reconstruction de stratégie dans 6. C05 est contrôlé avant le contexte IA, puis cotation, niveaux, dimensionnement et réservation. IA absente ou illisible → NEUTRAL ; aucune panne ne lève un veto C05 ou du compte. `ControleTechniqueNeutre` est un scénario explicite, interdit en DEMO/REEL. Profil de compte mal qualifié, base UTC inconnue ou démarrage non rapproché → environnement non prêt. En netting une exclusivité explicite du symbole est nécessaire avant admission.

Un SL absent ou différent du niveau accepté sur une position possédée ouverte bloque toutes les nouvelles entrées du compte avec `PROTECTION_ERROR/SL_ABSENT`, pendant sa clôture de sécurité. La réserve initiale reste engagée. Les protections courantes du rapprochement proviennent des champs obligatoires de la position native, y compris après reprise.

P-08 : un dossier unique mémorise les tentatives horodatées et leur dernière cause. Spread ou écart d'entrée excessif attend une nouvelle cotation jusqu'à la borne exclusive du TTL ; la minuterie d'expiration ne remplace pas la dernière cause par celle d'une vieille cotation. Une nouvelle cotation du symbole déclenche un nouveau contrôle. Au TTL exact, produire `SIGNAL_EXPIRED` avec la dernière cause ; aucune entrée rétroactive. Refus définitif et expiration consomment le signal sans quota.

## Persistance avant transmission

Les commandes `ENTREE` préparées sont dans `lot.preparations`, jamais dans `lot.commandes`. Le lot contient déjà la réservation et le cycle préparé. La frontière externe persiste atomiquement cet état, puis appelle `confirmer_persistance(preuve, instant_ms)` avec une vraie `PreuvePersistance` de cette révision et des références d'entrée. Une preuve absente, périmée ou étrangère n'autorise rien.

Après la preuve, relire le compte, les spécifications, C05, le contexte mémoire et la cotation connue ; appeler le vrai `revalider_avant_envoi` de 3 pour le volume exact et la réserve initiale. Si un contrôle échoue, consommer ce signal, retirer la préparation et libérer seulement sa réservation non remplie. Si tous passent, rendre une fois la commande protégée déjà préparée et mémoriser sa référence transmise. Une preuve répétée ne renvoie rien. Les clôtures et protections sont dans les commandes immédiates et ne dépendent d'aucune preuve de journalisation.

Les horaires natifs doivent être connus et ouverts, et aucune échéance 0e déjà atteinte à l'instant de l'admission ; sinon refus d'environnement. Le mode de remplissage préparé doit toujours être autorisé et l'unité de point inchangée avant transmission. Le timeout d'accusé commence à l'instant de transmission autorisée après la preuve, en conservant la borne initiale du TTL. Un accusé natif déjà connu retire la préparation sans créer de quota ni retransmission. Le contrôle final ajoute sa cotation et ses horodatages aux tentatives ; `lot.compte` donne à l'enveloppe C09 les données effectivement connues du compte.

Le compte lu par le port appartient au même instant logique que l'événement ; le producteur externe estampille cette connaissance sans inventer un prix. Les cotations gardent leurs heures fournisseur et réception propres. Les positions natives doivent être rapprochées par 5b au redémarrage ; les réservations restent engagées pendant un état ambigu. Une sortie en attente bloque son sous-jacent, les autres ressources restant arbitrées par le registre commun.

## Reprise et traces

`etat` exporte des valeurs immuables et les vrais états des couches internes. Un redémarrage rétablit les gardes, risques, quotas et tentatives via 5b ; il retire les préparations d'envoi et rapproche, sans retransmettre. Les intentions encore en attente de cotation sont consommées sans entrée rétroactive. Les événements natifs ultérieurs priment sur les demandes de marché ; les commandes devenues sans objet après clôture confirmée sont retirées du lot.

`prochaine_echeance_ms` est le minimum des TTL en attente, minuteries 4, échéances 5a et, pour les positions ouvertes, cadence de surveillance chargée `exit_retry_interval_seconds`. Aucun réveil n'invente de cotation. Les dossiers permettent à l'enveloppe C09 de journaliser les intentions et tentatives avec `issue=None` avant une vraie issue ; seul un premier volume positif produit `REMPLIE` et consomme le quota.

Tests catégorie 1 : preuve de persistance, relecture finale, P-08/L-18/L-19, idempotence, C05/IA, profil et compte, gardes, arbitrage L-17 et états mal formés. Catégorie 2 : bloc réel 0–6, compte London/EMA, ordres protégés, réponses natives avant sorties, reprise et réservations ; seules frontières sont scénarisées. Couture S4/S5 après gel.
