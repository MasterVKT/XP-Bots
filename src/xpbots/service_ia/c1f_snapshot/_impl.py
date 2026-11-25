"""Implémentation de la couche 1f (snapshot). Révisable sous harnais complet."""
from dataclasses import dataclass
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, canonique,
    decoder, empreinte, entier, instant, iso, texte)
from xpbots.contexte_ia.c0_types import SCHEMA_SNAPSHOT, charger_parametres
from xpbots.contexte_ia.c1_snapshot import decoder_snapshot


def fabriquer_snapshot(ressources,sequence,genere_ms,evenements):
    r=ressources
    if not isinstance(r,RessourcesIA):raise ErreurService('RESSOURCES_CHARGEES_REQUISES')
    entier(sequence,1);instant(genere_ms)
    if not isinstance(evenements,(list,tuple)) or any(type(e) is not dict for e in evenements):
        raise ErreurService('EVENEMENTS_JSON_REQUIS')
    payload=dict(schema=SCHEMA_SNAPSHOT,sequence=sequence,generated_at_utc=iso(genere_ms),
        integration_digest=r.digest,events=list(evenements))
    b=canonique(dict(payload=payload,sha256=empreinte(payload)))
    try:decoder_snapshot(b,genere_ms,charger_parametres(r.configuration))
    except ValueError:raise ErreurService('SNAPSHOT_NON_CONFORME') from None
    return b


@dataclass(frozen=True)
class PublicationSnapshot:
    sequence: int
    octets: bytes
    publie: bool
    erreur: str | None = None

    def __post_init__(self):
        entier(self.sequence,1)
        if type(self.octets) is not bytes or type(self.publie) is not bool:
            raise ErreurService('PUBLICATION_HORS_CONTRAT')
        if self.publie==(self.erreur is not None):raise ErreurService('STATUT_PUBLICATION_AMBIGU')
        if self.erreur is not None:texte(self.erreur)


class EcrivainSnapshot:
    def __init__(self,ressources,depot,publier):
        if not isinstance(ressources,RessourcesIA) or not callable(getattr(depot,'transaction',None)) or not callable(publier):
            raise ErreurService('PORTS_SNAPSHOT_REQUIS')
        self.r=ressources;self.depot=depot;self._publier=publier

    def publier(self,genere_ms,evenements):
        instant(genere_ms)
        def preparer(t):
            ancien=t['schedule_state'].get('snapshot_sequence')
            if ancien is None:
                if t['context_snapshots']:raise ErreurService('COMPTEUR_SNAPSHOT_PERDU')
                ancien=dict(sequence=0,generated_ms=0,integration_digest=self.r.digest)
            if type(ancien) is not dict or set(ancien)!={'sequence','generated_ms','integration_digest'}:
                raise ErreurService('COMPTEUR_SNAPSHOT_INVALIDE')
            entier(ancien['sequence']);instant(ancien['generated_ms'])
            if ancien['integration_digest']!=self.r.digest:raise ErreurService('COMPTEUR_CONFIGURATION_DIFFERENTE')
            if genere_ms<ancien['generated_ms']:raise ErreurService('GENERATION_EN_RECUL')
            sequence=ancien['sequence']+1
            if str(sequence) in t['context_snapshots']:raise ErreurService('SEQUENCE_ARCHIVE_CONFLICTUELLE')
            b=fabriquer_snapshot(self.r,sequence,genere_ms,evenements);v=decoder(b)
            t['schedule_state']['snapshot_sequence']=dict(sequence=sequence,
                generated_ms=genere_ms,integration_digest=self.r.digest)
            t['context_snapshots'][str(sequence)]=dict(sequence=sequence,
                generated_at=iso(genere_ms),payload_hash=v['sha256'],payload=v['payload'],
                publication_status='PREPARED')
            return sequence,b
        sequence,b=self.depot.transaction(preparer)
        try:
            retour=self._publier(b)
            if retour is not None:return PublicationSnapshot(sequence,b,False,'CONTRAT_PUBLICATION_INVALIDE')
        except (OSError,ValueError):return PublicationSnapshot(sequence,b,False,'PUBLICATION_ECHOUEE')
        return PublicationSnapshot(sequence,b,True)
