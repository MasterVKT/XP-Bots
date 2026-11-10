"""Mutations des huit unites de rejeu, des trois coutures et du correctif prix de phase 10, sur copies temporaires et suite des deux robots.

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


MUTATIONS=[{'nom': '0a_commissions_ajoutees', 'fichier': 'src/xpbots/rejeu/c0a_types/_impl.py', 'avant': 'return self.profit_brut-self.frais_entree-self.frais_sortie', 'apres': 'return self.profit_brut+self.frais_entree+self.frais_sortie', 'couche': '0a'}, {'nom': '0b_delai_reference_decale', 'fichier': 'src/xpbots/rejeu/c0b_protocole/_impl.py', 'avant': "('REFERENCE',250,1,Decimal(1))", 'apres': "('REFERENCE',251,1,Decimal(1))", 'couche': '0b'}, {'nom': '1a_empreinte_ignoree', 'fichier': 'src/xpbots/rejeu/c1a_ticks/_impl.py', 'avant': 'if empreinte!=manifeste.sha256:', 'apres': 'if False and empreinte!=manifeste.sha256:', 'couche': '1a'}, {'nom': '1b_delai_entree_ignore', 'fichier': 'src/xpbots/rejeu/c1b_simulateur/_impl.py', 'avant': 'if self.instant_ms<a.envoi_ms+self.scenario.delai_ms+a.plan.retards_ms[a.index]:continue', 'apres': 'if self.instant_ms<a.envoi_ms+a.plan.retards_ms[a.index]:continue', 'couche': '1b'}, {'nom': '1c_retention_faussee', 'fichier': 'src/xpbots/rejeu/c1c_metriques/_impl.py', 'avant': 'ratio=D(candidat)/D(reference)', 'apres': 'ratio=D(candidat)/D(reference+1)', 'couche': '1c'}, {'nom': '1d_graine_non_reproductible', 'fichier': 'src/xpbots/rejeu/c1d_bootstrap/_impl.py', 'avant': 'generateur=random.Random(parametres.graine)', 'apres': 'generateur=random.Random(parametres.graine+1)', 'couche': '1d'}, {'nom': '2_fills_non_transmis', 'fichier': 'src/xpbots/rejeu/c2_executeur/_impl.py', 'avant': 'maj[n]=MiseAJourBras(r,base_utc=p.base_utc())\n            q=', 'apres': 'maj[n]=MiseAJourBras((),base_utc=p.base_utc())\n            q=', 'couche': '2'}, {'nom': '3_egalite_des_seuils_refusee', 'fichier': 'src/xpbots/rejeu/c3_rapports/_impl.py', 'avant': "if relation=='>=':ok=observe>=seuil", 'apres': "if relation=='>=':ok=observe>seuil", 'couche': '3'}, {'nom': 'S1_tous_ticks_perdus', 'fichier': 'src/xpbots/rejeu/squelette.py', 'avant': 'return iter(analyser_ticks_manifestes(lignes,manifeste))', 'apres': 'return iter(())', 'couche': 'S1'}, {'nom': 'S5_compatibilite_glissement_ajoute', 'fichier': 'src/xpbots/rejeu/squelette.py', 'avant': "ScenarioExecution('SYNTHETIQUE_S5',0,0,Decimal(1))", 'apres': "ScenarioExecution('SYNTHETIQUE_S5',0,1,Decimal(1))", 'couche': 'S5'}, {'nom': 'S7_stress_ignore', 'fichier': 'src/xpbots/app/rejeu_squelette.py', 'avant': 'return charger_protocole(configuration).scenario(nom)', 'apres': "return charger_protocole(configuration).scenario('REFERENCE')", 'couche': 'S7'}, {'nom': '0d_grille_ask_stress_refusee', 'fichier': 'src/xpbots/execution/c0d_prix/_impl.py', 'avant': 'if cotation.spread<0:', 'apres': 'if cotation.spread<0 or not est_sur_grille(cotation.ask,tick):', 'couche': 'AMONT0d'}]


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
            domaine='squelette' if m['couche'].startswith('S') else 'london_execution_coordinateur' if m['couche'].startswith('AMONT') else 'london_rejeu'
            if r['code'] and not any(domaine in str(t) for t in r['en_defaut']):
                raise RuntimeError('aucun test fonctionnel du composant en défaut')
            if journal:
                journal.parent.mkdir(parents=True,exist_ok=True)
                with journal.open('a',encoding='utf-8',newline='\n') as f:
                    f.write(json.dumps(dict(empreinte=empreinte,resultat=r),ensure_ascii=True)+'\n')
        return r
    harnais.executer=verifier
    if '--rapport' not in suite: suite+=['--rapport','.local/reports/mutations_rejeu_phase10.json']
    sys.argv=[sys.argv[0]]+suite
    return harnais.main()


if __name__=='__main__': raise SystemExit(main())
