#!/usr/bin/env python3
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pickle

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

def authenticate_gmail():
    """Authenticate with Gmail and save token"""

    creds = None

    # Check if token.json exists
    if os.path.exists('token.json'):
        print("token.json existe déjà. Utilisation du token existant...")
        with open('token.json', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Rafraîchissement du token...")
            creds.refresh(Request())
        else:
            print("Création d'un nouveau token...")
            print("Une fenêtre de navigateur va s'ouvrir pour vous authentifier.")
            print("Connectez-vous avec votre compte Gmail dédié.\n")

            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future use
        with open('token.json', 'wb') as token:
            pickle.dump(creds, token)
        print("✓ Token sauvegardé dans token.json")

    print("✓ Authentification réussie!")
    print(f"✓ Email: {creds.token}")
    return creds

if __name__ == '__main__':
    try:
        authenticate_gmail()
        print("\nConfiguration terminée!")
        print("Vous pouvez maintenant utiliser Gmail pour envoyer des mails.")
    except Exception as e:
        print(f"Erreur: {e}")
        sys.exit(1)
