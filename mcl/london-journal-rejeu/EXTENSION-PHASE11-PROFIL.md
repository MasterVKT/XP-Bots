# Extension du profil courant pour PAPER

P11-10 : le simulateur C10 possède des conditions datées, mais aucun port pour
recevoir une fermeture exceptionnelle ou une contrainte native relue pendant
une séance. Le direct doit garder le même livre et les mêmes calculs, sans
accéder aux attributs privés ni reconstruire son historique à chaque cycle.

Décision : extension additive `actualiser_profil`, limitée à la condition
actuellement qualifiée, sans renouvellement implicite de sa validité. Les
propriétés économiques et la liaison restent stables. Les mises à jour seront
des opérations archivées du livre PAPER pour une reprise causale.

Rayon MCL constaté : 1b → 2 → 3. Défigeages tracés avant les contrats et tests ;
les consommateurs C10 restent inchangés et repassent leurs gates et gels.
Aucune règle ni valeur métier n'est modifiée. La confrontation au terminal
reste en 13.1 ; les tests utilisent le vrai simulateur et les couches figées.
