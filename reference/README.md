# Fonctions de référence

Ces modules servent à comparer les futurs portages aux spécifications. Ils ne constituent pas un robot opérationnel.

- [technical.py](technical.py) : EMA, RSI et ATR de Wilder, horaires, états de repli, configurations London et arrondis de niveaux. Les détecteurs comptent des configurations potentielles ; ils n'appliquent pas tout le portefeuille, les quotas après fills, le fondamental ou l'exécution du courtier.
- [llm_contracts.py](llm_contracts.py) : validation stricte des sorties, preuve textuelle, horodatage causal, veto facultatif, lecture du snapshot et calcul des plafonds de coût. Aucun appel réseau ou ordre n'est présent. La persistance, les ACL, la réservation transactionnelle et les protections d'un service de production restent à construire.

Les valeurs sont chargées depuis `config/`, les schémas depuis `schemas/` et les prompts depuis `prompts/`. Il n'existe plus de copie de ces réglages dans un générateur de documents. Les fonctions existantes ont été déplacées sans modification de leur corps ; les empreintes de leur arbre syntaxique sont conservées dans [conservation_ressources.json](../docs/validation/conservation_ressources.json).

Depuis la racine, lancer `python tools/verify_project.py` pour les vérifier. Les tests n'utilisent ni clé API ni historique privé et n'effectuent aucune inférence locale ou distante.
