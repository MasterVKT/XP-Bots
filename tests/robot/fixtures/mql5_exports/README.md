# Exports MQL5 synthétiques de contrat

Ces fichiers sont construits à la main au format D12 du document 08. Ils ne
proviennent d'aucun terminal ni compte réel et ne prouvent pas l'exécution
du service MQL5. Ils servent à confronter les formes publiées aux vrais
lecteurs Python : SpecificationsMT5 et GardeAnnonces.

Le serveur fictif avance d'une heure sur UTC. La table S01 couvre novembre
2026. Les séances distinguent cotation et négociation, et un avis fictif
retire l'intervalle 09:30–10:00 UTC. Le premier calendrier est vide ; la
version suivante ajoute une annonce HIGH USD à 09:15 UTC, dont le nom UTF-8
et les identifiants sont synthétiques. Sa première connaissance dépend de
l'instant de réception dans le test, jamais de l'heure native du fichier.

L'horizon du calendrier inclut les durées forward et max_age de CF, plus
la cadence technique de soixante secondes du service. Le test démontre
qu'un horizon limité à forward seul devient insuffisant dès la seconde
suivante. Aucun paramètre métier n'est modifié pour accepter ces exports.

Les contrôles statiques des sources accompagnent cette vérification de
formats. Compilation MetaEditor, comparaison aux fonctions natives et
qualification S01/S08 restent à exécuter explicitement en phase 13.1.
