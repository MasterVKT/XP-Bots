# Couche 1b — simulateur causal C10

Unité : simulateur_execution, dépendances 0a/0b, noyau et exécution figés.
SimulateurExecution(configuration, conditions, creation_ms, scenario, plans=None)
implémente les sept calculs du port courtier et le transport des commandes C08.
conditions est une collection de ConditionContrat non chevauchants par symbole,
avec frais connus et symboles natifs stables. À chaque instant, seules les
conditions effectives dont connu_ms et profil.releve_ms ne dépassent pas cet
instant sont disponibles. Absence, chevauchement, devise non USD et coût inconnu
sont des erreurs ; aucun tarif nul n'est déduit d'une absence. Le compte commence
au capital de la configuration, sans apport, retrait ni réinitialisation.

specifications, profit, frais_aller_retour, frais_sortie, marge, etat_compte,
controler utilisent les objets canoniques. Profit = sens × volume × contrat ×
écart ; marge à levier configuré. Fonds propres = solde + flottant, long au Bid,
short à l'Ask. Les minima de commissions s'appliquent par ordre, non par morceau
de remplissage. Le solde peut devenir négatif après un gap. La réserve de
glissement C07 ne devient jamais un débit du P&L. base_utc reconstruit la base
depuis les mouvements natifs, avec preuve d'absence de position à minuit.

tick_decision(tick) applique le facteur de spread au seul Ask ; Bid est conservé.
sur_tick(tick) attend le tick historique brut, met à jour le compte avec la même
cotation stressée et rend les réponses natives. Le pilote transmet tick_decision
au moteur une seule fois. Le premier tick de clé strictement supérieure, d'heure
>= envoi + délai, remplit un marché accepté. Achat à Ask + incréments tick_size,
vente à Bid - incréments ; sortie au marché dans le sens défavorable opposé.
Le TTL interdit un nouvel envoi expiré ; un ordre accepté reste un fait natif
jusqu'à remplissage ou annulation effectivement confirmée.

SL/TP déjà actifs sont traités sur le premier tick exécutable qui les touche,
avant une clôture logicielle en attente. Leur activation est native : aucun
second délai d'envoi n'est ajouté au déclenchement d'un SL déjà attaché. Un stop
subit gap et glissement adverse. Un TP est une limite : au niveau ou mieux, sans
pénalité adverse. L'ordre des ticks de même milliseconde décide de la première
touche ; aucune déduction OHLC. Les protections d'une entrée sont actives dès son
remplissage. Sans cotation, les demandes restent en attente ; aucun prix ancien
ne sert à inventer une sortie. Une position traversant le blackout est signalée
comme erreur de code, pas fermée artificiellement.

soumettre(commandes) déduplique les références et rend réponses et observations
natives. observation(cle=None), positions_ouvertes, profil_compte, avancer_au(t),
prochaine_echeance_ms et extraire_reponses(t) permettent le rapprochement et les
accusés différés sans tick artificiel. courbe, trades, reponses exposent des
instantanés. premiers_remplissages rend les paires (cle, instant_ms) des entrées
effectivement remplies, indépendamment de leur clôture. enregistrer_contexte(cle, contexte) attache le contexte causal aux
trades. Les livres de deux instances ne partagent aucun état mutable.

PlanExecution(statut=ACCEPTE, retard_accuse_ms=0, fractions=(1,), retards_ms=(0,),
reliquat_annule=True, protections=True, mise_a_jour=True) est une doublure explicite du seul comportement externe : statut
d'accusé, retard, fractions natives et délais relatifs, reliquat annulé, présence
de protections et refus de mise à jour. Les fractions cumulées ne dépassent pas
un, et les volumes natifs respectent le pas. Un accusé INCONNU ne supprime pas
l'ordre. Le profil SYNTHETIQUE_S5 de compatibilité peut déclarer zéro délai et
zéro glissement ; il utilise le même simulateur, n'est jamais appelé REFERENCE
C10. Les vrais scénarios de recherche viennent de 0b.

Les champs de PlanExecution sont strictement typés ; les fractions sont Decimal.
Les tarifs variables de plusieurs partiels sont cumulés à leurs dates de
remplissage, puis comparés au minimum déjà exigé pour cet ordre ; une baisse de
tarif ne crée jamais un remboursement fictif. Les données du contexte sont
copiées à leur enregistrement. ErreurRejeu signale chronologie ou condition
inexploitable ; une commande ou un tick d'un type étranger lève TypeError.

Tests propres : prix calculés à la main, 249/250 ms et 999/1000 ms, un/deux
incréments, stress Bid inchangé, TP limite, gap et séquence SL/TP, absence de
cotation, frais minima/partiels et coûts datés, flottant et marge, idempotence,
accusés inconnus/différés, protections et blackout. Jonctions : commandes, cycle,
dimensionnement et gardes réels, sans second moteur d'admission dans le simulateur.
