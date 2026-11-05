# Contrat de la couche 0 — parametres-ia (artefact `service-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 1a, 1b, 1c, 1d
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : aucune
- **Module** : `src/xpbots/service_ia/c0_parametres.py`
- **Sources normatives** : A02, A04 à A11, A14 ; plan maître, section 7.G

---

Unité : parametres_ia
Responsabilité : Charger l'export IA, les schémas et les prompts exacts.
Signature : charger_parametres_ia() -> ParametresIA
Entrée : config/, schemas/, prompts/
Sortie : objet immuable
Effets de bord : aucun
Erreurs, exceptions : ConfigurationInvalide

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/service_ia/test_c0_cat1_*.py`) : export IA, schémas et prompts exacts.
- Catégorie 2 (`tests/robot/service_ia/test_c0_cat2_*.py`) : —.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
