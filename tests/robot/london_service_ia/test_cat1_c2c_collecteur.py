"""Catégorie 1 : polling conditionnel, redirections et backoff du collecteur."""
import unittest
from datetime import datetime, timezone
from email.utils import format_datetime
from xpbots.service_ia.c0_types import ErreurService, ReponseHTTP
from .support_collecteur import composer, avancer


class Collecteur(unittest.TestCase):
    def test_poll_et_headers_conditionnels_304_sans_nouveau(self):
        def premier(q,http):return http.reponse(q,entetes=(('ETag','"rss-v1"'),('Last-Modified','Mon, 16 Nov 2026 08:00:00 GMT')))
        def identique(q,http):return http.reponse(q,304,corps=b'')
        r,m,h,http,c=composer(actions=[premier,identique]);a=c.collecter('FED')
        self.assertEqual(len(a.nouveaux),1)
        self.assertEqual(c.collecter('FED').statut,'DIFFERE');self.assertEqual(len(http.requetes),1)
        avancer(r,h);b=c.collecter('FED');self.assertEqual(b.statut,'NON_MODIFIE');self.assertFalse(b.nouveaux)
        self.assertEqual(dict(http.requetes[-1].entetes)['If-None-Match'],'"rss-v1"')
        self.assertIn('If-Modified-Since',dict(http.requetes[-1].entetes))
    def test_304_sans_copie_reste_partiel_et_backoff(self):
        r,m,h,http,c=composer(actions=[lambda q,http:http.reponse(q,304,corps=b'')]);t=h.t
        a=c.collecter('FED');self.assertEqual(a.couverture,'PARTIAL');self.assertEqual(a.statut,'ERREUR')
        self.assertEqual(m.tables['feed_state']['FED']['next_poll_ms'],t+r.p['rss_failure_backoff_seconds']*1000)
    def test_boe_403_aucun_contournement(self):
        r,m,h,http,c=composer(actions=[lambda q,http:http.reponse(q,403,corps=b'forbidden')]);t=h.t
        a=c.collecter('BOE');self.assertEqual(a.couverture,'PARTIAL');self.assertFalse(a.nouveaux)
        self.assertEqual(len(http.requetes),1);self.assertEqual(http.requetes[0].url,r.p['feeds'][-1]['url'])
        h.t+=r.p['rss_poll_seconds']*1000;self.assertEqual(c.collecter('BOE').statut,'DIFFERE')
    def test_retry_after_superieur_secondes_et_date(self):
        for date in (False,True):
            r,m,h,http,c=composer();delta=r.p['rss_failure_backoff_seconds']*2
            fin=h.t+delta*1000
            valeur=format_datetime(datetime.fromtimestamp(fin/1000,timezone.utc),usegmt=True) if date else str(delta)
            http.actions=[lambda q,http:http.reponse(q,429,corps=b'',entetes=(('Retry-After',valeur),))]
            c.collecter('FED');self.assertEqual(m.tables['feed_state']['FED']['next_poll_ms'],fin)
    def test_retry_after_immense_ne_boucle_pas(self):
        r,m,h,http,c=composer(actions=[lambda q,http:http.reponse(q,503,corps=b'',entetes=(('Retry-After','9'*5000),))])
        c.collecter('FED');self.assertGreater(m.tables['feed_state']['FED']['next_poll_ms'],h.t+600000)
        avancer(r,h);self.assertEqual(c.collecter('FED').statut,'DIFFERE');self.assertEqual(len(http.requetes),1)
    def test_trois_redirections_acceptees_quatrieme_refusee(self):
        for n,succes in ((3,True),(4,False)):
            r,m,h,http,c=composer()
            http.actions=[lambda q,http:http.reponse(q,302,corps=b'',entetes=(('Location','/feeds/other.xml'),))]*n
            a=c.collecter('FED');self.assertEqual(a.statut=='RECU',succes)
            self.assertEqual(len(http.requetes),4)
    def test_cible_http_autre_domaine_port_ou_identifiants_refuses_avant_hop(self):
        for cible in ('http://www.federalreserve.gov/feed','https://evil.test/feed',
                'https://www.federalreserve.gov:444/feed','https://user@www.federalreserve.gov/feed'):
            r,m,h,http,c=composer(actions=[lambda q,http:http.reponse(q,302,corps=b'',entetes=(('Location',cible),))])
            self.assertEqual(c.collecter('FED').statut,'ERREUR');self.assertEqual(len(http.requetes),1)
    def test_timeout_taille_et_xml_invalide_partiels_sans_texte(self):
        def timeout(q,http):raise TimeoutError('Ne jamais archiver cette exception')
        def tardif(q,http):http.h.attendre(q.timeout_s+1);return http.reponse(q)
        for action in (timeout,tardif,lambda q,http:http.reponse(q,corps=b'x'*(q.max_octets+1)),
                lambda q,http:http.reponse(q,corps=b'<broken')):
            r,m,h,http,c=composer(actions=[action]);a=c.collecter('FED')
            self.assertEqual(a.couverture,'PARTIAL');self.assertFalse(m.tables['source_items'])
    def test_source_inconnue_et_horloge_en_recul_refusees(self):
        r,m,h,http,c=composer()
        with self.assertRaises(ErreurService):c.collecter('BLOG')
        c.collecter('FED');h.t-=1
        with self.assertRaises(ErreurService):c.collecter('FED')
    def test_304_apres_panne_restaure_copie_sans_nouvelle_classification(self):
        r,m,h,http,c=composer();premier=c.collecter('FED');avancer(r,h)
        http.actions=[lambda q,http:http.reponse(q,503,corps=b'')]
        self.assertEqual(c.collecter('FED').couverture,'PARTIAL')
        h.t+=r.p['rss_failure_backoff_seconds']*1000
        http.actions=[lambda q,http:http.reponse(q,304,corps=b'')]
        a=c.collecter('FED');self.assertEqual(a.couverture,'COMPLETE');self.assertFalse(a.nouveaux)
        self.assertEqual(len(m.tables['source_items']),len(premier.nouveaux))
