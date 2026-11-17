"""Qualification C04 native et faits D12, sans fichiers ni import du SDK."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, Context, localcontext
from hashlib import sha256
import json
from xpbots.infra.c0a_types import ErreurInfra, TableHeureServeur, champ_natif, entier_natif, nombre_decimal
from xpbots.infra.c1_session import SessionMT5
from xpbots.noyau.c0a_temps import verifier_instant, instant_depuis_iso
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1b_instrument import (Intervalle, HorairesCotation,
    construire_profil_compte, construire_profil_instrument)
from xpbots.execution.c0a_types import RefusExecution
from xpbots.noyau.c1c_domaine import Motif

_EPOQUE = datetime.fromtimestamp(0,timezone.utc)
_JOUR_MS = timedelta(days=1)//timedelta(milliseconds=1)
_QUALIFICATION = frozenset(('schema','known_at_utc_ms','valid_until_utc_ms','decision_id','preuves',
    'catalogue_complet','compte','symboles','debut_horaires_ms','fin_horaires_ms','convention_ticks'))
_COMPTE = frozenset(('entite','serveur','type_compte','devise','levier','mode_marge','mode_stop_out',
    'empreinte_compte_sha256','assiette_stop_out','historique_complet','exclusivites_netting'))
_SYMBOLE = frozenset(('canonique','sous_jacent','commission_par_lot_par_cote','commission_minimum_par_ordre',
    'commission_nulle_confirmee','devise_frais','convention_swap','protections_a_l_entree',
    'convention_declenchement_verifiee','modes_remplissage','flags_natifs','minuit_egal_fin_24h',
    'cout_aller_retour_usd_volume_min','longueur_commentaire_max','historique_ticks_complet'))
_FLAGS = frozenset(('filling_mode','order_mode','trade_exemode','chart_mode'))
_COUTS = ('commission_par_lot_par_cote','commission_minimum_par_ordre','cout_aller_retour_usd_volume_min')
_COMMISSIONS = ('commission_par_lot_par_cote','commission_minimum_par_ordre')
_REMPLISSAGES = frozenset(('FOK','IOC','RETURN'))


def _objet(v,cles):
    if type(v) is not dict or set(v)!=set(cles):raise ErreurInfra('champs exacts de qualification requis')
    return v


def _texte(v):
    if type(v) is not str or not v.strip():raise ErreurInfra('preuve textuelle requise')
    return v


def _naturel(v,minimum=0):
    if type(v) is not int or v<minimum:raise ErreurInfra('entier explicite requis')
    return v


def _booleen(v):
    if type(v) is not bool:raise ErreurInfra('preuve booleenne explicite requise')
    return v


def _cout(v):
    if type(v) is not str:raise ErreurInfra('cout decimal documente requis')
    try:d=Decimal(v)
    except InvalidOperation:raise ErreurInfra('cout decimal invalide') from None
    if not d.is_finite() or d<0:raise ErreurInfra('cout decimal fini positif ou nul requis')
    return d


def _paires(paires):
    resultat={}
    for k,v in paires:
        if k in resultat:raise ErreurInfra('cle JSON dupliquee')
        resultat[k]=v
    return resultat


def _non_fini(v):raise ErreurInfra('nombre JSON non fini')


def _json(octets):
    if type(octets) is not bytes:raise ErreurInfra('export absent')
    try:return json.loads(octets.decode('utf-8'),object_pairs_hook=_paires,parse_constant=_non_fini)
    except (UnicodeError,json.JSONDecodeError):raise ErreurInfra('export JSON UTF8 invalide') from None


def _natif_texte(objet,nom):return _texte(champ_natif(objet,nom))
def _natif_entier(objet,nom):return entier_natif(champ_natif(objet,nom))
def _natif_nombre(objet,nom):return nombre_decimal(champ_natif(objet,nom))


def _date_native(texte):
    _texte(texte)
    try:d=datetime.strptime(texte,'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc)
    except ValueError:raise ErreurInfra('date native invalide') from None
    if d.strftime('%Y.%m.%d %H:%M:%S')!=texte:raise ErreurInfra('date native non canonique')
    return (d-_EPOQUE)//timedelta(milliseconds=1)


def _nom_enum(sdk,prefixe,valeur):
    valeur=entier_natif(valeur)
    noms=[n[len(prefixe):] for n in dir(sdk) if n.startswith(prefixe) and getattr(sdk,n)==valeur]
    if len(noms)!=1:raise ErreurInfra('enumeration native inconnue')
    return noms[0]


def _heure(texte,*,fin=False):
    _texte(texte)
    if fin and texte=='24:00:00':return timedelta(days=1)//timedelta(milliseconds=1)
    try:d=datetime.strptime(texte,'%H:%M:%S')
    except ValueError:raise ErreurInfra('heure de seance invalide') from None
    if d.strftime('%H:%M:%S')!=texte:raise ErreurInfra('heure de seance non canonique')
    return timedelta(hours=d.hour,minutes=d.minute,seconds=d.second)//timedelta(milliseconds=1)


def _intervalles_jour(liste,plein):
    if type(liste) is not list:raise ErreurInfra('liste de seances requise')
    resultat=[]
    for item in liste:
        _objet(item,('debut','fin'))
        a,b=_heure(item['debut']),_heure(item['fin'],fin=True)
        if a==b:
            if not plein or a!=0:raise ErreurInfra('seance nulle non qualifiee')
            b+=_JOUR_MS
        elif b<a:b+=_JOUR_MS
        if resultat and a<resultat[-1][1]:raise ErreurInfra('seances non ordonnees ou chevauchantes')
        resultat.append((a,b))
    return tuple(resultat)


def _ordonner(intervalles):
    resultat=tuple(sorted(intervalles))
    if any(b.debut_ms<a.fin_ms for a,b in zip(resultat,resultat[1:])):
        raise ErreurInfra('seances UTC chevauchantes')
    return resultat


def _reunir(intervalles):
    resultat=[]
    for i in _ordonner(intervalles):
        if resultat and resultat[-1].fin_ms==i.debut_ms:
            resultat[-1]=Intervalle(resultat[-1].debut_ms,i.fin_ms)
        else:resultat.append(i)
    return tuple(resultat)


class SpecificationsMT5:
    def __init__(self,session,commun,table,qualification,liaisons,*,seances_max_age_ms,
                 fermetures_max_age_ms,max_jours_horaires,ecart_horloges_max_ms,etat=None):
        if not isinstance(session,SessionMT5) or not isinstance(commun,ParametresCommuns) or not isinstance(table,TableHeureServeur):
            raise ErreurInfra('session et contrats reels requis')
        self._session,self._commun,self._table=session,commun,table
        self._ages={'SEANCES':_naturel(seances_max_age_ms,1),'FERMETURES':_naturel(fermetures_max_age_ms,1)}
        self._ecart=_naturel(ecart_horloges_max_ms)
        self._max_jours=_naturel(max_jours_horaires,1)
        try:
            brut=json.dumps(qualification,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
            self._q=_json(brut)
        except (ValueError,TypeError):raise ErreurInfra('qualification JSON explicite requise') from None
        self._valider_qualification()
        if type(liaisons) is not dict or not liaisons or any(s not in commun.universe_priority or type(b) is not str for s,b in liaisons.items()):
            raise ErreurInfra('liaisons explicites requises')
        self._liaisons=dict(liaisons)
        if len(set(liaisons.values()))!=len(liaisons):raise ErreurInfra('liaison courtier en double')
        for s,b in liaisons.items():
            if b not in self._q['symboles'] or self._q['symboles'][b]['canonique']!=s:
                raise ErreurInfra('liaison absente de la qualification')
        if len({self._q['symboles'][b]['sous_jacent'] for b in liaisons.values()})!=len(liaisons):
            raise ErreurInfra('un seul symbole par sous-jacent requis')
        configuration=dict(qualification=self._q,liaisons=self._liaisons,table=dict(serveur=table.serveur,
            version=table.version,date_releve=table.date_releve,mesures=table.mesures,
            segments=[(s.debut_utc_ms,s.fin_utc_ms,s.decalage_secondes) for s in table.segments]),
            ages=self._ages,ecart=self._ecart,max_jours=self._max_jours)
        self._empreinte=sha256(json.dumps(configuration,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        self._exports={};self._invalides=set();self._dernier_ms=0
        if etat is not None:self._restaurer(etat)

    def _valider_qualification(self):
        q=_objet(self._q,_QUALIFICATION)
        if q['schema']!='xp-qualification-mt5-v1' or q['catalogue_complet'] is not True:
            raise ErreurInfra('catalogue qualifie complet requis')
        if type(q['convention_ticks']) is not str or q['convention_ticks'] not in ('UTC','SERVEUR_S01'):
            raise ErreurInfra('convention de ticks qualifiee S01 requise')
        for nom in ('known_at_utc_ms','valid_until_utc_ms','debut_horaires_ms','fin_horaires_ms'):verifier_instant(q[nom])
        if q['valid_until_utc_ms']<=q['known_at_utc_ms'] or q['fin_horaires_ms']<=q['debut_horaires_ms']:
            raise ErreurInfra('validite de qualification invalide')
        if q['fin_horaires_ms']-q['debut_horaires_ms']>self._max_jours*_JOUR_MS:
            raise ErreurInfra('couverture horaire au dela du plafond explicite')
        _texte(q['decision_id'])
        if type(q['preuves']) is not list or not q['preuves']:raise ErreurInfra('preuves de qualification absentes')
        for p in q['preuves']:_texte(p)
        c=_objet(q['compte'],_COMPTE)
        for nom in ('entite','serveur','type_compte','devise','mode_marge','mode_stop_out'):_texte(c[nom])
        _naturel(c['levier'],1);_booleen(c['historique_complet'])
        empreinte=_texte(c['empreinte_compte_sha256'])
        if len(empreinte)!=len(sha256().hexdigest()) or any(v not in '0123456789abcdef' for v in empreinte):
            raise ErreurInfra('empreinte du compte qualifie requise')
        if (c['type_compte']!='STANDARD' or c['devise']!=self._commun.account_currency or c['levier']!=self._commun.account_leverage
                or c['serveur']!=self._table.serveur or c['mode_marge'] not in ('NETTING','HEDGING')
                or c['mode_stop_out'] not in ('PERCENT','MONEY')
                or c['mode_stop_out']=='MONEY' and c['assiette_stop_out'] not in ('EQUITY','FREE_MARGIN')
                or c['mode_stop_out']=='PERCENT' and c['assiette_stop_out'] is not None):
            raise ErreurInfra('compte externe non qualifie')
        if (type(c['exclusivites_netting']) is not list or len(set(c['exclusivites_netting']))!=len(c['exclusivites_netting'])
                or any(s not in self._commun.universe_priority for s in c['exclusivites_netting'])):
            raise ErreurInfra('exclusivites netting invalides')
        if type(q['symboles']) is not dict or not q['symboles']:raise ErreurInfra('catalogue de symboles absent')
        for nom,p in q['symboles'].items():
            _texte(nom);_objet(p,_SYMBOLE)
            if p['canonique'] not in self._commun.universe_priority:raise ErreurInfra('canonique inconnu')
            _texte(p['sous_jacent']);_texte(p['convention_swap'])
            for k in _COUTS:_cout(p[k])
            for k in ('commission_nulle_confirmee','protections_a_l_entree','convention_declenchement_verifiee',
                      'minuit_egal_fin_24h','historique_ticks_complet'):_booleen(p[k])
            if not p['protections_a_l_entree'] or not p['convention_declenchement_verifiee'] or p['devise_frais']!=self._commun.account_currency:
                raise ErreurInfra('protections et frais non qualifies')
            if not p['commission_nulle_confirmee'] and not any(_cout(p[k]) for k in _COMMISSIONS):
                raise ErreurInfra('commission nulle non confirmee')
            _naturel(p['longueur_commentaire_max'],1)
            if (type(p['modes_remplissage']) is not list or not p['modes_remplissage']
                    or len(set(p['modes_remplissage']))!=len(p['modes_remplissage'])
                    or any(m not in _REMPLISSAGES for m in p['modes_remplissage'])):
                raise ErreurInfra('modes de remplissage non qualifies')
            for v in _objet(p['flags_natifs'],_FLAGS).values():_naturel(v)

    def _connue(self,t):
        verifier_instant(t)
        if not self._q['known_at_utc_ms']<=t<self._q['valid_until_utc_ms'] or instant_depuis_iso(self._table.date_releve)>t:
            raise ErreurInfra('qualification future ou perimee')

    def preuve_compte(self,t):
        self._connue(t)
        return dict(self._q['compte'])

    def convention_ticks(self,t):
        self._connue(t)
        return self._q['convention_ticks']

    def preuve(self,symbole,t):
        self._connue(t)
        if symbole not in self._liaisons:raise ErreurInfra('symbole non lie')
        return json.loads(json.dumps(self._q['symboles'][self._liaisons[symbole]]))

    def convertir_serveur(self,texte):return self._table.utc_de_serveur(_date_native(texte))

    def compte(self,t):
        try:
            self._connue(t);q=self._q['compte'];c=self._session.appeler('account_info');sdk=self._session.sdk
            serveur=_natif_texte(c,'server');numero=_natif_entier(c,'login')
            if numero<=0 or sha256((serveur+'\0'+str(numero)).encode('utf-8')).hexdigest()!=q['empreinte_compte_sha256']:
                raise ErreurInfra('compte natif different de la qualification')
            mode=_natif_entier(c,'margin_mode')
            modes={sdk.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING:'HEDGING',sdk.ACCOUNT_MARGIN_MODE_RETAIL_NETTING:'NETTING',sdk.ACCOUNT_MARGIN_MODE_EXCHANGE:'NETTING'}
            if mode not in modes:raise ErreurInfra('mode marge inconnu')
            so=_nom_enum(sdk,'ACCOUNT_STOPOUT_MODE_',champ_natif(c,'margin_so_mode'))
            donnees=dict(entite=_natif_texte(c,'company'),serveur=_natif_texte(c,'server'),plateforme='MT5',
                type_compte=q['type_compte'],devise=_natif_texte(c,'currency'),levier=_natif_entier(c,'leverage'),
                mode_marge=modes[mode],mode_stop_out=so,niveau_appel_marge=_natif_nombre(c,'margin_so_call'),
                niveau_stop_out=_natif_nombre(c,'margin_so_so'),releve_ms=t)
            if any(donnees[k]!=q[k] for k in ('entite','serveur','type_compte','devise','levier','mode_marge','mode_stop_out')):
                raise ErreurInfra('compte natif different de la preuve')
            resultat=construire_profil_compte(donnees,self._commun)
            if resultat.profil is None:raise ErreurInfra('compte natif incomplet')
            return resultat.profil
        except (ValueError,TypeError,KeyError,AttributeError):return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'qualification_compte_native')

    def _selectionner(self,symbole):
        choisi=self._liaisons[symbole];sous_jacent=self._q['symboles'][choisi]['sous_jacent'];candidats=[]
        for nom,p in self._q['symboles'].items():
            if p['sous_jacent']!=sous_jacent:continue
            if p['canonique']!=symbole:raise ErreurInfra('catalogue sous-jacent ambigu')
            n=self._session.appeler('symbol_info',nom)
            minimum=_natif_nombre(n,'volume_min');contrat=_natif_nombre(n,'trade_contract_size')
            if minimum<=0 or contrat<=0:raise ErreurInfra('exposition minimale native inconnue')
            with localcontext(Context(prec=48)):
                candidats.append((minimum*contrat,_cout(p['cout_aller_retour_usd_volume_min']),nom))
        if not candidats or min(candidats)[-1]!=choisi:raise ErreurInfra('liaison fixe non minimale')

    def instrument(self,symbole,t):
        try:
            self._connue(t)
            if isinstance(self.compte(t),RefusExecution):raise ErreurInfra('compte non qualifie')
            self._selectionner(symbole);nom=self._liaisons[symbole];p=self._q['symboles'][nom]
            n=self._session.appeler('symbol_info',nom);sdk=self._session.sdk
            if _natif_texte(n,'name')!=nom:raise ErreurInfra('symbole natif different')
            if _natif_texte(n,'currency_base')+_natif_texte(n,'currency_profit')!=symbole:
                raise ErreurInfra('sous-jacent natif incompatible avec le canonique')
            if type(champ_natif(n,'spread_float')) is not bool:raise ErreurInfra('type de spread natif inconnu')
            if any(_natif_entier(n,k)!=v for k,v in p['flags_natifs'].items()):raise ErreurInfra('flags natifs modifies')
            if _natif_entier(n,'chart_mode')!=sdk.SYMBOL_CHART_MODE_BID or _natif_entier(n,'order_mode')<=0:
                raise ErreurInfra('Bid et protections natives requis')
            execution=_nom_enum(sdk,'SYMBOL_TRADE_EXECUTION_',champ_natif(n,'trade_exemode'))
            if execution=='MARKET' and 'RETURN' in p['modes_remplissage']:raise ErreurInfra('RETURN interdit en MARKET')
            mode=_natif_entier(n,'trade_mode')
            modes={sdk.SYMBOL_TRADE_MODE_FULL:'FULL',sdk.SYMBOL_TRADE_MODE_LONGONLY:'BUY_ONLY',
                sdk.SYMBOL_TRADE_MODE_SHORTONLY:'SELL_ONLY',sdk.SYMBOL_TRADE_MODE_CLOSEONLY:'CLOSE_ONLY',sdk.SYMBOL_TRADE_MODE_DISABLED:'DISABLED'}
            if mode not in modes:raise ErreurInfra('droits natifs inconnus')
            donnees=dict(symbole=symbole,symbole_courtier=nom,sous_jacent=p['sous_jacent'],
                devise_base=_natif_texte(n,'currency_base'),devise_cotation=_natif_texte(n,'currency_profit'),
                devise_marge=_natif_texte(n,'currency_margin'),mode_calcul=_nom_enum(sdk,'SYMBOL_CALC_MODE_',champ_natif(n,'trade_calc_mode')),
                mode_execution=execution,mode_negociation=modes[mode],modes_remplissage=p['modes_remplissage'],
                protections_a_l_entree=p['protections_a_l_entree'],convention_declenchement_verifiee=p['convention_declenchement_verifiee'],
                commission_nulle_confirmee=p['commission_nulle_confirmee'],devise_frais=p['devise_frais'],
                horaires=self._horaires(nom,t),releve_ms=t)
            decimaux={'taille_contrat':'trade_contract_size','tick_size':'trade_tick_size','point':'point','valeur_tick':'trade_tick_value',
                'volume_min':'volume_min','volume_max':'volume_max','volume_pas':'volume_step','volume_limite':'volume_limit',
                'swap_achat':'swap_long','swap_vente':'swap_short','marge_initiale':'margin_initial','marge_maintenance':'margin_maintenance'}
            donnees.update({k:_natif_nombre(n,v) for k,v in decimaux.items()})
            donnees.update({k:_natif_entier(n,v) for k,v in {'digits':'digits','distance_stops_min_points':'trade_stops_level','niveau_gel_points':'trade_freeze_level'}.items()})
            donnees.update({k:_cout(p[k]) for k in _COMMISSIONS})
            resultat=construire_profil_instrument(donnees,self._commun)
            if resultat.profil is None:raise ErreurInfra('profil natif incomplet')
            return resultat.profil
        except (ValueError,TypeError,KeyError,AttributeError):return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'qualification_instrument_native')

    def _valider_export(self,nom,octets,t):
        d=_json(octets)
        if nom=='FERMETURES':
            _objet(d,('schema','version','date_releve','fermetures'))
            if d['schema']!='xp-fermetures-v1':raise ErreurInfra('schema fermeture invalide')
            date=instant_depuis_iso(d['date_releve'])
            if type(d['fermetures']) is not list:raise ErreurInfra('liste fermeture requise')
            par_symbole={}
            for f in d['fermetures']:
                _objet(f,('symbole','debut_utc','fin_utc','nature','source'))
                _texte(f['symbole']);_texte(f['source'])
                if f['nature'] not in ('FERMETURE','SEANCE_REDUITE'):raise ErreurInfra('nature fermeture invalide')
                i=Intervalle(instant_depuis_iso(f['debut_utc']),instant_depuis_iso(f['fin_utc']))
                par_symbole.setdefault(f['symbole'],[]).append(i)
            for vs in par_symbole.values():
                if tuple(vs)!=_ordonner(vs):raise ErreurInfra('fermetures non ordonnees')
        else:
            _objet(d,('schema','version','export_serveur','export_gmt','symbole','jours'))
            if d['schema']!='xp-export-seances-v1' or d['symbole']!=nom:raise ErreurInfra('schema ou symbole seance invalide')
            date=self.convertir_serveur(d['export_serveur']);gmt=_date_native(d['export_gmt'])
            if abs(gmt-date)>self._ecart or gmt>t:raise ErreurInfra('heures export non concordantes')
            if type(d['jours']) is not list or len(d['jours'])!=7:raise ErreurInfra('sept jours explicites requis')
            plein=self._q['symboles'][nom]['minuit_egal_fin_24h']
            for numero,jour in enumerate(d['jours']):
                _objet(jour,('jour','cotation','negociation'))
                if type(jour['jour']) is not int or jour['jour']!=numero:raise ErreurInfra('jours non ordonnes')
                _intervalles_jour(jour['cotation'],plein);_intervalles_jour(jour['negociation'],plein)
        _naturel(d['version'],1)
        if date>t:raise ErreurInfra('export futur')
        return d,date

    def recevoir_exports(self,t,*,seances,fermetures):
        verifier_instant(t)
        if t<self._dernier_ms:raise ErreurInfra('reception non causale')
        if type(seances) is not dict or set(seances)!=set(self._liaisons.values()):raise ErreurInfra('un export par symbole lie requis')
        nouveaux=[]
        for nom,octets in tuple(seances.items())+(('FERMETURES',fermetures),):
            try:
                d,date=self._valider_export(nom,octets,t);ancien=self._exports.get(nom)
                if ancien is not None:
                    version=ancien['version']
                    if d['version']<version or d['version']==version and octets!=ancien['octets']:
                        raise ErreurInfra('version export reculee ou contradictoire')
                    if d['version']==version:
                        self._invalides.discard(nom);continue
                    if date<ancien['date_ms']:raise ErreurInfra('date export reculee')
                r=dict(nom=nom,version=d['version'],octets=octets,reception_ms=t,date_ms=date)
                self._exports[nom]=r;self._invalides.discard(nom);nouveaux.append(dict(r))
            except (ValueError,TypeError,KeyError):self._invalides.add(nom)
        self._dernier_ms=t
        return tuple(nouveaux)

    @property
    def erreurs_exports(self):return tuple(sorted(self._invalides))

    def _export_courant(self,nom,t):
        if nom in self._invalides or nom not in self._exports:raise ErreurInfra('export absent ou invalide')
        r=self._exports[nom];age=self._ages['FERMETURES' if nom=='FERMETURES' else 'SEANCES']
        if not 0<=t-min(r['reception_ms'],r['date_ms'])<=age:raise ErreurInfra('export perime')
        return _json(r['octets'])

    def _horaires(self,nom,t):
        d=self._export_courant(nom,t);f=self._export_courant('FERMETURES',t)
        debut,fin=self._q['debut_horaires_ms'],self._q['fin_horaires_ms']
        if not debut<=t<fin:raise ErreurInfra('horaire hors validite')
        bornes=[(max(debut,s.debut_utc_ms)+timedelta(seconds=s.decalage_secondes)//timedelta(milliseconds=1),
                 min(fin,s.fin_utc_ms)+timedelta(seconds=s.decalage_secondes)//timedelta(milliseconds=1))
            for s in self._table.segments if max(debut,s.debut_utc_ms)<min(fin,s.fin_utc_ms)]
        if not bornes:raise ErreurInfra('horaire hors table')
        premier,dernier=min(a for a,b in bornes),max(b for a,b in bornes)
        a=premier//_JOUR_MS*_JOUR_MS-_JOUR_MS
        b=(dernier-1)//_JOUR_MS*_JOUR_MS
        plein=self._q['symboles'][nom]['minuit_egal_fin_24h'];cotations=[];negociations=[]
        for jour_ms in range(a,b+_JOUR_MS,_JOUR_MS):
            jour=(_EPOQUE+timedelta(milliseconds=jour_ms)).isoweekday()%7
            for cle,resultat in (('cotation',cotations),('negociation',negociations)):
                for x,y in _intervalles_jour(d['jours'][jour][cle],plein):
                    if jour_ms+x>=dernier or jour_ms+y<=premier:continue
                    x,y=self._table.utc_de_serveur(jour_ms+x),self._table.utc_de_serveur(jour_ms+y)
                    if x<fin and y>debut:resultat.append(Intervalle(max(debut,x),min(fin,y)))
        cotations,negociations=_ordonner(cotations),_ordonner(negociations)
        intersections=tuple(Intervalle(max(a.debut_ms,b.debut_ms),min(a.fin_ms,b.fin_ms))
            for a in cotations for b in negociations if max(a.debut_ms,b.debut_ms)<min(a.fin_ms,b.fin_ms))
        fermetures=tuple(Intervalle(instant_depuis_iso(v['debut_utc']),instant_depuis_iso(v['fin_utc']))
            for v in f['fermetures'] if v['symbole']==nom)
        return HorairesCotation(_reunir(intersections),fermetures,debut,fin)

    def exporter_etat(self):
        return dict(schema='xp-specifications-mt5-v1',configuration_sha256=self._empreinte,
            dernier_ms=self._dernier_ms,exports={k:dict(v) for k,v in self._exports.items()},invalides=self.erreurs_exports)

    def _restaurer(self,etat):
        _objet(etat,('schema','configuration_sha256','dernier_ms','exports','invalides'))
        if etat['schema']!='xp-specifications-mt5-v1' or etat['configuration_sha256']!=self._empreinte:
            raise ErreurInfra('etat specifications incompatible')
        verifier_instant(etat['dernier_ms'])
        noms=set(self._liaisons.values())|{'FERMETURES'}
        if type(etat['exports']) is not dict or not set(etat['exports'])<=noms or not isinstance(etat['invalides'],(list,tuple)) or not set(etat['invalides'])<=noms:
            raise ErreurInfra('inventaire exports restaure invalide')
        for nom,r in etat['exports'].items():
            _objet(r,('nom','version','octets','reception_ms','date_ms'))
            verifier_instant(r['reception_ms'])
            d,date=self._valider_export(nom,r['octets'],r['reception_ms'])
            if r['nom']!=nom or type(r['version']) is not int or r['version']!=d['version'] or type(r['date_ms']) is not int or date!=r['date_ms'] or r['reception_ms']>etat['dernier_ms']:
                raise ErreurInfra('reception restauree contradictoire')
            self._exports[nom]=dict(r)
        self._invalides=set(etat['invalides']);self._dernier_ms=etat['dernier_ms']
