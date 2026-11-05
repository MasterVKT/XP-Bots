# Contrat de la couche 1a — mt5-adaptateurs (artefact `infrastructure`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 9 et 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2
- **Dépend de** : couches 0c (réelles et figées) ; amont figé : amont-execution ; frontières externes doublées : metatrader5
- **Module** : `src/xpbots/infrastructure/mt5/adaptateurs.py`
- **Sources normatives** : C04, C08 (rapprochement, redémarrage), A04, A08, A10 ; plan maître, section 7.I

---

Unité : flux_ticks_mt5
Responsabilité : Lire les ticks MT5 et la couverture du flux.
Signature : FluxTicksMT5 (port FluxTicks).lire_depuis(symbole, instant) -> list[Tick]
Entrée : symbole courtier, instant ms
Sortie : ticks UTC ordonnés (R14)
Effets de bord : aucun
Erreurs, exceptions : aucune

---

Unité : calcul_courtier_mt5
Responsabilité : Exposer les calculs et caractéristiques natifs du courtier.
Signature : CalculCourtierMT5 (port CalculCourtier).profit(...) ; marge(...) ; verifier(...) ; profil(symbole)
Entrée : ordre hypothétique, symbole
Sortie : valeurs natives en Decimal
Effets de bord : aucun
Erreurs, exceptions : CalculIndisponible

---

Unité : courtier_mt5
Responsabilité : Envoyer les ordres protégés et rapprocher positions et transactions.
Signature : CourtierMT5 (port Courtier).envoyer(ordre) ; positions() ; transactions(depuis) ; modifier_tp(...)
Entrée : ordre protégé avec magic et empreinte de clé
Sortie : réponses natives normalisées
Effets de bord : ordres réels sur compte démo seulement après accord explicite
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/infrastructure/test_c1a_cat1_*.py`) : même suite de contrats que les doublures (flux, calculs, courtier).
- Catégorie 2 (`tests/robot/infrastructure/test_c1a_cat2_*.py`) : --contrat-mt5-demo sur le poste Windows.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
