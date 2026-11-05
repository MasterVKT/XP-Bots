# Contrat de la couche 1b — constructeur-bougies (artefact `donnees-temps`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 2), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : aucune
- **Module** : `src/xpbots/donnees_temps/c1b_bougies.py`
- **Sources normatives** : C03 (points 1 à 12), C11.1, C11.3, C11.4 ; plan maître, section 7.A

---

Unité : constructeur_bougies
Responsabilité : Agréger les ticks en bougies M15/H1 Bid clôturées sur [T,T+d) aligné UTC et signaler les trous.
Signature : ConstructeurBougies(symbole, periode_s).ajouter_tick(tick) -> list[Bougie] ; signaler_couverture(evt) -> list[EvenementTrou] ; avancer_horloge(i) -> list[Bougie]
Entrée : ticks ordonnés (instant, séquence) ; événements de couverture ; calendrier de séances
Sortie : bougies clôturées OHLC Bid avec validité et nombre de ticks ; événements de trou
Effets de bord : état de la bougie en formation
Erreurs, exceptions : TickHorsOrdre si un tick recule (rejeté, journalisé)

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c1b_cat1_*.py`) : tick à T+900 dans la bougie suivante (C11.3), égalités de ms par séquence, minute inchangée ≠ trou, fermeture officielle ≠ trou, interruption inexpliquée = trou, H1 invisible avant clôture, clôture par horloge, bougie sans Bid (R4).
- Catégorie 2 (`tests/robot/donnees_temps/test_c1b_cat2_*.py`) : via la couche 3.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
