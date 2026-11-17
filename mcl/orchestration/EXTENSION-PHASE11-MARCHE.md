# Extension de phase 11 — réceptions de marché causales

Décision du 10/11/2026 avant code : le consommateur physique ne peut pas déclarer
la couverture future de C03 au démarrage. MoteurDecision construit actuellement
un RegistreCouverture statique pour toute sa durée. Les mises à jour D12 ne sont
pas livrables au FluxBougies, bien que celui-ci expose actualiser_horaires.
Le coordinateur calcule les sorties avec ses anciens profils tant qu’aucune
nouvelle intention ne lui fait relire specifications. Ces lacunes du consommateur
réel sont détectées avant de construire les adaptateurs de profondeur 2.

Corrections à la source, sans modification de seuil :

- Contrats orchestration 0 : extension de ReceptionExterne, nature MARCHE,
  symbole obligatoire, bytes JSON strict xp-etat-marche-v1, table None. Champs
  existants et défauts conservés ; aucune nouvelle dépendance.
- Orchestration 2 : interpréter ces faits avant les sorties et les bougies.
  Par symbole, version strictement croissante, répétition identique ignorée,
  collision refusée, horaires noyau nouveaux ou None (inchangés), périodes de
  couverture attestées finissant au plus tard à la réception. Source de couverture
  en mémoire, actualisée seulement par ces événements journalisés. Aucun accès
  physique. Les horaires utilisent le vrai FluxBougies.actualiser_horaires.
  État courant conservé dans une enveloppe xp-flux-moteur-v2 du champ flux opaque ;
  les flux jamais mis à jour gardent leur format et comportement d’origine.
  La reprise utilise les entrées initiales de construction conservées et les faits
  scellés du checkpoint ; aucun changement du contrat de FluxBougies.
- Coordinateur 6 : correction C04/C08, relire les profils des symboles possédés
  avant evaluer_sorties, intégrer les horaires connus à l’instant, conserver les
  contrôles d’identité et refuser les profils futurs. Les appels sont enregistrés
  par le port journalisé existant et rejoués sans backend. Aucune règle de sortie
  nouvelle, aucun moteur concurrent.
- Codec 3 : jonction supplémentaire des états dynamiques ; mêmes types publics
  et mêmes sceaux. Défigeage de test tracé, aucun import aval ajouté.

Ordre : défigeage/extension 0, contrat et tests, gate/gel ; correction coordinateur
6, gate/gel ; extension 2, gate/gel ; jonction codec 3, gate/gel ; checkpoint global.
Les autres amonts et les quinze modifications utilisateur restent intacts.

Packet MARCHE : exactement schema, version, horaires, periodes_couvertes.
horaires : None ou objet exactement seances, fermetures, debut_validite_ms,
fin_validite_ms ; intervalles couples d’entiers UTC ms du noyau. Toutes les clés
JSON sont uniques, aucun bool comme entier, nombre non fini, symbole inconnu,
couverture future ou version contradictoire. Un fait invalide n’autorise pas
une entrée et oblige la reprise de l’instance invalidée selon le contrat existant.
Tests : trou pendant connexion perdue, récupération attestée, horaire modifié,
répétition/collision/futur, reprise/checkpoint et C11.14 sans backend réel.
