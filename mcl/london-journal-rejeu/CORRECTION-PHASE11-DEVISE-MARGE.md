# Devise de marge native du Forex dans le livre PAPER

P11-11 est révélé par le premier consommateur physique : le profil EURUSD
construit par SpecificationsMT5 annonce une marge en EUR et un profit en USD,
conformément aux champs natifs du faux SDK. Le constructeur C10 refusait toute
devise de marge différente de celle du compte, malgré sa formule qui convertit
déjà la marge en devise de base au prix d'entrée. Le livre PAPER ne pouvait donc
pas consommer ce profil C04 réel sans le déformer.

La correction conserve le profil et le SDK, et accepte cette déclaration pour
le mode FOREX. La marge USD demeure volume × taille du contrat × prix / levier.
Elle est confrontée au vrai CalculsMT5 composé sur le faux SDK, à l'achat et à la
vente. Les frais et la cotation restent en devise du compte ; les conversions
croisées et les autres modèles de marge ne sont pas déduits de cette exception.
La confrontation au terminal réel demeure S07, en 13.1.

Le contrat de 1b change : défigeage de nature modification, puis revalidation
des consommateurs 2 et 3 dans l'ordre et gate global. La construction du support
d'application 1a est suspendue pendant cette remontée ; ses tests de jonction
capturent le défaut sans modifier de fixture pour le masquer.
