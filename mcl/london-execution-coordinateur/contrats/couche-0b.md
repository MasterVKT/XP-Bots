# Contrat de la couche 0b — ports_controles

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 5a, 6.
- **Dépend de** : noyau amont ; aucune autre couche de cet artefact.

Unité : ports_controles
Responsabilité : Ports structurels de contrôle et deux implémentations neutres nommées, explicitement injectées.
Signature : `ControleFondamental`, `LecteurContexteIA`, `ControleTechniqueNeutre`, `ComplementAbsent`
Entrée : Symbole, sens et instant du noyau ; aucune source fondamentale réelle.
Sortie : Ports structurels de contrôle et deux implémentations neutres nommées, explicitement injectées.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

Le port fondamental expose `evaluer(symbole, sens, instant_ms)` et `clotures_obligatoires(instant_ms)` ; le port IA expose `evaluer(symbole, instant_ms)`. `ControleTechniqueNeutre.scenario` vaut TECHNICAL_CONTROL_NEUTRAL et rend ANY/ALLOW sous la forme de la décision admise du noyau, sans demande de clôture. Il est réservé au contrôle technique isolé et n’est jamais un défaut de composition de production. `ComplementAbsent` rend exclusivement NEUTRAL, sans pouvoir lever un refus fondamental. Les erreurs du vrai fondamental ne sont jamais transformées en permission neutre par ces classes.

## Spécification exécutable

`tests/robot/london_execution_coordinateur/test_cat1_c0b_ports_controles.py` : conformité structurelle, deux sens, nom du scénario et absence de veto additionnel.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.
