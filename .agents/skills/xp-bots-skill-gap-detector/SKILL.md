---
name: xp-bots-skill-gap-detector
description: "Détecteur de lacunes de skills XP-Bots, chargé à chaque requête : inventorie les types de tâches effectués, les classe (couvert, partiellement couvert, non couvert réutilisable, non couvert ponctuel), consigne au registre .agents/skill-gap-ledger.json et crée ou étend une skill routée par une seule commande. Déclencheurs : lacune de skill, aucune skill ne couvre, créer une skill, étendre une skill, registre des lacunes, couverture des skills."
---

# Détection des lacunes de skills

## Workflow

1. Inventorier les **types de tâches** réellement effectués dans la requête (jamais une liste de fichiers).
2. Classer chaque type : **couvert** ; **partiellement couvert** → étendre ; **non couvert et réutilisable**
   → créer ; **non couvert et ponctuel** → consigner.
3. Consigner toute lacune au registre :
   `python .agents/skills/xp-bots-skill-gap-detector/scripts/skill_gap_ledger.py record --label "<type de tâche>" --evidence "<preuve courte>"`.
   À la deuxième occurrence, la lacune ponctuelle est promue (`list`, `show --id …` pour consulter).
4. Créer ou étendre seulement à ce moment : lire `references/creation-procedure.md`, puis lancer
   `create_skill.py` (d'abord `--dry-run`). Hors mode écriture (planification, lecture seule) : ne rien
   écrire et déclarer la skill envisagée.
5. Reporter le classement dans la clé `couverture_skills` du pied d'audit.

## Garde-fous

- Préférer l'extension à la création ; au plus une nouvelle skill par requête.
- Pas de skill pour une commande unique ni pour une règle déjà canonique (`AGENTS.md`, `PROJECT_RULES.md`).
- Nom de dossier = champ `name` ; validateurs verts avant la fin de la requête.
- Toute décision du registre appartient au vocabulaire fermé du script ; une autre valeur est refusée.
