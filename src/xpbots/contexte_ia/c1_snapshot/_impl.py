"""Le résultat validé est atomique : aucun veto n'est extrait avant validation de toute la liste."""
from xpbots.contexte_ia.c0_types import (ErreurContexte, ParametresContexte, SCHEMA_SNAPSHOT,
    SnapshotIA, SnapshotRecu, Veto, decoder_objet, empreinte, entier, instant, sha256_hex, utc)

_ENVELOPPE=frozenset({'payload','sha256'})
_PAYLOAD=frozenset({'schema','sequence','generated_at_utc','integration_digest','events'})
_EVENEMENT=frozenset({'event_id','reason_code','canonical_symbols','valid_from_utc',
    'valid_until_utc','item_id','provider_id'})


class ErreurSnapshot(ErreurContexte):
    def __init__(self,raison):
        if raison not in ('ABSENT','TAILLE','JSON','SCHEMA','EMPREINTE','CONFIGURATION',
            'SEQUENCE','FUTUR','PERIME','EVENEMENT'):raise ErreurContexte('raison de rejet inconnue')
        self.raison=raison
        super().__init__('snapshot refusé : '+raison)


def decoder_snapshot(octets,reception_ms,parametres,derniere_sequence=0):
    instant(reception_ms);entier(derniere_sequence)
    if not isinstance(parametres,ParametresContexte):raise ErreurContexte('paramètres réels requis')
    p=parametres
    if octets is None:raise ErreurSnapshot('ABSENT')
    if type(octets) is not bytes:raise ErreurSnapshot('JSON')
    if len(octets)>p.max_octets:raise ErreurSnapshot('TAILLE')
    try:r=decoder_objet(octets)
    except ErreurContexte as e:raise ErreurSnapshot('JSON') from e
    if set(r)!=_ENVELOPPE or type(r['payload']) is not dict or set(r['payload'])!=_PAYLOAD:
        raise ErreurSnapshot('SCHEMA')
    b=r['payload']
    try:sha256_hex(r['sha256'])
    except ErreurContexte as e:raise ErreurSnapshot('EMPREINTE') from e
    if empreinte(b)!=r['sha256']:raise ErreurSnapshot('EMPREINTE')
    if b['schema']!=SCHEMA_SNAPSHOT:raise ErreurSnapshot('SCHEMA')
    if b['integration_digest']!=p.empreinte_integration:raise ErreurSnapshot('CONFIGURATION')
    try:sequence=entier(b['sequence'],1)
    except ErreurContexte as e:raise ErreurSnapshot('SEQUENCE') from e
    if sequence<derniere_sequence:raise ErreurSnapshot('SEQUENCE')
    try:genere=utc(b['generated_at_utc'])
    except ErreurContexte as e:raise ErreurSnapshot('SCHEMA') from e
    if genere>reception_ms:raise ErreurSnapshot('FUTUR')
    if reception_ms-genere>p.age_max_ms:raise ErreurSnapshot('PERIME')
    if type(b['events']) is not list:raise ErreurSnapshot('EVENEMENT')
    vetos=[];identites={}
    try:
        for e in b['events']:
            if type(e) is not dict or set(e)!=_EVENEMENT:raise ErreurContexte('champs événement invalides')
            if type(e['canonical_symbols']) is not list:raise ErreurContexte('liste de symboles requise')
            v=Veto(e['event_id'],e['canonical_symbols'],utc(e['valid_from_utc']),utc(e['valid_until_utc']),
                e['item_id'],e['provider_id'],e['reason_code'])
            if (v.valid_from_ms>genere or v.provider_id not in p.fournisseurs
                    or any(s not in p.symboles for s in v.symboles)):
                raise ErreurContexte('heure, fournisseur ou symbole invalide')
            if v.event_id in identites and identites[v.event_id]!=v:
                raise ErreurContexte('identité contradictoire dans le snapshot')
            identites[v.event_id]=v;vetos.append(v)
    except ErreurContexte as e:raise ErreurSnapshot('EVENEMENT') from e
    return SnapshotRecu(SnapshotIA(sequence,genere,p.empreinte_integration,tuple(vetos),r['sha256'],octets),reception_ms)
