"""Catégorie 1, couche 2 : faits de couverture/horaires causaux, sans frontières physiques."""
from dataclasses import replace
import json
import unittest
from robot.outils.orchestration import C, T, composer_bras, ticks_courts
from xpbots.orchestration.c0_contrats import ReceptionExterne, EntreeMoteur, ErreurOrchestration
from xpbots.orchestration.c1_bras import construire_bras
from xpbots.orchestration.c2_moteur import MoteurDecision
from xpbots.execution.c0b_controles import ControleTechniqueNeutre


def composer():
    b,p,h,c=composer_bras()
    m=MoteurDecision(C,(b,),h,c,scenario_fondamental=ControleTechniqueNeutre.scenario)
    return m,b,p,h,c


def paquet(t,version=1,horaires=None,periodes=None):
    return json.dumps(dict(schema='xp-etat-marche-v1',version=version,horaires=horaires,
        periodes_couvertes=[[T,t]] if periodes is None and t>T else ([] if periodes is None else periodes)),
        ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def recevoir(m,p,t,octets,ticks=(),symbole='EURUSD'):
    p.avancer_au(t)
    for tick in ticks:p.sur_tick(tick)
    return m.traiter(EntreeMoteur(t,len(m.entrees)+1,'TICKS' if ticks else 'MINUTERIE',tuple(ticks),
        receptions=(ReceptionExterne('MARCHE',octets,symbole),)))


def reprendre(m,b,p,h,c):
    cp=m.exporter_checkpoint()
    b2=construire_bras(C,b.deploiement,b.nom,p.profils,p,b.fondamental,cp.instant_ms,
        observation=p.observation(),base_utc=p.base_utc(),etat=cp.bras[0])
    r=MoteurDecision(C,(b2,),h,c,scenario_fondamental=ControleTechniqueNeutre.scenario,
        checkpoint=cp,entrees=m.entrees)
    return r


class TestMarcheCausal(unittest.TestCase):
    def test_reception_repetition_et_flux_sans_mise_a_jour_conserve(self):
        m,b,p,h,c=composer()
        self.assertEqual(json.loads(m.etat.flux[0][1])['schema'],'xp-flux-bougies-v1')
        s=recevoir(m,p,T,paquet(T))
        self.assertTrue(any(e.contenu.get('alerte')=='MARCHE_ACTUALISE' for e in s.enregistrements))
        avant=json.loads(m.etat.flux[0][1])['marche']
        s=recevoir(m,p,T+1,paquet(T))
        self.assertFalse(any(e.contenu.get('alerte')=='MARCHE_ACTUALISE' for e in s.enregistrements))
        self.assertEqual(json.loads(m.etat.flux[0][1])['marche'],avant)

    def test_collision_recul_et_version_bool_refuses(self):
        for b in (paquet(T+1,1),paquet(T,0),paquet(T,True)):
            m,_,p,_,_=composer();recevoir(m,p,T,paquet(T))
            with self.assertRaises(ErreurOrchestration):recevoir(m,p,T+1,b)

    def test_documents_hostiles_couverture_future_et_intervalles_refuses(self):
        documents=[b'\xff',b'{"schema":"xp-etat-marche-v1","version":1,"version":2}',
            paquet(T,periodes=[[T,T+1]]),paquet(T,periodes=[[True,T]]),
            paquet(T+10,periodes=[[T+5,T+9],[T,T+5]]),
            paquet(T+10,periodes=[[T,T+8],[T+5,T+9]]),
            paquet(T,horaires={}),
            b'{"schema":"xp-etat-marche-v1","version":1,"horaires":null,"periodes_couvertes":NaN}']
        for b in documents:
            m,_,p,_,_=composer()
            with self.subTest(b=b),self.assertRaises(ErreurOrchestration):recevoir(m,p,T,b)

    def test_horaires_explicitement_futurs_et_symbole_etranger_refuses(self):
        d=dict(seances=[[T,T+100]],fermetures=[],debut_validite_ms=T+1,fin_validite_ms=T+100)
        m,_,p,_,_=composer()
        with self.assertRaises(ErreurOrchestration):recevoir(m,p,T,paquet(T,horaires=d))
        m,_,p,_,_=composer()
        with self.assertRaises(ErreurOrchestration):recevoir(m,p,T,paquet(T),symbole='ETRANGER')

    def test_reprise_checkpoint_conserve_marche_et_prochain_evenement(self):
        m,b,p,h,c=composer();recevoir(m,p,T,paquet(T))
        r=reprendre(m,b,p,h,c)
        self.assertEqual(r.exporter_checkpoint(),m.exporter_checkpoint())
        a=recevoir(m,p,T+1,paquet(T+1,2))
        z=recevoir(r,p,T+1,paquet(T+1,2))
        # La reprise C08 ajoute son propre rapprochement natif ; le fait de marché
        # et le prochain état C03 restent identiques, sans supprimer cette preuve.
        self.assertEqual(r.exporter_checkpoint().flux,m.exporter_checkpoint().flux)
        def marches(sortie):
            return tuple((e.contenu['symbole'],e.contenu['version']) for e in sortie.enregistrements
                         if e.contenu.get('alerte')=='MARCHE_ACTUALISE')
        self.assertEqual(marches(a),marches(z))

    def test_trou_de_couverture_connu_classe_la_bougie_reelle_en_trou(self):
        m,b,p,h,c=composer();ticks=ticks_courts();pas=C.technique.commun.timeframe_seconds*1000
        recevoir(m,p,T,paquet(T),ticks=(ticks[0],))
        recevoir(m,p,T+pas,paquet(T+pas,2),ticks=(ticks[1],))
        s=recevoir(m,p,T+2*pas,paquet(T+2*pas,3,periodes=[[T,T+pas]]),ticks=(ticks[2],))
        self.assertTrue(any(e.contenu.get('alerte')=='DATA_GAP' for e in s.enregistrements))
        self.assertTrue(any(e.type.value=='CLOTURE' and not e.contenu['bougie']['valide'] for e in s.enregistrements))

    def test_nouveaux_horaires_utilises_par_le_vrai_flux(self):
        m,b,p,h,c=composer();ticks=ticks_courts();pas=C.technique.commun.timeframe_seconds*1000
        recevoir(m,p,T,paquet(T),ticks=(ticks[0],))
        ferme=dict(seances=[],fermetures=[],debut_validite_ms=T,fin_validite_ms=T+4*pas)
        s=recevoir(m,p,T+pas,paquet(T+pas,2,horaires=ferme),ticks=(ticks[1],))
        clotures=[e for e in s.enregistrements if e.type.value=='CLOTURE']
        self.assertTrue(clotures)
        self.assertTrue(all(not e.contenu['bougie']['valide'] for e in clotures))

    def test_reprise_d_un_horaire_expire_ne_renouvelle_pas_sa_connaissance(self):
        m,b,p,h,c=composer()
        horaire=dict(seances=[[T,T+10]],fermetures=[],debut_validite_ms=T,fin_validite_ms=T+10)
        recevoir(m,p,T,paquet(T,horaires=horaire))
        p.avancer_au(T+20);m.traiter_evenement(T+20)
        r=reprendre(m,b,p,h,c)
        self.assertEqual(r.exporter_checkpoint().flux,m.exporter_checkpoint().flux)
        self.assertEqual(json.loads(r.etat.flux[0][1])['marche']['reception_ms'],T)
