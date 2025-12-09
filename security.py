# ==============================================================================
# GEN-CONTROL V1.1 - Module Sécurité (Compatible Streamlit Récent)
# Gestion Auth, IP (Nouvelle API) & Tokens
# ==============================================================================
import bcrypt
import pyotp
import jwt
import streamlit as st # Nécessaire pour la nouvelle méthode IP
from datetime import datetime, timedelta
from typing import Tuple, Optional

# Clé secrète pour signer les tokens
SECRET_KEY = "DI-SOLUTIONS-SUPER-SECRET-KEY-2025"

class EnhancedSecurityManager:
    def __init__(self, db_connection):
        self.db = db_connection

    # --- GESTION IP (MÉTHODE OFFICIELLE STREAMLIT) ---
    @staticmethod
    def get_remote_ip() -> str:
        """Récupère l'IP client via la nouvelle API st.context.headers"""
        try:
            # Cette méthode remplace l'ancien hack websocket
            if hasattr(st, "context") and hasattr(st.context, "headers"):
                headers = st.context.headers
                # X-Forwarded-For est présent si derrière un proxy (Cloud), sinon Host ou Remote-Addr
                return headers.get("X-Forwarded-For", "127.0.0.1").split(',')[0]
        except Exception:
            pass
        return "127.0.0.1" # Fallback local

    def check_signup_abuse(self, ip_address) -> bool:
        """Vérifie si cette IP a créé trop de comptes (>2 / 24h)"""
        try:
            query = """
                SELECT COUNT(*) as cnt FROM users 
                WHERE signup_ip = ? 
                AND created_at > datetime('now', '-1 day')
            """
            res = self.db.execute_read(query, (ip_address,))
            count = res[0]['cnt'] if res else 0
            return count >= 2
        except Exception as e:
            print(f"Erreur check abuse: {e}")
            return False

    # --- AUTHENTIFICATION ---
    def verify_password(self, username, password, ip_address) -> Tuple[bool, str]:
        """Vérifie le mot de passe hashé (Bcrypt)"""
        try:
            user_data = self.db.execute_read("SELECT password_hash FROM users WHERE username = ?", (username,))
            if not user_data: return False, "Utilisateur inconnu"
            
            stored_hash = user_data[0]['password_hash']
            
            # Gestion stricte des types bytes/str pour Bcrypt
            if isinstance(stored_hash, str): stored_hash = stored_hash.encode('utf-8')
            password_bytes = password.encode('utf-8')
            
            if bcrypt.checkpw(password_bytes, stored_hash): return True, "Connexion réussie"
            else: return False, "Mot de passe incorrect"
        except Exception as e: return False, f"Erreur technique: {str(e)}"

    def create_user(self, username, password, role='user', tier='DISCOVERY', ip='127.0.0.1'):
        """Crée un utilisateur avec hachage sécurisé"""
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            self.db.execute_write(
                "INSERT INTO users (username, password_hash, role, license_tier, signup_ip) VALUES (?, ?, ?, ?, ?)",
                (username, hashed, role, tier, ip)
            )
            return True, ""
        except Exception as e:
            return False, str(e)

    # --- SESSION & 2FA ---
    def is_2fa_enabled(self, username) -> bool:
        try:
            rows = self.db.execute_read("SELECT two_factor_secret FROM users WHERE username = ?", (username,))
            return bool(rows and rows[0]['two_factor_secret'])
        except: return False

    def verify_totp(self, username, token) -> bool:
        try:
            rows = self.db.execute_read("SELECT two_factor_secret FROM users WHERE username = ?", (username,))
            if rows and rows[0]['two_factor_secret']:
                return pyotp.TOTP(rows[0]['two_factor_secret']).verify(token)
            return False
        except: return False

    def create_session_token(self, username, ip_address) -> str:
        payload = {'sub': username, 'ip': ip_address, 'iat': datetime.utcnow(), 'exp': datetime.utcnow() + timedelta(hours=8)}
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    def validate_session(self, token) -> bool:
        try:
            jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            return True
        except: return False

    def logout(self, token): pass