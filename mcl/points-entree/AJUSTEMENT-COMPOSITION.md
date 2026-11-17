# Ajustement du DAG de phase 11

La lecture du code réel établit deux consommateurs d'une même composition :
la boucle directe et le rejeu d'incident. La fabrique C10 mesure les journées
du protocole et ne peut pas reconstruire les fabriques du direct. Une unité
1f compose donc les bras London réels, C05 et l'IA, sans logique métier copiée.
La commande de rapports lit aussi les archives C10 produites par 1c : 1e
dépend de 1c et 1f et passe en profondeur 2. Principal reste en profondeur 3.

Question-test : la composition se construit et se teste sans boucle ni rapport,
à partir de 0 et des amonts figés ; chaque consommateur requiert sa composition.
Le parallélisme déclaré de 1a/1b/1c/1d/1f suit ces dépendances réelles. Aucun
ordre d'exécution n'est utilisé pour calculer la profondeur. Le checkpoint de
journal est reconstruit par le moteur public ; la reprise C08 reste obligatoire.
