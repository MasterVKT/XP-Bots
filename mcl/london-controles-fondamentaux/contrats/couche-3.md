# Couche 3 — Port de permissions C05

Statut : finalisé avant code le 09/11/2026, après CP2 et gel de 0, 1a, 1b et 2.

`PermissionsFondamentales(commun, convertir_serveur, etat=None)` implémente le port canonique
ControleFondamental. Il assemble le vrai RegistrePermissions et la vraie GardeAnnonces ; aucune
doublure interne, lecture, horloge, calcul macro ou IA. `EtatFondamental(permissions, calendrier,
dernier_ms)` est une valeur immuable de reprise ; les deux sous-états sont revalidés et aucune
réception ne peut dépasser le dernier temps observé. Les consultations historiques restent causales.

Les entrées `recevoir_permission(symbole, octets, reception_ms)`, `recevoir_calendrier(octets,
reception_ms, table)` et `interrompre(symbole, instant_ms)` délèguent aux vraies couches et rendent
leurs résultats. Le temps des événements ne recule pas, même pour une entrée rejetée. Les rejets
ne remplacent pas la dernière permission valide. Une interruption est explicite.

`avancer(instant_ms)` rend les EvenementSuivi encore non consommés de 2 ; l'appelant les journalise
en C09. La réception d'un même instant précède ce suivi. `prochaine_echeance_ms(instant_ms)` rend
le minimum des échéances heartbeat/expiration et des transitions connues de calendrier, ou None.
Aucun tick n'est fabriqué à ces échéances. Les réceptions externes futures sont planifiées par
leur source, jamais anticipées par le contrôle.

`evaluer(symbole, sens, instant_ms) -> DecisionFondamentale` applique les effets dans cet ordre :
FLATTEN valide impose clôture et blocage ; une annonce HIGH connue dans sa fenêtre impose la
clôture même sans permission valide ; absence/interruption/expiration bloque sans clôture ; NO_NEW
ou direction incompatible bloque sans clôture ; calendrier absent, périmé ou insuffisant bloque
sans clôture ; sinon l'entrée est admise. Les motifs et détails sont ceux du noyau C09. Une
direction qui change ne ferme pas une position. FLATTEN expiré ne commande plus de clôture.

`clotures_obligatoires(instant_ms) -> tuple[str,...]` rend les mêmes obligations, dans l'ordre
stable de l'univers chargé, indépendamment du sens. Le contrôle ne possède aucune position et
ne ferme rien lui-même : le coordinateur filtre propriété et priorité C08. Le complément IA absent
ou NEUTRAL n'altère aucune décision C05. Le scénario TECHNICAL_CONTROL_NEUTRAL demeure un choix
explicite de composition, jamais un comportement par défaut du port réel.

Tests : C11.8/9, A14-6/8 côté socle, priorités FLATTEN/HIGH, calendrier tardif, direction sans
liquidation, reprise, égalité historique par préfixe et absence de contournement par complément absent.
