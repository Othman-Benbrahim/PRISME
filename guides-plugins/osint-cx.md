# OSINT Cross-Reference — examiner des indices publics

[Retour aux guides](README.md)

## À quoi sert ce plugin ?

**OSINT** regroupe des recherches autour d'un identifiant et calcule un indice de
concordance. Il ne fait pas appel au modèle IA de PRISME. Le parcours d'audit porte
sur vos propres comptes, domaines ou organisation, ou sur un audit autorisé.

Un profil trouvé ne prouve pas son propriétaire. Une adresse IP ne donne pas une
adresse personnelle précise. Le score de concordance n'est pas une probabilité
calibrée et ne s'enregistre pas automatiquement dans [Calibration](calibration.md).

## Premier essai sans clé

1. Ouvrez **OSINT** et saisissez un pseudonyme de compte que vous contrôlez.
2. Choisissez **Pseudonyme**, ou laissez **Auto** si le format est sans ambiguïté.
3. Gardez **GitHub public** et **Score de corrélation** cochés ; laissez les modules
   à clé et les outils locaux décochés pour commencer.
4. Cliquez sur **Rechercher** et examinez chaque carte, son URL et son état.
5. Ouvrez les profils proposés. Vérifiez qu'il s'agit bien du compte recherché,
   pas simplement d'un compte portant le même pseudo.
6. Utilisez **Sauver comme .md** pour conserver le rapport dans le dossier courant.

Pour un domaine, sélectionnez **Domaine** et renseignez un domaine que vous gérez.
Si Auto se trompe, imposez le type. Le champ principal attend un identifiant ;
l'URL complète d'un profil LinkedIn dispose d'un champ séparé dans son module.

## Ce que les modules cherchent réellement

| Entrée ou module | Informations examinées | Prérequis |
|---|---|---|
| Pseudonyme | Présence possible sur différentes plateformes | Internet ; faux positifs possibles |
| Email | Format, Gravatar éventuel et domaine associé | Internet pour les recherches ; ne prouve pas que la boîte existe |
| Téléphone | Format et indicatif | Analyse de format ; pas d'identification du titulaire |
| IP | Type d'adresse, informations réseau et géolocalisation approximative si publique | Service réseau accessible |
| Domaine | DNS et informations RDAP disponibles | Réseau |
| GitHub public | Profil public | Pas de clé demandée par ce module |
| Wikidata | Entités publiques correspondant au terme | Pas de clé demandée |
| API Entreprises | Résultats d'entreprises correspondant au terme | Pas de clé demandée |
| Reddit public | Informations publiques du profil | Accès public pouvant être limité |
| Profil X API | Profil renvoyé par l'API X | Jeton et droits adaptés |
| LinkedIn via RapidAPI | Données renvoyées par le fournisseur choisi | Clé et configuration compatibles |
| Maigret/Sherlock local | Recherche de pseudos via un outil installé | Commande locale disponible ; ses recherches utilisent le réseau |

Ne cochez que les modules utiles. Leur présence dans le formulaire ne garantit
pas que vos droits d'accès, le service distant ou un outil local soient disponibles.

## Configurer les modules optionnels

Dans **Plugins → OSINT Cross-Reference → Secrets**, renseignez seulement les secrets
nécessaires :

| Module | Nom du secret |
|---|---|
| X | `X_BEARER_TOKEN` |
| LinkedIn via RapidAPI | `RAPIDAPI_KEY` |

Les URL et paramètres non secrets peuvent être placés dans
`plugins/osint-cx/.env`, puis pris en compte en relançant PRISME. Pour RapidAPI,
les réglages sont `LINKEDIN_RAPIDAPI_HOST`, `LINKEDIN_RAPIDAPI_ENDPOINT`,
`LINKEDIN_RAPIDAPI_METHOD` et `LINKEDIN_RAPIDAPI_PARAM`. Recopiez les valeurs de
**votre fournisseur** ; une clé seule ne suffit pas et les offres ne sont pas interchangeables.

Maigret et Sherlock ne sont pas fournis comme fonctions internes de PRISME. Dans
la version source, si vous choisissez de les installer dans votre environnement :

```powershell
python -m pip install maigret
# Ou, pour utiliser Sherlock :
python -m pip install sherlock-project
```

L'option **Maigret/Sherlock local** essaie les outils disponibles. Une installation
manquante doit être signalée ; PRISME ne lance pas lui-même une installation pip.
Le paramètre `OSINTCX_CLI_TIMEOUT`, en secondes, règle l'attente, par exemple
`OSINTCX_CLI_TIMEOUT=120` dans le fichier de configuration. L'intégration de ces
outils externes à la future distribution `.exe` reste à vérifier pendant E9.

## Lire le score sans le surinterpréter

Le calcul additionne des indices : présence sur plusieurs domaines, pseudo exact,
nom affiché, localisation, organisation ou site communs. L'interface détaille les
raisons et les points. Les seuils actuels du code sont :

| Score | Niveau affiché |
|---|---|
| 0 à 34 | faible |
| 35 à 64 | moyen |
| 65 à 100 | fort |

**80/100 ne signifie pas « 80 % de chances que ce soit la même personne ».** Les
sources peuvent se recopier ou partager des informations erronées. Un résultat
HTTP positif, un pseudo commun ou une ville identique demandent une vérification.

## Données et dépannage

Les identifiants et critères saisis sont envoyés aux sources interrogées. Les outils
« locaux » de recherche de pseudos contactent eux aussi des sites. Les résultats
sont affichés dans l'interface et certaines réponses sont conservées temporairement
en cache mémoire ; le rapport `.md` n'est créé qu'au clic de sauvegarde. Il porte
la provenance d'import, sans intervention de modèle.

| Symptôme | Que faire ? |
|---|---|
| Erreur de clé ou accès refusé | Vérifier le secret, les droits et les réglages du service concerné |
| CLI introuvable | Installer l'outil choisi dans l'environnement utilisé, puis relancer PRISME |
| Timeout | Réduire les modules ; ajuster le délai de l'outil local si nécessaire |
| Profil absent | Vérifier le pseudo et le service ; absence de résultat n'est pas preuve d'absence de compte |
| Données contradictoires | Conserver les divergences et les sources plutôt que conclure à partir du seul score |

**Test OSINT** aide à inspecter les capacités disponibles. **Repère de réussite :**
vous pouvez expliquer quels indices soutiennent le score et retrouver chacun dans
une source vérifiée manuellement.
