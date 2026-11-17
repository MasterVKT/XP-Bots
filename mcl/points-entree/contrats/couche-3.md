# Couche 3 — principal (finalisé le 14/11/2026 avant code)

`main(argv=None, *, sdk=None) -> int` et `python -m xpbots.app` exposent le même
dispatcher. L'injection SDK est une frontière de test, pas une option de la CLI.
Le parseur et les commandes hors ligne ne chargent jamais MetaTrader5. Les
arguments invalides rendent 2, l'aide et une commande réussie 0, une interruption
opérateur 130. Les diagnostics portent des codes stables, sans traceback ni
erreur native brute. Aucune option d'identifiant, mot de passe ou clé d'API.

`--racine-depot` (défaut `.`), placé avant la commande, désigne les ressources
de confiance : trois fichiers techniques/IA/conservation lus par 4, puis
charger_configuration_figee. Les registres sont analysés par 0 ; le mode ne
se remplace pas depuis un argument. Tout fichier passe par l'infrastructure,
avec plafond technique de document de 64 Mio par défaut et refus de .env.
--max-octets-document permet d'augmenter explicitement cette borne technique
pour les archives C10 ou d'incident volumineuses ; une valeur positive est
requise et aucun paramètre métier ne change. Les sorties
s'écrivent atomiquement et refusent l'écrasement sans --ecraser.

## Commandes

| Commande | Arguments propres | Chemin réel |
|---|---|---|
| gabarits | --sortie-registre, --sortie-fermetures | gabarits non exécutables de 0 |
| parametres-export | --registre, --sortie | table de chemins.table_heure et TSV de 0, horizon CF |
| qualifier | --registre, --sortie, --terminal facultatif | 4 et qualifier 1d en lecture seule |
| direct | --registre, --archive-incident, --jusqua-utc et --max-iterations facultatifs, --terminal facultatif | BoucleDirect 2 et archive du dernier COMMIT |
| rejeu | --registre, --demande, --ticks, --archive, --rapport ; --ouvrir-reserve et --gel facultatifs | décodage et lancer_rejeu 1c |
| rapports | --registre, --archives (une ou plusieurs), --sortie | rapporter_archives 1e |
| incident | --archive, --sortie | rapporter_incident 1e, sans backend |
| geler-code | --registre, --sortie | inventaire réel empreinte_robot 4 |

--ecraser s'applique aux seules sorties explicites, jamais au premier gel
du registre du réservé. Les commandes qualifier/direct possèdent leurs
ressources physiques et les ferment dans tous les chemins. Si fermer() signale
un worker encore actif après l'attente bornée, le propriétaire garde ressources
et verrou, alerte et attend son retour ; le processus ne quitte pas de lui-même
en abandonnant cette attente. Les protections, accusés inconnus et arrêts
persistent selon 2/4 ; aucune commande de réactivation automatique n'est ajoutée.

Les rapports C10 s'enveloppent dans xp-dossier-validation-v1 avec commit et
empreintes CF du registre, puis le vrai rapport C3. Sans preuves qualifiées,
ils restent NON_VALIDE. Aucun nouveau moteur financier ou seuil de validation.
Une archive d'incident reste opérationnelle et ne constitue pas un tel dossier.

## Gel et test réservé

xp-gel-robot-v1 contient schema, commit, empreintes, instant_utc_ms et inventaire
réel de 4. La racine doit contenir le fichier du principal exécuté sous
src/xpbots ; les octets de cet inventaire, ses noms et son SHA sont recalculés
à la vérification. Un manifeste seulement déclaré ne suffit pas.

Le callback AutorisationReserve de l'exécuteur reçoit cette attestation réelle.
Sous un vrai VerrouProcessus, il conserve le premier gel autorisé dans
<racine-depot>/.local/validation/registre_reserve.json, commun aux invocations.
Les vérifications du vrai RegistreReserve restent avant toute lecture de prix,
demande et préchargement compris. L'option --ouvrir-reserve est explicite ;
elle exige --gel. Les consultations ultérieures gardent le même commit, CF et
inventaire ; les refus de changement restent tracés sans changer le premier gel.
Une écriture, un registre ou une horloge incohérents refusent l'accès. Ni une
archive ni --ecraser n'autorisent un nouveau gel du réservé.

## Validation

Catégorie 1 : aide/parsing sans SDK, gabarits, sorties protégées, erreurs et
racine étrangère, cohérence des formats. Catégorie 2 : vrais blocs et fichiers
temporaires, qualification et direct court par FauxMT5, archive/incident exacts,
rejeu/rapports C10, gel réel et verrou persistant du réservé entre commandes.
Le test de changement de code utilise une copie temporaire du runtime et
exécute le CLI de cette copie, pas un autre arbre seulement déclaré.
Le solde natif synthétique peut différer du capital CF : PAPER garde le capital
CF pour son livre et son moteur. La séance complète de 2 reste la preuve C11.14
du même chemin. Compilation MQL5, terminal et API réels restent différés.
