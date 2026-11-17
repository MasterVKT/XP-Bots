"""Les preuves sont des fichiers liés au registre, jamais un statut isolé."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import gzip,json,unittest
from robot.outils.orchestration import C
from robot.outils.qualification_mt5 import T
from robot.points_entree.test_cat1_c0_configuration import registre,decision
from robot.points_entree.test_cat1_c1c_rejeu import demande_fixture
from xpbots.app.c0_configuration import analyser_registre,ErreurApplication
from xpbots.app.c1c_cli_rejeu import lancer_rejeu
from xpbots.app.c2_boucle_direct import verifier_autorisations
from xpbots.rejeu.c3_rapports import serialiser_rapport


class TestAutorisationsPhysiques(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with TemporaryDirectory() as r:
            d,lignes=demande_fixture();p=Path(r)/'ticks.csv.gz'
            p.write_bytes(gzip.compress(''.join(lignes).encode(),mtime=0))
            cls.rapport=json.loads(serialiser_rapport(lancer_rejeu(C,d,p)['rapport']))

    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.fichier=Path(self.temp.name)/'rapport.json'

    def application(self,r,*,veto=False,muter=None):
        d=registre('DEMO' if veto else 'REEL')
        dossier=dict(schema='xp-dossier-validation-v1',commit=d['commit'],empreintes=deepcopy(d['empreintes']),rapport=r)
        if muter is not None:muter(dossier)
        b=serialiser_rapport(dossier).encode();self.fichier.write_bytes(b)
        ref=dict(chemin=str(self.fichier),sha256=sha256(b).hexdigest())
        objet='ACTIVATION_VETO_A13' if veto else 'DEPLOIEMENT_REEL'
        dec=decision(d,objet,());dec['preuves']={'A13':ref} if veto else {'C10_RESERVE':ref,'C10_DEMO':ref}
        d['decisions']=[dec]
        if veto:
            d['activation_veto']=True
            d['statut_a13']=dict(statut='VALIDE',rapport=ref['chemin'],empreinte=ref['sha256'])
        return analyser_registre(d,C,T)

    def declaration_hostile(self):
        # Fabrication explicite pour atteindre les refus situés après le statut.
        # Ce document n'est ni un résultat C10 qualifié ni une preuve financière.
        r=deepcopy(self.rapport)
        r.update(statut='VALIDE',limites=[],preuves_attestees=dict(fiche_c04=True,gel_robot=True,journaux_demo=True))
        r['matrice_c10'].update(complete=True,fondamental_complet=True)
        crit=[dict(nom='FIXTURE_DECLARATIVE',statut='SATISFAIT')]
        r['criteres_apriori']=[dict(usage=u,methodes=[C.technique.london['strategy_id']],
            provenance='COURTIER_HISTORIQUE',regime_fondamental='PERMISSIONS_EXTERNES',ecart=None,
            criteres=deepcopy(crit)) for u in ('VALIDATION','RESERVE')]
        r['effectifs_globaux']=[dict(regime_fondamental='PERMISSIONS_EXTERNES',criteres=deepcopy(crit))]
        r['voisinage']['complet']=True
        return r

    def test_rapport_reel_de_la_commande_non_valide_n_autorise_pas_le_reel(self):
        self.assertEqual(self.rapport['statut'],'NON_VALIDE')
        with self.assertRaisesRegex(ErreurApplication,'VALIDATION_C10_NON_ETABLIE'):
            verifier_autorisations(self.application(self.rapport))

    def test_sha_des_octets_avant_parsing_et_contexte_commit_cf(self):
        a=self.application(self.rapport);self.fichier.write_bytes(self.fichier.read_bytes()+b' ')
        with self.assertRaisesRegex(ErreurApplication,'EMPREINTE_RAPPORT_DIFFERENTE'):verifier_autorisations(a)
        for muter in (lambda d:d.update(commit='c'*40),lambda d:d['empreintes'].update(ia='d'*64)):
            with self.subTest(mutation=muter),self.assertRaisesRegex(ErreurApplication,'RAPPORT_VALIDATION_ETRANGER'):
                verifier_autorisations(self.application(self.rapport,muter=muter))

    def test_statut_valide_contradictoire_ou_criteres_supprimes_refuse(self):
        mutations=(lambda r:r['criteres_apriori'][0]['criteres'][0].update(statut='ECHEC'),
            lambda r:r['criteres_apriori'][1].update(criteres=[]),
            lambda r:r.update(effectifs_globaux=[]),lambda r:r['voisinage'].update(complet=False))
        for muter in mutations:
            r=self.declaration_hostile();muter(r)
            with self.subTest(mutation=muter),self.assertRaisesRegex(ErreurApplication,'VALIDATION_C10_CONTRADICTOIRE'):
                verifier_autorisations(self.application(r))

    def test_a13_vide_ou_declarant_ses_preuves_absentes_refuse(self):
        r=self.declaration_hostile();r['a13']=[]
        with self.assertRaisesRegex(ErreurApplication,'VALIDATION_FINANCIERE_A13_ABSENTE'):
            verifier_autorisations(self.application(r,veto=True))
        r['a13']=[dict(rapport=dict(statut='VALIDE',preuves_reelles_attestees=False,
            qualification_semantique=dict(statut='QUALIFIE_DECLARE',criteres=[dict(nom='FIXTURE_SEMANTIQUE',statut='SATISFAIT')]),
            criteres=[dict(nom='trades_clos:IA:'+C.technique.london['strategy_id'],statut='SATISFAIT')]))]
        with self.assertRaisesRegex(ErreurApplication,'VALIDATION_FINANCIERE_A13_ABSENTE'):
            verifier_autorisations(self.application(r,veto=True))

    def test_a13_statut_contredit_par_critere_ou_semantique_sans_criteres_refuse(self):
        for mauvais in ('ECHEC','NON_EVALUABLE','SEMANTIQUE_VIDE'):
            r=self.declaration_hostile()
            v=dict(statut='VALIDE',preuves_reelles_attestees=True,
                qualification_semantique=dict(statut='QUALIFIE_DECLARE',criteres=[dict(nom='FIXTURE_SEMANTIQUE',statut='SATISFAIT')]),
                criteres=[dict(nom='trades_clos:IA:'+C.technique.london['strategy_id'],statut='SATISFAIT'),
                    dict(nom='AUTRE_CRITERE_FIXTURE',statut='SATISFAIT')],criteres_non_applicables=[])
            if mauvais=='SEMANTIQUE_VIDE':v['qualification_semantique']['criteres']=[]
            else:
                v['criteres'][1]['statut']=mauvais
                if mauvais=='ECHEC':v['criteres_non_applicables']=['AUTRE_CRITERE_FIXTURE']
            r['a13']=[dict(rapport=v)]
            with self.subTest(mauvais=mauvais),self.assertRaisesRegex(ErreurApplication,'VALIDATION_FINANCIERE_A13_ABSENTE'):
                verifier_autorisations(self.application(r,veto=True))
