# Contrat de la couche 0c — mt5-connexion (artefact `infrastructure`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 9 et 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 1a
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : metatrader5
- **Module** : `src/xpbots/infrastructure/mt5/connexion.py`
- **Sources normatives** : C04, C08 (rapprochement, redémarrage), A04, A08, A10 ; plan maître, section 7.I

---

Unité : connexion_mt5
Responsabilité : Ouvrir et contrôler la connexion au terminal MT5.
Signature : ConnexionMT5.ouvrir(parametres) ; terminal() ; compte() ; fermer()
Entrée : terminal installé, compte démo
Sortie : informations terminal et compte sans secret journalisé
Effets de bord : aucun
Erreurs, exceptions : TerminalIndisponible

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/infrastructure/test_c0c_cat1_*.py`) : initialisation et terminal_info sur doublure.
- Catégorie 2 (`tests/robot/infrastructure/test_c0c_cat2_*.py`) : contrat MT5 démo manuel.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
