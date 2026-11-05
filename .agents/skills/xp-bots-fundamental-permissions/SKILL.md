---
name: xp-bots-fundamental-permissions
description: "Contrat C05 de XP-Bots : permissions fondamentales externes obligatoires (schéma fundamental-permission-v1, ANY/LONG_ONLY/SHORT_ONLY, ALLOW/NO_NEW/FLATTEN, séquence, known_at, validité 900 s, heartbeat), garde d'annonces HIGH par devise, fenêtre [N−900 s, N+900 s), fraîcheur et couverture du calendrier, causalité des heures de connaissance, scénario TECHNICAL_CONTROL_NEUTRAL. Utiliser pour concevoir ou vérifier l'interface avec le module fondamental et le calendrier. Déclencheurs : fondamental, permission fondamentale, FLATTEN, NO_NEW, annonce, calendrier, news, NEWS_WINDOW, heartbeat, known_at, C05."
---

# Permissions fondamentales et garde d'annonces

## Ressources

- Autorité : section C05 des deux spécifications (schéma JSON, conditions, effets) et C08 point 2 (priorité des
  clôtures obligatoires) ; valeurs `news_*` et `fundamental_*` du bloc `common` de
  `config/parametres_figes_v3.json`.
- Données historiques nécessaires : section 4 de `docs/data/03_Donnees_Historiques_Requises_et_Validation.md`.
- Composant à construire : contrôles fondamentaux obligatoires (`docs/architecture/GUIDE_IMPLEMENTATION.md`).

## Workflow

1. Écrire le validateur de message avant toute logique : toutes les conditions de C05 (ordre des heures,
   durée positive au plus 900 s, séquence strictement croissante par symbole, aucun timestamp futur, réception
   locale au plus tôt `known_at`).
2. Implémenter les effets : direction incompatible, `NO_NEW`, message absent, périmé ou invalide → blocage des
   nouvelles entrées ; `FLATTEN` → clôture des positions possédées sur le symbole puis blocage ; changement de
   direction → aucune clôture automatique.
3. Implémenter la garde d'annonces : devises concernées par symbole, fenêtre `[N−900 s, N+900 s)` début inclus
   et fin exclue, clôture envoyée à N−900 s, calendrier âgé d'au plus 86 400 s et couvrant 172 800 s.
4. Tester C11 points 8 et 9 et les cas tardifs : annonce apprise pendant sa fenêtre, calendrier révisé sans
   réécriture du passé, contrôle au signal puis juste avant l'ordre.
5. Rejouer `python tools/verify_project.py` (les deux suites vérifient la présence de ces contrats).

## Garde-fous

- Le complément LLM ne remplace jamais une permission manquante : sa panne vaut `NEUTRAL`, pas `ANY/ALLOW`.
- `TECHNICAL_CONTROL_NEUTRAL` n'existe que pour un contrôle technique isolé explicitement nommé, jamais comme
  substitut implicite d'un fournisseur absent en réel.
- Ne pas recréer des permissions historiques avec des données macro révisées, le DXY ou des titres téléchargés
  aujourd'hui : c'est une fuite d'information.
- Conserver les versions de calendrier et les heures de connaissance ; ne pas rejouer un signal déjà refusé
  quand le biais change ensuite.
