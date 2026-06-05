# Agent IA de Prospection Commerciale 🤖

Agent Python 100% automatisé alimenté par **Explorium** (base de données B2B) + **Claude IA** + **Gmail**.

**Le flux:** Explorium cherche les entreprises → Claude génère 2 templates d'emails → Tu les valides une fois → L'agent envoie automatiquement → Surveille les réponses et relance après 5 jours (max 3 contacts).

---

## Prérequis

- Python 3.11+
- Clé API Anthropic (`sk-ant-...`)
- Clé API Explorium (base de données B2B)
- Compte Gmail
- Compte Google Cloud (pour OAuth2 Gmail)

---

## Installation

### 1. Cloner le projet

```bash
git clone <repo>
cd prospecting-agent
pip install -r requirements.txt
```

### 2. Configurer Google Cloud

1. Aller sur [console.cloud.google.com](https://console.cloud.google.com)
2. Créer un nouveau projet
3. Activer **Gmail API** et **Places API** (optionnel)
4. Créer des identifiants OAuth2 (application de bureau)
5. Télécharger `credentials.json` et le placer à la racine du projet

### 3. Configurer le fichier .env

```bash
cp .env.example .env
```

Remplir les valeurs dans `.env` :

```env
ANTHROPIC_API_KEY=sk-ant-...
GMAIL_SENDER_EMAIL=votre.email@gmail.com
MY_NAME=Votre Nom
MY_TITLE=Développeur Web Freelance
NOTIFICATION_EMAIL=votre.email@gmail.com
```

### 4. Lancer la configuration guidée

```bash
python main.py setup
```

Cette commande :
- Vérifie toutes les clés API
- Lance l'authentification OAuth2 Gmail (ouvre le navigateur)
- Initialise la base de données SQLite
- Envoie un email de test

---

## Utilisation

### Étape 1 : Configuration initiale

```bash
py main.py setup
```

Valide toutes les clés API et l'authentification Gmail.

### Étape 2 : Générer les 2 templates d'email (UNE SEULE FOIS)

```bash
py main.py validate-templates
```

Claude génère 2 templates :
- Template 1 : pour entreprises **SANS SITE WEB**
- Template 2 : pour entreprises avec **SITE MÉDIOCRE**

Tu les lis et tu valides. Ensuite c'est stocké et l'agent les utilise pour tous les envois futurs.

### Étape 3 : Lancer les recherches Explorium

```bash
# Avec les secteurs par défaut (.env)
py main.py prospect

# Secteurs personnalisés
py main.py prospect --sectors "restaurant,plombier,coiffeur" --max-results 200

# Aperçu sans sauvegarder
py main.py prospect --dry-run
```

Résultat : prospects sauvegardés en base (SQLite).

### Étape 4 : Envoyer les emails (avant de lancer l'agent)

```bash
# Envoyer aux 20 premiers prospects
py main.py send-emails --limit 20

# L'agent choisira automatiquement le bon template selon le site
```

### Étape 5 : Lancer l'agent automatique (24/7)

```bash
py main.py start-agent
```

L'agent tourne en arrière-plan et :
- **Envoie** les relances (lun-ven 8h-18h, après 5 jours sans réponse)
- **Surveille** les réponses (toutes les 30 min)
- **Notifie** quand quelqu'un répond
- **Désinscrit** automatiquement ceux qui répondent "Stop"
- **Limite** à 3 contacts max par prospect

### Tableau de bord

```bash
py main.py status
```

### Gérer les prospects

```bash
# Lister les contactés
py main.py list-prospects --status contacted

# Lister par secteur / ville
py main.py list-prospects --city Paris --limit 50
```

---

## Architecture

```
prospecting-agent/
├── main.py                           # CLI (Click)
├── config.py                         # Variables d'environnement
├── database/
│   ├── models.py                     # Modèles SQLAlchemy
│   └── crud.py                       # Fonctions CRUD
├── prospecting/
│   ├── explorium_client.py           # API Explorium (cherche + enrichit)
│   └── website_analyzer.py           # Score le site web (0-100)
├── email_agent/
│   ├── gmail_client.py               # Gmail OAuth2
│   ├── email_writer.py               # Génération templates + personnalisation
│   ├── email_templates.py            # Stockage des templates validés
│   ├── sender.py                     # Envoi + suivi
│   └── reply_monitor.py              # Surveillance réponses
├── scheduler/
│   └── follow_up_scheduler.py        # APScheduler (relances auto)
└── notifications/
    └── notifier.py                   # Ntfy.sh + Pushover + Gmail
```

**Flux complet :**
```
1. Explorium API
   └─ Cherche entreprises par secteur
   └─ Récupère emails des décideurs
   └─ Retourne : nom, domain, email

2. Website Analyzer
   └─ Score le domain (0-100)
   └─ Détecte problèmes (pas HTTPS, design vieux, etc.)

3. Email Templates (Claude IA)
   └─ Génère 2 templates UNE FOIS (tu valides)
   └─ Template 1 : pas de site web
   └─ Template 2 : site médiocre

4. Sender (Gmail)
   └─ Choisit bon template selon le site
   └─ Personnalise avec le nom de l'entreprise
   └─ Envoie via Gmail

5. Reply Monitor (24/7 auto)
   └─ Reçoit une réponse ? → Notification
   └─ Pas de réponse après 5j ? → Relance auto
   └─ Répond "Stop" ? → Désinscription auto
```

---

## Scoring des sites web

| Score | Signification | Template utilisé |
|-------|--------------|-------------------|
| 0 | Aucun site web | Template 1 (pas de site) |
| 1-50 | Site très médiocre | Template 2 (site à refaire) |
| 51-65 | Site médiocre | Template 2 (site à refaire) |
| > 65 | Site correct | Ignoré ❌ |

**Critera d'analyse :**
- Pas HTTPS → -20 pts
- Pas responsive → -15 pts
- Load time > 3s → -15 pts
- Design vieux (copyright > 3 ans) → -10 pts
- Pas Google Analytics → -5 pts
- Flash / obsolète → -10 pts

## Workflow automatique

```
JOUR 1 — Envoi initial
  ├─ L'agent prend les 50 premiers prospects "new"
  ├─ Choisit le bon template (selon site)
  ├─ Envoie via Gmail
  └─ Marque : "contacted", planifie relance J6

JOUR 6 — Relance automatique
  ├─ Récupère prospects avec "contacted" + next_follow_up ≤ aujourd'hui
  ├─ Renvoie avec template 2 (plus direct)
  └─ Marque : contact_count + 1, planifie relance J11

JOUR 11 — Dernier envoi
  ├─ Vérifie contact_count < 3
  ├─ Dernier mail plus court
  └─ Contact_count = 3 → "unsubscribed" (stop les futures relances)

24/7 — Monitoring
  ├─ Réponse reçue ? → status "replied" + notification
  ├─ "Stop" détecté ? → status "unsubscribed" (respect RGPD)
  └─ Pas de réponse ? → Relance auto le jour prévu
```

---

## Troubleshooting

### Erreur OAuth2 Gmail
```
Error 400: redirect_uri_mismatch
```
→ Dans Google Cloud Console, ajouter `http://localhost` aux URIs de redirection autorisées.

### Rate limit Gmail
L'agent attend automatiquement 60 secondes entre chaque email. La limite est configurable avec `DAILY_EMAIL_SEND_LIMIT` dans `.env`.

### "No module named 'lxml'"
```bash
pip install lxml
```

### Erreur `credentials.json` introuvable
Télécharger le fichier depuis Google Cloud Console → APIs & Services → Credentials → votre client OAuth2 → Download JSON. Le renommer en `credentials.json`.

### DuckDuckGo retourne peu de résultats
C'est normal, DuckDuckGo est le fallback gratuit. Pour de meilleurs résultats, configurer `GOOGLE_PLACES_API_KEY`.

### L'agent ne trouve pas d'emails
Ajouter une clé `HUNTER_IO_API_KEY` dans `.env` pour améliorer la détection.

---

## RGPD

Cet agent collecte uniquement des données professionnelles publiquement disponibles :
- Nom de l'entreprise
- Email professionnel
- Site web
- Adresse professionnelle

Chaque email inclut une option de désinscription ("répondez Stop"). Les prospects ayant répondu "Stop" sont automatiquement marqués `unsubscribed` et ne reçoivent plus de contacts.
