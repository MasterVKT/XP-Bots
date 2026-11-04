# Nettoyage des ressources et préparation du merge

Opération du **4 novembre 2026**. Le but est de garder une base claire pour construire les robots tout en préservant les travaux précédents et les ajouts effectués dans le dépôt distant.

## Organisation retenue

Les deux fichiers déjà suivis dans `livrables/strategies_m15/` contiennent maintenant les spécifications complètes **3.1.0**, IA distante incluse. Leurs chemins historiques sont conservés. Les décisions, données requises et choix IA sont répartis dans `docs/`. Les paramètres, schémas et prompts ont chacun un emplacement unique dans `config/`, `schemas/` et `prompts/`. Les fonctions utiles et leurs contrôles se trouvent dans `reference/`, `tests/` et `tools/`.

Les paramètres techniques et IA, les sections C03–C11/S01/S02 et les corps des fonctions déplacées n'ont pas été modifiés. Les générateurs qui pouvaient recréer des versions obsolètes ont été retirés des ressources actives. La version technique V3 et la version documentaire 3.1.0 restent distinguées.

## Archive locale récupérable

Les fichiers originaux ont été déplacés dans :

```text
D:\PROJETS\XP-Bots-archives\2026-11-04_organisation\
```

Le fichier `manifest_avant_nettoyage.json` dans cette archive inventorie **1 679 fichiers**, **185 106 150 octets**, avec leur chemin d'origine et leur SHA-256. Chaque empreinte a été revérifiée après déplacement. L'archive est hors du dépôt ; un clone Git seul ne la contient donc pas.

L'archive conserve notamment :

- `.codex-artifact-work/` : anciens générateurs, scripts de recherche, caches M1, intermédiaires et résultats explicitement invalides ;
- `livrables/` : V1, V2 de recherche, V3.0, V3.1 avant rangement, ZIP et résultats détaillés de combinaisons ;
- `docs/` : les deux documents source avant rangement ; la référence Forex IA utile est également conservée dans le dépôt actuel ;
- `input_clean.md` : conversation source brute, remplacée comme point d'entrée du projet par le README actuel.

Les résultats invalides et les versions anciennes ne servent jamais de réglages actifs. Les traces détaillées et prix restent récupérables pour une analyse historique, sans alourdir Git. L'archive contient aussi le script ponctuel de rangement, qui ne fait pas partie des outils courants du projet.

Pour récupérer un élément, lire son chemin dans le manifeste, copier uniquement cet élément depuis l'archive et vérifier son SHA-256. Placer les prix et résultats bruts dans un emplacement exclu par `.gitignore`, ou utiliser un dossier de recherche séparé. Ne pas réexécuter les anciens générateurs dans la racine nettoyée : ils ciblent l'ancienne arborescence et peuvent rétablir des documents dépassés.

## État distant vérifié

Une récupération des références distantes a été effectuée sans modifier la branche locale :

| Référence au moment de l'audit | Commit |
|---|---|
| Branche locale `master` | `9dc1b163542517441c30531828543c3b38fa2a23` |
| `origin/master` | `d9e02d133fae13361dba9a0ca2317208cd5bbe21` |
| Ancêtre commun | `9dc1b163542517441c30531828543c3b38fa2a23` |

Les trois nouveaux commits distants ajoutent **20 fichiers** dans `.claude/skills/mcl-matryoshka-construction-layers/` et `livrables/skills/`. Aucun des cinq fichiers auparavant suivis localement n'a changé à distance. Le nettoyage ne crée ni ne supprime de fichier dans ces deux emplacements distants. Leurs contenus seront apportés par le merge.

Les différences locales et distantes sont contrôlées dans un index Git temporaire par `python tools/verify_project.py --git`. Le contrôle inclut les nouveaux fichiers non encore ajoutés à Git, recherche aussi les collisions fichier/dossier et vérifie que tous les ajouts distants restent identiques dans l'arbre combiné. Il laisse la branche, l'index réel et les fichiers de travail en place.

## Merge ultérieur

Le nettoyage laisse les modifications locales à examiner et à enregistrer. Il n'a effectué ni commit, ni merge, ni push. Les suppressions des deux anciens générateurs et de la conversation brute sont intentionnelles ; les deux spécifications existantes sont des mises à jour au même chemin.

Après revue et commit des modifications locales, le merge prévu est un merge Git ordinaire de `origin/master`. Si des travaux distants arrivent entre-temps, récupérer d'abord les nouvelles références puis relancer la vérification. La simulation validée aujourd'hui ne constitue pas une garantie pour un autre état du dépôt.

Le `.gitignore` laisse les skills distants suivables, y compris leur ZIP. Aucun `reset --hard`, nettoyage forcé, renormalisation globale ou push forcé n'est nécessaire pour cette organisation.

Les deux fichiers de paramètres figés et la référence utilisateur conservent leurs octets d'origine grâce à des règles ciblées de `.gitattributes`. Les autres fichiers texte utilisent LF. Les conversions automatiques Windows ne doivent pas invalider les empreintes lors d'un clone du dépôt.
