import streamlit as st
import pandas as pd
from datetime import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database.models import init_db, ProspectStatus
from database.crud import get_prospects, get_stats, create_prospect, prospect_exists
from sqlalchemy.orm import sessionmaker
from database.models import get_engine
import json

st.set_page_config(
    page_title="Agent de Prospection IA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

def get_db():
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

st.title("🤖 Agent de Prospection IA")
st.markdown("---")

db = get_db()
stats = get_stats(db)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📊 Total Prospects", stats.get("total", 0))
with col2:
    st.metric("✨ Nouveaux", stats.get("by_status", {}).get("new", 0))
with col3:
    st.metric("📧 Contactés", stats.get("by_status", {}).get("contacted", 0))
with col4:
    st.metric("💬 Réponses", stats.get("by_status", {}).get("replied", 0))

st.markdown("---")

tabs = st.tabs([
    "📋 Prospects",
    "📥 Importer CSV",
    "✉️ Templates Email",
    "📤 Envoyer Emails",
    "📊 Exporter",
    "⚙️ Paramètres"
])

with tabs[0]:
    st.header("📋 Liste des Prospects")

    col1, col2 = st.columns([1, 1])

    with col1:
        filter_status = st.selectbox(
            "Filtrer par statut",
            ["Tous", "new", "contacted", "replied", "converted", "unsubscribed"]
        )

    with col2:
        filter_city = st.text_input("Filtrer par ville (optionnel)", "")

    status_filter = None if filter_status == "Tous" else ProspectStatus(filter_status)
    prospects = get_prospects(db, status=status_filter, city=filter_city if filter_city else None, limit=1000)

    if prospects:
        df = pd.DataFrame([
            {
                "ID": p.id,
                "Entreprise": p.company_name,
                "Email": p.email or "—",
                "Téléphone": p.phone or "—",
                "Secteur": p.industry or "—",
                "Ville": p.city or "—",
                "Score Site": p.website_score or 0,
                "Statut": p.status.value if p.status else "—",
                "Créé": p.created_at.strftime("%d/%m/%Y") if p.created_at else "—"
            }
            for p in prospects
        ])

        st.dataframe(df, use_container_width=True, height=400)
        st.caption(f"✅ {len(prospects)} prospects affichés")
    else:
        st.info("Aucun prospect trouvé.")

with tabs[1]:
    st.header("📥 Importer des Prospects")
    st.write("Exporte une liste de Vibe Prospecting en CSV, puis importe-la ici.")

    uploaded_file = st.file_uploader("Choisir un fichier CSV", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("**Aperçu du fichier :**")
        st.dataframe(df.head(5))

        if st.button("Importer les prospects"):
            imported = 0
            skipped = 0

            for _, row in df.iterrows():
                company_name = str(row.get("Entreprise", "")).strip()
                city = str(row.get("Ville", "")).strip()

                if not company_name:
                    skipped += 1
                    continue

                if prospect_exists(db, company_name, city):
                    skipped += 1
                    continue

                prospect_data = {
                    "company_name": company_name,
                    "industry": str(row.get("Secteur", "")).strip() or "",
                    "address": str(row.get("Adresse", "")).strip() or "",
                    "city": city,
                    "phone": str(row.get("Téléphone", "")).strip() or "",
                    "email": str(row.get("Email", "")).strip() or "",
                    "website_url": str(row.get("Site web", "")).strip() or "",
                    "website_score": int(row.get("Score", 0)) if "Score" in row else 0,
                    "website_issues": json.dumps([]),
                    "source": "import_csv",
                    "status": ProspectStatus.new
                }

                create_prospect(db, prospect_data)
                imported += 1

            st.success(f"✅ {imported} prospects importés ! ({skipped} ignorés)")

with tabs[2]:
    st.header("✉️ Templates d'Email")

    from email_agent.email_templates import list_all_templates
    templates = list_all_templates(db)

    if templates:
        st.write("**Templates actuels :**")
        for t in templates:
            st.subheader(f"Template: {t['type']}")
            st.write(f"**Objet:** {t['subject']}")
            st.text_area(f"**Corps:**", value=t['body'], height=150, disabled=True, key=f"template_{t['id']}")
    else:
        st.info("Aucun template. Valide les templates pour en créer.")

    if st.button("🔄 Régénérer templates avec Claude"):
        from email_agent.email_writer import generate_email_templates
        st.write("Génération en cours...")
        try:
            templates_data = generate_email_templates()
            st.success("✅ Templates générés !")
            st.json(templates_data)
        except Exception as e:
            st.error(f"❌ Erreur: {e}")

with tabs[3]:
    st.header("📤 Envoyer les Emails")

    col1, col2 = st.columns([1, 1])

    with col1:
        limit = st.number_input("Nombre d'emails à envoyer", min_value=1, max_value=100, value=5)

    with col2:
        dry_run = st.checkbox("Aperçu seulement (dry-run)", value=True)

    if st.button("📨 Envoyer les emails"):
        st.write("Envoi en cours...")

        from email_agent.sender import send_prospecting_email
        prospects_to_send = get_prospects(db, status=ProspectStatus.new, limit=limit)

        sent = 0
        for p in prospects_to_send:
            if not p.email:
                st.warning(f"⚠️ Pas d'email pour {p.company_name}")
                continue

            if not dry_run:
                try:
                    if send_prospecting_email(db, p.id):
                        sent += 1
                        st.success(f"✅ {p.company_name} ({p.email})")
                    else:
                        st.error(f"❌ Erreur: {p.company_name}")
                except Exception as e:
                    st.error(f"❌ {p.company_name}: {e}")
            else:
                st.info(f"[DRY-RUN] Enverrait à {p.company_name} <{p.email}>")

        if not dry_run:
            st.success(f"✅ {sent} emails envoyés !")

with tabs[4]:
    st.header("📊 Exporter les Prospects")

    col1, col2 = st.columns([1, 1])

    with col1:
        export_format = st.selectbox("Format d'export", ["Excel", "CSV"])

    with col2:
        export_status = st.selectbox("Exporter", ["Tous", "new", "contacted", "replied"])

    if st.button("📥 Générer l'export"):
        status_filter = None if export_status == "Tous" else ProspectStatus(export_status)
        prospects = get_prospects(db, status=status_filter, limit=10000)

        if prospects:
            df = pd.DataFrame([
                {
                    "ID": p.id,
                    "Entreprise": p.company_name,
                    "Email": p.email or "",
                    "Téléphone": p.phone or "",
                    "Secteur": p.industry or "",
                    "Adresse": p.address or "",
                    "Ville": p.city or "",
                    "Score Site": p.website_score or 0,
                    "Statut": p.status.value if p.status else "",
                    "Date Création": p.created_at.strftime("%d/%m/%Y") if p.created_at else ""
                }
                for p in prospects
            ])

            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

            if export_format == "Excel":
                try:
                    filename = f"prospects_{timestamp}.xlsx"
                    df.to_excel(filename, index=False)

                    with open(filename, "rb") as f:
                        st.download_button(
                            label="📥 Télécharger Excel",
                            data=f.read(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    st.success(f"✅ {len(prospects)} prospects prêts à télécharger")
                except Exception as e:
                    st.error(f"Erreur: {e}")
            else:
                filename = f"prospects_{timestamp}.csv"
                csv = df.to_csv(index=False, encoding="utf-8")
                st.download_button(
                    label="📥 Télécharger CSV",
                    data=csv,
                    file_name=filename,
                    mime="text/csv"
                )
                st.success(f"✅ {len(prospects)} prospects prêts à télécharger")
        else:
            st.info("Aucun prospect à exporter.")

with tabs[5]:
    st.header("⚙️ Paramètres")

    st.write("### Information de l'agent")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Version", "1.0.0")
    with col2:
        st.metric("Base de données", "SQLite (prospects.db)")
    with col3:
        st.metric("État", "✅ Opérationnel")

    st.write("### Configuration")

    from config import (
        ANTHROPIC_API_KEY, EXPLORIUM_API_KEY, GMAIL_SENDER_EMAIL,
        MY_NAME, MY_TITLE, FOLLOW_UP_DELAY_DAYS, MAX_CONTACTS_PER_PROSPECT
    )

    config_data = {
        "🔑 Anthropic API": "✅ Configuré" if ANTHROPIC_API_KEY else "❌ Non configuré",
        "🔑 Explorium API": "✅ Configuré" if EXPLORIUM_API_KEY else "❌ Non configuré",
        "📧 Email expéditeur": GMAIL_SENDER_EMAIL or "Non configuré",
        "👤 Nom": MY_NAME or "Non configuré",
        "💼 Titre": MY_TITLE or "Non configuré",
        "⏱️ Délai relance (jours)": FOLLOW_UP_DELAY_DAYS,
        "📞 Max contacts par prospect": MAX_CONTACTS_PER_PROSPECT,
    }

    for key, value in config_data.items():
        st.write(f"**{key}:** {value}")

    st.info("📝 Pour modifier la configuration, édite le fichier `.env`")

db.close()

st.markdown("---")
st.caption("🤖 Agent de Prospection IA | Développé avec Claude + Streamlit")
