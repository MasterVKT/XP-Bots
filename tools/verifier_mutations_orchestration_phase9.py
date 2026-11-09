"""Mutations des contrats, des bras, du moteur et des coutures de phase 9, sur copies temporaires et suite des deux robots.

Le harnais commun vérifie une copie saine, l'unicité des motifs et leur syntaxe. Une détection exige
un test fonctionnel du composant visé (ou de la couture), jamais seulement une garde de carte.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import verifier_mutations_london_phase4 as harnais


def mutation(nom,fichier,avant,apres,couche):
    return dict(nom=nom,fichier=fichier,avant=avant,apres=apres,couche=couche)


MUTATIONS=[
    mutation('0_nature_ticks_incoherente_admise','src/xpbots/orchestration/c0_contrats/_impl.py',
        "if bool(ticks)!=(self.nature=='TICKS'):","if False:",'0'),
    mutation('1_ia_branchee_en_reference','src/xpbots/orchestration/c1_bras/_impl.py',
        'contexte=lecteur_ia if nom==IA else None','contexte=lecteur_ia','1'),
    mutation('1_rejeu_consulte_backend','src/xpbots/orchestration/c1_bras/_impl.py',
        'resultat=self._attendus[self._position].resultat;self._position+=1',
        'resultat=appeler_calcul(self._port,nom,*args,**kwargs);self._position+=1','1'),
    mutation('2_repetition_retraitee','src/xpbots/orchestration/c2_moteur/_impl.py',
        'if self._entrees and e==self._entrees[-1].entree:',
        'if False and self._entrees and e==self._entrees[-1].entree:','2'),
    mutation('S4_reponses_minuterie_perdues','src/xpbots/orchestration/squelette.py',
        'self.moteur.traiter_evenement(instant_ms,mises_a_jour={self.bras:MiseAJourBras(reponses,observation,base_utc)})',
        'self.moteur.traiter_evenement(instant_ms,mises_a_jour={self.bras:MiseAJourBras((),observation,base_utc)})','S4'),
    mutation('S5_octets_snapshot_perdus','src/xpbots/rejeu/squelette.py',
        "ReceptionExterne('SNAPSHOT',p.octets)","ReceptionExterne('SNAPSHOT',None)",'S5'),
    mutation('S7_port_ia_non_branche','src/xpbots/app/rejeu_squelette.py',
        "base_utc=p.base_utc(),lecteur_ia=ia if nom=='IA' else None))",
        'base_utc=p.base_utc(),lecteur_ia=None))','S7'),
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
            domaine='squelette' if m['couche'].startswith('S') else 'orchestration'
            if r['code'] and not any(domaine in str(t) for t in r['en_defaut']):
                raise RuntimeError('aucun test fonctionnel du composant en défaut')
            if journal:
                journal.parent.mkdir(parents=True,exist_ok=True)
                with journal.open('a',encoding='utf-8',newline='\n') as f:
                    f.write(json.dumps(dict(empreinte=empreinte,resultat=r),ensure_ascii=True)+'\n')
        return r
    harnais.executer=verifier
    if '--rapport' not in suite: suite+=['--rapport','.local/reports/mutations_orchestration_phase9.json']
    sys.argv=[sys.argv[0]]+suite
    return harnais.main()


if __name__=='__main__': raise SystemExit(main())
