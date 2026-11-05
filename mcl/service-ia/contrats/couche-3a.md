# Contrat de la couche 3a — ecrivain-snapshot (artefact `service-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 4
- **Dépend de** : couches 2a (réelles et figées) ; amont figé : aucun ; frontières externes doublées : ipc-ecriture
- **Module** : `src/xpbots/service_ia/c3a_ecrivain_snapshot.py`
- **Sources normatives** : A02, A04 à A11, A14 ; plan maître, section 7.G

---

Unité : ecrivain_snapshot
Responsabilité : Publier atomiquement le snapshot et son heartbeat.
Signature : EcrivainSnapshot.publier(evenements, i)
Entrée : vetos valides, séquence persistée
Sortie : fichier remplacé atomiquement
Effets de bord : écriture disque
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/service_ia/test_c3a_cat1_*.py`) : remplacement atomique, réessais, heartbeat 30 s, séquence persistée.
- Catégorie 2 (`tests/robot/service_ia/test_c3a_cat2_*.py`) : lu par contexte-ia.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
