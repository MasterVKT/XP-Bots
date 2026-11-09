# Couche 2 — Cache causal et reprise

Statut : finalisé avant code le 09/11/2026 ; 0 et 1 figées. Consommateur : 3. A10/A12.

| Élément | Contrat |
|---|---|
| Unité | cache_vetos |
| Responsabilité | Conserver les vetos acceptés sans renouvellement, leur connaissance et la dernière séquence |
| Signature | CacheVetos(parametres, etat=None), recevoir(octets, reception_ms), avancer(instant_ms), consulter(symbole, instant_ms) |
| Entrée | Paramètres réels, snapshots externes, état pur et temps logique monotone |
| Sortie | ReceptionSnapshot immuable ; tuple de VetoConnu actifs ; EtatCache exportable |
| Effets de bord | État mémoire explicite seulement, aucune horloge/fichier/réinférence |
| Erreurs | ErreurContexte pour appel/reprise incohérents ; réception invalide rend un résultat rejeté |

`EtatCache(dernier_snapshot=None, scelles=(), dernier_ms=0)` garde la dernière réception validée,
les identités déjà connues et le temps logique observé. `derniere_sequence` et `dernier_snapshot`
sont consultables sans exporter le registre complet. `ReceptionSnapshot(acceptee, ignoree, raison,
snapshot, ajoutes)` distingue ajout, relecture et rejet. Les seuls ajouts viennent du vrai validateur 1.

La séquence en recul est refusée ; même séquence et hash différents sont une réécriture refusée.
Une relecture encore fraîche est ignorée, sans changer la première réception ni la connaissance.
Un heartbeat neuf, y compris vide, ne retire aucun veto accepté et ne modifie pas sa fin. Un ID déjà
connu avec des champs différents invalide toute la réception, même si cet ID a expiré. Une liste
contenant de nouveaux IDs et une réécriture n'ajoute donc rien partiellement.

Le cache actif contient seulement les événements non expirés. Les identités scellées et leur preuve
originale sont conservées séparément afin d'empêcher une résurrection avec un nouvel until. Aucune
durée de rétention arbitraire n'est inventée. La couche physique future pourra représenter ces
preuves en tables ; le lecteur ne conserve pas l'historique de tous les heartbeats.

`consulter(symbole, instant_ms)` rend les vetos dont la réception initiale est connue et dont
valid_from ≤ instant < valid_until, triés par ID pour un choix de preuve déterministe. Une requête
historique utilise seulement les identités alors reçues. `avancer` met à jour le temps et purge le
cache actif ; les réceptions ont lieu avant l'observation du même instant. Un rejet peut avancer
le temps observé mais ne change ni séquence acceptée, ni preuve, ni identité validée.
`prochaine_echeance_ms(instant_ms)` rend la première fin future d'un veto alors connu, ou None.

La reprise revalide chaque preuve et le dernier snapshot depuis leurs octets originaux avec le vrai
validateur 1, à la réception originale. Métadonnées, séquences, connaissance, unicité des IDs et
causalité sont vérifiées ; une preuve perdue ou altérée est refusée. Aucune date n'est renouvelée.
Tests propres : `test_cat1_c2_cache.py` ; jonction : `test_cat2_c2_cache.py`, A14-2/7/16 et préfixes.
