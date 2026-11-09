# Couche 2 — orchestration

Finalisation après le nouveau gel de 0 et 1. Enveloppe pure, sans import de méthode,
lecture physique, horloge ou réseau.

`MoteurDecision(configuration, bras, horaires, periodes_couvertes, *,
controle_fondamental=None, lecteur_ia=None, source_fondamentale=None,
source_ia=None, scenario_fondamental=None, etat=None)` exige un déploiement commun,
des coordinateurs tracés et des stratégies et comptes distincts entre bras.
Le mode A/B chargé exige REFERENCE et IA et un lecteur réel ; REFERENCE conserve
le complément absent. C05 est partagé. Son absence exige le scénario technique
neutre explicite. Les sources synthétiques facultatives exposent `extraire(t)` ;
leurs réceptions typées sont journalisées avant application. Horaires, profils et
périodes portent les mêmes symboles.

`traiter(EntreeMoteur) -> SortieEvenement` exige numéros contigus et dates monotones.
La répétition identique de la dernière entrée est ignorée sans calcul, commande ou
enregistrement. Réécriture, recul ou entrée étrangère sont refusés. Un échec après
mutation invalide le moteur, qui ne peut plus rendre de commandes ou exporter son état.

Chaque réception applique C05 et IA puis avance leurs états. Les faits natifs et
sorties obligatoires de tous les bras précèdent toute bougie et tout signal. Les
bougies sont construites une seule fois, partagées immuablement, ordonnées par
clôture, H1 avant M15 puis priorité des symboles. Tous les signaux du groupe sont
soumis ensemble à chaque coordinateur : C08 assure les priorités et réservations
atomiques. Les issues reviennent à leur stratégie par le bras. PERSISTANCE ne touche
que les bras ciblés, sans appel préalable modifiant la révision de la preuve.
Aucune minuterie ne crée de prix. Les commandes restent étiquetées par bras.

`entrees` expose des `EntreeJournalisee` avec toutes les réceptions et tous les appels
et résultats normalisés des calculs. `rejouer(entree_journalisee)` réutilise exactement
`traiter` et le port journalisé de 1, sans consultation du backend ni appel IA. Tout
appel manquant, supplémentaire ou différent provoque une divergence. Les paramètres
initiaux et `initialisation_calculs` sont fournis identiquement à la reconstruction.

`traiter_ticks`, `traiter_evenement` et `confirmer_persistance` adaptent les données
vers ce chemin unique. `prochaine_echeance_ms` combine coordinateurs, C05, IA et
réceptions. `etat` fournit `EtatMoteur`, photographie scellée de la configuration,
des flux publics C03, des états publics des bras et contrôles et du journal.
La reprise exige des bras et contrôles restaurés par leurs API réelles ; elle vérifie
leur concordance puis reprend les flux publics C03. Le scellement détecte une
corruption accidentelle, sans authentifier un stockage physique futur.

Catégorie 1 : validation, répétition, causalité, isolation, calculs et divergence,
échéances, reprise et corruption ; C11.10 avec fabriques contractuelles externes.
Catégorie 2 : jonction réelle 0→1→2 London, journée A/B, journal exactement rejoué
sur backend interdit, veto sans rattrapage et sorties prioritaires. Aucun seuil ou
coût modifié. Simulateur C10, métriques et persistance physique restent futurs.
