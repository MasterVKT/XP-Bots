# Contrat de la couche 4 — cycle_ordre

- **Statut** : finalisé le 07/11/2026 avant son implémentation ; construction incrémentale de la composante cyclique C08.
- **Consommateurs cartographiés** : 5a, 5b, 6 ; exécution papier S5 puis infrastructure.
- **Dépend de** : 0a, 0d, 1a, 3 ; noyau réel et figé.

Unité : cycle_ordre
Responsabilité : gérer une intention protégée depuis la préparation de l'envoi jusqu'à sa clôture confirmée, sans appeler l'exécution ni le stockage.
Signature : `identifier_courtier(cle, longueur_empreinte)` ; `IdentiteCourtier(magic, commentaire)` ; `CommandeExecution(nature, cle, reference, instant_ms, donnees)` ; `ReponseCourtier(nature, cle, reference, instant_ms, donnees)` ; `PreuvePersistance(revision, references)` ; `PreuveAbsence(cle, instant_ms, debut_ms, fin_ms, historique_complet, envoi_termine, absence_definitive, aucun_ordre, aucune_position, aucune_execution)` ; `EtatCycle` (champs ci-dessous) ; `TraceCycle(type, donnees)` ; `EffetsCycle(etat, commandes=(), issues=(), traces=())` ; `CycleOrdre(commun, signal, plan, profil, longueur_empreinte, etat=None)`.
Entrée : paramètres communs chargés, signal et plan réels de la couche 3, profil C04, réponses natives horodatées, cotation connue et minuteries explicites ; état complet pour restauration.
Sortie : état immuable, commandes conditionnées par la transaction externe, issues du noyau et traces C09.
Effets de bord : état mémoire explicite ; seuls les calculs C04 passent par 1a ; aucun ordre, fichier, réseau, horloge ou attente.
Erreurs : `ErreurExecution` pour valeur mal formée, réponse contradictoire de même identifiant ou appel hors contrat ; refus motivé et clôture de sécurité pour les échecs métier.

## Interface du cycle

- `preparer_envoi(instant_ms)` rend une seule entrée protégée ; répéter l'appel ne retransmet rien. TTL encore ouvert. L'état et la réservation sont validés par le stockage externe avant exécution de la commande.
- `sur_reponse(reponse, cotation=None)` intègre accusé, remplissage, protections, clôture ou annulation. Un accusé sans volume ne consomme aucun quota ; le premier volume positif produit exactement une issue `REMPLIE`.
- `sur_minuterie(instant_ms, *, cotation=None, negociable=False)` applique les délais d'accusé, rapprochement, protection et sortie sans dormir.
- `demander_cloture(instant_ms, cause, *, motif=None, detail=None, priorite=0, volume_cible=Decimal(0), peut_envoyer=False)` conserve la demande jusqu'à confirmation native, avec la priorité la plus haute et sans retirer SL.
- `controler_risque(registre, gardes, port, instant_ms, cotation=None)` lit spécifications et compte réels par 1a, appelle le vrai dimensionnement 3 avec plan initial, prix, volume confirmé et frais d'entrée réels, puis réduit ou clôture. Aucune recopie de C07.
- `confirmer_absence(preuve)` ne termine une intention non remplie que si la preuve native couvre l'envoi et confirme sa fin et l'absence définitive d'ordre, position et transaction. Historique vide ou délai seul ne suffisent pas.
- `reprendre(instant_ms)` demande un rapprochement avant décision, sans renvoi d'entrée. Risques, premier remplissage, tentatives et identifiants reçus sont conservés.
- Propriétés : `etat: EtatCycle`, `prochaine_echeance_ms: int | None`.

## Frontières : trames fermées

`NatureCommande` : `ENTREE`, `TP`, `CLOTURE`, `ANNULATION`, `RAPPROCHEMENT`, `ALERTE`, `MINUTERIE`.
`NatureReponse` : `ACCUSE`, `REMPLISSAGE`, `PROTECTIONS`, `CLOTURE`, `ANNULATION`.
`StatutAccuse` : `ACCEPTE`, `REFUSE`, `INCONNU`.

La clé est réelle, la référence non vide, l'instant UTC entier et la correspondance immuable. Les champs de chaque ligne sont exacts : absence ou surplus refusé. Les décimaux sont finis ; prix et volumes d'action strictement positifs ; frais et reliquats non négatifs ; booléens refusés à la place d'entiers. Les champs facultatifs sont présents et peuvent valoir `None`.

| Commande | Champs de `donnees` |
|---|---|
| ENTREE | `symbole_courtier`, `sens`, `volume`, `prix`, `sl`, `tp`, `deviation_points`, `mode_remplissage`, `magic`, `commentaire`, `risque_initial`, `budget_gele`, `expire_ms` |
| TP | `ticket`, `sl`, `tp` ; SL exactement inchangé |
| CLOTURE | `ticket`, `volume`, `cause`, `motif` facultatif, `detail` facultatif, `priorite` |
| ANNULATION | `ordre` |
| RAPPROCHEMENT | `symbole_courtier`, `magic`, `commentaire`, `depuis_ms` |
| ALERTE | `code`, `gravite` ; codes déterministes sans secret |
| MINUTERIE | `echeance_ms` ; jamais avant la création de la commande |

| Réponse | Champs de `donnees` |
|---|---|
| ACCUSE | `commande`, `statut`, `code_natif`, `definitif`, `ordre` facultatif ; le ticket natif est conservé avant le premier remplissage |
| REMPLISSAGE | `transaction`, `ticket`, `ordre` facultatif, `volume_cumule`, `volume_position`, `prix_moyen`, `execution_ms`, `frais_entree` facultatif (inconnu ≠ zéro), `sl` facultatif, `tp` facultatif, `reliquat`, `reliquat_annule` |
| PROTECTIONS | `ticket`, `sl` facultatif, `tp` facultatif |
| CLOTURE | `ticket`, `volume_restant`, `prix`, `execution_ms`, `frais_sortie`, `cause` |
| ANNULATION | `ordre`, `confirmee` |

L'exécution ne peut être postérieure à la réception. Volume cumulé d'entrée et volume encore ouvert sont distincts. Une exécution positive tardive fait foi. Les réponses identiques sont idempotentes ; aucune ne recrée ordre ou quota. Tout refus natif confirmé consomme le signal, sans renvoi automatique.

## État persistant pur

`EtatCycle` expose `cle` et les champs nommés suivants, avec valeurs initiales conservatrices :

| Groupe | Champs |
|---|---|
| Progression | `statut`, `dernier_ms`, `envoi_ms`, `accuse_recu`, `numero_commande`, `reponses_recues` |
| Exécution | `premier_fill_ms`, `volume_cumule`, `volume_ouvert`, `prix_moyen`, `frais_entree` (None si inconnus), `ticket_position`, `ticket_ordre`, `sl_natif`, `tp_natif`, `niveaux_reels`, `quota_compte`, `reliquat_annule`, `annulation_demandee` |
| Protections | `tentatives_protection`, `prochaine_protection_ms`, `protections_validees`, `risque_verifie` |
| Inconnu | `inconnu_ms`, `prochain_rapprochement_ms`, `alerte_inconnue` |
| Sortie | `volume_cible`, `cause_sortie`, `motif_sortie`, `detail_sortie`, `priorite_sortie`, `sortie_en_cours`, `prochain_reessai_ms`, `instant_cloture_ms`, `cause_cloture_native` |

Restauration vérifiée contre clé, signal, plan initial et profil. Aucun quota ni délai n'est remis à zéro. Une sortie n'est terminale qu'après volume nul confirmé et reliquat traité. Sans cotation, la demande reste prioritaire et les protections natives sont conservées.

Une clôture ou réduction déjà transmise est rapprochée jusqu'à son résultat natif ; elle n'est pas renvoyée aveuglément pendant son exécution. Un refus confirmé rend possible un nouvel essai au délai chargé ; un accusé inconnu ne vaut pas refus. Une réduction partielle confirmée autorise seulement la quantité encore nécessaire pour atteindre la cible, sans double réduction en attente.

## Garanties C07/C08 et D-08

Magic positif sur 63 bits dérivé du SHA-256 du couple déploiement/stratégie ; commentaire `XPB3:` puis empreinte de clé à la longueur explicitement fournie. La longueur et sa conservation seront confrontées à S-05. Aucun identifiant de compte. Modes FOK, IOC, RETURN dans cet ordre ; inconnu → environnement non prêt. Déviation = partie entière inférieure de g/point, sans garantie de prix natif.

Intention, réservation et commandes appartiennent à une transaction externe. `PreuvePersistance` énumère sa révision et les références validées : la coquille ne transmet aucune entrée sans cette preuve. Une panne de journalisation ne doit pas empêcher une clôture de sécurité ou le maintien des protections. Le cœur ne réalise pas de persistance physique. Toute intention non terminale restaurée est rapprochée, jamais rejouée comme entrée.

À l'échéance d'accusé sans réponse, état inconnu et symbole verrouillé. Rapprochement immédiat, cadence rapide durant la fenêtre chargée, lente ensuite sans limite ; alerte unique au-delà de la fenêtre. Une réponse inconnue ne libère aucun risque et ne vaut jamais rejet.

Partiel : annuler tout reliquat non déjà confirmé annulé, jamais compléter. SL absent ou différent du niveau accepté : clôture immédiate de protection sans attendre un TP. TP recalculé par 0d au prix moyen réel, SL fixe ; cible déjà dépassée → clôture au prix disponible. Corrections bornées par nombre, délais et échéance chargés, puis clôture si le plan reste invalide. Le contrôle 3 conserve budget et fonds propres de référence initiaux, frais d'entrée réels et seule réserve de sortie. Les causes de sécurité sont celles du noyau étendu, sans nouveau motif.

## Tests et construction

Catégorie 1 : cycle minimal vivant, refus, partiel, inconnu/rapprochement, protections, réduction ; bornes exactes, idempotence, état mal formé, D-08 et paramètres modifiés. Contrôle catégorie 1 après chaque transition ajoutée, puis catégorie 2 et régression intégrale avant gel.

Catégorie 2 : vrais types, prix, réservations, gardes et dimensionnement ; seules réponses et fonctions du courtier sont scénarisées. Issues appliquées au vrai moteur London pour L-12 ; aucune doublure d'une couche interne.
