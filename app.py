# ==============================================================================
# GEN-CONTROL V1.1.4 - PATCH FINAL (ANTI-COUPURE)
# ==============================================================================
import streamlit as st
import os
import time
from datetime import datetime
import uuid
import urllib.parse

# Imports des modules
from database import ThreadSafeDatabase
from security import EnhancedSecurityManager
from physics import IsoWillansModel, ReferenceEngineLibrary, AtmosphericParams
from analytics import DetailedLoadFactorManager, IntelligentAnomalyDetector, AdaptiveLearningEngine
from reports import PDFReportGenerator
from payments import render_payment_page

st.set_page_config(page_title="GEN-CONTROL V1.1", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- CSS ---
st.markdown("""
<style>
    .main-header { font-size: 1.5rem; font-weight: bold; color: #003366; margin-bottom: 1rem; border-bottom: 2px solid #FF4B4B; padding-bottom: 5px; }
    .verdict-box { padding: 15px; border-radius: 8px; text-align: center; margin: 10px 0; font-weight: bold; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .share-btn { display: inline-block; background-color: #25D366; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: bold; margin-top: 10px; text-align: center; width: 100%; }
    .maintenance-alert { background-color: #e3f2fd; border-left: 5px solid #2196f3; padding: 10px; border-radius: 5px; color: #0d47a1; font-size: 0.9em; margin-top: 10px;}
    .tech-card { background-color: #f8f9fa; padding: 15px; border-radius: 5px; border: 1px solid #b0b0b0; font-size: 0.9em; margin-bottom: 15px; color: #333; }
    .license-warning { background-color: #ffeeba; color: #856404; padding: 10px; border-radius: 5px; border: 1px solid #ffeeba; margin-bottom: 15px;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db(): return ThreadSafeDatabase.get_instance()

def init_session():
    if 'db' not in st.session_state: st.session_state.db = get_db()
    if 'security' not in st.session_state: st.session_state.security = EnhancedSecurityManager(st.session_state.db)
    if 'analytics' not in st.session_state: 
        st.session_state.detector = IntelligentAnomalyDetector()
        st.session_state.learning = AdaptiveLearningEngine()
        st.session_state.pdf_gen = PDFReportGenerator()

# --- FONCTION SIDEBAR SÉCURISÉE ---
def render_sidebar():
    if 'auth_token' not in st.session_state:
        return None

    with st.sidebar:
        st.title("GEN-CONTROL")
        st.caption("V1.1.2 (Final)")
        
        tier = st.session_state.get('license_tier', 'DISCOVERY')
        user = st.session_state.get('user', 'Utilisateur')
        st.info(f"👤 {user}\n🏷️ Licence : {tier}")
        
        opts = ["📱 Audit Terrain", "🎯 Calibration"]
        if tier == 'DISCOVERY': opts.append("💎 Devenir PRO")
        if tier in ['PRO', 'CORPORATE']: opts.append("🧠 Intelligence")
        if st.session_state.get('role') == 'admin': opts.append("🔐 Admin")
        
        menu = st.radio("Navigation", opts)
        
        st.markdown("---")
        
        if st.button("Déconnexion", type="primary", use_container_width=True):
            st.session_state.pop('auth_token', None)
            st.session_state.pop('user', None)
            st.session_state.pop('role', None)
            st.rerun()

        st.markdown("---")
        st.warning("⚠️ **AVIS JURIDIQUE**")
        st.markdown("<div style='font-size:0.7em; text-align:justify;'>Outil d'aide à la décision technique (ISO 15550). Résultats non contractuels.</div>", unsafe_allow_html=True)
        
        return menu

def render_auth():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color:#003366'>🔐 GEN-CONTROL</h1>", unsafe_allow_html=True)
        tab_login, tab_signup = st.tabs(["Connexion", "Créer un compte"])
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Identifiant")
                password = st.text_input("Mot de passe", type="password")
                if st.form_submit_button("Se connecter"):
                    sec = st.session_state.security; ip = sec.get_remote_ip()
                    success, msg = sec.verify_password(username, password, ip)
                    if success:
                        st.session_state['auth_token'] = sec.create_session_token(username, ip)
                        st.session_state['user'] = username
                        u_data = st.session_state.db.execute_read("SELECT role, license_tier FROM users WHERE username = ?", (username,))
                        st.session_state['role'] = u_data[0]['role'] if u_data else 'user'
                        st.session_state['license_tier'] = u_data[0]['license_tier'] if u_data else 'DISCOVERY'
                        st.rerun()
                    else: st.error(msg)
        with tab_signup:
            st.info("🎁 3 Audits Offerts")
            with st.form("signup_form"):
                c1, c2 = st.columns(2)
                new_user = c1.text_input("Identifiant")
                new_pass = c2.text_input("Mot de passe", type="password")
                email = st.text_input("Email (Obligatoire)")
                phone =