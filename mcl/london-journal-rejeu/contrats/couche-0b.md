# Couche 0b — protocole

Statut : finalisé avant source. Consommateurs : 1b, 1c, 1d, 2 et 3.
Dépend de : ConfigurationFigee du noyau, aucune unité parallèle.

Unité : protocole_c10. Responsabilité : protocole fixé avant lecture des données.
Signatures : ErreurProtocole(ValueError), BlocC10, ScenarioExecution,
ParametresBootstrap, SeuilsC10, ProtocoleC10 et charger_protocole(configuration).
Valeurs immuables, nombres finis, bool refusé comme entier, aucun effet de bord.

BlocC10(nom, debut, fin_exclusive, usage) porte des dates UTC à bornes semi-ouvertes,
et expose intervalle_ms. Les blocs normatifs couvrent initialisation, développement,
validation, test réservé et diagnostic. Le continu couvre le début des performances
jusqu’à la fin de l’historique demandé. Le début effectif du diagnostic V3 et le
protocole prospectif sont rapportés séparément. Aucun accès de fichier n’est autorisé
par ce type ; le verrou avant lecture appartient à 2.

ScenarioExecution(nom, delai_ms, ticks_adverses, facteur_spread) décrit l’exécution.
Le chargeur produit REFERENCE (250 ms, un incrément tick_size, spread historique)
et STRESS (1 000 ms, deux incréments, Ask=Bid+1,25×spread ; Bid conservé), P-11.
Le type permet des paramètres explicites pour les tests de frontière ; l’exécuteur
de recherche n’accepte que les scénarios du protocole. Aucun coût de commission
n’est inventé dans ces scénarios : il vient des conditions datées de 0a.

ParametresBootstrap(replications, bloc_jours, graine, percentile_bas,
percentile_haut) est chargé depuis les cinq clés bootstrap de l’export IA.
Les percentiles sont dans [0,100], bas<haut. Les paramètres financiers A13 et
les cibles de fréquence et rétention viennent aussi de la configuration chargée.
Les seuls seuils exclusivement textuels de C10 sont codés ici et testés contre
la spécification : effectifs du test réservé, PF, drawdowns et référence exploitable.

ProtocoleC10 expose blocs, continu, prospectif, debut_diagnostic_v3, scenarios,
bootstrap, seuils et perturbations. Les six perturbations sont des triples
(nom, champ, valeur) : objectifs et buffer ×0,9/×1,1, durée 6 480/7 920 s.
Elles ne dépendent pas d’une recherche sur les données. Le chargeur n’importe
pas 0a ; 2 convertit ces triples vers EcartRejeu lors de leur utilisation.

Erreurs : ErreurProtocole sur configuration non chargée, entier ou décimal invalide,
intervalle ou paramètres incohérents. Catégorie 1 : dates exactes, bornes, scénarios,
P-11, seuils, six écarts distincts et chargement effectif des paramètres exportés.
La présence des seules valeurs textuelles codées est vérifiée dans C10 par les tests.
Pas de catégorie 2 entre nouvelles couches.
