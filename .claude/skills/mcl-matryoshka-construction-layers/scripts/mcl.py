#!/usr/bin/env python3
"""mcl.py - outillage de la methode MCL (Matryoshka Construction Layers).

Rend mecaniques les controles que la methode prescrit (III.3, III.7 a III.10) :
carte des couches, invariant verifie sur le code reel, regression gate journalise,
gel / defigeage des contrats, baseline a cliquet, traces auto-instrumentees (II.6).

Bibliotheque standard uniquement (Python >= 3.8). Aucune dependance.

Sous-commandes :
  init        cree le dossier d'etat (carte.json, journal.jsonl, contrats/, PLAN-MCL.md)
  analyser    DAG des unites : cycles (Tarjan), profondeurs, couches paralleles,
              controle de divergence (etapes 3 et 4)
  exporter    configuration d'un outil de test d'architecture (III.3)
  verifier    code reel contre la carte : invariant, paralleles, frontieres externes,
              cycles, divergence, contrats figes, baseline (III.3, III.8)
  rayon       consommateurs directs et transitifs d'une couche ou d'une unite (III.9)
  gate        regression gate : architecture + tests, journalise, aiguillage (I.7, III.7)
  figer       gele le contrat d'une couche (exige un gate vert sur l'etat courant)
  defiger     leve formellement le gel : extension | modification | correction
  checkpoint  journalise un checkpoint de refactoring (etape 8)
  baseline    cree / resserre / reinitialise la baseline de dette (cliquet, III.8)
  statut      etat des couches, couches constructibles, checkpoint du
  rapport     metriques issues des traces (hypotheses auto-instrumentees, II.6)

Codes de sortie : 0 succes ; 1 echec de controle (violation stricte, gate rouge,
gel refuse) ; 2 erreur d'usage ou de configuration.
"""

import argparse
import ast
import datetime as _dt
import fnmatch
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

VERSION = "1.0.0"
DOSSIER_DEFAUT = "mcl"
REGLES = ("invariant", "paralleles", "externes", "cycles", "divergence", "contrats_figes")
REGLES_DEFAUT = {
    "invariant": "strict",
    "paralleles": "strict",
    "externes": "strict",
    "cycles": "strict",
    "divergence": "warn",
    "contrats_figes": "strict",
}
NATURES_DEFIGEAGE = ("extension", "modification", "correction")
REPERTOIRES_IGNORES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env", "build", "dist",
    "target", ".dart_tool", ".gradle", "bin", "obj", "vendor", ".idea", ".vscode",
    ".mypy_cache", ".pytest_cache", ".tox", ".nyc_output", "coverage", ".next",
    ".svelte-kit", ".cache", ".ruff_cache",
}
FICHIERS_IGNORES = ("*.pyc", "*.pyo", ".coverage", ".DS_Store", "*.class")
EXTENSIONS = {
    "python": (".py",),
    "javascript": (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"),
    "typescript": (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"),
    "go": (".go",),
    "java": (".java",),
    "kotlin": (".kt", ".kts"),
    "csharp": (".cs",),
    "php": (".php",),
    "dart": (".dart",),
    "rust": (".rs",),
}


# --------------------------------------------------------------------------- utilitaires

class ErreurMCL(Exception):
    """Erreur d'usage ou de configuration (code de sortie 2)."""


def maintenant():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_fichier(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(65536), b""):
            h.update(bloc)
    return h.hexdigest()


def norm(p):
    """Chemin relatif normalise, separateur '/'."""
    p = os.path.normpath(p).replace("\\", "/")
    return "" if p == "." else p


def prefixe_chemin(prefixe, chemin):
    """Vrai si `chemin` est `prefixe` ou se trouve dessous (comparaison par composants)."""
    prefixe, chemin = norm(prefixe), norm(chemin)
    return chemin == prefixe or chemin.startswith(prefixe + "/")


def prefixe_module(prefixe, nom, separateurs=(".", "/", "\\", "::")):
    if nom == prefixe:
        return True
    return any(nom.startswith(prefixe + s) for s in separateurs)


def ecrire_json(chemin, donnees):
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
        f.write("\n")


def lire_json(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ErreurMCL("fichier introuvable : %s (lancer d'abord `mcl.py init`)" % chemin)
    except json.JSONDecodeError as e:
        raise ErreurMCL("JSON invalide dans %s : %s" % (chemin, e))


def tarjan(noeuds, aretes):
    """Composantes fortement connexes, version iterative.

    Renvoie la liste des composantes en ordre topologique inverse : une composante
    est emise apres toutes celles dont elle depend (la premiere emise est une feuille).
    `aretes[n]` = ensemble des noeuds dont n depend.
    """
    index, bas, sur_pile, pile, resultat = {}, {}, set(), [], []
    compteur = [0]
    for depart in noeuds:
        if depart in index:
            continue
        travail = [(depart, iter(sorted(aretes.get(depart, ()))))]
        index[depart] = bas[depart] = compteur[0]
        compteur[0] += 1
        pile.append(depart)
        sur_pile.add(depart)
        while travail:
            v, it = travail[-1]
            avance = False
            for w in it:
                if w not in index:
                    index[w] = bas[w] = compteur[0]
                    compteur[0] += 1
                    pile.append(w)
                    sur_pile.add(w)
                    travail.append((w, iter(sorted(aretes.get(w, ())))))
                    avance = True
                    break
                if w in sur_pile:
                    bas[v] = min(bas[v], index[w])
            if avance:
                continue
            travail.pop()
            if travail:
                bas[travail[-1][0]] = min(bas[travail[-1][0]], bas[v])
            if bas[v] == index[v]:
                comp = []
                while True:
                    w = pile.pop()
                    sur_pile.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                resultat.append(sorted(comp))
    return resultat


def lettres(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(97 + r) + s
    return s


# --------------------------------------------------------------------------- contexte

class Contexte:
    def __init__(self, racine, dossier):
        self.racine = os.path.abspath(racine)
        self.dossier = os.path.join(self.racine, dossier)
        self.dossier_rel = norm(os.path.relpath(self.dossier, self.racine))
        self.chemin_carte = os.path.join(self.dossier, "carte.json")
        self.chemin_journal = os.path.join(self.dossier, "journal.jsonl")
        self.chemin_baseline = os.path.join(self.dossier, "baseline.json")
        self._carte = None

    # -- carte
    @property
    def carte(self):
        if self._carte is None:
            self._carte = lire_json(self.chemin_carte)
            self._valider_carte()
        return self._carte

    def _valider_carte(self):
        c = self._carte
        c.setdefault("couches", [])
        c.setdefault("unites", [])
        c.setdefault("externes", [])
        c.setdefault("sources", ["."])
        regles = dict(REGLES_DEFAUT)
        regles.update(c.get("regles", {}))
        for r, m in regles.items():
            if r not in REGLES:
                raise ErreurMCL("regle inconnue dans carte.json : %s" % r)
            if m not in ("strict", "warn", "off"):
                raise ErreurMCL("mode inconnu pour la regle %s : %s (strict|warn|off)" % (r, m))
        c["regles"] = regles
        ids = [x["id"] for x in c["couches"]]
        if len(ids) != len(set(ids)):
            raise ErreurMCL("identifiants de couche dupliques dans carte.json")
        for x in c["couches"]:
            if not isinstance(x.get("profondeur"), int) or x["profondeur"] < 0:
                raise ErreurMCL("couche %s : 'profondeur' entier >= 0 obligatoire" % x["id"])
            x.setdefault("chemins", [])
            x.setdefault("imports", [])
            x.setdefault("contrats", [])
        uids = [u["id"] for u in c["unites"]]
        if len(uids) != len(set(uids)):
            raise ErreurMCL("identifiants d'unite dupliques dans carte.json")
        eids = {e["id"] for e in c["externes"]}
        if eids & set(uids):
            raise ErreurMCL("un identifiant est a la fois unite et frontiere externe : %s"
                            % sorted(eids & set(uids)))
        for u in c["unites"]:
            u.setdefault("depend_de", [])
            inconnues = [d for d in u["depend_de"] if d not in uids and d not in eids]
            if inconnues:
                raise ErreurMCL("unite %s : dependances inconnues %s (ni unite ni externe)"
                                % (u["id"], inconnues))
            if u.get("couche") is not None and u["couche"] not in ids:
                raise ErreurMCL("unite %s : couche '%s' absente de 'couches'" % (u["id"], u["couche"]))
        for e in c["externes"]:
            e.setdefault("imports", [])
            e.setdefault("couches_autorisees", [])
            for cid in e["couches_autorisees"]:
                if cid not in ids:
                    raise ErreurMCL("externe %s : couche autorisee inconnue %s" % (e["id"], cid))

    def couche(self, cid):
        for x in self.carte["couches"]:
            if x["id"] == cid:
                return x
        raise ErreurMCL("couche inconnue : %s" % cid)

    def couches_triees(self):
        return sorted(self.carte["couches"], key=lambda x: (x["profondeur"], x["id"]))

    def deps_couches(self):
        """Graphe declare couche -> couches dont elle depend.

        Source : dependances des unites. Pour une couche sans unite, repli prudent :
        toutes les couches de profondeur strictement inferieure.
        """
        carte = self.carte
        unite_couche = {u["id"]: u.get("couche") for u in carte["unites"]}
        deps = {x["id"]: set() for x in carte["couches"]}
        avec_unites = set()
        for u in carte["unites"]:
            cu = u.get("couche")
            if cu is None:
                continue
            avec_unites.add(cu)
            for d in u["depend_de"]:
                cd = unite_couche.get(d)
                if cd is not None and cd != cu:
                    deps[cu].add(cd)
        for x in carte["couches"]:
            if x["id"] not in avec_unites:
                deps[x["id"]] = {y["id"] for y in carte["couches"] if y["profondeur"] < x["profondeur"]}
        return deps

    def consommateurs_couche(self, cid):
        deps = self.deps_couches()
        inverses = {k: set() for k in deps}
        for k, ds in deps.items():
            for d in ds:
                inverses.setdefault(d, set()).add(k)
        directs = sorted(inverses.get(cid, ()), key=self._cle_couche)
        vus, a_voir = set(), list(directs)
        while a_voir:
            n = a_voir.pop()
            if n in vus:
                continue
            vus.add(n)
            a_voir.extend(inverses.get(n, ()))
        transitifs = sorted(vus - set(directs), key=self._cle_couche)
        return directs, transitifs

    def _cle_couche(self, cid):
        x = self.couche(cid)
        return (x["profondeur"], x["id"])

    # -- journal
    def journal(self):
        if not os.path.exists(self.chemin_journal):
            return []
        entrees = []
        with open(self.chemin_journal, encoding="utf-8") as f:
            for n, ligne in enumerate(f, 1):
                ligne = ligne.strip()
                if not ligne:
                    continue
                try:
                    entrees.append(json.loads(ligne))
                except json.JSONDecodeError:
                    raise ErreurMCL("journal corrompu, ligne %d : %s" % (n, self.chemin_journal))
        return entrees

    def journaliser(self, entree):
        entree = dict(entree)
        entree.setdefault("date", maintenant())
        os.makedirs(self.dossier, exist_ok=True)
        with open(self.chemin_journal, "a", encoding="utf-8") as f:
            f.write(json.dumps(entree, ensure_ascii=False, sort_keys=True) + "\n")
        return entree

    def etat_couches(self):
        etat = {x["id"]: {"statut": "a_construire"} for x in self.carte["couches"]}
        for e in self.journal():
            cid = e.get("couche")
            if cid not in etat:
                continue
            if e["type"] == "figer":
                etat[cid] = {"statut": "figee", "contrats": e.get("contrats", {}), "date": e["date"]}
            elif e["type"] == "defiger":
                etat[cid] = dict(etat[cid], statut="defigee", nature=e.get("nature"),
                                 motif=e.get("motif"), date=e["date"])
        return etat

    # -- fichiers
    def fichiers_projet(self):
        """Fichiers du projet (hors caches, hors journal), chemins relatifs."""
        journal_rel = norm(os.path.relpath(self.chemin_journal, self.racine))
        liste = None
        if shutil.which("git"):
            try:
                sortie = subprocess.run(
                    ["git", "-C", self.racine, "ls-files", "-co", "--exclude-standard", "-z"],
                    capture_output=True, check=True).stdout
                liste = [norm(p) for p in sortie.decode("utf-8", "replace").split("\0") if p]
            except (subprocess.CalledProcessError, OSError):
                liste = None
        if liste is None:
            liste = []
            for base, reps, fics in os.walk(self.racine):
                reps[:] = [r for r in reps if r not in REPERTOIRES_IGNORES]
                for f in fics:
                    liste.append(norm(os.path.relpath(os.path.join(base, f), self.racine)))
        resultat = []
        for p in sorted(set(liste)):
            if p == journal_rel:
                continue
            parties = p.split("/")
            if any(x in REPERTOIRES_IGNORES for x in parties[:-1]):
                continue
            if any(fnmatch.fnmatch(parties[-1], m) for m in FICHIERS_IGNORES):
                continue
            if os.path.isfile(os.path.join(self.racine, p)):
                resultat.append(p)
        return resultat

    def empreinte(self):
        """Empreinte de l'etat courant de l'arbre de travail (journal exclu)."""
        h = hashlib.sha256()
        for p in self.fichiers_projet():
            h.update(p.encode("utf-8") + b"\0")
            h.update(sha256_fichier(os.path.join(self.racine, p)).encode() + b"\n")
        return h.hexdigest()

    def fichiers_contrat(self, couche):
        trouves = set()
        for motif in couche.get("contrats", []):
            for p in glob.glob(os.path.join(self.racine, motif), recursive=True):
                if os.path.isfile(p):
                    trouves.add(norm(os.path.relpath(p, self.racine)))
        return sorted(trouves)

    def hash_contrats(self, couche):
        return {p: sha256_fichier(os.path.join(self.racine, p)) for p in self.fichiers_contrat(couche)}


# --------------------------------------------------------------------------- analyse du graphe

def analyser_unites(carte):
    """Etapes 3 et 4 : DAG, cycles, profondeurs, paralleles, divergence."""
    unites = carte["unites"]
    externes = {e["id"] for e in carte["externes"]}
    ids = [u["id"] for u in unites]
    aretes = {u["id"]: {d for d in u["depend_de"] if d not in externes} for u in unites}
    comps = tarjan(ids, aretes)
    comp_de = {}
    for i, comp in enumerate(comps):
        for n in comp:
            comp_de[n] = i
    profondeur_comp = {}
    for i, comp in enumerate(comps):  # ordre topologique inverse : dependances deja calculees
        deps = {comp_de[d] for n in comp for d in aretes[n]} - {i}
        profondeur_comp[i] = 0 if not deps else 1 + max(profondeur_comp[d] for d in deps)
    profondeur = {n: profondeur_comp[comp_de[n]] for n in ids}
    cycles = [c for c in comps if len(c) > 1 or (c[0] in aretes[c[0]])]

    # groupes paralleles proposes : une lettre par composante a une profondeur partagee
    par_profondeur = {}
    for i, comp in enumerate(comps):
        par_profondeur.setdefault(profondeur_comp[i], []).append(comp)
    ordre = {u: k for k, u in enumerate(ids)}
    propositions = {}
    for p, liste in par_profondeur.items():
        liste.sort(key=lambda c: min(ordre[n] for n in c))
        for j, comp in enumerate(liste):
            gid = str(p) if len(liste) == 1 else "%d%s" % (p, lettres(j))
            for n in comp:
                propositions[n] = gid

    dependants = {n: set() for n in ids}
    for n, ds in aretes.items():
        for d in ds:
            dependants[d].add(n)
    racines = [n for n in ids if not dependants[n]]
    isolees = [n for n in ids if not aretes[n] and not dependants[n]
               and not any(d in externes for d in next(u for u in unites if u["id"] == n)["depend_de"])]
    sans_resp = [u["id"] for u in unites if not str(u.get("responsabilite", "")).strip()]

    couches = {x["id"]: x for x in carte["couches"]}
    divergences = []
    for u in unites:
        cid = u.get("couche")
        if cid is None:
            continue
        declaree = couches[cid]["profondeur"]
        if declaree != profondeur[u["id"]]:
            raison = sorted(aretes[u["id"]], key=lambda d: -profondeur[d])
            detail = ("depend de %s (profondeur %d)" % (raison[0], profondeur[raison[0]])
                      if raison else "ne depend d'aucune unite interne")
            divergences.append("unite %s : couche declaree %s (profondeur %d) mais profondeur calculee %d ; %s"
                               % (u["id"], cid, declaree, profondeur[u["id"]], detail))
    unite_couche = {u["id"]: u.get("couche") for u in unites}
    for u in unites:
        cu = unite_couche[u["id"]]
        for d in aretes[u["id"]]:
            cd = unite_couche.get(d)
            if cu is None or cd is None:
                continue
            if cu == cd and comp_de[u["id"]] != comp_de[d]:
                divergences.append("unites %s et %s dans la meme couche %s alors que %s depend de %s "
                                   "(une dependance impose une profondeur strictement superieure)"
                                   % (u["id"], d, cu, u["id"], d))
            elif cu != cd and couches[cu]["profondeur"] == couches[cd]["profondeur"]:
                divergences.append("couches paralleles %s et %s : %s depend de %s ; des couches de meme "
                                   "profondeur ne dependent pas l'une de l'autre" % (cu, cd, u["id"], d))
            elif cu != cd and couches[cd]["profondeur"] > couches[cu]["profondeur"]:
                divergences.append("INVARIANT : %s (couche %s) depend de %s (couche %s, plus externe)"
                                   % (u["id"], cu, d, cd))
    consommateurs_externes = {}
    for u in unites:
        for d in u["depend_de"]:
            if d in externes:
                consommateurs_externes.setdefault(d, []).append(u["id"])
    return {
        "profondeur": profondeur,
        "composantes": comps,
        "cycles": cycles,
        "propositions": propositions,
        "racines": racines,
        "isolees": isolees,
        "sans_responsabilite": sans_resp,
        "divergences": divergences,
        "consommateurs_externes": consommateurs_externes,
        "aretes": aretes,
        "dependants": dependants,
    }


def cmd_analyser(ctx, args):
    carte = ctx.carte
    if not carte["unites"]:
        raise ErreurMCL("aucune unite dans carte.json : renseigner 'unites' (etape 2.3) avant d'analyser")
    a = analyser_unites(carte)
    if args.json:
        print(json.dumps({k: (sorted(v) if isinstance(v, set) else v) for k, v in a.items()
                          if k not in ("aretes", "dependants")}, ensure_ascii=False, indent=2))
        return 0
    prof = a["profondeur"]
    n_max = max(prof.values())
    print("# Analyse MCL du graphe de dependances (etapes 3 et 4)\n")
    print("- Unites : %d ; frontieres externes : %d ; profondeur maximale (couche N) : %d"
          % (len(prof), len(carte["externes"]), n_max))
    print("- Composantes cycliques condensees : %d\n" % len(a["cycles"]))
    print("## Carte des couches calculee\n")
    print("| Profondeur calculee | Unite | Couche declaree | Subdivision proposee | Depend de |")
    print("|---|---|---|---|---|")
    for u in sorted(carte["unites"], key=lambda u: (prof[u["id"]], a["propositions"][u["id"]], u["id"])):
        deps = ", ".join(sorted(u["depend_de"])) or "rien (feuille)"
        print("| %d | %s | %s | %s | %s |" % (prof[u["id"]], u["id"], u.get("couche", "-"),
                                             a["propositions"][u["id"]], deps))
    print("\n## Ordre de construction\n")
    groupes = {}
    toutes_declarees = all(u.get("couche") is not None for u in carte["unites"])
    for u in carte["unites"]:
        g = u["couche"] if toutes_declarees else a["propositions"][u["id"]]
        groupes.setdefault((prof[u["id"]], g), []).append(u["id"])
    for p in range(n_max + 1):
        gs = sorted(g for (q, g) in groupes if q == p)
        libelle = "couche %d" % p + (" (noyau)" if p == 0 else "") + (" (enveloppe)" if p == n_max else "")
        if len(gs) > 1:
            print("- %s : groupes paralleles %s -> construction simultanee possible, contrats finalises "
                  "ensemble" % (libelle, ", ".join(gs)))
        else:
            membres = groupes.get((p, gs[0]), []) if gs else []
            cyclique = any(len(c) > 1 and set(membres) & set(c) for c in a["cycles"])
            note = ""
            if len(membres) > 1:
                note = (" (composante cyclique condensee : co-construction bornee du noyau minimal)" if cyclique
                        else " (%d unites sans dependance mutuelle : construction simultanee possible)" % len(membres))
            print("- %s : %s%s" % (libelle, gs[0] if gs else "-", note))
        for g in gs:
            print("    - %s : %s" % (g, ", ".join(sorted(groupes[(p, g)]))))
    if a["cycles"]:
        print("\n## Cycles detectes (composantes fortement connexes)\n")
        for c in a["cycles"]:
            print("- %s -> preferer briser le cycle par une interface si c'est un defaut de conception ; "
                  "sinon condenser en une couche, construite en interne : noyau minimal co-construit, "
                  "croissance incrementale, doublure de sectionnement temporaire en repli (III.2, 2.5.a)"
                  % " <-> ".join(c))
    print("\n## Controle de divergence (carte declaree contre graphe formalise)\n")
    if any(u.get("couche") is None for u in carte["unites"]):
        print("- Unites sans couche declaree : %s (les assigner a l'etape 4)"
              % ", ".join(u["id"] for u in carte["unites"] if u.get("couche") is None))
    if a["divergences"]:
        for d in a["divergences"]:
            print("- DIVERGENCE : %s" % d)
        print("\n> Resoudre chaque divergence avant toute construction : dependance mal comprise ou unite "
              "manquante. C'est un signal, pas un echec.")
    elif all(u.get("couche") is not None for u in carte["unites"]):
        print("- Aucune divergence.")
    print("\n## Frontieres externes (etape 6)\n")
    if carte["externes"]:
        for e in carte["externes"]:
            cons = a["consommateurs_externes"].get(e["id"], [])
            print("- %s : contrat attendu + doublure minimale ; consommateurs %s ; implementation reelle "
                  "uniquement en couche(s) %s" % (e["id"], ", ".join(cons) or "(aucun)",
                                                    ", ".join(e["couches_autorisees"]) or "(a declarer)"))
    else:
        print("- Aucune frontiere externe declaree.")
    alertes = []
    if len(a["racines"]) > 1:
        alertes.append("plusieurs racines (%s) : verifier l'enveloppe (couche N) de l'artefact"
                       % ", ".join(a["racines"]))
    if a["isolees"]:
        alertes.append("unites sans aucune relation de dependance (trait 3 d'une unite valide) : %s"
                       % ", ".join(a["isolees"]))
    if a["sans_responsabilite"]:
        alertes.append("unites sans responsabilite enoncee en une phrase : %s" % ", ".join(a["sans_responsabilite"]))
    if alertes:
        print("\n## Alertes\n")
        for x in alertes:
            print("- %s" % x)
    if args.ecrire:
        if carte["couches"]:
            raise ErreurMCL("--ecrire refuse : 'couches' deja renseigne (editer carte.json a la main)")
        brut = lire_json(ctx.chemin_carte)
        vus = {}
        for u in brut["unites"]:
            g = a["propositions"][u["id"]]
            u["couche"] = g
            vus.setdefault(g, prof[u["id"]])
        brut["couches"] = [{"id": g, "profondeur": p, "nom": "", "chemins": [], "imports": [],
                            "contrats": ["%s/contrats/couche-%s.md" % (ctx.dossier_rel, g)]}
                           for g, p in sorted(vus.items(), key=lambda kv: (kv[1], kv[0]))]
        ecrire_json(ctx.chemin_carte, brut)
        print("\ncarte.json mis a jour : %d couches proposees ; renseigner 'chemins' et 'imports' "
              "(convention une couche = un module nomme)." % len(brut["couches"]))
    return 1 if a["divergences"] else 0


# --------------------------------------------------------------------------- extraction des imports

def retirer_commentaires_c(texte, diese=False, guillemets="\"'`"):
    """Retire // ... et /* ... */ (et # si diese) hors chaines, en conservant les sauts de ligne."""
    out, i, n = [], 0, len(texte)
    quote = None
    while i < n:
        c = texte[i]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(texte[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in guillemets:
            quote = c
            out.append(c)
            i += 1
            continue
        if texte.startswith("//", i) or (diese and c == "#"):
            j = texte.find("\n", i)
            i = n if j < 0 else j
            continue
        if texte.startswith("/*", i):
            j = texte.find("*/", i + 2)
            bloc = texte[i:(n if j < 0 else j + 2)]
            out.append("\n" * bloc.count("\n"))
            i = n if j < 0 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _ligne(texte, pos):
    return texte.count("\n", 0, pos) + 1


RE_JS = re.compile(r"""(?:\bimport\s+(?:type\s+)?(?:[^'"`;]*?\s+from\s+)?|\bexport\s+[^'"`;]*?\s+from\s+|"""
                   r"""\brequire\s*\(\s*|\bimport\s*\(\s*)['"]([^'"]+)['"]""")
RE_GO_BLOC = re.compile(r"^\s*import\s*\((.*?)\)", re.S | re.M)
RE_GO_UN = re.compile(r'^\s*import\s+(?:[\w.]+\s+)?"([^"]+)"', re.M)
RE_GO_SPEC = re.compile(r'(?:[\w.]+\s+)?"([^"]+)"')
RE_JAVA = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+?)(?:\.\*)?(?:\s+as\s+\w+)?\s*;?\s*$", re.M)
RE_CS = re.compile(r"^\s*(?:global\s+)?using\s+(?:static\s+)?(?:\w+\s*=\s*)?([\w.]+)\s*;", re.M)
RE_PHP = re.compile(r"^\s*use\s+(?:function\s+|const\s+)?\\?([\w\\]+)", re.M)
RE_DART = re.compile(r"""^\s*(?:import|export|part)\s+['"]([^'"]+)['"]""", re.M)
RE_RUST_CRATE = re.compile(r"\bcrate((?:::[A-Za-z_]\w*)+)")
RE_RUST_USE = re.compile(r"^\s*(?:pub\s+)?(?:use|extern\s+crate)\s+([A-Za-z_]\w*)", re.M)


def extraire_imports(chemin_rel, texte):
    """Renvoie une liste de (cible, relatif, ligne). `relatif` vaut un chemin resolu ou None."""
    ext = os.path.splitext(chemin_rel)[1].lower()
    dossier = os.path.dirname(chemin_rel)
    res = []
    if ext == ".py":
        try:
            arbre = ast.parse(texte)
        except SyntaxError:
            return None
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.Import):
                for a in noeud.names:
                    res.append((a.name, None, noeud.lineno))
            elif isinstance(noeud, ast.ImportFrom):
                if noeud.level == 0:
                    for a in noeud.names:
                        cible = noeud.module if a.name == "*" else "%s.%s" % (noeud.module, a.name)
                        res.append((cible, None, noeud.lineno))
                else:
                    base = dossier
                    for _ in range(noeud.level - 1):
                        base = os.path.dirname(base)
                    mod = (noeud.module or "").replace(".", "/")
                    for a in noeud.names:
                        p = norm(os.path.join(base, mod, "" if a.name == "*" else a.name))
                        res.append(((noeud.module or "") + "." + a.name, p, noeud.lineno))
        return res
    if ext in EXTENSIONS["javascript"]:
        propre = retirer_commentaires_c(texte)
        for m in RE_JS.finditer(propre):
            spec = m.group(1)
            rel = norm(os.path.join(dossier, spec)) if spec.startswith(".") else None
            res.append((spec, rel, _ligne(propre, m.start())))
        return res
    if ext == ".go":
        propre = retirer_commentaires_c(texte)
        for m in RE_GO_BLOC.finditer(propre):
            for s in RE_GO_SPEC.finditer(m.group(1)):
                res.append((s.group(1), None, _ligne(propre, m.start(1) + s.start())))
        for m in RE_GO_UN.finditer(propre):
            res.append((m.group(1), None, _ligne(propre, m.start())))
        return res
    if ext in (".java", ".kt", ".kts"):
        propre = retirer_commentaires_c(texte)
        for m in RE_JAVA.finditer(propre):
            res.append((m.group(1), None, _ligne(propre, m.start())))
        return res
    if ext == ".cs":
        propre = retirer_commentaires_c(texte)
        for m in RE_CS.finditer(propre):
            res.append((m.group(1), None, _ligne(propre, m.start())))
        return res
    if ext == ".php":
        propre = retirer_commentaires_c(texte, diese=True)
        for m in RE_PHP.finditer(propre):
            res.append((m.group(1).replace("\\", "/"), None, _ligne(propre, m.start())))
        return res
    if ext == ".dart":
        propre = retirer_commentaires_c(texte)
        for m in RE_DART.finditer(propre):
            spec = m.group(1)
            rel = None
            if not re.match(r"^[a-z]+:", spec):
                rel = norm(os.path.join(dossier, spec))
            res.append((spec, rel, _ligne(propre, m.start())))
        return res
    if ext == ".rs":
        propre = retirer_commentaires_c(texte, guillemets="\"")
        for m in RE_RUST_CRATE.finditer(propre):
            res.append(("crate" + m.group(1), None, _ligne(propre, m.start())))
        for m in RE_RUST_USE.finditer(propre):
            if m.group(1) not in ("crate", "self", "super", "std", "core", "alloc"):
                res.append((m.group(1), None, _ligne(propre, m.start())))
        return res
    return []


# --------------------------------------------------------------------------- verification

class Verification:
    def __init__(self, ctx):
        self.ctx = ctx
        carte = ctx.carte
        self.couches = carte["couches"]
        self.par_id = {x["id"]: x for x in self.couches}
        langages = carte.get("langage") or list(EXTENSIONS)
        if isinstance(langages, str):
            langages = [langages]
        exts = set()
        for lg in langages:
            if lg not in EXTENSIONS:
                raise ErreurMCL("langage non pris en charge : %s (%s)" % (lg, ", ".join(sorted(EXTENSIONS))))
            exts.update(EXTENSIONS[lg])
        self.extensions = exts
        self.sources = [norm(s) for s in carte["sources"]]
        self.exclure = carte.get("exclure", [])
        self.imports_couche = []
        for x in self.couches:
            prefixes = list(x["imports"])
            if not prefixes and ".py" in exts:
                prefixes = [self._module_python(ch) for ch in x["chemins"]]
            for p in prefixes:
                if p:
                    self.imports_couche.append((p.replace("\\", "/"), x["id"]))
        self.imports_couche.sort(key=lambda t: -len(t[0]))

    def _module_python(self, chemin):
        chemin = norm(chemin)
        for s in sorted(self.sources, key=len, reverse=True):
            if s and prefixe_chemin(s, chemin):
                chemin = chemin[len(s):].lstrip("/")
                break
        return chemin.replace("/", ".")

    def couche_du_fichier(self, chemin_rel):
        meilleur = None
        for x in self.couches:
            for ch in x["chemins"]:
                if prefixe_chemin(ch, chemin_rel) and (meilleur is None or len(norm(ch)) > meilleur[0]):
                    meilleur = (len(norm(ch)), x["id"])
        return meilleur[1] if meilleur else None

    def couche_de_la_cible(self, cible, relatif):
        if relatif is not None:
            return self.couche_du_fichier(relatif)
        c = cible.replace("\\", "/")
        for prefixe, cid in self.imports_couche:
            if prefixe_module(prefixe, c):
                return cid
        return None

    def fichiers_source(self):
        for p in self.ctx.fichiers_projet():
            if os.path.splitext(p)[1].lower() not in self.extensions:
                continue
            if self.sources and not any(s == "" or prefixe_chemin(s, p) for s in self.sources):
                continue
            if any(fnmatch.fnmatch(p, m) for m in self.exclure):
                continue
            yield p

    def executer(self):
        regles = self.ctx.carte["regles"]
        externes = self.ctx.carte["externes"]
        violations, infos = [], {"fichiers_analyses": 0, "fichiers_hors_carte": [], "illisibles": []}
        aretes_reelles = {}
        for p in self.fichiers_source():
            cs = self.couche_du_fichier(p)
            if cs is None:
                infos["fichiers_hors_carte"].append(p)
                continue
            infos["fichiers_analyses"] += 1
            try:
                with open(os.path.join(self.ctx.racine, p), encoding="utf-8", errors="replace") as f:
                    texte = f.read()
            except OSError:
                infos["illisibles"].append(p)
                continue
            imports = extraire_imports(p, texte)
            if imports is None:
                infos["illisibles"].append(p)
                continue
            src = self.par_id[cs]
            for cible, relatif, ligne in imports:
                ct = self.couche_de_la_cible(cible, relatif)
                if ct is not None and ct != cs:
                    aretes_reelles.setdefault(cs, {}).setdefault(ct, []).append((p, ligne, cible))
                    dst = self.par_id[ct]
                    if dst["profondeur"] > src["profondeur"]:
                        violations.append(("invariant", p, ligne, cible,
                                           "couche %s (profondeur %d) reference la couche %s (profondeur %d, "
                                           "plus externe)" % (cs, src["profondeur"], ct, dst["profondeur"])))
                    elif dst["profondeur"] == src["profondeur"]:
                        violations.append(("paralleles", p, ligne, cible,
                                           "couches paralleles %s et %s (profondeur %d) : aucune dependance "
                                           "mutuelle permise" % (cs, ct, src["profondeur"])))
                if ct is None:
                    c = cible.replace("\\", "/")
                    for e in externes:
                        if any(prefixe_module(pr, c) for pr in e["imports"]):
                            if cs not in e["couches_autorisees"]:
                                violations.append(("externes", p, ligne, cible,
                                                   "frontiere externe '%s' importee en couche %s ; autorisee "
                                                   "uniquement en %s (doublure ailleurs, etape 6)"
                                                   % (e["id"], cs, ", ".join(e["couches_autorisees"]) or "-")))
                            break
        # cycles au niveau des couches dans le graphe reel
        noeuds = [x["id"] for x in self.couches]
        comps = tarjan(noeuds, {k: set(v) for k, v in aretes_reelles.items()})
        for comp in comps:
            if len(comp) > 1:
                exemple = []
                for a in comp:
                    for b, occ in aretes_reelles.get(a, {}).items():
                        if b in comp:
                            exemple.append("%s->%s (%s:%d)" % (a, b, occ[0][0], occ[0][1]))
                violations.append(("cycles", ",".join(comp), 0, "<->".join(comp),
                                   "cycle entre couches dans le code reel : " + "; ".join(exemple)))
        # divergence : arete reelle non justifiee par une dependance declaree entre unites
        if self.ctx.carte["unites"]:
            declarees = self.ctx.deps_couches()
            for a, cibles in aretes_reelles.items():
                for b, occ in cibles.items():
                    if b not in declarees.get(a, set()) and self.par_id[b]["profondeur"] < self.par_id[a]["profondeur"]:
                        violations.append(("divergence", occ[0][0], occ[0][1], occ[0][2],
                                           "dependance reelle %s -> %s absente de la carte declaree "
                                           "(mettre la carte a jour ou retirer la dependance)" % (a, b)))
        # contrats figes
        etat = self.ctx.etat_couches()
        for cid, e in etat.items():
            if e["statut"] != "figee" or cid not in self.par_id:
                continue
            actuels = self.ctx.hash_contrats(self.par_id[cid])
            figes = e.get("contrats", {})
            for p in sorted(set(actuels) | set(figes)):
                if actuels.get(p) != figes.get(p):
                    quoi = "ajoute" if p not in figes else ("supprime" if p not in actuels else "modifie")
                    violations.append(("contrats_figes", p, 0, cid,
                                       "contrat de la couche figee %s %s sans defigeage formel" % (cid, quoi)))
        resultat = []
        for v in violations:
            mode = regles.get(v[0], "strict")
            if mode == "off":
                continue
            resultat.append({"regle": v[0], "fichier": v[1], "ligne": v[2], "cible": v[3], "message": v[4],
                             "mode": mode, "cle": "%s|%s|%s" % (v[0], v[1], v[3])})
        return resultat, infos


def lire_baseline(ctx):
    if not os.path.exists(ctx.chemin_baseline):
        return None
    return lire_json(ctx.chemin_baseline)


def controle_baseline(ctx):
    """Renvoie un message d'erreur si la baseline a ete alteree hors procedure."""
    if not os.path.exists(ctx.chemin_baseline):
        return None
    attendu = None
    for e in ctx.journal():
        if e["type"] == "baseline":
            attendu = e.get("sha256")
    actuel = sha256_fichier(ctx.chemin_baseline)
    if attendu is None:
        return "baseline presente mais jamais enregistree au journal (creer via `mcl.py baseline --creer`)"
    if attendu != actuel:
        return "baseline alteree hors procedure (empreinte differente de la derniere trace du journal)"
    return None


def verifier(ctx, mode_force=None):
    v = Verification(ctx)
    violations, infos = v.executer()
    if mode_force:
        for x in violations:
            x["mode"] = mode_force
    base = lire_baseline(ctx)
    cles_base = set(base.get("violations", [])) if base else set()
    for x in violations:
        x["dette"] = x["cle"] in cles_base and x["regle"] != "contrats_figes"
    resolues = sorted(cles_base - {x["cle"] for x in violations})
    alteration = controle_baseline(ctx)
    return violations, infos, resolues, alteration


def afficher_verification(violations, infos, resolues, alteration):
    strictes = [x for x in violations if x["mode"] == "strict" and not x["dette"]]
    avert = [x for x in violations if x["mode"] == "warn" and not x["dette"]]
    dettes = [x for x in violations if x["dette"]]
    print("Fichiers analyses : %d ; hors carte : %d%s" % (
        infos["fichiers_analyses"], len(infos["fichiers_hors_carte"]),
        (" ; illisibles : %s" % ", ".join(infos["illisibles"])) if infos["illisibles"] else ""))
    for titre, liste in (("VIOLATIONS STRICTES", strictes), ("AVERTISSEMENTS", avert),
                         ("DETTE TOLEREE (baseline)", dettes)):
        if liste:
            print("\n%s (%d)" % (titre, len(liste)))
            for x in liste:
                loc = "%s:%d" % (x["fichier"], x["ligne"]) if x["ligne"] else x["fichier"]
                print("  [%s] %s  -> %s\n      %s" % (x["regle"], loc, x["cible"], x["message"]))
    if resolues:
        print("\n%d violation(s) de la baseline resolue(s) : lancer `mcl.py baseline --resserrer` "
              "(le cliquet empeche leur retour)." % len(resolues))
    if alteration:
        print("\nBASELINE : %s" % alteration)
    ok = not strictes and not alteration
    print("\nResultat architecture : %s" % ("VERT" if ok else "ROUGE"))
    return ok, len(strictes), len(avert)


def cmd_verifier(ctx, args):
    violations, infos, resolues, alteration = verifier(ctx, args.mode)
    if args.json:
        print(json.dumps({"violations": violations, "infos": infos, "baseline_resolues": resolues,
                          "baseline_alteree": alteration}, ensure_ascii=False, indent=2))
        strictes = [x for x in violations if x["mode"] == "strict" and not x["dette"]]
        return 1 if strictes or alteration else 0
    ok, _, _ = afficher_verification(violations, infos, resolues, alteration)
    return 0 if ok else 1


# --------------------------------------------------------------------------- gate, gel, defigeage

def dependances_non_figees(ctx, cid):
    etat = ctx.etat_couches()
    return sorted((d for d in ctx.deps_couches()[cid] if etat[d]["statut"] != "figee"), key=ctx._cle_couche)


def executer_commande(cmd, racine):
    debut = time.time()
    print("\n$ %s" % cmd, flush=True)
    code = subprocess.run(cmd, shell=True, cwd=racine).returncode
    return code, round(time.time() - debut, 3)


def cmd_gate(ctx, args):
    if not args.regression:
        raise ErreurMCL("--regression obligatoire : le gate relance l'INTEGRALITE de la suite existante")
    if bool(args.couche) == bool(args.global_):
        raise ErreurMCL("preciser soit --couche ID (gate de couche), soit --global (checkpoint, fusion, nightly)")
    entree = {"type": "gate", "couche": args.couche, "portee": "couche" if args.couche else "global",
              "etapes": [], "resultat": "rouge"}
    if args.couche:
        couche = ctx.couche(args.couche)
        entree["profondeur"] = couche["profondeur"]
        manquantes = dependances_non_figees(ctx, args.couche)
        if manquantes:
            entree["motif_refus"] = "dependances non figees : %s" % ", ".join(manquantes)
            entree["empreinte"] = ctx.empreinte()
            ctx.journaliser(entree)
            print("GATE ROUGE - INVARIANT : la couche %s depend de couche(s) non figee(s) : %s.\n"
                  "Une couche n'est jamais construite tant que toutes celles dont elle depend ne sont pas "
                  "testees, validees et stables." % (args.couche, ", ".join(manquantes)))
            return 1
    print("== Gate MCL : %s ==" % ("couche " + args.couche if args.couche else "global"))
    violations, infos, resolues, alteration = verifier(ctx)
    ok_archi, n_strict, n_warn = afficher_verification(violations, infos, resolues, alteration)
    entree["architecture"] = {"vert": ok_archi, "violations_strictes": n_strict, "avertissements": n_warn}
    etapes = []
    if args.unitaire:
        etapes.append(("unitaire", args.unitaire))
    if args.integration:
        etapes.append(("integration", args.integration))
    etapes.extend(("regression", c) for c in args.regression)
    codes = {}
    for categorie, cmd in etapes:
        code, duree = executer_commande(cmd, ctx.racine)
        entree["etapes"].append({"categorie": categorie, "commande": cmd, "code": code, "duree_s": duree})
        codes.setdefault(categorie, []).append(code)
        if categorie == "unitaire" and code != 0:
            break
    ok_tests = all(c == 0 for cs in codes.values() for c in cs) and "regression" in codes
    if "unitaire" in codes and codes["unitaire"][0] != 0:
        entree["aiguillage"] = "regression_locale"
        conseil = ("Test unitaire de la couche courante en echec -> REGRESSION LOCALE : la cause coincide avec "
                   "le declencheur. Corriger la couche courante (aucune recherche ailleurs).")
    elif not ok_tests and "unitaire" in codes:
        entree["aiguillage"] = "interaction_ou_amont"
        conseil = ("Unitaire vert mais integration/regression rouge -> cause dans l'INTERACTION ou PLUS BAS. "
                   "Ouvrir la remontee de couches (sequentielle <= N sondes, ou dichotomie ~log N) avec des "
                   "doublures de coupe temporaires, puis appliquer le protocole correctif (references/"
                   "07-diagnostic-correction.md).")
    elif not ok_tests:
        entree["aiguillage"] = "indetermine"
        conseil = ("Regression rouge. Fournir --unitaire pour obtenir l'aiguillage mecanique "
                   "(locale contre amont).")
    else:
        conseil = None
    entree["resultat"] = "vert" if (ok_archi and ok_tests) else "rouge"
    entree["empreinte"] = ctx.empreinte()
    ctx.journaliser(entree)
    print("\n== GATE %s ==" % entree["resultat"].upper())
    if conseil:
        print(conseil)
    if entree["resultat"] == "vert" and args.couche:
        print("Couche %s eligible au gel : `mcl.py figer --couche %s` (sans modifier l'arbre d'ici la)."
              % (args.couche, args.couche))
    return 0 if entree["resultat"] == "vert" else 1


def dernier_gate(ctx, cid):
    dernier = None
    for e in ctx.journal():
        if e["type"] == "gate" and e.get("couche") == cid:
            dernier = e
    return dernier


def cmd_figer(ctx, args):
    couche = ctx.couche(args.couche)
    etat = ctx.etat_couches()[args.couche]
    if etat["statut"] == "figee":
        print("La couche %s est deja figee." % args.couche)
        return 0
    manquantes = dependances_non_figees(ctx, args.couche)
    if manquantes:
        print("GEL REFUSE - dependances non figees : %s." % ", ".join(manquantes))
        return 1
    g = dernier_gate(ctx, args.couche)
    if g is None or g.get("resultat") != "vert":
        print("GEL REFUSE - aucun gate vert pour la couche %s. Le gel ne s'accorde que sur base entierement "
              "verte : lancer `mcl.py gate --couche %s --regression ...`." % (args.couche, args.couche))
        return 1
    if g.get("empreinte") != ctx.empreinte():
        print("GEL REFUSE - l'arbre de travail a change depuis le dernier gate vert de %s. Relancer le gate."
              % args.couche)
        return 1
    contrats = ctx.hash_contrats(couche)
    if not contrats:
        print("GEL REFUSE - aucun fichier de contrat pour la couche %s (champ 'contrats' de carte.json). "
              "Le contrat est redige avant l'implementation (etape 5) ; le gel porte sur lui." % args.couche)
        return 1
    ctx.journaliser({"type": "figer", "couche": args.couche, "profondeur": couche["profondeur"],
                     "contrats": contrats, "par": args.par, "empreinte": g["empreinte"]})
    print("Couche %s FIGEE (%d fichier(s) de contrat). L'implementation interne reste revisable sous "
          "harnais complet ; le contrat est desormais read-only." % (args.couche, len(contrats)))
    return 0


def cmd_defiger(ctx, args):
    couche = ctx.couche(args.couche)
    etat = ctx.etat_couches()[args.couche]
    if etat["statut"] != "figee":
        raise ErreurMCL("la couche %s n'est pas figee (statut : %s)" % (args.couche, etat["statut"]))
    if not args.motif.strip():
        raise ErreurMCL("--motif obligatoire : chaque defigeage laisse une trace (quoi, pourquoi)")
    directs, transitifs = ctx.consommateurs_couche(args.couche)
    ctx.journaliser({"type": "defiger", "couche": args.couche, "profondeur": couche["profondeur"],
                     "nature": args.nature, "motif": args.motif, "par": args.par,
                     "rayon": {"directs": directs, "transitifs": transitifs}})
    print("Couche %s DEFIGEE (%s). Rayon d'impact : directs %s ; transitifs %s."
          % (args.couche, args.nature, ", ".join(directs) or "aucun", ", ".join(transitifs) or "aucun"))
    if args.nature == "extension":
        print("Circuit : revue standard. Extension additive (methode ou parametre optionnel a valeur par defaut "
              "conservatrice) : propagation quasi nulle. Mettre a jour le contrat, gate, re-figer.")
    elif args.nature == "correction":
        print("Circuit : ajouter a la suite de %s un test qui capture le cas revele, corriger A LA SOURCE. "
              "Si le contrat reste inchange : revalider, re-figer, regression globale ; la propagation s'arrete "
              "la. Si le contrat change : declarer un defigeage 'modification'." % args.couche)
    else:
        print("Circuit : arbitrage demandeur + proprietaire de couche + consommateurs listes ci-dessus. "
              "Tracer la decision (gabarit assets/gabarits/defigeage-adr.md : quoi, pourquoi, rayon constate). "
              "Cascade dans l'ordre des couches : re-verifier chaque consommateur contre le nouveau contrat, "
              "le defiger a son tour s'il doit s'adapter, puis re-figer.")
    return 0


def cmd_checkpoint(ctx, args):
    etat = ctx.etat_couches()
    figees = [ctx.couche(c)["profondeur"] for c, e in etat.items() if e["statut"] == "figee"]
    ctx.journaliser({"type": "checkpoint", "profondeur_max_figee": max(figees) if figees else None,
                     "notes": args.notes, "par": args.par})
    print("Checkpoint journalise. Traiter en lot : revisions d'implementation a contrat constant, puis "
          "changements de contrat via `defiger --nature modification`. Terminer par un gate global "
          "(`mcl.py gate --global --regression ...`) : un lot = une seule regression integrale.")
    return 0


def cmd_baseline(ctx, args):
    violations, _, resolues, alteration = verifier(ctx)
    actuelles = sorted({x["cle"] for x in violations if x["regle"] not in ("contrats_figes", "divergence")})
    if args.creer or args.reinitialiser:
        if args.creer and os.path.exists(ctx.chemin_baseline):
            raise ErreurMCL("baseline deja existante : utiliser --resserrer, ou --reinitialiser (cle du gardien)")
        if not (args.par and args.motif):
            raise ErreurMCL("--par et --motif obligatoires : la cle du gardien est tracee a chaque usage")
        ecrire_json(ctx.chemin_baseline, {"mcl": 1, "date": maintenant(), "violations": actuelles})
        action = "creation" if args.creer else "reinitialisation"
        ctx.journaliser({"type": "baseline", "action": action, "nb": len(actuelles), "par": args.par,
                         "motif": args.motif, "sha256": sha256_fichier(ctx.chemin_baseline)})
        print("Baseline %s : %d violation(s) capturee(s). Toute violation NOUVELLE bloquera ; toute violation "
              "resolue resserrera la baseline." % (action, len(actuelles)))
        return 0
    if args.resserrer:
        base = lire_baseline(ctx)
        if base is None:
            raise ErreurMCL("aucune baseline : `mcl.py baseline --creer --par NOM --motif ...`")
        if alteration:
            print("RESSERREMENT REFUSE - %s" % alteration)
            return 1
        restantes = sorted(set(base["violations"]) - set(resolues))
        if len(restantes) == len(base["violations"]):
            print("Rien a resserrer.")
            return 0
        base["violations"], base["date"] = restantes, maintenant()
        ecrire_json(ctx.chemin_baseline, base)
        ctx.journaliser({"type": "baseline", "action": "resserrement", "nb": len(restantes),
                         "retirees": len(resolues), "sha256": sha256_fichier(ctx.chemin_baseline)})
        print("Baseline resserree : %d violation(s) retiree(s) definitivement, %d restante(s)."
              % (len(resolues), len(restantes)))
        return 0
    raise ErreurMCL("preciser --creer, --resserrer ou --reinitialiser")


# --------------------------------------------------------------------------- statut, rayon, rapport

def cmd_statut(ctx, args):
    etat = ctx.etat_couches()
    deps = ctx.deps_couches()
    journal = ctx.journal()
    print("# Statut MCL - %s\n" % ctx.carte.get("artefact", {}).get("nom", "artefact"))
    print("| Couche | Profondeur | Statut | Depend de | Dernier gate | Constructible maintenant |")
    print("|---|---|---|---|---|---|")
    constructibles = []
    for x in ctx.couches_triees():
        cid = x["id"]
        e = etat[cid]
        g = dernier_gate(ctx, cid)
        manque = [d for d in deps[cid] if etat[d]["statut"] != "figee"]
        ok = e["statut"] != "figee" and not manque
        if ok:
            constructibles.append(cid)
        statut = e["statut"] + (" (%s)" % e["nature"] if e["statut"] == "defigee" else "")
        print("| %s | %d | %s | %s | %s | %s |" % (
            cid, x["profondeur"], statut, ", ".join(sorted(deps[cid], key=ctx._cle_couche)) or "-",
            g["resultat"] if g else "-",
            "oui" if ok else ("-" if e["statut"] == "figee" else "non (attend %s)" % ", ".join(sorted(manque)))))
    print()
    if not ctx.carte["couches"]:
        print("Aucune couche declaree : cartographier (etapes 1 a 4), puis `mcl.py analyser --ecrire`.")
        return 0
    if all(e["statut"] == "figee" for e in etat.values()):
        print("Toutes les couches sont figees : l'enveloppe est construite et validee.")
    else:
        print("Couche(s) constructible(s) maintenant : %s%s" % (
            ", ".join(constructibles) or "aucune",
            " -> groupes paralleles : construction simultanee possible" if len(constructibles) > 1 else ""))
    # consommateurs a re-verifier apres modification de contrat
    for i, e in enumerate(journal):
        if e["type"] != "defiger" or e.get("nature") != "modification":
            continue
        refige = next((j for j in range(i + 1, len(journal)) if journal[j]["type"] == "figer"
                       and journal[j].get("couche") == e["couche"]), None)
        if refige is None:
            print("- Defigeage 'modification' de %s ouvert (%s)." % (e["couche"], e.get("motif", "")))
            continue
        a_verifier = []
        for c in e["rayon"]["directs"] + e["rayon"]["transitifs"]:
            ok = any(journal[j].get("couche") == c and (journal[j]["type"] == "figer" or
                     (journal[j]["type"] == "gate" and journal[j].get("resultat") == "vert"))
                     for j in range(refige + 1, len(journal)))
            if not ok:
                a_verifier.append(c)
        if a_verifier:
            print("- Cascade de la modification de %s : consommateurs a re-verifier (ordre des couches) : %s"
                  % (e["couche"], ", ".join(sorted(a_verifier, key=ctx._cle_couche))))
    # checkpoint du
    pas = int(ctx.carte.get("checkpoint_tous_les", 2))
    dernier_cp = max((i for i, e in enumerate(journal) if e["type"] == "checkpoint"), default=-1)
    profs = {e.get("profondeur") for e in journal[dernier_cp + 1:] if e["type"] == "figer"}
    profs.discard(None)
    if len(profs) >= pas:
        print("- CHECKPOINT DE REFACTORING DU : %d niveau(x) fige(s) depuis le dernier (etape 8)." % len(profs))
    ouvertes = [c for c, e in etat.items() if e["statut"] == "defigee"]
    if ouvertes:
        print("- Couches defigees en attente de re-gel : %s" % ", ".join(sorted(ouvertes, key=ctx._cle_couche)))
    return 0


def cmd_rayon(ctx, args):
    if args.couche:
        directs, transitifs = ctx.consommateurs_couche(args.couche)
        print("Couche %s - consommateurs directs : %s ; transitifs : %s" % (
            args.couche, ", ".join(directs) or "aucun", ", ".join(transitifs) or "aucun"))
        return 0
    a = analyser_unites(ctx.carte)
    if args.unite not in a["dependants"]:
        raise ErreurMCL("unite inconnue : %s" % args.unite)
    directs = sorted(a["dependants"][args.unite])
    vus, pile = set(), list(directs)
    while pile:
        n = pile.pop()
        if n not in vus:
            vus.add(n)
            pile.extend(a["dependants"][n])
    print("Unite %s - consommateurs directs : %s ; transitifs : %s" % (
        args.unite, ", ".join(directs) or "aucun", ", ".join(sorted(vus - set(directs))) or "aucun"))
    return 0


def cmd_rapport(ctx, args):
    j = ctx.journal()
    gates = [e for e in j if e["type"] == "gate"]
    defs = [e for e in j if e["type"] == "defiger"]
    print("# Rapport MCL (traces auto-instrumentees, II.6 niveau N1)\n")
    if j:
        print("Periode : %s -> %s ; entrees de journal : %d\n" % (j[0]["date"], j[-1]["date"], len(j)))
    print("## Gates (H1, H2, H8)\n")
    print("| Portee | Profondeur | Gates | Verts | Rouges | Regr. locales | Interaction/amont | "
          "Duree regression cumulee (s) |")
    print("|---|---|---|---|---|---|---|---|")
    groupes = {}
    for g in gates:
        cle = (g.get("couche") or "global", g.get("profondeur", -1))
        groupes.setdefault(cle, []).append(g)
    cumul = 0.0
    for (portee, p), gs in sorted(groupes.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        d = sum(s["duree_s"] for g in gs for s in g.get("etapes", []) if s["categorie"] == "regression")
        cumul += d
        print("| %s | %s | %d | %d | %d | %d | %d | %.1f |" % (
            portee, p if p >= 0 else "-", len(gs), sum(g["resultat"] == "vert" for g in gs),
            sum(g["resultat"] == "rouge" for g in gs),
            sum(g.get("aiguillage") == "regression_locale" for g in gs),
            sum(g.get("aiguillage") == "interaction_ou_amont" for g in gs), d))
    print("\nCout cumule du gate (somme des regressions) : %.1f s. Prediction declaree (H8) : croissance "
          "quadratique ~N^2/2 lancements pour N couches ; comparer la courbe ci-dessus." % cumul)
    print("\n## Defigeages (H5 : les extensions additives doivent dominer les modifications)\n")
    for n in NATURES_DEFIGEAGE:
        print("- %s : %d" % (n, sum(e.get("nature") == n for e in defs)))
    par_couche = {}
    for e in defs:
        if e.get("nature") == "correction":
            par_couche[e["couche"]] = par_couche.get(e["couche"], 0) + 1
    if par_couche:
        print("- corrections par couche : %s" % ", ".join("%s=%d" % kv for kv in sorted(par_couche.items())))
    print("\n## Baseline de dette (cliquet)\n")
    for e in (e for e in j if e["type"] == "baseline"):
        print("- %s %s : %d violation(s)%s" % (e["date"], e["action"], e.get("nb", 0),
                                               (" (par %s)" % e["par"]) if e.get("par") else ""))
    print("\n## Checkpoints (etape 8) : %d" % sum(e["type"] == "checkpoint" for e in j))
    print("\n> Lecture : medianes plutot que moyennes ; ces traces sont un niveau N1 (auto-mesure, sans groupe "
          "de controle). Elles ne demontrent aucune superiorite statistique de MCL.")
    return 0


# --------------------------------------------------------------------------- export d'outillage

def _couches_profondeur(ctx):
    return ctx.couches_triees()


def _prefixe_import(ctx, x):
    if x["imports"]:
        return x["imports"][0]
    v = Verification(ctx)
    return v._module_python(x["chemins"][0]) if x["chemins"] else None


def exporter_importlinter(ctx, args):
    couches = _couches_profondeur(ctx)
    noms = {x["id"]: _prefixe_import(ctx, x) for x in couches}
    manquants = [cid for cid, n in noms.items() if not n]
    if manquants:
        raise ErreurMCL("couches sans module Python ('imports' ou 'chemins') : %s" % ", ".join(manquants))
    racines = args.paquet_racine or sorted({n.split(".")[0] for n in noms.values()})
    lignes = ["# Genere par mcl.py %s - carte des couches MCL (III.3)." % VERSION,
              "# Regle : dependances autorisees vers N'IMPORTE QUELLE couche plus interne (profondeur quelconque).",
              "[importlinter]"]
    if len(racines) == 1:
        lignes.append("root_package = %s" % racines[0])
    else:
        lignes.append("root_packages =")
        lignes.extend("    %s" % r for r in racines)
    if any(e["imports"] for e in ctx.carte["externes"]):
        lignes.append("include_external_packages = True")
    lignes += ["", "[importlinter:contract:mcl-couches]",
               "name = MCL - invariant des couches (dependances vers l'interieur uniquement)",
               "type = layers", "layers ="]
    par_p = {}
    for x in couches:
        par_p.setdefault(x["profondeur"], []).append(noms[x["id"]])
    for p in sorted(par_p, reverse=True):
        lignes.append("    " + " | ".join(par_p[p]))
    for e in ctx.carte["externes"]:
        if not e["imports"]:
            continue
        sources = [noms[x["id"]] for x in couches if x["id"] not in e["couches_autorisees"]]
        if not sources:
            continue
        lignes += ["", "[importlinter:contract:mcl-externe-%s]" % re.sub(r"\W+", "-", e["id"]),
                   "name = MCL - frontiere externe %s confinee a la couche d'infrastructure" % e["id"],
                   "type = forbidden", "source_modules ="]
        lignes += ["    %s" % s for s in sources]
        lignes.append("forbidden_modules =")
        lignes += ["    %s" % m for m in e["imports"]]
    return "\n".join(lignes) + "\n", ".importlinter"


def _regex_chemins(chemins):
    return "^(" + "|".join(re.escape(norm(c)) for c in chemins) + ")(/|$)"


def exporter_depcruise(ctx, args):
    couches = _couches_profondeur(ctx)
    sans = [x["id"] for x in couches if not x["chemins"]]
    if sans:
        raise ErreurMCL("couches sans 'chemins' : %s" % ", ".join(sans))
    regles = []
    for x in couches:
        externes_ = [y for y in couches if y["profondeur"] > x["profondeur"]]
        paralleles = [y for y in couches if y["profondeur"] == x["profondeur"] and y["id"] != x["id"]]
        if externes_:
            regles.append({"name": "mcl-invariant-%s" % x["id"], "severity": "error",
                           "comment": "Couche %s : aucune reference vers une couche plus externe" % x["id"],
                           "from": {"path": _regex_chemins(x["chemins"])},
                           "to": {"path": _regex_chemins([c for y in externes_ for c in y["chemins"]])}})
        if paralleles:
            regles.append({"name": "mcl-paralleles-%s" % x["id"], "severity": "error",
                           "comment": "Couches paralleles : aucune dependance mutuelle",
                           "from": {"path": _regex_chemins(x["chemins"])},
                           "to": {"path": _regex_chemins([c for y in paralleles for c in y["chemins"]])}})
    for e in ctx.carte["externes"]:
        interdites = [x for x in couches if x["id"] not in e["couches_autorisees"]]
        if e["imports"] and interdites:
            regles.append({"name": "mcl-externe-%s" % re.sub(r"\W+", "-", e["id"]), "severity": "error",
                           "comment": "Frontiere externe %s : implementation reelle uniquement en %s"
                                      % (e["id"], ", ".join(e["couches_autorisees"])),
                           "from": {"path": _regex_chemins([c for x in interdites for c in x["chemins"]])},
                           "to": {"path": "node_modules/(" + "|".join(re.escape(m) for m in e["imports"]) + ")/"}})
    regles.append({"name": "mcl-cycles", "severity": "error", "comment": "Detection de cycles",
                   "from": {}, "to": {"circular": True}})
    corps = json.dumps({"forbidden": regles, "options": {"doNotFollow": {"path": "node_modules"},
                                                         "tsPreCompilationDeps": True}},
                       ensure_ascii=False, indent=2)
    return ("/** Genere par mcl.py %s - carte des couches MCL (III.3). */\nmodule.exports = %s;\n"
            % (VERSION, corps)), ".dependency-cruiser.cjs"


def _ident(cid):
    return "C" + re.sub(r"\W", "_", cid)


def exporter_archunit(ctx, args):
    couches = _couches_profondeur(ctx)
    paquets = {x["id"]: (x["imports"][0] if x["imports"] else None) for x in couches}
    manquants = [c for c, p in paquets.items() if not p]
    if manquants:
        raise ErreurMCL("couches sans paquet Java ('imports') : %s" % ", ".join(manquants))
    if args.paquet_racine:
        racine = args.paquet_racine[0]
    else:
        parties = [p.split(".") for p in paquets.values()]
        commun = []
        for morceaux in zip(*parties):
            if len(set(morceaux)) != 1:
                break
            commun.append(morceaux[0])
        racine = ".".join(commun)
        if not racine:
            raise ErreurMCL("aucun paquet racine commun : preciser --paquet-racine")
    l = ["// Genere par mcl.py %s - carte des couches MCL (III.3)." % VERSION,
         "// Regle : dependances autorisees vers n'importe quelle couche plus interne, a profondeur quelconque.",
         "import com.tngtech.archunit.junit.AnalyzeClasses;",
         "import com.tngtech.archunit.junit.ArchTest;",
         "import com.tngtech.archunit.lang.ArchRule;",
         "",
         "import static com.tngtech.archunit.library.Architectures.layeredArchitecture;",
         "import static com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices;",
         "",
         '@AnalyzeClasses(packages = "%s")' % racine,
         "class MclCouchesTest {",
         "",
         "    @ArchTest",
         "    static final ArchRule invariant_mcl = layeredArchitecture()",
         "            .consideringOnlyDependenciesInLayers()"]
    for x in couches:
        l.append('            .layer("%s").definedBy("%s..")' % (_ident(x["id"]), paquets[x["id"]]))
    for x in couches:
        internes = [_ident(y["id"]) for y in couches if y["profondeur"] < x["profondeur"]]
        if internes:
            l.append('            .whereLayer("%s").mayOnlyAccessLayers(%s)'
                     % (_ident(x["id"]), ", ".join('"%s"' % i for i in internes)))
        else:
            l.append('            .whereLayer("%s").mayNotAccessAnyLayer()' % _ident(x["id"]))
    l[-1] += ";"
    l += ["",
          "    @ArchTest",
          '    static final ArchRule sans_cycles = slices().matching("%s.(*)..").should().beFreeOfCycles();'
          % racine]
    for e in ctx.carte["externes"]:
        interdites = [paquets[x["id"]] for x in couches if x["id"] not in e["couches_autorisees"]]
        if e["imports"] and interdites:
            l += ["",
                  "    @ArchTest",
                  "    static final ArchRule externe_%s = com.tngtech.archunit.lang.syntax.ArchRuleDefinition"
                  ".noClasses()" % re.sub(r"\W", "_", e["id"]),
                  "            .that().resideInAnyPackage(%s)" % ", ".join('"%s.."' % p for p in interdites),
                  "            .should().dependOnClassesThat().resideInAnyPackage(%s);"
                  % ", ".join('"%s.."' % m for m in e["imports"])]
    l.append("}")
    return "\n".join(l) + "\n", "MclCouchesTest.java"


def exporter_deptrac(ctx, args):
    couches = _couches_profondeur(ctx)
    sans = [x["id"] for x in couches if not x["chemins"]]
    if sans:
        raise ErreurMCL("couches sans 'chemins' : %s" % ", ".join(sans))
    l = ["# Genere par mcl.py %s - carte des couches MCL (III.3)." % VERSION, "deptrac:", "  paths:"]
    for s in ctx.carte["sources"]:
        l.append("    - ./%s" % norm(s) if norm(s) else "    - ./")
    l.append("  layers:")
    for x in couches:
        l += ["    - name: %s" % _ident(x["id"]), "      collectors:"]
        for c in x["chemins"]:
            l += ["        - type: directory", "          value: %s/.*" % norm(c)]
    l.append("  ruleset:")
    for x in couches:
        internes = [_ident(y["id"]) for y in couches if y["profondeur"] < x["profondeur"]]
        if internes:
            l.append("    %s:" % _ident(x["id"]))
            l += ["      - %s" % i for i in internes]
        else:
            l.append("    %s: ~" % _ident(x["id"]))
    return "\n".join(l) + "\n", "deptrac.yaml"


def exporter_netarchtest(ctx, args):
    couches = _couches_profondeur(ctx)
    ns = {x["id"]: (x["imports"][0] if x["imports"] else None) for x in couches}
    manquants = [c for c, p in ns.items() if not p]
    if manquants:
        raise ErreurMCL("couches sans namespace .NET ('imports') : %s" % ", ".join(manquants))
    ancre = args.ancre or "TypeAncre"
    l = ["// Genere par mcl.py %s - carte des couches MCL (III.3)." % VERSION,
         "// Remplacer %s par un type public de l'assembly analysee." % ancre,
         "using NetArchTest.Rules;", "using Xunit;", "", "public class MclCouchesTests", "{",
         "    private static readonly System.Reflection.Assembly Cible = typeof(%s).Assembly;" % ancre]
    for x in couches:
        interdits = [ns[y["id"]] for y in couches
                     if y["profondeur"] > x["profondeur"] or (y["profondeur"] == x["profondeur"] and y["id"] != x["id"])]
        if not interdits:
            continue
        l += ["", "    [Fact]", "    public void Couche_%s_ne_reference_ni_couche_externe_ni_parallele()"
              % re.sub(r"\W", "_", x["id"]), "    {",
              "        var resultat = Types.InAssembly(Cible)",
              '            .That().ResideInNamespace("%s")' % ns[x["id"]],
              "            .ShouldNot().HaveDependencyOnAny(%s)" % ", ".join('"%s"' % i for i in interdits),
              "            .GetResult();", "        Assert.True(resultat.IsSuccessful);", "    }"]
    l.append("}")
    return "\n".join(l) + "\n", "MclCouchesTests.cs"


EXPORTEURS = {
    "importlinter": exporter_importlinter,
    "depcruise": exporter_depcruise,
    "archunit": exporter_archunit,
    "deptrac": exporter_deptrac,
    "netarchtest": exporter_netarchtest,
}


def cmd_exporter(ctx, args):
    if not ctx.carte["couches"]:
        raise ErreurMCL("aucune couche declaree")
    contenu, nom = EXPORTEURS[args.outil](ctx, args)
    if args.sortie:
        chemin = os.path.join(ctx.racine, args.sortie)
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(contenu)
        print("Configuration %s ecrite : %s" % (args.outil, args.sortie))
    else:
        sys.stdout.write(contenu)
        sys.stderr.write("(nom de fichier usuel : %s)\n" % nom)
    return 0


# --------------------------------------------------------------------------- init

def cmd_init(ctx, args):
    if os.path.exists(ctx.chemin_carte) and not args.force:
        raise ErreurMCL("%s existe deja (--force pour ecraser la carte ; le journal n'est jamais ecrase)"
                        % ctx.chemin_carte)
    os.makedirs(os.path.join(ctx.dossier, "contrats"), exist_ok=True)
    carte = {
        "mcl": 1,
        "artefact": {"nom": args.nom, "echelle": args.echelle, "mode": args.mode, "description": ""},
        "langage": args.langage,
        "sources": args.sources or ["."],
        "exclure": [],
        "couches": [],
        "unites": [],
        "externes": [],
        "regles": dict(REGLES_DEFAUT),
        "checkpoint_tous_les": 2,
    }
    ecrire_json(ctx.chemin_carte, carte)
    if not os.path.exists(ctx.chemin_journal):
        open(ctx.chemin_journal, "a", encoding="utf-8").close()
    gabarits = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "gabarits")
    for nom, dest in (("PLAN-MCL.md", "PLAN-MCL.md"), ("contrat-couche.md", "contrats/_gabarit-contrat.md")):
        src = os.path.join(gabarits, nom)
        cible = os.path.join(ctx.dossier, dest)
        if os.path.exists(src) and not os.path.exists(cible):
            shutil.copyfile(src, cible)
    print("Dossier MCL initialise : %s (carte.json, journal.jsonl, contrats/, PLAN-MCL.md)." % ctx.dossier_rel)
    print("Suite : etapes 1 a 4 dans PLAN-MCL.md, unites dans carte.json, puis `mcl.py analyser`.")
    return 0


# --------------------------------------------------------------------------- CLI

def construire_parseur():
    p = argparse.ArgumentParser(prog="mcl.py", description="Outillage de la methode MCL "
                                "(Matryoshka Construction Layers).")
    p.add_argument("--racine", default=".", help="racine du projet (defaut : .)")
    p.add_argument("--dossier", default=DOSSIER_DEFAUT, help="dossier d'etat MCL relatif a la racine (defaut : mcl)")
    p.add_argument("--version", action="version", version="mcl.py " + VERSION)
    sp = p.add_subparsers(dest="commande", required=True)

    s = sp.add_parser("init", help="cree le dossier d'etat MCL")
    s.add_argument("--nom", default="artefact")
    s.add_argument("--langage", default=None, help="python, typescript, go, java, kotlin, csharp, php, dart, rust...")
    s.add_argument("--echelle", default="composant", choices=["tache", "tranche", "composant", "application"])
    s.add_argument("--mode", default="pur", choices=["pur", "composite"])
    s.add_argument("--sources", nargs="*", help="repertoires de code a analyser")
    s.add_argument("--force", action="store_true")
    s.set_defaults(f=cmd_init)

    s = sp.add_parser("analyser", help="DAG, cycles, profondeurs, paralleles, divergence")
    s.add_argument("--json", action="store_true")
    s.add_argument("--ecrire", action="store_true", help="ecrit les couches proposees si 'couches' est vide")
    s.set_defaults(f=cmd_analyser)

    s = sp.add_parser("exporter", help="configuration d'outil de test d'architecture")
    s.add_argument("--outil", required=True, choices=sorted(EXPORTEURS))
    s.add_argument("--sortie", help="fichier de sortie relatif a la racine (defaut : stdout)")
    s.add_argument("--paquet-racine", nargs="*", help="paquet(s) racine (importlinter, archunit)")
    s.add_argument("--ancre", help="type ancre de l'assembly (netarchtest)")
    s.set_defaults(f=cmd_exporter)

    s = sp.add_parser("verifier", help="controle du code reel contre la carte")
    s.add_argument("--mode", choices=["warn", "strict"], help="force le mode de toutes les regles")
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_verifier)

    s = sp.add_parser("rayon", help="consommateurs directs et transitifs")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--couche")
    g.add_argument("--unite")
    s.set_defaults(f=cmd_rayon)

    s = sp.add_parser("gate", help="regression gate journalise")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--couche")
    g.add_argument("--global", dest="global_", action="store_true")
    s.add_argument("--unitaire", help="commande des tests de categorie 1 de la couche courante")
    s.add_argument("--integration", help="commande des tests de categorie 2 (jonction sur le bloc reel)")
    s.add_argument("--regression", action="append", help="commande de la suite INTEGRALE (repetable)")
    s.set_defaults(f=cmd_gate)

    s = sp.add_parser("figer", help="gele le contrat d'une couche")
    s.add_argument("--couche", required=True)
    s.add_argument("--par", default=None)
    s.set_defaults(f=cmd_figer)

    s = sp.add_parser("defiger", help="leve formellement le gel d'une couche")
    s.add_argument("--couche", required=True)
    s.add_argument("--nature", required=True, choices=NATURES_DEFIGEAGE)
    s.add_argument("--motif", required=True)
    s.add_argument("--par", default=None)
    s.set_defaults(f=cmd_defiger)

    s = sp.add_parser("checkpoint", help="journalise un checkpoint de refactoring")
    s.add_argument("--notes", default="")
    s.add_argument("--par", default=None)
    s.set_defaults(f=cmd_checkpoint)

    s = sp.add_parser("baseline", help="baseline de dette a cliquet")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--creer", action="store_true")
    g.add_argument("--resserrer", action="store_true")
    g.add_argument("--reinitialiser", action="store_true")
    s.add_argument("--par")
    s.add_argument("--motif")
    s.set_defaults(f=cmd_baseline)

    s = sp.add_parser("statut", help="etat des couches et prochaines couches constructibles")
    s.set_defaults(f=cmd_statut)

    s = sp.add_parser("rapport", help="metriques issues des traces")
    s.set_defaults(f=cmd_rapport)
    return p


def main(argv=None):
    args = construire_parseur().parse_args(argv)
    ctx = Contexte(args.racine, args.dossier)
    try:
        return args.f(ctx, args)
    except ErreurMCL as e:
        sys.stderr.write("mcl.py : erreur : %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
