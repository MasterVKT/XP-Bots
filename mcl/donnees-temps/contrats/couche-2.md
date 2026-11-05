# Contrat de la couche 2 — etat-indicateurs (artefact `donnees-temps`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 2), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3
- **Dépend de** : couches 1c (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : stockage-etat
- **Module** : `src/xpbots/donnees_temps/c2_etat_indicateurs.py`
- **Sources normatives** : C03 (points 1 à 12), C11.1, C11.3, C11.4 ; plan maître, section 7.A

---

Unité : etat_indicateurs
Responsabilité : Précharger, persister et restaurer les états récursifs par symbole et en tracer l'empreinte.
Signature : EtatIndicateursSymbole.precharger(bougies) -> Empreinte ; appliquer(bougie) -> Indicateurs ; sauvegarder(stockage) ; restaurer(stockage) -> bool
Entrée : au moins warmup_closed_m15_bars bougies M15 clôturées ; port Stockage
Sortie : indicateurs courants ; empreinte (premier horodatage, SHA-256) ; statut WARMUP
Effets de bord : lecture et écriture via le port Stockage
Erreurs, exceptions : PrechargementInsuffisant ; EtatIncompatible si l'empreinte stockée diffère

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c2_cat1_*.py`) : préchargement insuffisant = WARMUP ; empreinte ; sauvegarde/restauration via doublure de Stockage ; préchargement différent journalisé.
- Catégorie 2 (`tests/robot/donnees_temps/test_c2_cat2_*.py`) : reprise après redémarrage identique au flux continu.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
