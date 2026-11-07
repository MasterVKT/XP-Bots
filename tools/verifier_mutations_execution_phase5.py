"""Mutations de phase 5 sur copies temporaires hors dépôt, avec suite intégrale pour chaque cas.

Réutilise le harnais éprouvé de phase 4, sans modifier sa source. La copie saine doit passer avant
les variantes ; une erreur syntaxique ou un motif non unique invalide le harnais. --selection permet
de rejouer explicitement un cas après correction, sans présenter ce rejeu ciblé comme un second lot complet.
--journal-progressif conserve chaque résultat validé et permet de reprendre après interruption,
seulement si les sources, les cartes et les paramètres ont exactement la même empreinte.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from threading import Lock

import verifier_mutations_london_phase4 as harnais


def mutation(nom, paquet, avant, apres, couche):
    return {'nom': nom, 'fichier': f'src/xpbots/execution/{paquet}/_impl.py',
            'avant': avant, 'apres': apres, 'couche': couche}


MUTATIONS = [
    mutation('0a_sens_ema_inverse', 'c0a_types', 'if signal.sens>0 else Sens.VENTE',
             'if signal.sens<0 else Sens.VENTE', '0a'),
    mutation('0a_risque_negatif_non_valide', 'c0a_types', "for n in ('risque_initial','volume'):",
             "for n in ('volume',):", '0a'),
    mutation('0b_neutre_demande_cloture', 'c0b_controles', 'return ()',
             "return ('fermeture_fantome',)", '0b'),
    mutation('0c_ttl_exact_admis', 'c0c_cotation', 'if instant_ms >= signal.cloture_ms+ttl:',
             'if instant_ms > signal.cloture_ms+ttl:', '0c'),
    mutation('0c_age_fournisseur_ignore', 'c0c_cotation', 'or instant_ms-cotation.instant_fournisseur_ms>age',
             'or False', '0c'),
    mutation('0c_age_reception_ignore', 'c0c_cotation', 'or instant_ms-cotation.instant_reception_ms>age',
             'or False', '0c'),
    mutation('0c_spread_plafond_exclu', 'c0c_cotation', 'if cotation.spread>decimal_depuis',
             'if cotation.spread>=decimal_depuis', '0c'),
    mutation('0d_spread_short_oublie', 'c0d_prix', 'brut if achat else brut+cotation.spread',
             'brut', '0d'),
    mutation('0d_tp_non_recalcule_au_fill', 'c0d_prix', 'n=_objectif(prix_reel,niveaux.stop',
             'n=_objectif(niveaux.entree,niveaux.stop', '0d'),
    mutation('0e_derniere_echeance_choisie', 'c0e_echeances', 'premier=min(t for t,c in echeances)',
             'premier=max(t for t,c in echeances)', '0e'),
    mutation('1a_panne_devient_zero', 'c1a_calcul', "return RefusExecution(Motif.ENVIRONMENT_NOT_READY,fonction)",
             'return Decimal(0)', '1a'),
    mutation('1b_seuil_quotidien_exclu', 'c1b_gardes', 'compte.fonds_propres<=base*',
             'compte.fonds_propres<base*', '1b'),
    mutation('1b_seuil_global_exclu', 'c1b_gardes', 'compte.fonds_propres<=pic*',
             'compte.fonds_propres<pic*', '1b'),
    mutation('1b_arret_global_non_persistant', 'c1b_gardes', 'bool(ancien and ancien.arret_global)',
             'False', '1b'),
    mutation('1b_retrait_ne_translate_pas_pic', 'c1b_gardes', 'ancien.pic+ajustement_pic',
             'ancien.pic', '1b'),
    mutation('1c_version_perimee_ignoree', 'c1c_reservations', 'or version_attendue!=self._etat.version',
             'or False', '1c'),
    mutation('1c_alias_sous_jacent_ignore', 'c1c_reservations',
             '(r.cle.symbole==cle.symbole or r.sous_jacent==sous_jacent)', '(r.cle.symbole==cle.symbole)', '1c'),
    mutation('1c_plafond_reserve_exact_exclu', 'c1c_reservations', 'if total+risque>decimal_depuis',
             'if total+risque>=decimal_depuis', '1c'),
    mutation('1c_fill_libere_reservation', 'c1c_reservations', 'if issue.nature is NatureIssue.REMPLIE:',
             'if False and issue.nature is NatureIssue.REMPLIE:', '1c'),
    mutation('2a_glissement_entree_recompte', 'c2a_risque',
             'entree=niveaux.entree if apres_remplissage else niveaux.entree+s*g',
             'entree=niveaux.entree+s*g', '2a'),
    mutation('2a_frais_entree_reels_oublies', 'c2a_risque', 'if apres_remplissage: frais+=frais_entree_reels',
             'if False and apres_remplissage: frais+=frais_entree_reels', '2a'),
    mutation('2a_reserve_glissement_minimale', 'c2a_risque', 'g=max(profil.tick_size,',
             'g=min(profil.tick_size,', '2a'),
    mutation('2b_symboles_avant_methodes', 'c2b_arbitrage', 'methodes[s.strategie],symboles[s.symbole]',
             'symboles[s.symbole],methodes[s.strategie]', '2b'),
    mutation('2b_registre_non_relu', 'c2b_arbitrage', 'yield CandidatArbitrage(signal,registre.etat)',
             'yield CandidatArbitrage(signal,EtatReservations())', '2b'),
    mutation('3_budget_exact_exclu', 'c3_dimensionnement', 'if risque.total>budget:',
             'if risque.total>=budget:', '3'),
    mutation('3_volume_arrondi_haut', 'c3_dimensionnement', 'rounding=ROUND_FLOOR',
             "rounding='ROUND_CEILING'", '3'),
    mutation('3_marge_native_cumulee_ignoree', 'c3_dimensionnement',
             'totale=controle.marge_totale_apres+pending', 'totale=marge+pending', '3'),
    mutation('3_budget_initial_non_gele', 'c3_dimensionnement', 'budget=plan_initial.budget_gele',
             'budget=decimal_depuis(commun.risk_fraction_per_entry)*compte.fonds_propres', '3'),
    mutation('3_stopout_ignore', 'c3_dimensionnement', 'or not controle.stop_out_respecte',
             'or False', '3'),
]


def main():
    selectionneur = argparse.ArgumentParser(add_help=False)
    selectionneur.add_argument('--selection', choices=[m['nom'] for m in MUTATIONS], action='append')
    selectionneur.add_argument('--journal-progressif')
    args, suite = selectionneur.parse_known_args()
    harnais.MUTATIONS = [m for m in MUTATIONS if not args.selection or m['nom'] in args.selection]
    if args.journal_progressif:
        racine = harnais.ROOT.resolve()
        journal = (racine / args.journal_progressif).resolve()
        if not journal.is_relative_to(racine / '.local'):
            raise ValueError('le journal progressif doit rester dans .local/')
        fichiers = {p for dossier in ('src', 'tests', 'tools', 'config', 'schemas', 'prompts', 'reference')
                    for p in (racine / dossier).rglob('*') if p.is_file() and p.suffix in ('.py', '.json')}
        fichiers.update((racine / 'mcl').glob('*/carte.json'))
        empreinte = hashlib.sha256()
        for fichier in sorted(fichiers):
            empreinte.update(fichier.relative_to(racine).as_posix().encode('utf-8') + b'\0')
            empreinte.update(hashlib.sha256(fichier.read_bytes()).digest())
        attendu = empreinte.hexdigest()
        anciens = {}
        if journal.exists():
            for ligne in journal.read_text(encoding='utf-8').splitlines():
                entree = json.loads(ligne)
                if entree['empreinte'] != attendu:
                    raise ValueError('journal de mutations incompatible avec les sources courantes')
                anciens[entree['resultat']['nom']] = entree['resultat']
        executer_original = harnais.executer
        verrou = Lock()

        def executer_progressif(copie, nom):
            if nom in anciens:
                return dict(anciens[nom])
            resultat = executer_original(copie, nom)
            if nom != 'copie_saine':
                extrait = resultat['extrait'].lower()
                if any(m in extrait for m in ('memoryerror', 'unable to allocate', 'winerror 1450', "can't start new thread")):
                    raise RuntimeError('ressources systeme insuffisantes : mutation non validee')
                if resultat['code'] and not any('london_execution_coordinateur' in str(t) for t in resultat['en_defaut']):
                    raise RuntimeError('mutation sans test du composant en defaut : detection non prouvee')
                with verrou:
                    journal.parent.mkdir(parents=True, exist_ok=True)
                    with journal.open('a', encoding='utf-8', newline='\n') as flux:
                        flux.write(json.dumps({'empreinte': attendu, 'resultat': resultat}, ensure_ascii=True) + '\n')
            return resultat

        harnais.executer = executer_progressif
    if '--rapport' not in suite:
        suite += ['--rapport', '.local/reports/mutations_execution_phase5.json']
    sys.argv = [sys.argv[0]] + suite
    return harnais.main()


if __name__ == '__main__':
    raise SystemExit(main())
