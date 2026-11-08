# Reprise : protections natives courantes

Décision du 07/11/2026 pendant la phase 6, avant le gel de son enveloppe. Elle répond aux exigences C04 et C08 de la phase autorisée : confirmer les positions et protections réellement présentes avant les décisions du robot. Elle ne modifie aucune règle de stratégie ni aucun seuil.

Le snapshot de propriété initial de 5b portait ticket, symbole, volume et identité D-08. L'historique de remplissage attestait les protections créées à l'origine, sans suffire à constater une suppression ultérieure du SL. Les champs courants `sl` et `tp` deviennent donc des arguments obligatoires de `PositionNative`. Une absence native confirmée vaut `None` ; une lecture indisponible doit rester une erreur d'environnement de la frontière.

Le propriétaire de 5b et son consommateur 6 sont construits dans cette même phase. Le défigeage de nature `modification` et son rayon direct vers 6 sont enregistrés dans le journal MCL. L'arbitrage relève de la mise en œuvre des exigences déjà autorisées ; il n'ajoute pas de demande d'action humaine, celle-ci étant réservée aux étapes prévues par le plan. Les producteurs synthétiques des tests de 6 sont adaptés au contrat ; 6, encore non gelée, est revalidée après le nouveau gel de 5b.

La transition de protection demeure dans le vrai cycle 4. Le rapprochement ne produit cette transition qu'après preuve complète de propriété, et conserve le risque initial jusqu'à clôture native confirmée. Les tests reproduisent un SL supprimé depuis le journal et vérifient l'absence de clôture d'une position étrangère.
