# Contrat de la couche 2 — etat-permissions (artefact `controles-fondamentaux`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 6), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3
- **Dépend de** : couches 1a (réelles et figées) ; amont figé : aucun ; frontières externes doublées : source-permissions, stockage-etat
- **Module** : `src/xpbots/fondamental/c2_etat_permissions.py`
- **Sources normatives** : C05, C08 point 2, C11.8, C11.9 ; plan maître, section 7.E

---

Unité : etat_permissions
Responsabilité : Conserver la dernière permission valide par symbole avec séquence, expiration et heartbeat.
Signature : EtatPermissions.recevoir(message) ; courante(symbole, i) -> MessagePermission | None
Entrée : messages validés
Sortie : permission courante ; événements de heartbeat manqué
Effets de bord : persistance via le port Stockage
Erreurs, exceptions : SequenceNonCroissante (message ignoré, journalisé)

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/fondamental/test_c2_cat1_*.py`) : séquence strictement croissante, expiration, heartbeat 60 s, persistance.
- Catégorie 2 (`tests/robot/fondamental/test_c2_cat2_*.py`) : via 3.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
