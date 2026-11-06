# Contrat de la couche 2 — moteur_london (enveloppe)

- **Statut** : finalisé le 06/11/2026, après gel des sept couches internes et checkpoint de niveau 1. Corrigé le 06/11/2026 par défigeage `correction` : fins LF pour la conservation des empreintes après normalisation Git.
- **Consommateurs cartographiés** : couture S3, composition S7, puis orchestration injectée (D-18).
- **Dépend de** : 0a, 0b, 1a, 1b, 1c, 1d et 1e, réelles et figées ; noyau et données ; aucune frontière externe.

Unité : moteur_london
Responsabilité : Appliquer S02 par symbole et appliquer les issues sans dépendre du coordinateur.
Signature : `MoteurLondon(parametres: ParametresLondon, symbole: str, tick_size: Decimal)` ;
`sur_bougie(enrichie: BougieEnrichie) -> ResultatTechnique | None` ; `sur_issue(issue: Issue) -> None` ;
propriétés `identifiant`, `etat_quotas`, `position_ouverte`, `range`, `gel` ;
`StrategieLondon(parametres: ParametresLondon, tailles_tick: Mapping[str, Decimal])` avec `identifiant`,
`sur_bougie` et `sur_issue` ; `fabriquer_strategie(configuration: ConfigurationFigee, tailles_tick) -> StrategieLondon`.
Entrée : bougies enrichies réelles d'un symbole canonique configuré ; taille de tick décimale explicite ;
issues de cette méthode et de ce symbole. La fabrique copie et valide toutes les tailles avant toute bougie.
Sortie : un résultat du noyau pour chaque nouvelle M15 ; aucune sortie pour une H1, une issue ou une M15
ancienne ou répétée. Les objets de diagnostic sont immuables. La stratégie crée paresseusement un moteur par symbole.
Effets de bord : seulement l'état interne, sans fichier ni horloge, sans import d'orchestration ou d'exécution.
Erreurs, exceptions : `ErreurLondon` pour mauvais types, durée incorrecte, symbole absent ou inconnu, issue
étrangère ou taille non décimale finie positive. Les métadonnées du jour et des heures doivent correspondre
au calendrier réel du début et de la fin de la bougie ; incohérence refusée avant modification de l'état.

Le moteur garde un jour Londres courant ; un événement d'un nouveau jour remet à zéro le range, le gel et les
quotas. La propriété d'une position n'est jamais effacée par minuit : seule une issue CLOTUREE de sa clé la lève.
Les issues REMPLIE sont idempotentes ; une répétition tardive après clôture ne rouvre pas la position. Une
clôture d'une autre intention ne clôt pas la position possédée. Toute issue ne rend rien : aucune inversion
instantanée ni ordre au moment du stop. La persistance physique appartient à l'infrastructure ultérieure ;
les quotas exposent déjà leur état restaurable et le moteur est reconstructible par rejeu de ses entrées.

Les seules ouvertures attendues du range sont conservées, y compris leurs invalidités. La première version
valide de chaque ouverture est traitée une fois ; une M15 ancienne n'est jamais réévaluée. Un trou M15
(TROU_DONNEES ou HORAIRES_INCONNUS) efface le range calculé et bloque l'entrée. À récupération (bougie couverte,
valide ou AUCUN_BID), il est recalculé si les vingt bougies mémorisées restent valides ; une fermeture officielle
ne simule pas une récupération. Une invalidité du range reste bloquante ce jour. Les invalidités H1 ne
pilotent pas l'état de trou du symbole, conformément au contrat du flux amont.

Une fois la borne F atteinte, la candidate H1 est calculée par 1b. Sa première version valide est conservée,
même si sa disponibilité est tardive. Aucune H1 suivante ou correction ne remplace le gel. Le contexte d'un
résultat antérieur à cette disponibilité n'expose pas sa valeur d'ATR. Une correction H1 déjà valide est
ignorée ; une première H1 valide peut remplacer une version invalide tant qu'aucun gel valide n'existe.

L'ordre de refus est : trou actif ; jour inactif ou hors fenêtre ; rang M15 et A ; range valide et disponible ;
gel disponible et connu à la clôture ; largeur admissible ; position London possédée ; cassure ; quota du sens ;
stop ; sinon signal. Les motifs et détails viennent du document 01, §9.3. Une M15 invalide hors trou donne
NO_SETUP/PAS_DE_CASSURE si elle atteint le contrôle de préchargement. Une disponibilité du range postérieure
à la clôture donne DATA_GAP/ATTENTE_RECALCUL. Les bornes de largeur sont incluses ; la fenêtre se calcule par
CalendrierLondres, sans décalage UTC constant. Les rangs minimaux incluent la bougie courante (P-10).

Le signal expose dans son contexte le jour, les quotas, la propriété, les extrêmes et la largeur du range,
son instant de disponibilité, l'ATR H1 figé et ses instants, W/A_H1, le TR, A, les fractions de corps et de
clôture, le buffer, la taille de tick et les trois composantes contraignantes du stop. Les refus conservent
les seules mesures déjà connues à leur clôture. Aucun filtre fondamental ou IA n'est ajouté ici : le refus
ultérieur ne consomme rien et seule une nouvelle clôture peut être étudiée.

## Spécification exécutable

`tests/robot/moteur_london/test_cat1_c2_moteur_london.py` et
`tests/robot/moteur_london/test_cat2_c2_moteur_london.py` : S02.6-1 à 8 au niveau technique, L-01 à L-13,
C11.1, C11.2 et C11.4 ; oracles london_setups, causalité par préfixe et vraies bougies issues des ticks.

## Comportements documentés (loi de Hyrum)

Les propriétés de diagnostic n'autorisent aucune modification d'état. Une instance appartient à un seul bras ;
chaque bras injectera sa propre stratégie. Les clés du contexte sont celles décrites ici, en français avec
soulignés ; les messages d'erreur ne sont pas garantis. Les refus ne déclenchent ni quota ni rattrapage.
