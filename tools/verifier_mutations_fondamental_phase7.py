"""Mutations C05 et couture de phase 7, sur copies temporaires et suite des deux robots.

Le harnais commun vérifie une copie saine, l'unicité des motifs et leur syntaxe. Une détection exige
un test fonctionnel du composant visé (ou de la couture), jamais seulement une garde de carte.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import verifier_mutations_london_phase4 as harnais


def mutation(nom,paquet,avant,apres,couche):
    return dict(nom=nom,fichier=f'src/xpbots/fondamental/{paquet}/_impl.py',avant=avant,apres=apres,couche=couche)


MUTATIONS=[
    mutation('0_or_devises_erronees','c0_types',"'XAUUSD': ('USD',)","'XAUUSD': ('EUR', 'USD')",'0'),
    mutation('1a_fin_validite_incluse','c1a_message','if instant_ms >= m.valid_until_ms:','if instant_ms > m.valid_until_ms:','1a'),
    mutation('1b_debut_fenetre_exclu','c1b_annonces','self._fenetre(a)[0] <= instant_ms < self._fenetre(a)[1]','self._fenetre(a)[0] < instant_ms < self._fenetre(a)[1]','1b'),
    mutation('1b_causalite_ignoree','c1b_annonces','if v.reception_ms <= instant_ms','if True','1b'),
    mutation('2_sequence_reecrite_acceptee','c2_etat_permissions','m.sequence <= precedente.message.sequence','m.sequence < precedente.message.sequence','2'),
    mutation('2_heartbeat_alerte_erronee','c2_etat_permissions',"EvenementSuivi('HEARTBEAT_MANQUE', s, m.sequence,","EvenementSuivi('PERMISSION_EXPIREE', s, m.sequence,",'2'),
    mutation('3_flatten_ignore','c3_permissions','if consultation.detail is None and m.risk_state is EtatRisque.FLATTEN:','if False and consultation.detail is None and m.risk_state is EtatRisque.FLATTEN:','3'),
    mutation('3_annonce_sans_permission_ignoree','c3_permissions','if annonces.cloture_obligatoire:','if annonces.cloture_obligatoire and consultation.detail is None:','3'),
    dict(nom='S4_contexte_permission_perdu',couche='S4',fichier='src/xpbots/orchestration/squelette.py',
        avant='return dict(permission=_journal(permission),dernier_evenement=',apres='return dict(permission=None,dernier_evenement='),
    dict(nom='S4_reprise_horloge_ancienne',couche='S4',fichier='src/xpbots/orchestration/squelette.py',
        avant='self._instant_fondamental=coordinateur.etat.dernier_ms',
        apres='self._instant_fondamental=controle_fondamental.etat.dernier_ms if controle_fondamental is not None else 0'),
    dict(nom='S5_sequence_journal_erronee',couche='S5',fichier='src/xpbots/rejeu/squelette.py',
        avant='sequence=r.permission.message.sequence if',apres='sequence=0 if'),
    dict(nom='S7_scenario_cli_implicite',couche='S7',fichier='src/xpbots/app/rejeu_squelette.py',
        avant="add_argument('--scenario',required=True",apres="add_argument('--scenario',required=False"),
]


def main():
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument('--selection',action='append',choices=[m['nom'] for m in MUTATIONS])
    p.add_argument('--journal-progressif')
    args,suite=p.parse_known_args()
    retenues=[m for m in MUTATIONS if not args.selection or m['nom'] in args.selection]
    harnais.MUTATIONS=retenues
    h=hashlib.sha256()
    root=harnais.ROOT.resolve()
    fichiers={f for d in ('src','tests','tools','config','schemas','prompts','reference')
        for f in (root/d).rglob('*') if f.is_file() and f.suffix in ('.py','.json')}
    fichiers.update((root/'mcl').glob('*/carte.json'))
    for f in sorted(fichiers):
        h.update(f.relative_to(root).as_posix().encode()+b'\0');h.update(hashlib.sha256(f.read_bytes()).digest())
    empreinte=h.hexdigest();anciens={};journal=None
    if args.journal_progressif:
        journal=(root/args.journal_progressif).resolve()
        if not journal.is_relative_to(root/'.local'): raise ValueError('journal hors .local/')
        if journal.exists():
            for l in journal.read_text(encoding='utf-8').splitlines():
                e=json.loads(l)
                if e['empreinte']!=empreinte: raise ValueError('sources modifiées depuis le journal')
                anciens[e['resultat']['nom']]=e['resultat']
    executer=harnais.executer
    def verifier(copie,nom):
        if nom in anciens: return dict(anciens[nom])
        r=executer(copie,nom)
        if nom!='copie_saine':
            if any(x in r['extrait'].lower() for x in ('memoryerror','unable to allocate','winerror 1450')):
                raise RuntimeError('ressources insuffisantes, résultat invalide')
            m=next(m for m in retenues if m['nom']==nom)
            domaine='squelette' if m['couche'].startswith('S') else 'london_fondamental'
            if r['code'] and not any(domaine in str(t) for t in r['en_defaut']):
                raise RuntimeError('aucun test fonctionnel du composant en défaut')
            if journal:
                journal.parent.mkdir(parents=True,exist_ok=True)
                with journal.open('a',encoding='utf-8',newline='\n') as f:
                    f.write(json.dumps(dict(empreinte=empreinte,resultat=r),ensure_ascii=True)+'\n')
        return r
    harnais.executer=verifier
    if '--rapport' not in suite: suite+=['--rapport','.local/reports/mutations_fondamental_phase7.json']
    sys.argv=[sys.argv[0]]+suite
    return harnais.main()


if __name__=='__main__': raise SystemExit(main())
