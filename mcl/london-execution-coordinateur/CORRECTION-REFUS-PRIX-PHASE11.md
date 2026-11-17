# P11-05 — refus natifs et nouvelle tentative contrôlée jusqu’au TTL

Défaut confirmé le 10/11/2026, avant les sources natives : C06 distingue les refus
permanents ; C08 consomme le signal en cas de refus définitif. Le document 08 §2.6
classe REQUOTE, PRICE_CHANGED, PRICE_OFF et TOO_MANY_REQUESTS non permanents.
CycleOrdre._accuse ignore pourtant definitif et termine tout REFUSE en
ENVIRONMENT_NOT_READY/REFUS_COURTIER. Le contrat de couche 4 dit abusivement que
tout refus confirmé consomme le signal. À corriger à la source, sans changer C06.
Les permanents volume/marge/protection/limites doivent aussi garder leurs motifs
du tableau documentaire, au lieu du seul refus générique.

Décision de conception avant code, à exécuter après le gel du codec MARCHE :

1. Extension additive de RegistreReservations (1c) :
   annuler_tentative(cle,version_attendue) -> EtatReservations|RefusExecution.
   Seulement réserve non remplie, clé non terminale, aucun verrou de sous-jacent,
   version courante exacte ; retirer cette réserve sans marquer la clé terminée.
   C’est une opération de ressource pure ; C6 doit prouver le refus natif explicite.
   Aucune libération sur timeout, None, statut inconnu, fill ou simple absence.
2. Correction/extension 4 : propriété refus_reessayable bool, vraie seulement
   après REFUSE définitif=False pour les quatre codes de prix documentés, sans
   aucun fill. Le cycle reste terminal REFUSEE pour CETTE tentative, sans Issue
   finale dans ce seul cas ; C6 conserve l’intention en attente. False avec code
   inconnu ou drapeau contradictoire -> INCONNU, pas droit de renvoi.
   Les refus permanents connus produisent le motif C09 exact ; les anciens codes
   synthétiques définitifs conservent le refus générique à défaut de correspondance.
3. EtatCycle ajoute numero_entree:int=0 en fin de champs, défaut conservateur.
   preparer_envoi mémorise le numéro de la vraie commande ENTREE avant MINUTERIE.
   Le compteur global numero_commande n’est jamais réinitialisé entre tentatives.
   _accuse accepte l’entrée courante ou une commande d’entrée déjà attestée dans
   reponses_recues ; pas un numéro qui appartenait à TP/minuterie. Un ACK ancien
   explicite REFUSE répété ne termine pas la nouvelle tentative ; un ancien
   ACK contradictoire verrouille en INCONNU. Les fills tardifs réels font toujours foi.
   Pour la compatibilité des états legacy sans numero_entree, le seul premier
   envoi historique est l’entrée 1 ; ne pas inventer d’autre référence.
4. Correction 6 : _actualiser_dossier garde EN_ATTENTE_COTATION si le cycle est
   refus_reessayable ; _accumuler libère sa réserve non remplie via 1c, sans Issue
   finale et sans quota. Le cycle terminal refusé reste dans l’état (C5b sait déjà
   restaurer un terminal sans réserve), pas un cycle non terminal orphelin.
   Une NOUVELLE cotation du symbole avant TTL suit tous les contrôles existants,
   dimensionnement frais/stop/risque/marge, réservation atomique, transaction et
   preuve de persistance. Nouveau CycleOrdre avec plan courant, compteurs de
   commande et réponses reçues conservés, envoi_ms=None/RESERVEE. Ainsi nouvelle
   référence d’entrée unique, jamais retransmission aveugle de la première.
   À TTL exact : SIGNAL_EXPIRED ; au redémarrage : règle existante d’abandon des
   intentions en attente, pas entrée rétroactive. 5a/5b inchangés si ces contrats
   réels suffisent (rejouer leur gate intégral).
5. Nouveau gate/gel de 1c, puis 4, puis 6 ; régression et jonction codec pour les
   états enrichis ; checkpoint global. Les types sont ceux du registre codec
   existant, aucun import aval ni SDK dans le cœur. Mettre la traçabilité dans le
   bilan et l’inventaire P11-05. Les corrections de développement ne comptent pas
   comme les deux passes correctives de l’audit final, encore non commencé.

Cas : chacun des quatre refus de prix, nouvelle cotation vs minuterie sans prix,
TTL-1/TTL exact, revalidation C05/spread/risque/volume/marge, preuve de stockage,
nouvelle référence/counter monotone, aucun quota sans fill ; refus permanents de
volume/marge/stops/droits/limites et codes inconnus ; None/timeout/CONNECTION
restent inconnus sans resend ; refus après fill et ACK/fill tardifs ; reprise
entre refus et nouveau prix ; codec/journal C11.14 sur vrais bras London.

Cette conception reste à confronter au code exact avant application. Ne pas
modifier une règle métier ou un export pour faciliter une nouvelle tentative.

Précisions issues de la lecture réelle :

- _commande incrémente aussi le compteur pour MINUTERIE : après ENTREE 1 puis
  MINUTERIE 2, la prochaine entrée est 3 (pas forcément 2). numero_entree courant
  suffit ; les commandes d’entrée anciennes sont attestées par les ACK déjà reçus.
- C5b._construire exige une réserve pour tout cycle NON terminal. Conserver donc
  le cycle refusé terminal REFUSEE sans réserve entre les tentatives ; DossierIntention
  reste EN_ATTENTE_COTATION. Le constructeur C6 doit autoriser précisément cette
  discordance prouvée par refus de prix, sans assouplir les autres concordances.
- Remplacer le couple de propriétés spéculatives par une seule propriété publique
  refus_reessayable_ms -> int|None, dérivée du dernier ACK non permanent de l’entrée
  courante et sans fill. C6 l’utilise aussi pour exiger une cotation reçue APRÈS
  ce refus. Ne pas comparer à EtatCycle.dernier_ms (qui avance aux minuteries).
- Lors d’une reprise, C6 abandonne cette attente comme ses autres attentes.
  _actualiser_dossier ne doit pas la ressusciter après Issue finale ; vérifier
  aussi le chemin _appliquer_observation -> _charger -> _actualiser_dossier.
- C6.traiter ajoute déjà les symboles des cotations reçues dans nouveaux ; aucune
  nouvelle tentative sur une minuterie seule. Vérifier néanmoins le timestamp de
  nouvelle réception > refus_reessayable_ms, pour ne pas recycler l’ancienne quote.
- C4 doit laisser un refus explicite non permanent sans Issue finale ; C6 libère
  la réserve via le nouveau 1c, conserve l’ancien cycle terminal et l’historique
  des réponses, puis recrée un CycleOrdre RESERVEE à plan nouveau et compteur
  monotone. Ne jamais appeler sur_issue avec une fausse Issue finale pour libérer.
- Les tests doivent aussi couvrir la concordance EtatCoordinateur au restart,
  l’expiration sans réserve encore active, et la non-résurrection d’une attente
  après le rapprochement initial.
