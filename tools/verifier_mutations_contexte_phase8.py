"""Mutations A10/A12 et couture de phase 8, sur copies temporaires et suite des deux robots.

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
    return dict(nom=nom,fichier=f'src/xpbots/contexte_ia/{paquet}/_impl.py',avant=avant,apres=apres,couche=couche)


MUTATIONS=[
    mutation('0_json_non_canonique','c0_types','sort_keys=True', 'sort_keys=False','0'),
    mutation('1_age_exact_refuse','c1_snapshot','reception_ms-genere>p.age_max_ms',
        'reception_ms-genere>=p.age_max_ms','1'),
    mutation('1_futur_accepte','c1_snapshot','if genere>reception_ms:',
        'if False and genere>reception_ms:','1'),
    mutation('2_connaissance_future_lue','c2_cache','if v.connu_ms<=instant_ms and symbole',
        'if True and symbole','2'),
    mutation('2_identite_reecrite_acceptee','c2_cache','if connu is not None and connu.veto!=v:',
        'if False and connu is not None and connu.veto!=v:','2'),
    mutation('3_garde_financiere_ignoree','c3_contexte','and not p.validation_financiere)',
        'and False)','3'),
    mutation('3_bras_reference_bloque','c3_contexte','bloque=p.bras_ia and not',
        'bloque=True and not','3'),
    dict(nom='S4_preuve_ia_absente',couche='S4',fichier='src/xpbots/orchestration/squelette.py',
        avant='return None if self._ia is None else self._ia.description(symbole,instant)',
        apres='return None'),
    dict(nom='S5_snapshot_recu_ignore',couche='S5',fichier='src/xpbots/rejeu/squelette.py',
        avant='r=self.lecteur.recevoir(p.octets,t)',apres='r=self.lecteur.recevoir(None,t)'),
    dict(nom='S7_lecteur_non_branche',couche='S7',fichier='src/xpbots/app/rejeu_squelette.py',
        avant='scenario=scenario,lecteur_ia=lecteur_ia)',apres='scenario=scenario,lecteur_ia=None)'),
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
            domaine='squelette' if m['couche'].startswith('S') else 'london_contexte_ia'
            if r['code'] and not any(domaine in str(t) for t in r['en_defaut']):
                raise RuntimeError('aucun test fonctionnel du composant en défaut')
            if journal:
                journal.parent.mkdir(parents=True,exist_ok=True)
                with journal.open('a',encoding='utf-8',newline='\n') as f:
                    f.write(json.dumps(dict(empreinte=empreinte,resultat=r),ensure_ascii=True)+'\n')
        return r
    harnais.executer=verifier
    if '--rapport' not in suite: suite+=['--rapport','.local/reports/mutations_contexte_phase8.json']
    sys.argv=[sys.argv[0]]+suite
    return harnais.main()


if __name__=='__main__': raise SystemExit(main())
