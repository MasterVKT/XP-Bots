# Procédure de création ou d'extension d'une skill

À charger seulement quand une lacune est classée « créer » ou « étendre », en mode écriture.

## 1. Décider

1. Relire le registre : `python .agents/skills/xp-bots-skill-gap-detector/scripts/skill_gap_ledger.py list`.
2. Étendre si une skill existante couvre déjà le domaine visé ; créer seulement pour un domaine réutilisable
   qu'une requête réelle vise, jamais pour un fichier ou une commande unique.
3. Une seule création par requête ; le générateur refuse une seconde création pour la même requête suivie.

## 2. Préparer le corps

Écrire le corps (sans frontmatter) dans un brouillon ignoré par Git, par exemple
`.local/skill-drafts/<nom>.md`. Il contient au minimum :

- `## Workflow` : étapes numérotées et vérifiables, avec les commandes réelles du projet ;
- `## Garde-fous` : pièges constatés dans XP-Bots, renvois à `.agents/PROJECT_RULES.md` plutôt que copie.

Interdits : placeholders non résolus (`TODO`, `TBD`, variables `<ROOT>`…), règles communes recopiées, README
auxiliaire, valeurs figées recopiées depuis `config/`.

## 3. Simuler puis créer

```text
python .agents/skills/xp-bots-skill-gap-detector/scripts/create_skill.py --dry-run \
  --name xp-bots-<domaine> --description "<ce que fait la skill et quand l'utiliser>" \
  --keywords "<mot>,<préfixe*>,<expression composée>" --catalog "<résumé en une ligne>" \
  --example-request "<requête réaliste du projet>" --body-file .local/skill-drafts/<nom>.md \
  [--gap-id <identifiant du registre>]
```

Puis la même commande sans `--dry-run`. Dans l'ordre, le générateur : valide nom, description, mots-clés et
ligne de catalogue ; vérifie **avant toute écriture** que les mots-clés sélectionnent la skill pour la requête
d'exemple ; crée `.agents/skills/<nom>/SKILL.md` ; ajoute la règle de routage, la ligne de catalogue et le cas
de test ; régénère les copies ; enregistre la décision au registre ; relance les validateurs et restaure l'état
antérieur s'ils échouent.

## 4. Étendre

```text
python .agents/skills/xp-bots-skill-gap-detector/scripts/create_skill.py --extend <skill> \
  --keywords "<nouveaux mots-clés>" --example-request "<requête>" [--append-file <section.md>] [--gap-id <id>]
```

Les mots-clés ajoutés doivent sélectionner la skill pour la requête d'exemple ; la section éventuelle est
ajoutée à la fin du `SKILL.md` canonique.

## 5. Clore

- `python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py` doit être vert.
- Déclarer la décision dans la clé `couverture_skills` du pied d'audit.
- Hors mode écriture : ne rien lancer, décrire la skill envisagée (nom, description, mots-clés, requête
  d'exemple) et consigner la lacune seulement quand l'écriture redevient permise.
