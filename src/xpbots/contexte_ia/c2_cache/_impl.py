"""Un heartbeat n'est ni une révocation ni une nouvelle durée de vie."""
from dataclasses import dataclass
from xpbots.contexte_ia.c0_types import (ErreurContexte, ParametresContexte, SnapshotRecu,
    VetoConnu, instant, texte)
from xpbots.contexte_ia.c1_snapshot import ErreurSnapshot, decoder_snapshot


@dataclass(frozen=True)
class EtatCache:
    dernier_snapshot: SnapshotRecu | None = None
    scelles: tuple[VetoConnu,...] = ()
    dernier_ms: int = 0

    def __post_init__(self):
        instant(self.dernier_ms)
        if self.dernier_snapshot is not None and not isinstance(self.dernier_snapshot,SnapshotRecu):
            raise ErreurContexte('dernière réception typée requise')
        if not isinstance(self.scelles,(tuple,list)) or any(not isinstance(v,VetoConnu) for v in self.scelles):
            raise ErreurContexte('identités typées requises')
        object.__setattr__(self,'scelles',tuple(self.scelles))


@dataclass(frozen=True)
class ReceptionSnapshot:
    acceptee: bool
    ignoree: bool
    raison: str | None = None
    snapshot: SnapshotRecu | None = None
    ajoutes: tuple[str,...] = ()

    def __post_init__(self):
        if type(self.acceptee) is not bool or type(self.ignoree) is not bool or self.acceptee and self.ignoree:
            raise ErreurContexte('résultat de réception incohérent')
        if self.acceptee or self.ignoree:
            if not isinstance(self.snapshot,SnapshotRecu) or self.raison is not None:
                raise ErreurContexte('réception validée requise')
        elif self.snapshot is not None or self.ajoutes or type(self.raison) is not str or not self.raison:
            raise ErreurContexte('motif de rejet requis')
        if not isinstance(self.ajoutes,(tuple,list)):raise ErreurContexte('IDs ajoutés requis')
        for v in self.ajoutes:texte(v)
        if self.ignoree and self.ajoutes:raise ErreurContexte('relecture sans ajout requise')
        object.__setattr__(self,'ajoutes',tuple(self.ajoutes))


class CacheVetos:
    def __init__(self,parametres,etat=None):
        if not isinstance(parametres,ParametresContexte):raise ErreurContexte('paramètres réels requis')
        e=EtatCache() if etat is None else etat
        if not isinstance(e,EtatCache):raise ErreurContexte('état de cache réel requis')
        self._p=parametres;self._dernier=e.dernier_snapshot;self._scelles={};self._dernier_ms=e.dernier_ms
        preuves={}
        def verifier(recu):
            cle=(recu.snapshot.empreinte_payload,recu.reception_ms,recu.snapshot.octets)
            if cle not in preuves:
                frais=decoder_snapshot(recu.snapshot.octets,recu.reception_ms,parametres)
                if frais!=recu:raise ErreurContexte('métadonnées différentes des octets acceptés')
                preuves[cle]=frais
        if self._dernier is not None:
            verifier(self._dernier)
            if self._dernier.reception_ms>e.dernier_ms:raise ErreurContexte('réception future dans la reprise')
        elif e.scelles:
            raise ErreurContexte('identités sans dernière séquence')
        for v in e.scelles:
            verifier(v.preuve)
            if (v.veto.event_id in self._scelles or v.connu_ms!=v.preuve.reception_ms
                    or v.veto not in v.preuve.snapshot.vetos
                    or v.preuve.snapshot.sequence>self.derniere_sequence
                    or v.connu_ms>self._dernier.reception_ms
                    or (v.preuve.snapshot.sequence==self.derniere_sequence
                        and v.preuve.snapshot.empreinte_payload!=self._dernier.snapshot.empreinte_payload)):
                raise ErreurContexte('identité ou causalité de reprise incohérente')
            self._scelles[v.veto.event_id]=v
        sequences={}
        for recu in preuves.values():
            s=recu.snapshot
            identite=(s.empreinte_payload,recu.reception_ms)
            if s.sequence in sequences and sequences[s.sequence]!=identite:
                raise ErreurContexte('preuves contradictoires pour une même séquence')
            sequences[s.sequence]=identite
            for v in s.vetos:
                scelle=self._scelles.get(v.event_id)
                if (scelle is None or scelle.veto!=v or scelle.connu_ms>recu.reception_ms
                        or scelle.preuve.snapshot.sequence>s.sequence):
                    raise ErreurContexte('veto accepté absent ou réécrit dans une preuve')
        receptions=[sequences[s][1] for s in sorted(sequences)]
        if receptions!=sorted(receptions):raise ErreurContexte('séquence et réception de reprise contradictoires')
        self._actifs=dict(self._scelles);self._purger(e.dernier_ms)

    @property
    def derniere_sequence(self):return self._dernier.snapshot.sequence if self._dernier is not None else 0

    @property
    def dernier_snapshot(self):return self._dernier

    @property
    def etat(self):return EtatCache(self._dernier,tuple(self._scelles.values()),self._dernier_ms)

    def _temps(self,t):
        instant(t)
        if t<self._dernier_ms:raise ErreurContexte('recul du temps logique du cache')

    def _purger(self,t):
        self._actifs={i:v for i,v in self._actifs.items() if v.veto.valid_until_ms>t}

    def avancer(self,instant_ms):
        self._temps(instant_ms);self._dernier_ms=instant_ms;self._purger(instant_ms)

    def recevoir(self,octets,reception_ms):
        self.avancer(reception_ms)
        try:recu=decoder_snapshot(octets,reception_ms,self._p,self.derniere_sequence)
        except ErreurSnapshot as e:return ReceptionSnapshot(False,False,e.raison)
        if self._dernier is not None and recu.snapshot.sequence==self.derniere_sequence:
            if recu.snapshot.empreinte_payload!=self._dernier.snapshot.empreinte_payload:
                return ReceptionSnapshot(False,False,'SEQUENCE_REECRITE')
            return ReceptionSnapshot(False,True,snapshot=self._dernier)
        for v in recu.snapshot.vetos:
            connu=self._scelles.get(v.event_id)
            if connu is not None and connu.veto!=v:
                return ReceptionSnapshot(False,False,'EVENEMENT_REECRIT')
        nouveaux={};ajoutes=[]
        for v in recu.snapshot.vetos:
            if v.event_id not in self._scelles and v.event_id not in nouveaux:
                nouveaux[v.event_id]=VetoConnu(v,reception_ms,recu);ajoutes.append(v.event_id)
        self._scelles.update(nouveaux)
        self._actifs.update(nouveaux);self._purger(reception_ms)
        self._dernier=recu
        return ReceptionSnapshot(True,False,snapshot=recu,ajoutes=tuple(ajoutes))

    def _connus(self,t):
        return self._actifs.values() if t>=self._dernier_ms else self._scelles.values()

    def consulter(self,symbole,instant_ms):
        instant(instant_ms)
        if type(symbole) is not str or symbole not in self._p.symboles:raise ErreurContexte('symbole hors univers')
        return tuple(sorted((v for v in self._connus(instant_ms)
            if v.connu_ms<=instant_ms and symbole in v.veto.symboles
            and v.veto.valid_from_ms<=instant_ms<v.veto.valid_until_ms),key=lambda v:v.veto.event_id))

    def prochaine_echeance_ms(self,instant_ms):
        instant(instant_ms)
        return min((v.veto.valid_until_ms for v in self._connus(instant_ms)
            if v.connu_ms<=instant_ms<v.veto.valid_until_ms),default=None)
