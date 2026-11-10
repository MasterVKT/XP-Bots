"""Garde avant lecture, expériences et perturbations explicites."""
from dataclasses import fields,replace
from datetime import date
from decimal import Decimal as D
import unittest
from robot.outils.rejeu import C,experience_courte,fabriques_horloge
from xpbots.rejeu.c0a_types import ErreurRejeu,EcartRejeu
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.rejeu.c2_executeur import (AutorisationReserve,RegistreReserve,ControlesRejeu,
    appliquer_ecart,executer_experience,executer_perturbations,executer_blocs)


def lancer(d,source,conditions,s,**options):
    return executer_experience(C,d,source,conditions,fabriques=fabriques_horloge((s,)),
        fabrique_controles=lambda _:ControlesRejeu.technique_neutre(C),**options)


class TestExecuteur(unittest.TestCase):
    def test_sans_quote_apres_envoi_cycle_inconnu_pas_experience_complete(self):
        import hashlib
        from xpbots.rejeu.c2_executeur import SourceTicks
        d,source,conditions,s,_=experience_courte()
        lignes=tuple(l for i,l in enumerate(source.lire()) if not i or int(l.split(',')[2])<=s)
        m=replace(source.manifeste,sha256=hashlib.sha256(''.join(lignes).encode()).hexdigest())
        r=lancer(d,SourceTicks(m,lambda:iter(lignes)),conditions,s)
        self.assertTrue(r.couverture_complete);self.assertFalse(r.bras['REFERENCE'].positions_ouvertes)
        self.assertTrue(any(str(v.etat.statut)=='INCONNUE' for v in r.bras['REFERENCE'].etat.coordinateur.reprise.cycles))
        self.assertFalse(r.complet)
    def test_conditions_datees_archivees_pour_comparabilite_des_couts(self):
        d,source,conditions,s,_=experience_courte();r=lancer(d,source,conditions,s)
        self.assertEqual(r.conditions,conditions)
        self.assertEqual(r.conditions[0].tarif.identifiant,'ZERO_DECLARE')
        with self.assertRaises(TypeError):r.initiales['REFERENCE'][0]['EURUSD']=None

    def test_reference_execution_courte_et_mesures_distinctes(self):
        d,source,conditions,s,compteur=experience_courte();r=lancer(d,source,conditions,s)
        self.assertEqual(compteur,['LECTURE']);self.assertEqual(set(r.bras),{'REFERENCE'})
        b=r.bras['REFERENCE'];n=b.comptages[('LONDON_V3','EURUSD')]
        self.assertEqual((n.configurations,n.signaux,n.entrees,len(b.trades)),(1,1,1,1))
        self.assertEqual(b.trades[0].entree_ms,s+250);self.assertTrue(r.complet)
        self.assertEqual(b.courbe[0].fonds_propres,D(100));self.assertEqual(len(r.jours),1)

    def test_reserve_refuse_avant_lecture_meme_si_renommee_validation(self):
        d,source,conditions,s,compteur=experience_courte(jour=date(2025,1,2));reg=RegistreReserve()
        with self.assertRaisesRegex(ErreurRejeu,'réservé'):lancer(d,source,conditions,s,registre_reserve=reg)
        self.assertEqual(compteur,[]);self.assertEqual(reg.historique[-1]['action'],'REFUS_RESERVE')

    def test_hash_syntaxique_ne_suffit_pas_et_option_explicite(self):
        for option,atteste in ((False,True),(True,False),(True,1)):
            d,source,conditions,s,compteur=experience_courte(jour=date(2025,1,2))
            d=replace(d,autorisation=AutorisationReserve(option,'a'*64,lambda _:atteste))
            with self.subTest(option=option,atteste=atteste),self.assertRaises(ErreurRejeu):lancer(d,source,conditions,s)
            self.assertEqual(compteur,[])

    def test_ouverture_unique_empreinte_stable_consultations_tracees(self):
        d,source,conditions,s,compteur=experience_courte(jour=date(2025,1,2));reg=RegistreReserve();appels=[]
        def attester(h):appels.append(h);self.assertEqual(compteur,[]);return True
        d=replace(d,autorisation=AutorisationReserve(True,'a'*64,attester))
        r=lancer(d,source,conditions,s,registre_reserve=reg)
        self.assertEqual(len(appels),2);self.assertEqual(reg.historique[0]['action'],'OUVERTURE_RESERVE')
        self.assertEqual(reg.historique[1]['action'],'CONSULTATION_RESERVE')
        self.assertEqual(r.journal_protocole[0]['action'],'PROTOCOLE_FIXE_AVANT_LECTURE')
        d=replace(d,autorisation=AutorisationReserve(True,'b'*64,lambda _:True))
        with self.assertRaises(ErreurRejeu):lancer(d,source,conditions,s,registre_reserve=reg)
        self.assertEqual(len(compteur),1)

    def test_diagnostic_2026_non_renommable_et_debut_v3(self):
        d,source,conditions,s,_=experience_courte(jour=date(2026,7,15))
        d=replace(d,bloc=replace(d.bloc,nom='TEST_INDEPENDANT',usage='TEST'))
        r=lancer(d,source,conditions,s);self.assertEqual(r.usage,'DIAGNOSTIC')
        d,source,conditions,s,compteur=experience_courte(jour=date(2026,5,4))
        with self.assertRaisesRegex(ErreurRejeu,'diagnostic'):lancer(d,source,conditions,s)
        self.assertEqual(compteur,[])

    def test_prospectif_apres_la_periode_exploree_ne_devient_pas_diagnostic(self):
        for jour in (date(2026,11,5),date(2027,3,8)):
            with self.subTest(jour=jour):
                d,source,conditions,s,_=experience_courte(jour=jour)
                r=lancer(d,source,conditions,s);self.assertEqual(r.usage,'PROSPECTIF')
        d,source,conditions,s,_=experience_courte(jour=date(2025,1,2))
        d=replace(d,autorisation=AutorisationReserve(True,'a'*64,lambda _:True))
        self.assertEqual(lancer(d,source,conditions,s).usage,'RESERVE')

    def test_jours_et_entrees_or_ne_deviennent_pas_frequence_forex(self):
        d,source,conditions,s,_=experience_courte()
        lignes=tuple(v.replace('EURUSD','XAUUSD') for v in source.lire())
        m=replace(source.manifeste,symboles={'XAUUSD':'XAUUSD'},
            horaires={'XAUUSD':source.manifeste.horaires['EURUSD']})
        import hashlib
        m=replace(m,sha256=hashlib.sha256(''.join(lignes).encode()).hexdigest())
        c=conditions[0]
        c=replace(c,profil=replace(c.profil,symbole='XAUUSD',symbole_courtier='XAUUSD',sous_jacent='XAUUSD',devise_base='XAU'))
        from xpbots.rejeu.c2_executeur import SourceTicks
        r=lancer(d,SourceTicks(m,lambda:iter(lignes)),(c,),s)
        self.assertEqual(len(r.jours),1);self.assertEqual(r.jours_forex,())
        self.assertEqual(r.bras['REFERENCE'].comptages[('LONDON_V3','XAUUSD')].entrees,1)

    def test_ecarts_exactement_prescrits_et_source_intacte(self):
        p=charger_protocole(C)
        for nom,champ,v in p.perturbations:
            variante=appliquer_ecart(C,EcartRejeu(nom,champ,v),'REJEU')
            self.assertNotEqual(variante.technique.empreinte_canonique,C.technique.empreinte_canonique)
            self.assertIs(variante.ia,C.ia)
            avant=C.technique.commun;apres=variante.technique.commun
            differences={f.name for f in fields(avant) if getattr(avant,f.name)!=getattr(apres,f.name)}
            if champ=='OBJECTIF':
                self.assertEqual(differences,set());self.assertEqual(D(str(variante.technique.london['take_profit_gross_price_r'])),D(2)*v)
            else:self.assertEqual(differences,{'structural_buffer_atr' if champ=='BUFFER' else 'max_position_wallclock_seconds'})
        self.assertEqual(C.technique.commun.max_position_wallclock_seconds,7200)
        with self.assertRaises(ErreurRejeu):appliquer_ecart(C,EcartRejeu('invente','OBJECTIF',D('.8')),'REJEU')
        with self.assertRaises(ErreurRejeu):appliquer_ecart(C,EcartRejeu(*p.perturbations[0]),'DEMO')

    def test_six_perturbations_executees_sans_selection(self):
        d,source,conditions,s,compteur=experience_courte()
        r=executer_perturbations(C,d,source,conditions,fabriques=fabriques_horloge((s,)),
            fabrique_controles=lambda _:ControlesRejeu.technique_neutre(C))
        self.assertEqual([v.demande.ecart.nom for v in r],[e[0] for e in charger_protocole(C).perturbations])
        self.assertEqual(len(compteur),6);self.assertTrue(all(v.bras['REFERENCE'].courbe[0].fonds_propres==100 for v in r))
        self.assertEqual(len({v.configuration.technique.empreinte_canonique for v in r}),6)

    def test_blocs_independants_ne_reutilisent_pas_les_comptes(self):
        d,source,conditions,s,_=experience_courte()
        r=executer_blocs(C,(d,replace(d,identifiant='deux')), {d.bloc.nom:source},conditions,
            fabriques=fabriques_horloge((s,)),fabrique_controles=lambda _:ControlesRejeu.technique_neutre(C))
        self.assertEqual([x.bras['REFERENCE'].courbe[0].fonds_propres for x in r],[D(100),D(100)])
        self.assertEqual(r[0].bras['REFERENCE'].trades[0].net,r[1].bras['REFERENCE'].trades[0].net)

    def test_absence_controles_et_mauvais_scenario_refuses_avant_lecture(self):
        d,source,conditions,s,compteur=experience_courte()
        with self.assertRaises(ErreurRejeu):executer_experience(C,d,source,conditions)
        self.assertEqual(compteur,[])
        with self.assertRaises(ValueError):lancer(replace(d,scenario='S5'),source,conditions,s)
        self.assertEqual(compteur,[])

    def test_grille_historique_variable_refusee_explicitement(self):
        d,source,conditions,s,compteur=experience_courte();c=conditions[0]
        a=replace(c,fin_ms=s);b=replace(c,debut_ms=s,connu_ms=s,profil=replace(c.profil,tick_size=D('.0001'),releve_ms=s))
        with self.assertRaisesRegex(ErreurRejeu,'grille'):lancer(d,source,(a,b),s)
        self.assertEqual(compteur,[])

    def test_ab_deux_comptes_et_meme_spread_stresse(self):
        d,source,conditions,s,_=experience_courte(mode=C.ia.parametres['default_evaluation_mode'],scenario='STRESS')
        r=lancer(d,source,conditions,s)
        self.assertEqual(set(r.bras),{'REFERENCE','IA'})
        # Pas de tick après délai STRESS avant s+900000 : même marché pour les deux livres.
        self.assertEqual([v.courbe[0].fonds_propres for v in r.bras.values()],[D(100),D(100)])
        a=r.bras['REFERENCE'].trades;b=r.bras['IA'].trades
        self.assertTrue(a);self.assertEqual(len(a),len(b))
        faits=lambda t:tuple(getattr(t,f.name) for f in fields(t) if f.name!='cle')
        self.assertEqual(tuple(map(faits,a)),tuple(map(faits,b)))
        self.assertNotEqual(a[0].cle.deploiement,b[0].cle.deploiement)
        self.assertEqual(a[0].prix_entree,D('1.102145'))
