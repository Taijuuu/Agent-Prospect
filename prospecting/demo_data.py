DEMO_PROSPECTS = [
    {
        "company_name": "Restaurant Le Petit Bistro",
        "industry": "Restaurants",
        "address": "42 Rue de la Paix, 75000 Paris",
        "city": "Paris",
        "phone": "01 23 45 67 89",
        "email": "contact@lepetitbistro.fr",
        "domain": None,
        "website_score": 0,
        "website_issues": ["Aucun site web"]
    },
    {
        "company_name": "Coiffeur Beauté & Style",
        "industry": "Salons de coiffure",
        "address": "128 Boulevard Saint-Germain, 75006 Paris",
        "city": "Paris",
        "phone": "01 44 07 12 34",
        "email": "info@beautystyle.fr",
        "domain": "https://beautystyle.fr",
        "website_score": 45,
        "website_issues": ["Design vieillot (2014)", "Pas responsive", "Lent au chargement"]
    },
    {
        "company_name": "Plomberie Dupont SARL",
        "industry": "Plombiers",
        "address": "65 Avenue Foch, 75016 Paris",
        "city": "Paris",
        "phone": "06 12 34 56 78",
        "email": "contact@plomberiedupont.fr",
        "domain": None,
        "website_score": 0,
        "website_issues": ["Aucun site web"]
    },
    {
        "company_name": "Électricité Martin & Fils",
        "industry": "Électriciens",
        "address": "19 Rue de Rivoli, 75004 Paris",
        "city": "Paris",
        "phone": "01 42 61 53 53",
        "email": "info@electricitemartin.fr",
        "domain": "http://electricite-martin.com",
        "website_score": 50,
        "website_issues": ["Pas SSL/HTTPS", "Pas Google Analytics"]
    },
    {
        "company_name": "Boulangerie Pains Dorés",
        "industry": "Boulangeries",
        "address": "7 Rue Mouffetard, 75005 Paris",
        "city": "Paris",
        "phone": "01 47 07 32 24",
        "email": "bonjour@painsdores.fr",
        "domain": None,
        "website_score": 0,
        "website_issues": ["Aucun site web"]
    },
    {
        "company_name": "Restaurant La Marée",
        "industry": "Restaurants",
        "address": "93 Rue de Turenne, 75003 Paris",
        "city": "Paris",
        "phone": "01 42 78 99 45",
        "email": "reservations@lamaree.fr",
        "domain": "https://lamaree-old.com",
        "website_score": 25,
        "website_issues": ["Design obsolète (2008)", "Flash", "Pas mobile-friendly"]
    },
]


def generate_demo_prospects(max_results: int = 6) -> list:
    return DEMO_PROSPECTS[:max_results]
