"""La décision IA ajoute seulement un veto aux contrôles obligatoires."""
from xpbots.contexte_ia.c0_types import ErreurContexte, PolitiqueVeto
from xpbots.contexte_ia.c2_cache import CacheVetos
from xpbots.execution.c0b_controles import LecteurContexteIA
from xpbots.noyau.c1c_domaine import ContexteIA, DecisionContexteIA


class LecteurContexte(LecteurContexteIA):
    def __init__(self,parametres,politique,etat=None):
        if not isinstance(politique,PolitiqueVeto):raise ErreurContexte('politique IA explicite requise')
        self._cache=CacheVetos(parametres,etat);self._p=parametres;self._politique=politique

    @property
    def politique(self):return self._politique

    @property
    def etat(self):return self._cache.etat

    def recevoir(self,octets,reception_ms):return self._cache.recevoir(octets,reception_ms)

    def avancer(self,instant_ms):self._cache.avancer(instant_ms)

    def prochaine_echeance_ms(self,instant_ms):return self._cache.prochaine_echeance_ms(instant_ms)

    def evaluer(self,symbole,instant_ms):
        actifs=self._cache.consulter(symbole,instant_ms)
        p=self._politique
        bloque=p.bras_ia and not (p.execution_reelle and self._p.validation_financiere_requise
            and not p.validation_financiere)
        if bloque and actifs:return DecisionContexteIA(ContexteIA.BLOCK,actifs[0].veto.event_id)
        return DecisionContexteIA(ContexteIA.NEUTRAL)

    def description(self,symbole,instant_ms):
        decision=self.evaluer(symbole,instant_ms);p=self._politique
        recu=self._cache.dernier_snapshot
        dernier=None
        if recu is not None and recu.reception_ms<=instant_ms:
            s=recu.snapshot
            dernier=dict(sequence=s.sequence,sha256=s.empreinte_payload,genere_ms=s.genere_ms,
                reception_ms=recu.reception_ms)
        vetos=[dict(event_id=v.veto.event_id,item_id=v.veto.item_id,provider_id=v.veto.provider_id,
            valid_from_ms=v.veto.valid_from_ms,valid_until_ms=v.veto.valid_until_ms,
            connu_ms=v.connu_ms,sha256_preuve=v.preuve.snapshot.empreinte_payload)
            for v in self._cache.consulter(symbole,instant_ms)]
        return dict(politique=dict(bras_ia=p.bras_ia,execution_reelle=p.execution_reelle,
            validation_financiere=p.validation_financiere),decision=decision.etat.value,
            evenement=decision.evenement,dernier_snapshot=dernier,vetos=vetos)
