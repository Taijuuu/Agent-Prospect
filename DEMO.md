# 🎮 Mode Démo — Test l'agent SANS frais

**L'agent est 100% fonctionnel en mode démo.** Tu peux tester tous les flux sans payer pour :
- Explorium (BDD d'entreprises)
- Anthropic API (Claude)

---

## ⚡ Quickstart Démo (3 minutes)

### 1. Charger les 6 prospects de démo

```powershell
py main.py prospect --demo
```

✅ 6 restaurants, coiffeurs, plombiers fictifs sont ajoutés en base.

### 2. Voir la liste

```powershell
py main.py list-prospects
```

Tu vois les 6 prospects avec leurs scores de site (0, 25, 45, 50).

### 3. Générer et valider les 2 templates d'email

```powershell
py main.py validate-templates --demo
```

Les 2 templates (pas de site / site médiocre) sont affichés et validés automatiquement.

### 4. Voir les emails à envoyer (aperçu)

```powershell
py main.py send-emails --limit 3 --dry-run
```

Montre exactement quels emails seraient envoyés, avec les données personnalisées.

### 5. Lancer l'agent en monitoring

```powershell
py main.py start-agent
```

L'agent attend les réponses et monitore les relances (sur les faux emails de démo, rien ne se passera, mais le code fonctionne).

---

## 📊 Ce que tu peux tester en démo

✅ **Recherche et filtrage** → `prospect --demo`
✅ **Scoring des sites** → scores de 0 à 50
✅ **Gestion de templates** → `validate-templates --demo`
✅ **Workflow d'envoi** → `send-emails --dry-run`
✅ **Statut et monitoring** → `status`, `list-prospects`
✅ **Planification des relances** → APScheduler configuré et prêt

❌ **Véritables emails** → pas d'envoi réel (données fictives)
❌ **Vraies entreprises** → données de démo seulement

---

## 🚀 Passer de la démo au production

### Étape 1 — Payer les crédits

- **Anthropic** → https://console.anthropic.com (Plans & Billing) — quelques euros
- **Explorium** → https://www.vibeprospecting.ai — checkouts crédits par usage

### Étape 2 — Enlever les flags `--demo`

```powershell
# De démo
py main.py prospect --demo

# À production
py main.py prospect
```

L'agent bascule automatiquement sur :
- Explorium pour la recherche réelle
- Claude API pour générer les emails
- Gmail pour envoyer les vrais emails

---

## 📝 Données de démo incluses

**6 prospects fictifs :**
1. Restaurant Le Petit Bistro (pas de site) → score 0
2. Coiffeur Beauté & Style (site médiocre) → score 45
3. Plomberie Dupont (pas de site) → score 0
4. Électricité Martin & Fils (site mauvais) → score 50
5. Boulangerie Pains Dorés (pas de site) → score 0
6. Restaurant La Marée (site obsolète) → score 25

**2 templates d'email prédéfinis :**
- Template "pas de site" → accent sur l'importance du web
- Template "site médiocre" → focus sur les points d'amélioration

---

## 🔧 Limitations de la démo

| Aspect | Démo | Production |
|--------|------|------------|
| Nombre prospects | 6 | Illimité (Explorium) |
| Templates | 2 pré-générés | Générés par Claude (IA) |
| Emails envoyés | 0 (simulation) | Vrais envois Gmail |
| Suivi réponses | Simulation | Réponses Gmail réelles |
| Coût | Gratuit | API + crédits |

---

## 💡 Idée : tester avec tes vrais emails

Si tu veux tester les vrais envois SANS Explorium, tu peux :

1. Éditer `prospecting/demo_data.py`
2. Remplacer les emails fictifs par TES emails de test
3. Lancer `py main.py prospect --demo`
4. Puis `py main.py send-emails` (vrais envois à TOI-MÊME)

Comme ça tu vois le flux complet : générer → envoyer → recevoir → relancer.

---

**Besoin d'aide ?** Regarde le `QUICKSTART.md` pour la config complète.
