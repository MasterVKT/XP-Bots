# Contrat de la couche 1 — snapshot (artefact `contexte-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 7), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : ipc-snapshot
- **Module** : `src/xpbots/contexte_ia/c1_snapshot.py`
- **Sources normatives** : A03, A07, A10, A12, A14 ; plan maître, section 7.F

---

Unité : snapshot
Responsabilité : Valider un snapshot lu du fichier d'IPC.
Signature : valider_snapshot(octets, maintenant, derniere_sequence) -> Snapshot | Rejet(motif)
Entrée : octets du fichier (≤ 32 Kio), instant, dernière séquence persistée
Sortie : snapshot accepté ou motif de rejet
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/contexte_ia/test_c1_cat1_*.py`) : taille, doublons, hash, schéma, séquence en recul, futur, âge 90 s, événement mal formé ; concordance overlay_decision.
- Catégorie 2 (`tests/robot/contexte_ia/test_c1_cat2_*.py`) : via 2.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
