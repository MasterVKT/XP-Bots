# Couche 1f — composition pure du moteur et reconstruction d'incident

Cette unité assemble les mêmes bras London, coordinateurs, C05 et lecteur IA
pour deux consommateurs réels : la boucle directe et le rejeu d'incident.
Elle ne lit ni fichier, ni horloge, ni SDK. Aucun calcul ou décision métier
n'est réimplémenté. Les fabriques London sont injectées au moteur commun.

`composer_moteur(configuration, initialisation, ports, *, checkpoint=None,
entrees=(), appels_initialisation=None)` retourne le vrai `MoteurDecision`.
Le document pur `xp-composition-direct-v1` contient : configuration (comparée
intégralement à la configuration de confiance), deploiement, mode,
longueur_empreinte, profils (canoniques), horaires initiaux, periodes_couvertes
initiales, initiales par bras (profil_compte, instant_ms, observation, base_utc),
scenario_fondamental, table_heure (document S01 qualifié ou None en neutre),
politique_ia (trois booléens). Les bras sont exactement REFERENCE en PAPER,
REFERENCE et IA en PAPER_AB ; un seul bras IA ou REFERENCE en DEMO/REEL selon
la politique explicite. Le neutre technique est interdit en DEMO/REEL.
La configuration complète et ces données sont archivées avant la première
entrée ; les identités restent vérifiées par les composants réels.

Chaque port calcule les sept opérations publiques et expose le ProfilCompte
initial canonique. `PortCompte(backend, profil_compte)` adapte le vrai calculateur
natif sans copier ses calculs. `fixer_disponibilite(symboles)` reçoit l'ensemble
des symboles à jour et refuse controler pour les autres, mais conserve tous les
calculs des défenses et les contrôles de remplacement des protections
(`remplacement=True`).
Les livres PAPER portent déjà cette garde ; ils ne partagent aucun portefeuille.

`rejouer_incident(configuration, initialisation, appels_initialisation, entrees,
checkpoint)` utilise des ports dont tout accès au backend lève. Les appels
d'initialisation archivés sont fournis AVANT la construction des bras. Toutes
les entrées sont rejouées par MoteurDecision.rejouer, dans l'ordre, puis le
checkpoint de journal est comparé exactement au checkpoint durable. Le résultat
contient le vrai moteur rejoué et toutes ses sorties. Il sert aussi au rapport
d'incident qui compare les octets C09, commandes et états, pas seulement les
effectifs. Une divergence ou troncature est une erreur ; aucun SDK de secours.

Pour une reprise directe, le consommateur exporte une fois le checkpoint
complet de ce moteur rejoué, puis rappelle composer_moteur avec les vrais ports,
ce checkpoint et le même journal. Les contrôles C05 et IA sont restaurés depuis
leurs états, les bras et le moteur passent par leurs constructeurs de reprise
C08. L'observation native fraîche est ensuite une nouvelle entrée à son heure
réelle : elle n'est pas antidatée au checkpoint. Cette reconstruction initiale
ne justifie aucune retransmission d'entrée ni levée d'arrêt persistant.

Catégorie 1 : document fermé, modes et politiques, backend interdit dès la
construction du rejeu, journal tronqué/altéré, garde de rattrapage sans bloquer
les calculs des défenses. Catégorie 2 : vrai livre C10, vrais bras London et
contrôles, rejeu strict identique simple et A/B ; reprise C08 sans entrée
rétroactive, états et arrêts préservés. Fixtures synthétiques, aucun ordre réel.

## Extension P11-17 — reconstruire les reprises archivées

Finalisée avant code le 14/11/2026. `rejouer_incident` accepte le paramètre
optionnel nommé `reprises=()`, tuple ordonné de CheckpointJournalMoteur.
À chaque compteur de préfixe indiqué, il exporte une fois le checkpoint
complet du moteur réellement rejoué puis rappelle composer_moteur avec ce
checkpoint et les mêmes ports interdits. Les vrais constructeurs C08 refont
ainsi la transformation de reprise ; leur checkpoint court doit égaler
exactement le marqueur déclaré avant de poursuivre les entrées archivées.
Un marqueur n'injecte aucun état dans le moteur et n'autorise aucune commande.
Compteurs en recul, hors journal, signatures et résultats divergents sont
refusés. Plusieurs reprises au même préfixe sont traitées dans leur ordre.
Sans marqueur, le comportement reste identique. Tests : reprise simple et
A/B, marqueur altéré et préfixe impossible, reconstruction sans backend.
