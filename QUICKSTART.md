# Quickstart — 5 minutes ⚡

## Avant de commencer

Tu as besoin de :
1. **Clé Anthropic** (`sk-ant-...`) → https://console.anthropic.com/keys
2. **Clé Explorium** (`40b63d63-...`) ✓ Déjà dans le `.env`
3. **`credentials.json`** (Google OAuth2 Gmail) → voir [setup complet](#setup-complet)

---

## MAINTENANT (5 min)

### 1️⃣ Ajouter ta clé Anthropic au `.env`

Ouvre `C:\Users\FRGLUTID\prospecting-agent\.env`

```env
ANTHROPIC_API_KEY=sk-ant-... # ← Colle ta clé ici
```

Sauvegarde.

### 2️⃣ Lancer la config

```powershell
cd C:\Users\FRGLUTID\prospecting-agent
py main.py setup
```

- ✓ Vérifie tes clés
- ✓ Lance l'auth Gmail (ouvre ton navigateur)
- ✓ Initialise la BDD

### 3️⃣ Générer et valider les templates (UNE SEULE FOIS)

```powershell
py main.py validate-templates
```

Claude génère 2 templates d'email. Tu les lis et tu dis "oui" si ça te plaît.

### 4️⃣ Chercher des prospects

```powershell
py main.py prospect --sectors "restaurant,plombier" --max-results 50
```

Les prospects sont sauvegardés dans `prospects.db`.

### 5️⃣ Envoyer les emails

```powershell
py main.py send-emails --limit 20
```

L'agent choisit automatiquement le bon template selon le site de chaque entreprise et envoie.

---

## MAINTENANT, LAISSE TOURNER

```powershell
py main.py start-agent
```

L'agent tourne 24/7 et :
- Surveille les réponses
- Relance après 5 jours (max 3 fois)
- Te notifie quand quelqu'un répond
- Respecte les désinscriptions ("Stop")

---

## Commandes utiles

```powershell
py main.py status                # Tableau de bord
py main.py list-prospects       # Voir tous les prospects
py main.py prospect --dry-run   # Tester une recherche
```

---

## Setup complet (si auth Gmail échoue)

1. Aller sur https://console.cloud.google.com
2. Créer un **nouveau projet**
3. Activer **Gmail API**
4. **Credentials** → **OAuth2 Client ID** → **Desktop app**
5. **Download JSON** → Renommer en `credentials.json`
6. Placer dans `C:\Users\FRGLUTID\prospecting-agent\`

Puis relancer `py main.py setup`.

---

**C'est tout.** L'agent fait le reste. 🚀
