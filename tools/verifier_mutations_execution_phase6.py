"""Mutations C08 et couture de phase 6, sur copies temporaires et suite des deux robots.

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
    return dict(nom=nom,fichier=f'src/xpbots/execution/{paquet}/_impl.py',avant=avant,apres=apres,couche=couche)


MUTATIONS=[
    mutation('4_premier_fill_recompte','c4_cycle','premier = self._etat.premier_fill_ms is None','premier = True','4'),
    mutation('4_reliquat_non_confirme','c4_cycle',"annule = d['reliquat_annule'] and d['reliquat'] == 0","annule = True",'4'),
    mutation('4_ack_inconnu_devient_refus','c4_cycle',"if d['statut'] is StatutAccuse.INCONNU:","if False and d['statut'] is StatutAccuse.INCONNU:",'4'),
    mutation('4_rapprochement_rapide_ignore','c4_cycle','intervalle = self._commun.reconcile_fast_poll_seconds if e.dernier_ms < limite else self._commun.reconcile_slow_poll_seconds','intervalle = self._commun.reconcile_slow_poll_seconds','4'),
    mutation('5a_echeance_exacte_ignoree','c5a_sorties','elif echeance.instant_ms <= instant_ms:','elif echeance.instant_ms < instant_ms:','5a'),
    mutation('5a_priorite_inversee','c5a_sorties','cause, motif, detail = min(candidats,','cause, motif, detail = max(candidats,','5a'),
    mutation('5a_flatten_ignore','c5a_sorties','if decision.cloture_obligatoire:','if False and decision.cloture_obligatoire:','5a'),
    mutation('5b_propriete_par_symbole_seul','c5b_reprise','if (natif.symbole_courtier, natif.magic, natif.commentaire) == (v.profil.symbole_courtier, identite.magic, identite.commentaire):','if natif.symbole_courtier == v.profil.symbole_courtier:','5b'),
    mutation('5b_protections_courantes_ignorees','c5b_reprise','if (e.sl_natif, e.tp_natif) != (n.sl, n.tp):','if False and (e.sl_natif, e.tp_natif) != (n.sl, n.tp):','5b'),
    mutation('5b_netting_sans_preuve','c5b_reprise','exclusif = not netting or (v is not None and v.profil.symbole in observation.exclusivites and n.origine_exclusive)','exclusif = True','5b'),
    mutation('6_ttl_exact_admis','c6_coordinateur','expire=instant_ms>=s.cloture_ms+_ms(self._p.entry_signal_ttl_seconds)','expire=instant_ms>s.cloture_ms+_ms(self._p.entry_signal_ttl_seconds)','6'),
    mutation('6_permission_c05_ignoree','c6_coordinateur','return self._fond(s) or self._refus_sorties or self._ia(s)','return self._refus_sorties or self._ia(s)','6'),
    mutation('6_sl_absent_autorise_entree','c6_coordinateur','if e.volume_ouvert and (e.sl_natif!=self._fiches[k].plan.niveaux.stop or e.niveaux_reels is None):','if False and e.volume_ouvert and (e.sl_natif!=self._fiches[k].plan.niveaux.stop or e.niveaux_reels is None):','6'),
    mutation('6_revalidation_risque_ignoree','c6_coordinateur','resultat=revalider_avant_envoi(v.plan,v.signal,profil,self._compte,self._registre,self._gardes,self._port,self._p)','resultat=None','6'),
    dict(nom='S4_issue_perdue',couche='S4',fichier='src/xpbots/orchestration/squelette.py',avant='self._strategie.sur_issue(issue)',apres='None'),
    dict(nom='S5_achat_rempli_bid',couche='S5',fichier='src/xpbots/rejeu/squelette.py',avant="d=c.donnees;prix=ask if k.sens is Sens.ACHAT else bid",apres='d=c.donnees;prix=bid'),
    dict(nom='S5_protections_ignorees',couche='S5',fichier='src/xpbots/rejeu/squelette.py',avant='if sl or tp:',apres='if False and (sl or tp):'),
    dict(nom='S5_doublons_transmis',couche='S5',fichier='src/xpbots/rejeu/squelette.py',avant='if c.reference in self._vues: continue',apres='if False and c.reference in self._vues: continue'),
    dict(nom='S7_scenario_implicite',couche='S7',fichier='src/xpbots/app/rejeu_squelette.py',avant="add_argument('--scenario',required=True",apres="add_argument('--scenario',required=False"),
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
            domaine='squelette' if m['couche'].startswith('S') else 'london_execution_coordinateur'
            if r['code'] and not any(domaine in str(t) for t in r['en_defaut']):
                raise RuntimeError('aucun test fonctionnel du composant en défaut')
            if journal:
                journal.parent.mkdir(parents=True,exist_ok=True)
                with journal.open('a',encoding='utf-8',newline='\n') as f:
                    f.write(json.dumps(dict(empreinte=empreinte,resultat=r),ensure_ascii=True)+'\n')
        return r
    harnais.executer=verifier
    if '--rapport' not in suite: suite+=['--rapport','.local/reports/mutations_execution_phase6.json']
    sys.argv=[sys.argv[0]]+suite
    return harnais.main()


if __name__=='__main__': raise SystemExit(main())
