# A+ Premium — version française

Produit source : `B0FRG1MRQR` — cardigan/costume long à capuche pour homme, thème assassin, mythologie nordique et Halloween, coloris kaki.

## Livrables

- `desktop/` : 10 images en **1464 × 600 px**.
- `mobile_600x450/` : 10 compositions mobiles dédiées en **600 × 450 px**.
- `_preview/desktop-contact-sheet.jpg` : planche de contrôle desktop.
- `_preview/mobile-contact-sheet.jpg` : planche de contrôle mobile.
- `_generated_l89/` : six scènes recalibrées sur la longueur du L, soit 89 cm.
- `asset_manifest.csv` : correspondance module / format / fichier.
- `prompts.md` : prompts ImageGen utilisés pour les scènes de campagne.
- `research.md` : données source et parti pris créatif.
- `build_aplus.py` : script reproductible de composition et d'export.

## Les 7 modules

| Module | Format A+ | Titre principal | Fichiers |
|---|---|---|---|
| 1 | Premium Full Image | ENTREZ DANS LA LÉGENDE | `01-hero-*` |
| 2 | Premium Background Image with Text | LA NUIT SE PORTE EN DÉTAILS | `02-design-*` |
| 3 | Premium Full Image | TROIS MONDES. UNE MÊME PRÉSENCE. | `03-worlds-*` |
| 4 | Premium Simple Image Carousel | CHANGEZ DE DÉCOR, GARDEZ LE MYSTÈRE | `04-carousel-01..04-*` |
| 5 | Premium Full Image | DOUX. RESPIRANT. PRÊT POUR LA NUIT. | `05-comfort-*` |
| 6 | Premium Full Image | DU S AU 4XL, TROUVEZ VOTRE ALLURE | `06-fit-*` |
| 7 | Premium Full Image | GUIDE DES TAILLES — S À 4XL | `07-size-guide-*` |

Trois formats sont donc employés : **Premium Full Image**, **Premium Background Image with Text** et **Premium Simple Image Carousel**. Les six modules hors carrousel restent tous des visuels pleine largeur.

## Contrôle des allégations

Les textes se limitent aux informations visibles sur la fiche source : toucher doux, tissu respirant, matière tissée, coupe slim standard, usage automne/hiver, lavage en machine et tailles S à 4XL. Le dernier module reprend les mesures fournies dans `sources/size-chart-original.png`, avec les décimales adaptées à la typographie française. Aucun pourcentage de matière, niveau de chaleur ou promesse technique n'a été inventé.

Tous les visuels portés utilisent désormais le L comme référence : longueur vêtement 89 cm, corps principal à mi/bas de cuisse, environ 8 à 15 cm au-dessus du genou ; seul le point le plus long du pan asymétrique peut approcher le haut de la rotule.

## Reconstruction

Depuis la racine du dépôt :

```powershell
python nineTools/A_Plus/10.A_Plus/chiyuqi_de_261005/fr_premium_aplus/build_aplus.py
```
