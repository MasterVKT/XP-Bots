# Couche 1a — livre PAPER durable

`LivrePapier(configuration, conditions, creation_ms, scenario='REFERENCE', *,
checkpoint=None, operations=())` possède un vrai SimulateurExecution C10. Il
ne contient aucun calcul d'admission, de remplissage, de frais ou de P&L et ne
lit aucun attribut privé d'un amont. Les sept calculs, observations, base UTC,
ticks de décision, réponses, trades et courbes proviennent de ce simulateur.
Le scénario est chargé depuis le protocole figé ; aucune variante de coût
n'est inventée. Deux instances ne partagent aucun état mutable.

Les symboles commencent indisponibles pour l'admission. Le pilote transmet les
profils/tarifs effectivement qualifiés par `actualiser_profil` et la disponibilité
du flux et des contrôles par `fixer_disponibilite(symbole, disponible, instant_ms)`.
Une indisponibilité rend ENVIRONMENT_NOT_READY à specifications/controler,
sans toucher au portefeuille, aux ordres en cours ou aux défenses. Ce booléen
est un fait de frontière C03/C04, jamais une règle technique supplémentaire.

`avancer_au(t)` avance uniquement l'horloge réelle du livre. `sur_tick`,
`extraire_reponses`, `soumettre`, `enregistrer_contexte`, `actualiser_profil`
et `fixer_disponibilite` archivent chaque mutation réussie comme une opération
canonique datée, numérotée et chaînée par SHA-256. Les arguments sont copiés
par le codec public avant application ; le résultat est lié par empreinte.
Une erreur de mutation invalide le livre : reprise depuis un état durable
requise, sans poursuivre sur un état éventuellement partiel.

`initialisation` expose les valeurs pures nécessaires à la reconstruction,
`checkpoint` la signature, l'instant final, le nombre d'opérations et la chaîne ;
`operations_depuis(numero)` rend le seul delta depuis une position archivée.
Le checkpoint n'inclut ni courbe ni historique d'opérations. À la reprise, le
préfixe complet est vérifié et rejoué une fois sur une nouvelle instance réelle,
sans SDK ni effet extérieur. Signature étrangère, numéro manquant, ordre,
argument, résultat, chaîne ou instant altéré sont refusés. Le registre de types
du codec est explicite et limité aux types C10 réellement nécessaires.

Tests catégorie 1 : disponibilité initiale fermée, actualisation causale,
copie des arguments, checkpoint borné, reprise exacte et altérations refusées,
portefeuilles indépendants et livre invalidé après erreur. Catégorie 2 : cycle,
gardes et dimensionnement réels ; ordres/fills/SL/TP et solde identiques après
reprise ; profit C10 comparé au calcul natif du faux SDK qualifié. Le physique
du journal et l'autorisation après COMMIT appartiennent aux couches 1b et 2.
