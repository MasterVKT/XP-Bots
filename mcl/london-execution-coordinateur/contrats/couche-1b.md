# Contrat de la couche 1b — gardes_compte

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 3, 5a, 5b, 6.
- **Dépend de** : 0a.

Unité : gardes_compte
Responsabilité : Base UTC vérifiée, pic et verrous persistants en mémoire exportable, ou refus lorsque la base/les flux sont inconnus.
Signature : `MouvementCompte`, `BaseReconstituee`, `reconstituer_base_utc(compte, mouvements, couverture, *, aucune_position_minuit)` ; `GardesCompte(commun, etat=None)` avec `observer`, `neutraliser_flux`, `reactiver`, `refus`, `etat`
Entrée : Instantané réel du compte ; mouvements de solde USD identifiés et couverture complète de l’historique ; état restauré optionnel.
Sortie : Base UTC vérifiée, pic et verrous persistants en mémoire exportable, ou refus lorsque la base/les flux sont inconnus.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

P-12 : à 00:00 UTC exactement, la base est l’équité observée ; en dehors de cet instant, elle est reconstituée par solde courant moins tous les mouvements depuis minuit, sur historique couvrant toute cette période et sans position à minuit. La base reconstituée est rapportée au jour UTC et à l’instantané exact ; les premières équités du jour ne la remplacent jamais. Le pic hors fonctionnement est borné par le solde reconstitué et ses variations chronologiques, pas par un flottant inventé. Les mouvements sont uniques, ordonnés causalement et sans heure future. Dépôts/retraits identifiés sont neutralisés en translatant les bases et le pic, avec référence idempotente ; flux inconnu bloque l’entrée.

Aux seuils inclusifs, équité ≤ base×(1−limite quotidienne) déclenche le verrou jusqu’au jour UTC suivant ; équité ≤ pic×(1−baisse globale) déclenche l’arrêt persistant. Le jour Londres n’intervient pas. Les pertes flottantes et frais sont déjà dans l’équité. Un état restauré garde les verrous ; un redémarrage ne réactive rien. Seule `reactiver` avec une nouvelle référence de décision de déploiement peut lever l’arrêt global, et ne lève pas le verrou quotidien du même jour. Tout compte observé doit avancer ou conserver son instant, jamais revenir dans le passé. Les demandes effectives de clôture appartiennent à la phase 6.

La reconstitution conserve également chaque flux identifié avec sa référence et son montant. À une reprise sur un nouveau jour UTC, les flux nouveaux translatent le pic antérieur ; une référence déjà neutralisée ne le translate pas une seconde fois. Un retrait ne doit donc jamais créer artificiellement une baisse globale. Ce cas a été ajouté et corrigé avant le premier gel de la couche.

## Spécification exécutable

`test_cat1_c1b_gardes_compte.py` : C11.13, seuils exacts, P-12, flux et erreurs ; `test_cat2_c1b_gardes_compte.py` : reprise réelle des états et jours UTC/Londres.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

## Phase 11 — flux qualifiés reçus pendant le jour ou une interruption

Correction/extension finalisée avant code actif, le 13/11/2026. Un essai natif
synthétique révèle qu'une BaseReconstituee qualifiée était ignorée en cours de
jour : après apport identifié de 100 sur base 100, le seuil quotidien attendu
196 ne verrouillait pas, la base restant 100. Les callbacks de l'infrastructure
doivent pouvoir livrer ces faits au vrai moteur sans accéder à ses champs privés.

GardesCompte.observer consomme les nouveaux flux d'une BaseReconstituee du jour
UTC et de l'instant EXACT du compte. Leurs références déjà neutralisées sont
inertes, y compris après reprise. Dans le même jour, leur somme translate la
base quotidienne et le pic ; au changement de jour, la nouvelle base demeure
la base du nouveau jour et seul l'ancien pic est translaté avant comparaison.
À 00:00 exactement, la base reste l'équité observée selon P-12 ; une preuve
qualifiée fournie peut néanmoins transporter les flux non encore neutralisés
pour le pic antérieur. Aucun flux identifié n'est pris pour un bénéfice.

Les verrous restent ceux des règles existantes : quotidien persistant dans le
même jour, global persistant sans nouvelle décision, même après un apport ou
un retrait. Une preuve future ou d'un autre instant/jour refuse sans mutation.
Le booléen flux_externe_non_neutralise reste bloquant : une simple variation
de balance n'est jamais une preuve de capital, et un apport inconnu ne sert
pas à relever un budget ni à modifier un pic.

reconstituer_base_utc ajoute le seul argument optionnel depuis_flux_ms=None.
Valeur absente : comportement antérieur conservé. Valeur fournie : historique
exigé jusqu'au minimum de minuit courant et de cette borne passée, et transport
des flux externes identifiés depuis cette borne, y compris avant minuit pendant
une interruption. Le calcul de la base quotidienne utilise TOUJOURS seulement
les mouvements du jour courant ; les anciens flux ne sont pas ajoutés une
seconde fois à la base du nouveau jour. Le moteur de gardes existant translate
le pic en utilisant les références persistées, sans recalcul extérieur.

Le producteur natif doit comparer le solde courant au dernier solde dont le
journal est rapproché avant de rendre flux_externe=False. Une différence
encore inexpliquée donne un état bloquant jusqu'à la réception des faits et
de la base qualifiés. Ce contrôle est une frontière physique, pas une seconde
neutralisation des fonds. Aucun seuil ni paramètre métier n'est modifié.

La même borne depuis_flux_ms gouverne également la reconstitution du pic de
SOLDE prouvé pendant l'interruption : déduire le solde au début de la couverture
des mouvements complets puis parcourir leurs variations de trading, avec les
flux externes neutralisés. Le calcul de la base du jour courant ne change pas.
Même dans le même jour, ou à minuit exact, un pic de solde historique prouvé
ne doit pas être oublié. Le pic retenu est le maximum de ce pic reconstitué,
du pic antérieur translaté et de l'équité courante ; aucun flottant non observé
n'est inventé. Les essais RED capturent aussi 100→120→108 pendant l'arrêt :
l'arrêt global doit être actif à la reprise, pas recalculé sur un faux pic 108.
