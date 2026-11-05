# Contrat de la couche 0 — parametres-et-seances (artefact `donnees-temps`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 2), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 1a, 1b, 1c
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : aucune
- **Module** : `src/xpbots/donnees_temps/c0_parametres_seances.py`
- **Sources normatives** : C03 (points 1 à 12), C11.1, C11.3, C11.4 ; plan maître, section 7.A

---

Unité : parametres_techniques
Responsabilité : Charger et valider le bloc common de la configuration figée en objet immuable, avec l'empreinte canonique du bundle.
Signature : charger_parametres_techniques(bundle) -> ParametresTechniques
Entrée : bundle JSON strict fourni par le chargeur du noyau (config/parametres_figes_v3.json)
Sortie : objet immuable typé de tous les champs de common ; empreinte SHA-256 canonique du bundle
Effets de bord : aucun
Erreurs, exceptions : ConfigurationInvalide : clé manquante ou en trop, type faux, valeur nulle ou non finie

---

Unité : calendrier_seances
Responsabilité : Représenter les séances de cotation natives d'un symbole et dire si un instant est en séance.
Signature : CalendrierSeances.en_seance(instant) -> bool ; prochaine_fermeture(instant) -> Instant | None
Entrée : intervalles UTC versionnés lus de l'environnement courtier (C04), jamais devinés
Sortie : appartenance à une séance ; instant de la prochaine fermeture ou pause
Effets de bord : aucun
Erreurs, exceptions : CalendrierInconnu si aucune donnée ne couvre l'instant (traduit en ENVIRONMENT_NOT_READY)

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c0_cat1_*.py`) : clés manquantes/en trop, types, valeurs nulles, empreinte égale à reference.technical.canonical_hash ; séances : en séance, pause, fermeture exceptionnelle, instant inconnu.
- Catégorie 2 (`tests/robot/donnees_temps/test_c0_cat2_*.py`) : —.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
