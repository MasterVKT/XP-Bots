# Couche 1 — session MT5 injectée

Statut : finalisé le 10/11/2026 avant code ; dépend de 0a gelée et de pathlib/os.
Signature : SessionMT5(sdk,mode,*,chemin_terminal=None,common_files_attendu=None),
attacher() -> EtatSession, actualiser() -> EtatSession, appeler(nom,*args,**kw),
fermer(). EtatSession(version_paquet,version_terminal,build,connecte,droits,
common_files,alertes). Propriétés publiques sdk, mode, etat, attachee.

Seul attacher appelle initialize, sans login/password/server ; le chemin du
terminal explicite peut être passé. Version paquet strictement 5.0.6231.
Mode DEMO exige ACCOUNT_TRADE_MODE_DEMO, REEL exige ACCOUNT_TRADE_MODE_REAL.
PAPER/PAPER_AB sont en lecture côté SDK ; ni identifiant ni numéro de compte
ne sont renvoyés dans EtatSession. Démarrage connecté et droits natifs requis
pour DEMO/REEL. actualiser signale ensuite connexion/droits dégradés ; aucune
entrée ne peut contourner la nouvelle qualification de l’enveloppe courtier.

Le dossier des échanges est exactement Path(commondata_path)/Files, racine
FILE_COMMON : ce suffixe est vérifié dans la documentation officielle MQL5.
Aucun chemin n’est construit depuis un nom d’utilisateur. Une variable attendue
différente produit l’alerte déterministe COMMON_FILES_DIFFERENT ; l’absence d’IA
est gérée NEUTRAL par le vrai lecteur, sans altérer les gardes C05.

appeler accepte seulement les fonctions natives utilisées, jamais login,
copy_rates_* ni aides Buy/Sell/Close. None déclenche un seul last_error, seul son
code est conservé dans ErreurNative ; aucune chaîne native sensible n’est exposée.
Un tableau vide ou un scalaire zéro n’est jamais assimilé à None.
Échec d’attachement après initialize réussi -> shutdown et état fermé ; fermer
est idempotent. Aucune lecture de .env, import du SDK ou appel réseau ici.

Tests Cat1 : faux SDK et chemins temporaires, versions, modes, droits, None,
last_error, fermeture et racine Common/Files. Cat2 : vraies conversions 0a et
structures du faux SDK ; contrat réel démo activé seulement en 13.1.
