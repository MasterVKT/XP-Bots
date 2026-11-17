# Couche 2 — orchestration

Finalisation après le nouveau gel de 0 et 1. Enveloppe pure, sans import de méthode,
lecture physique, horloge ou réseau.

`MoteurDecision(configuration, bras, horaires, periodes_couvertes, *,
controle_fondamental=None, lecteur_ia=None, source_fondamentale=None,
source_ia=None, scenario_fondamental=None, etat=None, checkpoint=None, entrees=())` exige un déploiement commun,
des coordinateurs tracés et des stratégies et comptes distincts entre bras.
Le mode A/B chargé exige REFERENCE et IA et un lecteur réel ; REFERENCE conserve
le complément absent. C05 est partagé. Son absence exige le scénario technique
neutre explicite. Les sources synthétiques facultatives exposent `extraire(t)` ;
leurs réceptions typées sont journalisées avant application. Horaires, profils et
périodes portent les mêmes symboles.

`traiter(EntreeMoteur) -> SortieEvenement` exige numéros contigus et dates monotones.
La répétition identique de la dernière entrée est ignorée sans calcul, commande ou
enregistrement. Réécriture, recul ou entrée étrangère sont refusés. Un échec après
mutation invalide le moteur, qui ne peut plus rendre de commandes ou exporter son état.

Chaque réception applique C05 et IA puis avance leurs états. Les faits natifs et
sorties obligatoires de tous les bras précèdent toute bougie et tout signal. Les
bougies sont construites une seule fois, partagées immuablement, ordonnées par
clôture, H1 avant M15 puis priorité des symboles. Tous les signaux du groupe sont
soumis ensemble à chaque coordinateur : C08 assure les priorités et réservations
atomiques. Les issues reviennent à leur stratégie par le bras. PERSISTANCE ne touche
que les bras ciblés, sans appel préalable modifiant la révision de la preuve.
Aucune minuterie ne crée de prix. Les commandes restent étiquetées par bras.

`entrees` expose des `EntreeJournalisee` avec toutes les réceptions et tous les appels
et résultats normalisés des calculs. `rejouer(entree_journalisee)` réutilise exactement
`traiter` et le port journalisé de 1, sans consultation du backend ni appel IA. Tout
appel manquant, supplémentaire ou différent provoque une divergence. Les paramètres
initiaux et `initialisation_calculs` sont fournis identiquement à la reconstruction.

`traiter_ticks`, `traiter_evenement` et `confirmer_persistance` adaptent les données
vers ce chemin unique. `prochaine_echeance_ms` combine coordinateurs, C05, IA et
réceptions. `etat` fournit `EtatMoteur`, photographie scellée de la configuration,
des flux publics C03, des états publics des bras et contrôles et du journal.
La reprise exige des bras et contrôles restaurés par leurs API réelles ; elle vérifie
leur concordance puis reprend les flux publics C03. Le scellement détecte une
corruption accidentelle, sans authentifier un stockage physique futur.

Catégorie 1 : validation, répétition, causalité, isolation, calculs et divergence,
échéances, reprise et corruption ; C11.10 avec fabriques contractuelles externes.
Catégorie 2 : jonction réelle 0→1→2 London, journée A/B, journal exactement rejoué
sur backend interdit, veto sans rattrapage et sorties prioritaires. Aucun seuil ou
coût modifié. La persistance physique est extérieure à cette couche pure.

## Extension additive de phase 11 — checkpoint et journal séparés

Statut : défigé en `extension` le 10/11/2026 avant le code, pour le consommateur
de persistance physique et la boucle D-09. Les appels et `EtatMoteur` existants
conservent leur comportement. Voir [la décision](../EXTENSION-PHASE11-CHECKPOINT.md).

`CheckpointMoteur(signature, instant_ms, numero_entrees, empreinte_journal, flux,
bras, fondamental, ia, empreinte)` est une photographie immuable sans copie du
journal. `exporter_checkpoint()` la produit. `numero_entrees` est le nombre exact
d’entrées acceptées ; `empreinte_journal` est une chaîne SHA-256, initialisée par
SHA-256 des octets vides et prolongée après chaque entrée réellement acceptée
par le SHA-256 canonique du couple (empreinte précédente, EntreeJournalisee).
Répétition ignorée ou moteur invalidé ne produisent aucune nouvelle photographie
utilisable. Le sceau du checkpoint porte sur tous ses champs sauf `empreinte`.

`entrees_depuis(numero)` rend les seules entrées dont le numéro est strictement
supérieur au dernier numéro déjà détenu par le consommateur. L’indice est un
entier strict de zéro au nombre courant, booléens et indices futurs refusés.
Cette lecture ne modifie ni le moteur ni son journal.

Pour reprendre, fournir `checkpoint` et la collection complète `entrees` à la
construction, après restauration publique des bras et des contrôles. `etat` et
`checkpoint` sont exclusifs ; des `entrees` seules sont refusées. Le compteur,
la chaîne, le sceau, les symboles, les configurations et les horloges doivent
concorder. Journal tronqué, réordonné, réécrit ou étranger : refus. La vérification
complète du journal intervient une fois à la reprise ; aucun accès externe n’est
ajouté au moteur et ses calculs C08 ne changent pas.

La forme canonique de la chaîne conserve la normalisation déjà employée par
les sceaux de l’orchestration : enums par valeur, Decimal et dates par texte,
octets par hexadécimal, champs publics des dataclasses, mappings triés en JSON
UTF-8 sans espaces ni nombre non fini. Ce scellement détecte une corruption ;
il n’authentifie pas le producteur du stockage.

Tests additionnels : `test_cat1_c2_checkpoint.py` et `test_cat2_c2_checkpoint.py` ;
équivalence avec la reprise par `EtatMoteur`, corruption du journal, bornes de
lecture et jonction réelle London A/B. Les tests antérieurs sont conservés.


## Extension de phase 11 : réceptions de marché causales

Finalisé le 10/11/2026 avant code ; consommation du nouveau contrat 0 gelé.
L’entrée publique traiter(EntreeMoteur) porte les ReceptionExterne MARCHE ; aucune
nouvelle source physique ni méthode d’entrée redondante. Les sources C05/IA
existantes restent en mémoire. Les faits MARCHE ne dépendent pas de l’existence
d’un contrôle C05 ; ils ne remplacent aucune permission.

Document UTF8 strict, clés uniques, nombres finis : exactement schema
xp-etat-marche-v1, version entier positif, horaires objet ou None,
periodes_couvertes liste de couples UTC ms. Horaires objet exactement seances,
fermetures, debut_validite_ms, fin_validite_ms ; construction par les vrais
Intervalle et HorairesCotation. La validité couvre l’instant de réception.
Couverture : vrais RegistreCouverture, intervalles triés sans chevauchement,
fin <= instant de réception ; aucune déclaration de données futures.

Par symbole : version croissante, même version/octets = répétition sans effet,
même version différente ou version reculée = ErreurOrchestration. Horaires None
garde le dernier horaire connu. Un symbole étranger est refusé avant traitement.
Toutes les validations du fait précèdent son application. Le moteur invalidé
après erreur de traitement suit le contrat existant : reprise obligatoire.

Application avant les sorties et bougies du cadre : source de couverture en
mémoire réassignée au vrai RegistreCouverture validé ; appel public au vrai
FluxBougies.actualiser_horaires. Ni copie du constructeur de bougies, ni lecture
des attributs privés de C03. Les mises à jour restent dans EntreeJournalisee.
Un événement accepté produit une trace C09 MARCHE_ACTUALISE avec symbole/version,
sans octets bruts sensibles. Les autres natures ont leur comportement antérieur.

Pour un flux ayant reçu MARCHE, le champ flux opaque de EtatMoteur et du
CheckpointMoteur contient une enveloppe xp-flux-moteur-v2 : exactement schema,
flux (export public C03), marche (version, empreinte_message, reception_ms, horaires,
periodes_couvertes). Les flux sans MARCHE gardent exactement la forme antérieure.
Le sceau du moteur protège l’ensemble, sans prétendre authentifier un stockage.
La reprise garde la signature des paramètres initiaux, restaure horaires et
couverture actuels depuis l’enveloppe, puis appelle FluxBougies.reprendre.
Aucun nouveau champ de dataclass ni changement de paramètre par défaut. reception_ms
garde la première lecture de la version courante, sans renouvellement sur répétition.
À la reprise, les faits sont validés à cette réception passée (<= instant du checkpoint),
afin de restaurer aussi un horaire devenu périmé en panne de source, sans le rajeunir.

Tests : faits hostiles et futurs, répétition/collision, trous et retour de
couverture attestée, horaires modifiés, comparaison reprise/checkpoint,
vrais bras London A/B, rejeu C11.14 sans backend et jonction du codec gelé.

## Extension D-09 : checkpoint de journal

exporter_checkpoint_journal() -> CheckpointJournalMoteur(signature, instant_ms,
numero_entrees, empreinte_journal, flux, coordinateurs, fondamental, ia, empreinte).
Les coordinateurs sont les paires ordonnées (bras, EtatCoordinateur), sans
historique de stratégies ni duplication du journal. Les flux sont identiques
à ceux du checkpoint complet. Les contrôles sont les engagements courants
définis ci-dessous, sans leurs historiques. verifier() contrôle types, numérotation
et sceau. L'API antérieure exporter_checkpoint reste inchangée.

Ce checkpoint se vérifie après rejeu du préfixe complet par MoteurDecision.rejouer,
à partir de l'initialisation archivée et avec calculs d'initialisation archivés.
Il ne se substitue pas directement au paramètre checkpoint du constructeur.
L'enveloppe peut exporter ensuite un checkpoint complet, une fois à la reprise,
pour reconstruire les bras et appliquer la reprise C08 existante avant le
rapprochement. Tests : équivalence des flux/coordinateurs et du rejeu, corruption,
codec, absence de bras/historique et taille sur la journée London préchargée.

### P11-15 — engagements courants des contrôles

`fondamental` est None ou le tuple `(xp-verification-c05-v1, dernier_ms,
dernier_permissions_ms, derniers_evenements, dernieres_permissions, curseurs,
dernier_calendrier)`. Les deux listes de faits par symbole sont des tuples
triés `(symbole, instant_ms, SHA_du_fait_public)` ; la permission valide la plus
récente reste engagée même après une interruption. Les curseurs heartbeat sont
les valeurs publiques courantes. Le calendrier est None ou
`(version, export_ms, reception_ms, SHA_de_la_version_publique_complete)`.

`ia` est None ou `(xp-verification-ia-v1, dernier_ms, dernier_snapshot, vetos)`.
Le dernier snapshot est None ou `(sequence, genere_ms, reception_ms,
empreinte_integration, empreinte_payload)`. Les veto scellés non expirés sont
triés par event_id et représentés par `(event_id, connu_ms, valid_from_ms,
valid_until_ms, SHA_du_veto_public, sequence_preuve, empreinte_payload_preuve,
reception_preuve_ms)`. Aucune copie des octets de preuve ni des identités
expirées n'est nécessaire dans ce point de vérification régulier.

Les SHA sont ceux de la représentation canonique du moteur, calculés sur les
objets publics immuables. Une mémoïsation bornée aux seuls faits courants évite
de refaire ce travail sur chaque minuterie ; elle ne participe pas aux décisions.
La chaîne du journal engage toujours TOUTES les réceptions et leurs calculs,
y compris les calendriers anciens et identités IA expirées. Ces derniers
restent aussi intégralement dans EtatMoteur et CheckpointMoteur.

Ces projections ne sont pas des états de restauration C05/IA. La reprise
rejoue le journal complet, vérifie ces engagements puis exporte le checkpoint
complet une fois. Les décisions C05, vérifications d'identité A10, historique
connu, quotas et gardes C08 restent exécutés par leurs composants inchangés.
Le codec conserve ses conteneurs typés et son registre ; aucun nouveau type
ou import piloté par une archive. Les consommateurs traitent ces deux champs
comme opaques. Les anciens checkpoints de journal à champs complets ne sont
pas migrés silencieusement ; la comparaison de reconstruction les refuse.
