# Contrat de la couche 2a — veto (artefact `service-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3a
- **Dépend de** : couches 1a, 1c (réelles et figées) ; amont figé : amont-contexte-ia ; frontières externes doublées : aucune
- **Module** : `src/xpbots/service_ia/c2a_veto.py`
- **Sources normatives** : A02, A04 à A11, A14 ; plan maître, section 7.G

---

Unité : evenement_veto
Responsabilité : Construire un événement OFFICIAL_UNSCHEDULED_POLICY selon A06.
Signature : construire_veto(extraction, texte, recu_a, calendrier) -> Veto | None
Entrée : extraction validée, texte, calendrier valide
Sortie : veto daté et symboles concernés ou rien
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/service_ia/test_c2a_cat1_*.py`) : conditions A06 ; calendrier POLICY_DECISION ±3 600 s ; fenêtre [réception, publication+900 s).
- Catégorie 2 (`tests/robot/service_ia/test_c2a_cat2_*.py`) : via 3a.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
