# Contrat de la couche 1e — quotas_london

- **Statut** : finalisé le 06/11/2026, avant implémentation ; gel après gate vert. Corrigé le 06/11/2026 par défigeage `correction` : fins LF pour la conservation des empreintes après normalisation Git.
- **Consommateurs cartographiés** : couche 2, moteur London.
- **Dépend de** : couches 0a et 0b réelles et figées ; noyau et données réels ; aucune frontière externe.

Unité : quotas_london
Responsabilité : celle du document 02, §6.3, sans ajout de règle métier.
Signature : `QuotasLondon(parametres: ParametresLondon, symbole: str, etat: EtatQuotas | None = None) ; changer_jour(jour: date) ; sur_issue(issue: Issue) ; refus(sens: Sens) -> RefusLondon | None ; etat -> EtatQuotas ; total -> int ; par_sens(sens: Sens) -> int`.
Entrée : paramètres London typés, valeurs du noyau et bougies enrichies réelles, selon la signature.
Sortie : valeur validée ou refus fermé conforme au document 01, §9.3.
Effets de bord : aucun accès externe ; seule la classe de quotas conserve son état interne.
Erreurs, exceptions : `ErreurLondon` pour les violations décrites ci-dessous.

Chaque issue REMPLIE signifie un volume confirmé non nul (partiel ou total). La première occurrence de
sa clé consomme exactement une entrée ; les répétitions sont idempotentes, même après une clôture. REFUSEE,
EXPIREE et CLOTUREE ne consomment rien. Le jour du remplissage est celui d'issue.instant_ms à Londres,
indépendamment du jour UTC. Un nouveau jour efface uniquement les quotas ; un événement ancien ne réinitialise
jamais le jour courant et son remplissage ancien est ignoré pour le quota courant. changer_jour refuse un
recul de date ; une même date conserve les compteurs. Le total est contrôlé avant le quota de direction.
Un refus rend DAILY_ENTRY_CAP/MAXIMUM_JOURNALIER ou SENS_DEJA_REMPLI. L'état immuable exporté conserve les clés,
pour permettre restauration et idempotence ; ses clés doivent concerner ce symbole et cette stratégie.
Une issue étrangère, un symbole vide, un jour invalide ou un sens non typé lève ErreurLondon.

## Spécification exécutable

`tests/robot/moteur_london/test_cat1_c1e_quotas_london.py` et
`tests/robot/moteur_london/test_cat2_c1e_quotas_london.py`.

## Comportements documentés (loi de Hyrum)

Les comparaisons n'ajoutent aucune tolérance ; les tests aux bornes utilisent des valeurs dyadiques.
Le texte exact des erreurs n'est pas garanti. Les refus rendent les codes et détails du noyau, sans nouveau code.
