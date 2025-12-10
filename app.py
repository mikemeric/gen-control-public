# ==============================================================================
# GEN-CONTROL V1.1 - VERSION ULTIME (Paiement Manuel & Admin V1.1.5)
# ==============================================================================
import streamlit as st
import os
import time
from datetime import datetime
import uuid
import bcrypt

# --- IMPORT DES MODULES LOCAUX ---
from database import ThreadSafeDatabase
from security import EnhancedSecurityManager
from physics import IsoWillansModel, ReferenceEngineLibrary, AtmosphericParams
from analytics import DetailedLoadFactorManager, IntelligentAnomalyDetector, AdaptiveLearningEngine
from reports import PDFReportGenerator
from payments import render_payment_page  # <--- MODULE PAIEMENT

# ==========================================
# CONFIGURATION DE LA PAGE
# ==========================================
st.set_page_config(
    page_title="GEN-CONTROL V1.1",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header { font-size: 1.5rem; font-weight: bold; color: #2C3E50; margin-bottom: 1rem; }
    .verdict-box { padding: 15px; border-radius: 8px; text-align: center; margin: 10px 0; font-weight: bold; color: white; }
    .stButton button { width: 100%; border-radius: 5px; height: 3em; }
    .license-warning { background-color: #ffeeba; color: #856404; padding: 10px; border-radius: 5px; border: 1px solid #ffeeba; margin-bottom: 15px;}
    .admin-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 20px; }
    .info-duration { font-size: 0.9em; color: #2980b9; font-weight: bold; margin-top: -15px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# GESTION SESSION
# ==========================================
@st.cache_resource
def get_db(): return ThreadSafeDatabase.get_instance()

def init_session():
    if 'db' not in st.session_state: st.session_state.db = get_db()
    if 'security' not in st.session_state: st.session_state.security = EnhancedSecurityManager(st.session_state.db)
    if 'analytics' not in st.session_state: 
        st.session_state.detector = IntelligentAnomalyDetector()
        st.session_state.learning = AdaptiveLearningEngine()
        st.session_state.pdf_gen = PDFReportGenerator()

# ==========================================
# AUTHENTIFICATION (LOGIN + SIGNUP + DISCLAIMER)
# ==========================================
def render_auth():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔐 GEN-CONTROL</h1>", unsafe_allow_html=True)
        st.markdown("<h5 style='text-align: center; color: gray;'>Powered by DI-SOLUTIONS</h5>", unsafe_allow_html=True)
        
        # --- DISCLAIMER JURIDIQUE ---
        st.warning("""
        ⚠️ **AVERTISSEMENT LÉGAL IMPORTANT**
        
        GEN-CONTROL est un outil d'aide à la décision basé sur des modèles théoriques. 
        Les résultats "ANOMALIE" constituent une alerte statistique et non une preuve juridique de culpabilité. 
        
        **DI-SOLUTIONS décline toute responsabilité quant à l'utilisation des résultats pour des sanctions disciplinaires sans confirmation par une expertise technique approfondie.**
        """)
        
        tab_login, tab_signup = st.tabs(["Se connecter", "Créer un compte (Gratuit)"])
        
        # --- LOGIN ---
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Identifiant")
                password = st.text_input("Mot de passe", type="password")
                if st.form_submit_button("Connexion"):
                    sec = st.session_state.security
                    ip = sec.get_remote_ip()
                    success, msg = sec.verify_password(username, password, ip)
                    
                    if success:
                        if sec.is_2fa_enabled(username):
                            st.session_state['temp_user'] = username
                            st.session_state['awaiting_2fa'] = True
                            st.rerun()
                        else:
                            st.session_state['auth_token'] = sec.create_session_token(username, ip)
                            st.session_state['user'] = username
                            u_data = st.session_state.db.execute_read("SELECT role, license_tier FROM users WHERE username = ?", (username,))
                            if u_data:
                                st.session_state['role'] = u_data[0]['role']
                                st.session_state['license_tier'] = u_data[0]['license_tier']
                            else:
                                st.session_state['role'] = 'user'; st.session_state['license_tier'] = 'DISCOVERY'
                            st.rerun()
                    else: st.error(msg)

        # --- SIGNUP ---
        with tab_signup:
            st.info("🎁 Créez un compte DISCOVERY pour tester gratuitement (limité à 3 audits).")
            with st.form("signup_form"):
                new_user = st.text_input("Choisir un identifiant")
                new_pass = st.text_input("Choisir un mot de passe", type="password")
                
                if st.form_submit_button("S'inscrire"):
                    sec = st.session_state.security
                    user_ip = sec.get_remote_ip()
                    
                    if sec.check_signup_abuse(user_ip):
                        st.error("⛔ Trop de comptes créés depuis cette IP.")
                    elif not new_user or not new_pass:
                        st.warning("Remplissez tous les champs.")
                    else:
                        success, msg = sec.create_user(new_user, new_pass, role='user', tier='DISCOVERY', ip=user_ip)
                        if success: st.success("✅ Compte créé ! Connectez-vous.")
                        else: st.error(f"Erreur: {msg}")

    if st.session_state.get('awaiting_2fa'):
        with col2:
            code = st.text_input("Code 2FA")
            if st.button("Valider"):
                sec = st.session_state.security
                user = st.session_state['temp_user']
                if sec.verify_totp(user, code):
                    st.session_state['auth_token'] = sec.create_session_token(user, "127.0.0.1")
                    st.session_state['user'] = user
                    u_data = st.session_state.db.execute_read("SELECT role, license_tier FROM users WHERE username = ?", (user,))
                    st.session_state['role'] = u_data[0]['role']
                    st.session_state['license_tier'] = u_data[0]['license_tier']
                    del st.session_state['temp_user']
                    del st.session_state['awaiting_2fa']
                    st.rerun()
                else: st.error("Code incorrect")

# ==========================================
# 1. AUDIT TERRAIN (ASSISTANT INTELLIGENT)
# ==========================================
def render_audit_page():
    tier = st.session_state.get('license_tier', 'DISCOVERY')
    st.markdown(f'<div class="main-header">📱 Audit Terrain <span style="font-size:0.6em; color:grey">({tier})</span></div>', unsafe_allow_html=True)
    db = st.session_state.db
    
    try:
        equipments = db.execute_read("SELECT equipment_id, equipment_name, profile_base, power_kw FROM equipment")
        if not equipments:
            st.warning("⚠️ Aucun équipement. Allez dans 'Calibration'.")
            return
        eq_options = {e['equipment_id']: f"{e['equipment_name']} ({e['profile_base']})" for e in equipments}
        selected_id = st.selectbox("Équipement", list(eq_options.keys()), format_func=lambda x: eq_options[x])
        eq_data = next(e for e in equipments if e['equipment_id'] == selected_id)
        last_audit = db.execute_read("SELECT index_end FROM audits WHERE equipment_id = ? ORDER BY timestamp DESC LIMIT 1", (selected_id,))
        suggested_start = float(last_audit[0]['index_end']) if last_audit else 0.0
    except: return

    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        meta = ReferenceEngineLibrary.get_metadata(eq_data['profile_base'])
        cat_prefix = meta.get('type', 'TP')
        scenarios = DetailedLoadFactorManager.get_scenarios_by_category(cat_prefix)
        if not scenarios: scenarios = DetailedLoadFactorManager.get_scenarios_by_category('TP')
        scenario_code = st.selectbox("Scénario", list(scenarios.keys()), format_func=lambda x: f"{scenarios[x].description}")
        selected_scenario = scenarios[scenario_code]

    with st.container():
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        start_h = c1.number_input(
            "⏱️ Début (Heures)", 
            min_value=0.0, step=1.0, format="%.1f", value=suggested_start,
            help="⚠️ Relevé de l'horamètre (heures moteur). Ne pas saisir de kilomètres !"
        )
        end_h = c2.number_input(
            "⏱️ Fin (Heures)", 
            min_value=start_h, step=1.0, format="%.1f",
            help="⚠️ Relevé de l'horamètre."
        )
        fuel_l = c3.number_input("⛽ Carburant (L)", min_value=0.0, step=1.0)
    
    hours = end_h - start_h
    
    if hours > 0:
        st.markdown(f'<div class="info-duration">ℹ️ Durée de fonctionnement : {hours:.1f} Heures</div>', unsafe_allow_html=True)
    elif hours < 0:
        st.error("⚠️ L'index de fin doit être supérieur au début.")
    
    # --- ASSISTANT DE CHARGE VISUEL ---
    with st.expander("⚙️ Avancé (Réglage de la Charge Moteur)", expanded=False):
        load_val = st.slider("Charge Moyenne Estimée (%)", 0, 100, int(selected_scenario.load_typ * 100))
        manual_load = load_val / 100.0

        if load_val <= 10:
            st.info(f"💤 **{load_val}% - RALENTI / REPOS** : Moteur tourne à vide (Chauffe matin, Clim à l'arrêt).")
        elif load_val <= 25:
            st.success(f"🏗️ **{load_val}% - STATIONNAIRE (PTO)** : Toupie béton, Grue, Benne. Le camion ne roule pas mais travaille.")
        elif load_val <= 45:
            st.success(f"🚚 **{load_val}% - ROUTE MIXTE / MOYENNE** : Trajet national avec villages, descentes et plats.")
        elif load_val <= 65:
            st.warning(f"🚛 **{load_val}% - TRACTION SOUTENUE** : Autoroute rapide chargée ou route avec beaucoup de faux-plats.")
        elif load_val <= 85:
            st.error(f"⛰️ **{load_val}% - MONTAGNE / DIFFICILE** : Montée de col, Piste boueuse, Surcharge importante.")
        else:
            st.error(f"🔥 **{load_val}% - EXTRÊME (Surchauffe)** : Pied au plancher permanent. Rare sur longue durée.")

    is_quota_blocked = False
    if tier == 'DISCOVERY':
        # QUOTA PAR UTILISATEUR
        user = st.session_state['user']
        count_res = db.execute_read("SELECT COUNT(*) as c FROM audits WHERE created_by = ?", (user,)) 
        count = count_res[0]['c'] if count_res else 0
        if count >= 3:
            is_quota_blocked = True
            st.markdown("""<div class="license-warning">🛑 <b>LIMITE DÉCOUVERTE ATTEINTE</b><br>Passez à la version PRO.</div>""", unsafe_allow_html=True)

    if st.button("🚀 LANCER L'ANALYSE", type="primary", disabled=is_quota_blocked):
        if hours <= 0: st.error("Durée invalide (<= 0h). Vérifiez vos index.")
        else:
            with st.spinner("Analyse..."):
                time.sleep(0.5)
                model = IsoWillansModel.from_reference_data(eq_data['profile_base'], eq_data['power_kw'])
                override = st.session_state.learning.get_equipment_override(selected_id, scenario_code, db)
                final_load = manual_load
                src = "Manuel" if manual_load != selected_scenario.load_typ else ("IA" if override else "Standard")
                if override and src == "IA": final_load = override.learned_load_typ
                atmos = AtmosphericParams(0, 25)
                pred = model.predict_consumption(final_load * 100, atmos)
                est_fuel = pred['consumption_corrected_l_h'] * hours
                dev = ((fuel_l - est_fuel) / est_fuel) * 100 if est_fuel > 0 else 0
                h_rows = db.execute_read("SELECT deviation_pct FROM audits WHERE equipment_id = ? ORDER BY timestamp DESC LIMIT 20", (selected_id,))
                h_data = [r['deviation_pct'] for r in h_rows] if h_rows else []
                anom = st.session_state.detector.detect_anomaly(selected_id, dev, h_data, scenario_code)
                st.session_state['last_audit'] = {'eq_id': selected_id, 'eq_name': eq_data['equipment_name'], 'scenario': scenario_code, 'start': start_h, 'end': end_h, 'fuel': fuel_l, 'est': est_fuel, 'dev': dev, 'z': anom.z_score, 'verdict': anom.verdict, 'conf': anom.confidence, 'hours': hours, 'recs': anom.recommendations, 'src': src}
                if 'current_pdf' in st.session_state: del st.session_state['current_pdf']

    if 'last_audit' in st.session_state:
        audit = st.session_state['last_audit']
        st.markdown("---")
        color = {'NORMAL': '#28a745', 'SUSPECT': '#ffc107', 'ANOMALIE': '#dc3545'}.get(audit['verdict'], 'grey')
        st.markdown(f"""<div class="verdict-box" style="background-color: {color};">RÉSULTAT : {audit['verdict']}</div>""", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Déclaré", f"{audit['fuel']:.1f} L")
        m2.metric("Théorique", f"{audit['est']:.1f} L", f"Src: {audit['src']}")
        m3.metric("Écart", f"{audit['dev']:+.1f} %", delta_color="inverse")
        if audit['recs']:
            with st.expander("💡 Recommandations"):
                for r in audit['recs']: st.markdown(f"- {r}")
        st.markdown("---")
        c_save, c_dl = st.columns(2)
        with c_save:
            if st.button("💾 SAUVEGARDER"):
                uid = str(uuid.uuid4())
                user_record = st.session_state['user']
                db.execute_write("""INSERT INTO audits (audit_uuid, timestamp, created_by, equipment_id, materiel_type, materiel_name, scenario_code, index_start, index_end, power_kw, fuel_declared_l, estimated_min, estimated_typ, estimated_max, uncertainty_pct, deviation_pct, z_score, verdict, confidence_pct, validated_by_operator) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                                 (uid, datetime.now().isoformat(), user_record, audit['eq_id'], eq_data['profile_base'], audit['eq_name'], audit['scenario'], audit['start'], audit['end'], eq_data['power_kw'], audit['fuel'], audit['est']*0.9, audit['est'], audit['est']*1.1, 10.0, audit['dev'], audit['z'], audit['verdict'], int(audit['conf']*100), 1))
                st.success("Enregistré !")
                pdf = st.session_state.pdf_gen.generate_audit_report({'audit_uuid': uid, 'equipment_name': audit['eq_name'], 'user': st.session_state['user'], 'fuel_declared': audit['fuel'], 'fuel_estimated': audit['est'], 'deviation': audit['dev'], 'verdict': audit['verdict'], 'scenario': audit['scenario'], 'hours': audit['hours']}, license_tier=tier)
                st.session_state['current_pdf'] = pdf.getvalue()
                st.session_state['current_pdf_name'] = f"AUDIT_{uid[:8]}.pdf"
                st.rerun()
        with c_dl:
            if 'current_pdf' in st.session_state:
                st.download_button("📄 TÉLÉCHARGER PDF", st.session_state['current_pdf'], st.session_state['current_pdf_name'], "application/pdf", type="primary")

    st.markdown("---")
    with st.expander(f"📜 Historique : {eq_data['equipment_name']}"):
        rows = db.execute_read("SELECT * FROM audits WHERE equipment_id = ? ORDER BY timestamp DESC LIMIT 5", (selected_id,))
        if rows: st.dataframe([{'Date': r['timestamp'][:16], 'L': r['fuel_declared_l'], 'Verdict': r['verdict']} for r in rows], use_container_width=True)

# ==========================================
# 2. CALIBRATION (GESTION PARC)
# ==========================================
def render_calibration_page():
    st.markdown('<div class="main-header">🎯 Calibration & Gestion Parc</div>', unsafe_allow_html=True)
    st.subheader("📝 Nouvel Équipement")
    
    type_eq = st.radio("Type d'équipement", ["Groupe Électrogène (GE)", "Camion / Poids-Lourd", "Engin BTP / Autre"], horizontal=True, key="equipment_type_selector")
    cat_map = {"Groupe Électrogène (GE)": "GE", "Camion / Poids-Lourd": "TRUCK", "Engin BTP / Autre": "OTHER"}
    selected_cat = cat_map[type_eq]
    
    engines_dict = ReferenceEngineLibrary.list_engines_by_type(selected_cat)
    if not engines_dict: engines_dict = {"GENERIC_ISO_DIESEL": "Standard Générique"}
    
    profile_code = st.selectbox("Profil Moteur (ISO)", list(engines_dict.keys()), format_func=lambda x: engines_dict.get(x, x), key=f"engine_select_{selected_cat}")
    meta = ReferenceEngineLibrary.get_metadata(profile_code)
    
    if selected_cat == "GE":
        unit_display = "kVA"; conversion_factor = 0.8 
    elif selected_cat == "TRUCK":
        unit_display = "CV"; conversion_factor = 1.0 / 1.36
    else:
        unit_display = "kW"; conversion_factor = 1.0
    
    if meta.get('fixed_power_kw') is not None:
        if meta.get('display_rating'): val_affichee = float(meta['display_rating'])
        else: val_affichee = meta['fixed_power_kw'] / conversion_factor if conversion_factor != 0 else meta['fixed_power_kw']
        is_locked = True
        power_kw_internal = float(meta['fixed_power_kw'])
    else:
        val_affichee = 100.0; is_locked = False; power_kw_internal = None

    with st.expander("🔧 Informations Techniques & Debug", expanded=False):
        st.info(f"**Profil:** {meta.get('name', profile_code)} | **Puissance Interne:** {power_kw_internal if power_kw_internal else 'Variable'} kW | **État:** {'🔒 Verrouillé' if is_locked else '✏️ Modifiable'}")

    with st.form("new_equipment_v1_final"):
        st.markdown("---")
        c1, c2 = st.columns(2)
        eq_id = c1.text_input("ID Unique (Immatriculation)", key="eq_id_input")
        name = c2.text_input("Nom Descriptif", key="eq_name_input")
        
        col_puissance, col_unite = st.columns([3, 1])
        with col_puissance:
            user_power_value = st.number_input("Puissance", min_value=1.0, max_value=50000.0, value=val_affichee, step=1.0, disabled=is_locked, key=f"power_input_{profile_code}_{selected_cat}", help="🔒 Valeur constructeur" if is_locked else "✏️ Saisie libre")
        with col_unite:
            st.metric("Unité", unit_display)
        
        if power_kw_internal is None: final_power_kw = user_power_value * conversion_factor
        else: final_power_kw = power_kw_internal
        
        if st.form_submit_button("✅ Enregistrer l'Équipement", type="primary"):
            if not eq_id or not name: st.error("⚠️ ID et Nom requis")
            elif final_power_kw <= 0: st.error("⚠️ Puissance invalide")
            else:
                try:
                    st.session_state.db.execute_write("INSERT INTO equipment (equipment_id, equipment_name, profile_base, power_kw) VALUES (?, ?, ?, ?)", (eq_id, name, profile_code, final_power_kw))
                    st.success(f"✅ Équipement ajouté !")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"❌ Erreur (ID existe ?) : {e}")

    st.markdown("---")
    st.subheader("📋 Liste des équipements enregistrés")
    rows = st.session_state.db.execute_read("SELECT * FROM equipment ORDER BY created_at DESC")
    if rows:
        data = [{'ID': r['equipment_id'], 'Nom': r['equipment_name'], 'Moteur': r['profile_base']} for r in rows]
        st.dataframe(data, use_container_width=True)
        if st.session_state.get('role') == 'admin':
            with st.expander("🗑️ Suppression (Admin uniquement)"):
                to_del = st.selectbox("Supprimer:", [r['equipment_id'] for r in rows])
                if st.button("⚠️ Confirmer Suppression"):
                    st.session_state.db.execute_write("DELETE FROM equipment WHERE equipment_id=?", (to_del,))
                    st.success("Supprimé")
                    time.sleep(0.5)
                    st.rerun()

# ==========================================
# 3. INTELLIGENCE (CORPORATE ONLY)
# ==========================================
def render_learning_page():
    tier = st.session_state.get('license_tier', 'DISCOVERY')
    st.markdown('<div class="main-header">🧠 Intelligence & Apprentissage</div>', unsafe_allow_html=True)
    if tier != 'CORPORATE':
        st.warning(f"🔒 Réservé aux licences CORPORATE (Vous: {tier})")
        st.button("🔄 Lancer l'apprentissage (Désactivé)", disabled=True)
    else:
        if st.button("🔄 Lancer l'apprentissage manuel (Batch)"):
            st.session_state.learning.batch_learn_from_all_equipment(st.session_state.db)
            st.success("Terminé.")
    rows = st.session_state.db.execute_read("SELECT * FROM equipment_load_overrides WHERE is_active=1")
    if rows: st.dataframe([dict(r) for r in rows])

# ==========================================
# 4. ADMINISTRATION (QG)
# ==========================================
def render_admin_page():
    if st.session_state.get('role') != 'admin' or st.session_state.get('license_tier') != 'CORPORATE':
        st.error("⛔ Accès Refusé.")
        return

    st.markdown('<div class="main-header">🔐 Administration (QG)</div>', unsafe_allow_html=True)
    
    # ONGLETS DE GESTION
    tab_money, tab_users, tab_db = st.tabs(["💰 Paiements EN ATTENTE", "👥 Utilisateurs", "💾 Base de Données"])
    
    # --- 1. GESTION DES PAIEMENTS MANUELS ---
    with tab_money:
        st.subheader("Validation des Paiements Mobile Money")
        db = st.session_state.db
        pendings = db.execute_read("SELECT * FROM transactions WHERE status = 'PENDING' ORDER BY timestamp DESC")
        
        if not pendings:
            st.info("Aucune demande de paiement en attente. Tout est calme. 🍵")
        else:
            for p in pendings:
                with st.expander(f"⏳ {p['amount']} FCFA - {p['username']} (ID: {p['mobile_money_id']})", expanded=True):
                    c1, c2, c3 = st.columns([2,1,1])
                    c1.write(f"**Date:** {p['timestamp']}\n\n**ID Transaction Client:** `{p['mobile_money_id']}`")
                    
                    if c2.button("✅ VALIDER", key=f"ok_{p['tx_ref']}"):
                        db.approve_transaction(p['tx_ref'])
                        st.success(f"Client {p['username']} passé en PRO !")
                        time.sleep(1)
                        st.rerun()
                        
                    if c3.button("❌ REFUSER", key=f"ko_{p['tx_ref']}"):
                        db.reject_transaction(p['tx_ref'])
                        st.warning("Transaction refusée.")
                        time.sleep(1)
                        st.rerun()

    # --- 2. GESTION UTILISATEURS ---
    with tab_users:
        st.subheader("Créer un nouvel utilisateur")
        with st.form("create_user_form"):
            c1, c2, c3 = st.columns(3)
            new_user = c1.text_input("Identifiant")
            new_pass = c2.text_input("Mot de Passe", type="password")
            new_role = c3.selectbox("Rôle", ["user", "admin"])
            new_tier = st.selectbox("Licence", ["DISCOVERY", "PRO", "CORPORATE"], index=0)
            
            if st.form_submit_button("Créer"):
                if new_user and new_pass:
                    sec = st.session_state.security
                    success, msg = sec.create_user(new_user, new_pass, new_role, new_tier)
                    if success: st.success("Utilisateur créé !")
                    else: st.error(msg)
        
        st.subheader("Liste des Utilisateurs")
        users = st.session_state.db.execute_read("SELECT username, role, license_tier, subscription_end, signup_ip FROM users")
        if users: st.dataframe([dict(u) for u in users], use_container_width=True)

    # --- 3. BACKUP ---
    with tab_db:
        st.subheader("📦 Sauvegarde")
        db_files = [f for f in os.listdir('.') if f.endswith('.db')]
        if db_files:
            with open(db_files[0], "rb") as f:
                st.download_button("⬇️ TÉLÉCHARGER BD", f, file_name=f"BACKUP_{datetime.now().strftime('%Y%m%d')}.db")

# ==========================================
# MAIN
# ==========================================
def main():
    init_session()
    if 'auth_token' not in st.session_state or not st.session_state.security.validate_session(st.session_state['auth_token']):
        render_auth()
        return

    with st.sidebar:
        st.title("GEN-CONTROL")
        user = st.session_state['user']
        role = st.session_state.get('role', 'user')
        tier = st.session_state.get('license_tier', 'DISCOVERY')
        
        colors = {'DISCOVERY': 'grey', 'PRO': 'orange', 'CORPORATE': 'green'}
        st.markdown(f'<span style="background-color:{colors.get(tier, "grey")}; padding:5px; border-radius:5px; color:white; font-weight:bold">{tier}</span>', unsafe_allow_html=True)
        st.caption(f"Connecté: {user} ({role})")
        
        options = ["📱 Audit Terrain", "🎯 Calibration"]
        
        if tier == 'DISCOVERY':
            options.append("💎 Devenir PRO")
            
        if tier == 'CORPORATE' or tier == 'PRO':
            options.append("🧠 Intelligence")
            
        if role == 'admin' and tier == 'CORPORATE': 
            options.append("🔐 Admin")
            
        menu = st.radio("Menu", options)
        
        if st.button("Déconnexion"):
            st.session_state.security.logout(st.session_state['auth_token'])
            del st.session_state['auth_token']
            st.rerun()
        st.markdown("---")
        st.caption("DI-SOLUTIONS SARL v1.1.5")

    if menu == "📱 Audit Terrain": render_audit_page()
    elif menu == "🎯 Calibration": render_calibration_page()
    elif menu == "🧠 Intelligence": render_learning_page()
    elif menu == "🔐 Admin": render_admin_page()
    elif menu == "💎 Devenir PRO": render_payment_page()

if __name__ == "__main__":
    main()