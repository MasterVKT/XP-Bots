# Couche 3 — rapports C10, A11 London et A13

Unité : rapports ; dépendances 0a/0b/1c/1d/2 et noyau figés. Aucun accès physique,
aucun appel de modèle, aucune sélection de paramètres. Les entrées sont les
ResultatExperience réels du rejeu, les éventuelles références comparables V1,
des preuves de qualification externes explicitement identifiées et les bornes
descriptive du rapport. Les valeurs de seuil sont chargées, jamais ajustées.

produire_rapport(experiences, references_v1=None, preuves=None,
qualification_semantique=None) rend un rapport immuable composé de tableaux de
critères, métriques par expérience et ventilations. Le rapport conserve scénario,
bloc, méthodes actives, mode, provenance, empreintes et écarts de chaque entrée.
Une expérience autonome et un continu sont distincts ; aucune addition de leurs
courbes ou de leurs profits ne fabrique une courbe de compte. Les statistiques
des méthodes seules et du portefeuille combiné ne se mélangent pas.

Les sept mesures C09 restent nommées séparément. Chaque compte dispose de ses
mesures. La qualification exige la matrice développement/validation/réservé,
référence/stress, chaque méthode seule et combinées, puis les deux continus
combinés : un seul sous-ensemble satisfaisant ne valide pas le protocole C10.
Chaque compte dispose de ses
mesures globales ; les méthodes/symboles ont leurs effectifs, résultats nets,
espérances, PF, réussite et R moyen. Un drawdown partagé est celui du compte,
pas la somme des drawdowns par méthode. Les coûts IA originaux sont réconciliés
une fois ; allocation par méthode et dépenses de recherche restent explicites.
Les factures répétées entre référence/stress/voisinages ne sont pas additionnées
dans le bilan de projet. Les observations non réelles ne valent pas coût réel.

Critere(nom, observe, seuil, relation, statut, raison) donne SATISFAIT, ECHEC ou
NON_EVALUABLE. Effectifs totaux, réservés et par symbole, espérance validation et
réservé séparées, PF référence/stress, drawdown, rétention et fréquence Forex
combinée sont confrontés aux seuils de 0b. Une référence V1 absente donne N/A,
jamais zéro. Sous min_reference le ratio reste numérique mais TROP_FAIBLE.
Le ratio de configurations est séparé de la rétention des transactions.
Le bootstrap utilise le même panel journalier, jours à zéro compris, et les
paramètres de l'export ; les bornes et réplications invalides sont rendues.
Les deux bornes inférieures exigées par C10 sont strictement positives pour
démontrer l'amélioration économique sur le réservé ; aucun résultat exploratoire
ni synthétique ne remplit cette preuve. Le drawdown intrajournalier observé reste
distinct du drawdown journalier rééchantillonné.

rapport_a11(experience) ventile les trades London par tranches de largeur
normalisée W/ATR_H1, heure de première cassure du jour, direction, composante
contraignante du stop, jour de semaine et symbole. Les tranches descriptives de
ratio ont une largeur d'une unité et ne sont pas des critères de décision.
Coûts de marché par trade, coûts IA alloués par méthode, refus par motif/heure,
entrées/signaux et simultanéité de positions Forex sont exposés. Les premiers
signaux et les signaux nouveaux après veto viennent des journaux, pas d'une
reconstruction de prix. Le rapport distingue gagnants/perdants de référence
bloqués directement par un veto IA, opportunités après expiration du veto et
signaux devenus trop tardifs pour la fenêtre. Le retournement après première
cassure est descriptif ; aucune causalité LLM n'est attribuée aux exclusions C05
ou au stop technique. Une observation manquante est signalée, jamais inventée.

rapport_a13(experience_ab, qualification_semantique=None, preuves=None) compare
deux portefeuilles complets, pas une liste de pertes retirées après coup. Les
trades sont appariés par méthode/symbole/clôture/sens, sans confondre les clés de
bras. Les effectifs affectés, journées distinctes, rétentions par méthode/symbole,
résultats après coûts IA réels, drawdowns et gain net incrémental sont calculés.
Le bootstrap apparié donne les distributions de gain incrémental, différence
d'espérance et de drawdown journalier. Les critères A13 sont ceux de l'export.
La qualification sémantique utilise corpus humain identifié, effectif, précision
des événements matériels, rappel et citations non vérifiées ; sans ce jeu réel,
statut NON_QUALIFIE. Une précision de JSON n'est jamais un taux de réussite des
trades. Le protocole prospectif, les journaux archivés et la qualification C04
sont des preuves distinctes des performances calculées.

Le rapport des six perturbations conserve toutes les expériences, leurs pertes,
arrêts et métriques. Zéro voisinage n'est retenu comme nouveau réglage. Les coûts
de référence et de stress sont comparés entre eux ; la comparaison à des journaux
de démonstration réels reste PREUVE_MANQUANTE tant que ces journaux ne sont pas
fournis et qualifiés. L'effet du fondamental compare un contrôle technique neutre
nommé et des permissions réelles sur les mêmes données ; absence d'un de ces
deux cas donne NON_EVALUABLE. La garde de calendrier n'est pas attribuée à l'IA.

PreuvesValidation porte des identifiants SHA-256 de qualification C04, de gel du
robot et de journaux prospectifs archivés ; les preuves absentes restent None.
QualificationSemantique porte fournisseur, empreinte du corpus humain, nombre
de textes, précision, rappel et citations non vérifiées. Les métadonnées sont
contrôlées, mais les tests synthétiques ne certifient pas leur réalité externe.
Sans provenance réelle qualifiée, réservé ouvert sous gel attesté et critères
complets, le verdict financier demeure NON_VALIDE. Les rapports chiffrés utiles
restent disponibles ; les limites sont des champs structurés.

serialiser_rapport(rapport) rend du JSON déterministe UTF-8 avec dates ISO,
Decimal en textes exacts et nombres non finis refusés. Un export ne remplace pas
les enregistrements canoniques C09. Tests propres : cas calculés à la main,
limites exactes des critères, N/A et trop faible, données manquantes, allocations
sans double débit, synopsis de toutes les perturbations, catégories distinctes.
Jonctions : vrai London en rejeu/AB, métriques et bootstrap réels, paiements et
vetos archivés synthétiques, qualification jamais attribuée aux fixtures.

Signatures arrêtées à la finalisation :
comparer_routes(gratuite, payante, configuration, *, dossiers=None, prompt=None,
regles=None, provenance_masquee=False, attester=None) rend les écarts de précision
et de rappel A13 (fractions 0,02 et 0,05, bornes incluses). Les trois empreintes
identifient le corpus apparié, le prompt et les règles communs ; leur attestation
externe et le masquage à l'annotateur sont nécessaires. Sans ces preuves :
NON_EVALUABLE. Les qualifications individuelles restent nécessaires et une
non-différence observée ne prouve jamais une équivalence universelle.

PreuvesValidation(fiche_c04=None, gel_robot=None, journaux_demo=None,
reponses_archivees=None, verifier=None) exige des SHA-256 lorsque présents ;
verifier(nature, empreinte) est le port d'attestation externe et doit rendre
exactement True pour chaque preuve nécessaire. Un hash bien formé ne prouve pas
sa réalité. QualificationSemantique(fournisseur, empreinte_corpus, humain,
nombre_textes, precision, rappel, citations_non_verifiees) porte les résultats
observés ; les seuils restent dans la configuration chargée.

Les références V1 sont une table expérience-candidate → ResultatExperience de
référence. La comparaison exige prix/manifeste identiques, même intervalle de
mesure, mêmes conditions contractuelles datées, mêmes coûts et mêmes réceptions
C05 archivées. Une divergence donne NON_COMPARABLE et empêche le critère de
rétention ; les métriques descriptives restent disponibles. Une perturbation ne
sert jamais de référence V1 ou de nouveau réglage retenu.

ObservationCoutDemo(reference, nature, symbole, delai_ms, ticks_adverses,
spread_prix, commission_usd) représente une observation normalisée depuis un
journal qualifié. comparer_couts_demo(experience, observations, preuves=None)
rapporte effectifs, min/moyenne/max et hypothèses REFERENCE/STRESS ; sans preuve
et données, il rend PREUVE_MANQUANTE, pas une conformité de courtier.

rapporter_papier(nombre_ticks, enregistrements, instantanes, configuration)
sert à S7 : instantanes associe chaque bras à trades, courbe, premiers fills,
positions ouvertes et scénario, déjà reçus en mémoire. Il ne consulte aucun
compte ou backend. Il expose les métriques disponibles et l'absence éventuelle
de compteur de configurations dans une ancienne composition ; ce cas n'est pas
transformé en zéro. Le statut financier reste NON_VALIDE_FIXTURE. Le rapport
complet des sept mesures s'obtient avec produire_rapport sur ResultatExperience.
