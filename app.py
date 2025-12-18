# ==============================================================================
# GEN-CONTROL V1.1.9 - VERSION STABLE & SÉCURISÉE
# (Intègre: Patch Profil, Fix Redirection Inscription, Sécurité Bcrypt)
# ==============================================================================
import streamlit as st
import os
import time
import bcrypt  # <--- INDISPENSABLE POUR LA SÉCURITÉ
from datetime import datetime
import uuid
import urllib.parse

# Imports des modules techniques
# Assurez-vous que les fichiers database.py, security.py, etc. sont bien présents
from database import ThreadSafeDatabase
from security import EnhancedSecurityManager
from physics import IsoWillansModel, ReferenceEngineLibrary, AtmosphericParams
from analytics import DetailedLoadFactorManager, IntelligentAnomalyDetector, AdaptiveLearningEngine
from reports import PDFReportGenerator

st.set_page_config(
    page_title="GEN-CONTROL V1.1", 
    page_icon="🛡️", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS (Style Tableau Comparatif & Design) ---
st.markdown("""
<style>
    .main-header { 
        font-size: 1.5rem; font-weight: bold; color: #003366; 
        margin-bottom: 1rem; border-bottom: 2px solid #FF4B4B; padding-bottom: 5px; 
    }
    .verdict-box { 
        padding: 15px; border-radius: 8px; text-align: center; margin: 10px 0; 
        font-weight: bold; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
    }
    .share-btn { 
        display: inline-block; background-color: #25D366; color: white; 
        padding: 10px 20px; border-radius: 5px; text-decoration: none; 
        font-weight: bold; margin-top: 10px; text-align: center; width: 100%; 
    }
    .maintenance-alert { 
        background-color: #e3f2fd; border-left: 5px solid #2196f3; 
        padding: 10px; border-radius: 5px; color: #0d47a1; font-size: 0.9em; margin-top: 10px;
    }
    .tech-card { 
        background-color: #f8f9fa; padding: 15px; border-radius: 5px; 
        border: 1px solid #b0b0b0; font-size: 0.9em; margin-bottom: 15px; color: #333; 
    }
    .cgu-box {
        font-size: 0.8em; color: #555; background-color: #f9f9f9;
        padding: 10px; border: 1px solid #ddd; border-radius: 5px;
        height: 150px; overflow-y: scroll; margin-bottom: 10px;
    }
    /* Tableau Comparatif B2B */
    .compare-table {
        width: 100%; border-collapse: collapse; font-size: 0.9em; margin-top: 20px;
    }
    .compare-table th { 
        background-color: #003366; color: white; padding: 12px; text-align: center; 
        border: 1px solid #ddd;
    }
    .compare-table td { 
        border: 1px solid #ddd; padding: 10px; text-align: center; color: #333;
    }
    .compare-feature { 
        text-align: left !important; font-weight: bold; background-color: #f0f2f6; 
        width: 30%;
    }
    .check { color: green; font-weight: bold; }
    .cross { color: red; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db(): return ThreadSafeDatabase.get_instance()

def init_session():
    if 'db' not in st.session_state: 
        st.session_state.db = get_db()
    if 'security' not in st.session_state: 
        st.session_state.security = EnhancedSecurityManager(st.session_state.db)
    if 'analytics' not in st.session_state: 
        st.session_state.detector = IntelligentAnomalyDetector()
        st.session_state.learning = AdaptiveLearningEngine()
        st.session_state.pdf_gen = PDFReportGenerator()

# --- SIDEBAR (MENU) ---
def render_sidebar():
    if 'auth_token' not in st.session_state:
        return None

    with st.sidebar:
        st.title("GEN-CONTROL")
        st.caption("V1.1.9 (Stable)")
        
        tier = st.session_state.get('license_tier', 'DISCOVERY')
        user = st.session_state.get('user', 'Utilisateur')
        st.info(f"👤 {user}\n🏷️ Licence : {tier}")
        
        # --- MENU PRINCIPAL ---
        opts = ["📱 Audit Terrain", "🎯 Calibration"]
        opts.append("👤 Mon Profil") # <--- NOUVEAU
        opts.append("💎 Offres & Licences")
        
        if tier in ['PRO', 'CORPORATE']: opts.append("🧠 Intelligence")
        if st.session_state.get('role') == 'admin': opts.append("🔐 Admin")
        
        menu = st.radio("Navigation", opts)
        
        st.markdown("---")
        
        if st.button("Déconnexion", type="primary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        st.markdown("---")
        st.warning("⚠️ **AVIS JURIDIQUE**")
        st.markdown(
            "<div style='font-size:0.7em; text-align:justify;'>"
            "Outil d'aide à la décision technique (ISO 15550). "
            "Résultats indicatifs."
            "</div>", 
            unsafe_allow_html=True
        )
        return menu

# --- AUTHENTIFICATION ---
def render_auth():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<h1 style='text-align: center; color:#003366'>🔐 GEN-CONTROL</h1>", 
            unsafe_allow_html=True
        )
        tab_login, tab_signup = st.tabs(["Connexion", "Créer un compte"])
        
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Identifiant")
                password = st.text_input("Mot de passe", type="password")
                
                if st.form_submit_button("Se connecter"):
                    sec = st.session_state.security
                    ip = sec.get_remote_ip()
                    success, msg = sec.verify_password(username, password, ip)
                    if success:
                        st.session_state['auth_token'] = sec.create_session_token(username, ip)
                        st.session_state['user'] = username
                        u_data = st.session_state.db.execute_read(
                            "SELECT role, license_tier FROM users WHERE username = ?", (username,)
                        )
                        st.session_state['role'] = u_data[0]['role'] if u_data else 'user'
                        st.session_state['license_tier'] = u_data[0]['license_tier'] if u_data else 'DISCOVERY'
                        st.rerun()
                    else: 
                        st.error(msg)

        with tab_signup:
            st.info("🎁 3 Audits Offerts (Offre Découverte)")
            with st.form("signup_form"):
                c1, c2 = st.columns(2)
                new_user = c1.text_input("Identifiant")
                new_pass = c2.text_input("Mot de passe", type="password")
                
                email = st.text_input("Email (Obligatoire)")
                phone = st.text_input("WhatsApp")
                company = st.text_input("Société")
                referral = st.text_input("Code Parrain (Optionnel)")
                
                st.markdown("---")
                st.markdown("**Conditions Générales d'Utilisation (CGU)**")
                st.markdown("""
                <div class="cgu-box">
                1. <b>Service :</b> GEN-CONTROL offre une analyse théorique de consommation.<br>
                2. <b>Limites :</b> Les résultats dépendent de la précision des données saisies.<br>
                3. <b>Données :</b> Conformité RGPD. Aucune revente de données.<br>
                4. <b>Licences :</b> L'offre Corporate inclut un déploiement spécifique.<br>
                5. <b>Litiges :</b> L'éditeur ne peut être tenu responsable des écarts constatés sur le terrain.
                </div>
                """, unsafe_allow_html=True)
                
                cgu_accepted = st.checkbox("J'accepte les CGU", value=False)
                
                if st.form_submit_button("Créer mon compte"):
                    sec = st.session_state.security
                    ip = sec.get_remote_ip()
                    
                    if not cgu_accepted:
                        st.error("🛑 Veuillez accepter les CGU.")
                    elif sec.check_signup_abuse(ip): 
                        st.error("Trop de comptes créés.")
                    elif not new_user or not new_pass or not email: 
                        st.warning("Remplissez tous les champs.")
                    else:
                        ok, msg = st.session_state.db.create_user_extended(
                            new_user, new_pass, email, phone, company, referral, ip=ip
                        )
                        if ok: 
                            st.success("Compte créé ! Redirection...")
                            # --- FIX REDIRECTION ---
                            time.sleep(2)
                            st.rerun()
                        else: 
                            st.error(f"Erreur: {msg}")

# --- PAGE PAIEMENT & LICENCES ---
def render_payment_page_local():
    st.markdown('<div class="main-header">💎 Grille Tarifaire & Licences 2025</div>', unsafe_allow_html=True)
    
    # Onglets de vente
    tab_pro, tab_corp, tab_comp = st.tabs(["💎 OFFRE PRO", "🏢 OFFRE CORPORATE (VIP)", "⚖️ COMPARATIF"])
    
    # --- 1. OFFRE PRO ---
    with tab_pro:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.info("### 🚀 Pour Freelances & PME")
            st.write("Professionnalisez vos audits et gagnez la confiance de vos clients.")
            st.markdown("""
            * **Audits Illimités** : Fini la limite des 3 essais.
            * **Rapports PDF Certifiés** : Sans filigrane "DÉMO". Propre et net.
            * **Cloud Sécurisé** : Vos données sont protégées.
            * **Support Prioritaire** : Ligne directe WhatsApp.
            """)
            st.metric("Abonnement Mensuel", "15 000 FCFA")
        
        with c2:
            st.write("### 💳 Activer le Pack PRO")
            with st.form("pay_pro"):
                phone_pay = st.text_input("Numéro Mobile Money", placeholder="6XX XXX XXX")
                tx_ref = st.text_input("ID Transaction (SMS)", placeholder="Ex: PP2305...")
                sponsor_code = st.text_input("Code Parrain", placeholder="Optionnel")
                
                if st.form_submit_button("S'ABONNER (15 000 F)"):
                    if len(phone_pay) > 8 and len(tx_ref) > 4:
                        st.session_state.db.declare_manual_payment(
                            tx_ref, st.session_state['user'], 15000, phone_pay
                        )
                        st.success("Activation en cours (Max 2h).")
                    else: st.error("Infos incomplètes.")

    # --- 2. OFFRE CORPORATE ---
    with tab_corp:
        st.error("### 🏢 L'arme absolue pour les Grandes Flottes & Industries")
        
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown("""
            **Pourquoi passer Corporate ?**
            C'est simple : Une seule anomalie carburant détectée rentabilise votre abonnement annuel.
            
            * 👑 **Multi-Utilisateurs** : Un compte Admin + Des comptes employés illimités.
            * 🧠 **Intelligence Artificielle (IA)** : Le logiciel APPREND de vos engins.
            * 🎨 **Marque Blanche** : Vos rapports PDF avec VOTRE LOGO d'entreprise.
            * 💾 **Souveraineté des Données** : Export local des bases de données & Déploiement sur site possible.
            * 📞 **Support VIP** : Ligne directe Ingénieur dédié.
            """)
        
        with c2:
            st.metric("Pack Mensuel (Facturation Annuelle)", "100 000 FCFA", "Rentabilité Immédiate")
            st.caption("Déploiement sur site ou Cloud Privé inclus.")
            
            with st.form("pay_corp"):
                phone_pay = st.text_input("Numéro Paiement", placeholder="6XX XXX XXX", key="cp_phone")
                tx_ref = st.text_input("ID Transaction / Bon de Commande", key="cp_ref")
                sponsor_code = st.text_input("Code Parrain", placeholder="Requis pour bonus", key="cp_par")
                
                if st.form_submit_button("DEMANDER L'ACTIVATION CORPORATE"):
                    if len(phone_pay) > 8:
                        st.session_state.db.declare_manual_payment(
                            tx_ref or "CORP_DEMAND", st.session_state['user'], 100000, phone_pay
                        )
                        st.success("Votre demande est traitée en priorité absolue.")
                        st.info("Un ingénieur va vous contacter pour le déploiement.")

    # --- 3. COMPARATIF ---
    with tab_comp:
        st.write("### ⚖️ Tableau Comparatif des Licences 2025")
        st.markdown("""
        <table class="compare-table">
            <tr>
                <th style="width:30%">FONCTIONNALITÉS</th>
                <th style="background-color:#eee; color:#555;">DISCOVERY<br>(Gratuit)</th>
                <th style="background-color:#28a745;">PRO<br>(15 000 F/mois)</th>
                <th style="background-color:#003366;">CORPORATE<br>(100 000 F/mois)</th>
            </tr>
            <tr>
                <td class="compare-feature">Quota d'Audits</td>
                <td>3 Max</td>
                <td class="check">✓ ILLIMITÉ</td>
                <td class="check">✓ ILLIMITÉ</td>
            </tr>
            <tr>
                <td class="compare-feature">Comptes Utilisateurs</td>
                <td>1</td>
                <td>1</td>
                <td class="check">MULTI-COMPTES</td>
            </tr>
            <tr>
                <td class="compare-feature">Rapport PDF</td>
                <td>Filigrane "DÉMO"</td>
                <td class="check">PROPRE (Certifié)</td>
                <td class="check">LOGO CLIENT + CERTIFIÉ</td>
            </tr>
             <tr>
                <td class="compare-feature">Intelligence Artificielle</td>
                <td class="cross">✘</td>
                <td class="cross">✘ (Lecture seule)</td>
                <td class="check">✓ ACTIVE (Apprentissage)</td>
            </tr>
             <tr>
                <td class="compare-feature">Base de Données</td>
                <td>Cloud Partagé</td>
                <td>Cloud Sécurisé</td>
                <td class="check">EXPORT LOCAL / SUR SITE</td>
            </tr>
            <tr>
                <td class="compare-feature">Support Technique</td>
                <td>Email (48h)</td>
                <td>Prioritaire</td>
                <td class="check">VIP (Téléphone Direct)</td>
            </tr>
        </table>
        <br>
        <div style="text-align:center; font-size:0.8em; color:#777;">
            Tarifs HT. L'offre Corporate nécessite un engagement annuel.
        </div>
        """, unsafe_allow_html=True)

# --- PAGES FONCTIONNELLES ---
def render_audit_page():
    tier = st.session_state.get('license_tier', 'DISCOVERY')
    st.markdown(
        f'<div class="main-header">📱 Audit Terrain <span style="font-size:0.6em; color:grey">({tier})</span></div>', 
        unsafe_allow_html=True
    )
    db = st.session_state.db
    
    try: aging_val = float(db.get_config_value("AGING_FACTOR", "1.05"))
    except: aging_val = 1.05

    try:
        equipments = db.execute_read("SELECT equipment_id, equipment_name, profile_base, power_kw FROM equipment")
        if not equipments: 
            st.warning("⚠️ Aucun équipement. Allez dans 'Calibration'."); return
            
        eq_options = {e['equipment_id']: f"{e['equipment_name']} ({e['profile_base']})" for e in equipments}
        selected_id = st.selectbox("Sélectionner l'engin", list(eq_options.keys()), format_func=lambda x: eq_options[x])
        eq_data = next(e for e in equipments if e['equipment_id'] == selected_id)
        
        last_audit = db.execute_read(
            "SELECT index_end FROM audits WHERE equipment_id = ? ORDER BY timestamp DESC LIMIT 1", (selected_id,)
        )
        suggested_start = float(last_audit[0]['index_end']) if last_audit else 0.0
    except: return

    meta = ReferenceEngineLibrary.get_metadata(eq_data['profile_base'])
    scenarios = DetailedLoadFactorManager.get_scenarios_by_category(meta.get('type', 'TP')) or DetailedLoadFactorManager.get_scenarios_by_category('TP')
    scenario_code = st.selectbox("Conditions", list(scenarios.keys()), format_func=lambda x: f"{scenarios[x].description}")
    selected_scenario = scenarios[scenario_code]

    if aging_val != 1.0: st.caption(f"ℹ️ Facteur Tropicalisation appliqué : **x{aging_val}**")

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    start_h = c1.number_input("⏱️ Index Début (h)", min_value=0.0, step=1.0, value=suggested_start)
    end_h = c2.number_input("⏱️ Index Fin (h)", min_value=start_h, step=1.0)
    fuel_l = c3.number_input("⛽ Carburant Remis (L)", min_value=0.0, step=1.0)
    
    hours = end_h - start_h
    if hours > 0:
        st.info(f"Durée : {hours:.1f} h")
        next_maint = 250 - (end_h % 250)
        if next_maint < 50: 
            st.markdown(f"""<div class="maintenance-alert">🛠️ Vidange dans {next_maint:.0f}h.</div>""", unsafe_allow_html=True)

    with st.expander("⚙️ Avancé"):
        load_val = st.slider("Charge Estimée (%)", 0, 100, int(selected_scenario.load_typ * 100))
        manual_load = load_val / 100.0

    blocked = False
    if tier == 'DISCOVERY':
        c = db.execute_read("SELECT COUNT(*) as c FROM audits WHERE created_by = ?", (st.session_state['user'],))[0]['c']
        if c >= 3: blocked = True; st.error("🛑 LIMITE 3 AUDITS. Passez PRO.")

    if st.button("LANCER L'AUDIT", type="primary", disabled=blocked):
        if hours <= 0: st.error("Index incohérents.")
        else:
            with st.spinner("Calcul..."):
                time.sleep(0.5)
                model = IsoWillansModel.from_reference_data(eq_data['profile_base'], eq_data['power_kw'])
                override = st.session_state.learning.get_equipment_override(selected_id, scenario_code, db)
                final_load = manual_load
                src = "Manuel" if manual_load != selected_scenario.load_typ else ("IA" if override else "Standard")
                if override and src == "IA": final_load = override.learned_load_typ
                
                pred = model.predict_consumption(final_load * 100, AtmosphericParams(0, 25), aging_factor=aging_val)
                est_fuel = pred['consumption_corrected_l_h'] * hours
                dev = ((fuel_l - est_fuel) / est_fuel) * 100 if est_fuel > 0 else 0
                
                h_rows = db.execute_read("SELECT deviation_pct FROM audits WHERE equipment_id = ? ORDER BY timestamp DESC LIMIT 20", (selected_id,))
                h_data = [r['deviation_pct'] for r in h_rows] if h_rows else []
                anom = st.session_state.detector.detect_anomaly(selected_id, dev, h_data, scenario_code)
                
                st.session_state['last_audit'] = {
                    'eq_id': selected_id, 'eq_name': eq_data['equipment_name'], 
                    'scenario': scenario_code, 'start': start_h, 'end': end_h, 
                    'fuel': fuel_l, 'est': est_fuel, 'dev': dev, 
                    'z': anom.z_score, 'verdict': anom.verdict, 
                    'conf': anom.confidence, 'hours': hours, 'src': src
                }

    if 'last_audit' in st.session_state:
        audit = st.session_state['last_audit']
        st.markdown("---")
        color = {'NORMAL': '#28a745', 'SUSPECT': '#ffc107', 'ANOMALIE': '#dc3545'}.get(audit['verdict'], 'grey')
        
        st.markdown(f"""<div class="verdict-box" style="background-color: {color};">RÉSULTAT : {audit['verdict']}</div>""", unsafe_allow_html=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Déclaré", f"{audit['fuel']:.1f} L")
        m2.metric("Théorique", f"{audit['est']:.1f} L")
        m3.metric("Écart", f"{audit['dev']:+.1f} %", delta_color="inverse")
        
        st.markdown("### 💾 Sauvegarde")
        legal_check = st.checkbox("Je certifie l'exactitude des relevés terrain.")
        c_save, c_share = st.columns(2)
        
        with c_save:
            if st.button("CONFIRMER"):
                if not legal_check: st.error("Certification requise.")
                else:
                    uid = str(uuid.uuid4())
                    db.execute_write(
                        """INSERT INTO audits (audit_uuid, timestamp, created_by, equipment_id, materiel_type, materiel_name, scenario_code, index_start, index_end, power_kw, fuel_declared_l, estimated_min, estimated_typ, estimated_max, uncertainty_pct, deviation_pct, z_score, verdict, confidence_pct, validated_by_operator) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                        (uid, datetime.now().isoformat(), st.session_state['user'], audit['eq_id'], eq_data['profile_base'], audit['eq_name'], audit['scenario'], audit['start'], audit['end'], eq_data['power_kw'], audit['fuel'], audit['est']*0.9, audit['est'], audit['est']*1.1, 10.0, audit['dev'], audit['z'], audit['verdict'], int(audit['conf']*100), 1)
                    )
                    st.success("Enregistré !")
                    pdf = st.session_state.pdf_gen.generate_audit_report({
                        'audit_uuid': uid, 'equipment_name': audit['eq_name'], 
                        'user': st.session_state['user'], 'fuel_declared': audit['fuel'], 
                        'fuel_estimated': audit['est'], 'deviation': audit['dev'], 
                        'verdict': audit['verdict'], 'scenario': audit['scenario'], 
                        'hours': audit['hours']}, license_tier=tier
                    )
                    st.session_state['current_pdf'] = pdf.getvalue()
                    st.session_state['current_pdf_name'] = f"AUDIT_{uid[:8]}.pdf"
                    st.rerun()
                    
        with c_share:
            msg_wa = f"🚨 *AUDIT*\nEngin: {audit['eq_name']}\nÉcart: {audit['dev']:+.1f}%\nVerdict: {audit['verdict']}"
            link = f'<a href="https://wa.me/?text={urllib.parse.quote(msg_wa)}" target="_blank" class="share-btn">📲 WhatsApp</a>'
            st.markdown(link, unsafe_allow_html=True)
            
        if 'current_pdf' in st.session_state:
            st.download_button("📄 PDF RAPPORT", st.session_state['current_pdf'], st.session_state['current_pdf_name'], "application/pdf", type="primary")

def render_calibration_page():
    st.markdown('<div class="main-header">🎯 Calibration (Fiche Technique)</div>', unsafe_allow_html=True)
    st.info("ℹ️ Les profils constructeurs verrouillent la puissance pour garantir la précision.")

    type_eq = st.radio("Catégorie", ["Groupe Électrogène (GE)", "Camion / Tracteur", "Engin / BTP"], horizontal=True)
    cat_map = {"Groupe Électrogène (GE)": "GE", "Camion / Tracteur": "TRUCK", "Engin / BTP": "OTHER"}
    
    engines = ReferenceEngineLibrary.list_engines_by_type(cat_map[type_eq])
    code = st.selectbox("Profil Constructeur", list(engines.keys()), format_func=lambda x: engines[x])
    meta = ReferenceEngineLibrary.get_metadata(code)
    
    st.markdown(f"""
    <div class="tech-card">
        <b>📋 FICHE TECHNIQUE CERTIFIÉE :</b> {meta.get('name')}<br>
        • <b>Architecture :</b> {meta.get('cylinders', 'Standard')}<br>
        • <b>Aspiration :</b> {meta.get('aspiration', 'Standard')}<br>
        • <b>Injection :</b> {meta.get('injection', 'Standard')}<br>
        <i>{meta.get('desc')}</i>
    </div>
    """, unsafe_allow_html=True)

    is_generic = "GENERIC" in code
    base_kw = meta.get('power', 100.0)

    if type_eq == "Groupe Électrogène (GE)":
        display_val = base_kw / 0.8; unit_label = "kVA (Apparent)"
    elif type_eq == "Camion / Tracteur":
        display_val = base_kw * 1.36; unit_label = "CV (DIN)"
    else:
        display_val = base_kw; unit_label = "kW (Mécanique)"

    c1, c2, c3 = st.columns(3)
    eid = c1.text_input("Immatriculation")
    name = c2.text_input("Nom Opérationnel")
    user_pwr = c3.number_input(
        f"Puissance Nominale ({unit_label})", value=float(display_val), 
        disabled=not is_generic, help="Verrouillé pour les profils constructeurs."
    )

    if st.button("ENREGISTRER LA CALIBRATION"):
        if eid and name:
            if type_eq == "Groupe Électrogène (GE)": final_kw = user_pwr * 0.8
            elif type_eq == "Camion / Tracteur": final_kw = user_pwr / 1.36
            else: final_kw = user_pwr
            try:
                st.session_state.db.execute_write(
                    "INSERT INTO equipment (equipment_id, equipment_name, profile_base, power_kw) VALUES (?, ?, ?, ?)", 
                    (eid, name, code, final_kw)
                )
                st.success(f"✅ {name} Calibré"); time.sleep(1); st.rerun()
            except: 
                st.error("ID existant.")
        else: 
            st.warning("ID et Nom requis.")

    st.markdown("### 📋 Parc Calibré")
    rows = st.session_state.db.execute_read("SELECT equipment_id, equipment_name, profile_base, power_kw FROM equipment ORDER BY created_at DESC")
    if rows: st.dataframe(rows, use_container_width=True)

def render_learning_page():
    st.markdown('<div class="main-header">🧠 Intelligence</div>', unsafe_allow_html=True)
    if st.session_state.get('license_tier') == 'CORPORATE':
        if st.button("Lancer Apprentissage"): 
            st.session_state.learning.batch_learn_from_all_equipment(st.session_state.db)
            st.success("OK")
    else: 
        st.warning("Réservé CORPORATE")

# --- NOUVEAU MODULE : PAGE PROFIL ---
def render_profile_page():
    st.markdown('<div class="main-header">👤 Mon Profil & Sécurité</div>', unsafe_allow_html=True)
    
    username = st.session_state.get('user')
    if not username: return

    db = st.session_state.db
    user_data = db.execute_read("SELECT * FROM users WHERE username = ?", (username,))
    
    if not user_data:
        st.error("Impossible de charger le profil.")
        return

    user = user_data[0] 

    with st.container():
        c1, c2, c3 = st.columns(3)
        c1.info(f"**Identifiant :** {user['username']}")
        c2.info(f"**Rôle :** {user['role']}")
        c3.success(f"**Licence :** {user['license_tier']}")
        
        c4, c5 = st.columns(2)
        c4.write(f"📧 **Email :** {user['email'] if user['email'] else 'Non renseigné'}")
        c5.write(f"🏢 **Société :** {user['company_name'] if user['company_name'] else 'Non renseignée'}")

    st.markdown("---")
    st.subheader("🔐 Modifier mon mot de passe")
    
    with st.form("pwd_change_form"):
        col_a, col_b = st.columns(2)
        current_pwd = col_a.text_input("Mot de passe actuel", type="password")
        new_pwd = col_b.text_input("Nouveau mot de passe", type="password")
        confirm_pwd = col_b.text_input("Confirmer le nouveau", type="password")
        
        if st.form_submit_button("METTRE À JOUR LE MOT DE PASSE", type="primary"):
            if new_pwd != confirm_pwd:
                st.error("❌ Les nouveaux mots de passe ne correspondent pas.")
            elif len(new_pwd) < 4:
                st.error("❌ Le mot de passe est trop court.")
            else:
                stored_hash = user['password_hash']
                if isinstance(stored_hash, str): stored_hash = stored_hash.encode('utf-8')
                
                if bcrypt.checkpw(current_pwd.encode('utf-8'), stored_hash):
                    new_salt = bcrypt.gensalt()
                    new_hash = bcrypt.hashpw(new_pwd.encode('utf-8'), new_salt)
                    try:
                        db.execute_write("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, username))
                        st.success("✅ Mot de passe modifié ! Déconnexion..."); time.sleep(2)
                        st.session_state.clear(); st.rerun()
                    except Exception as e: st.error(f"Erreur technique : {str(e)}")
                else: st.error("❌ L'ancien mot de passe est incorrect.")

def render_admin_page():
    if st.session_state.get('role') != 'admin': return
    st.markdown('<div class="main-header">🔐 Admin QG</div>', unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["⚙️ Config", "💰 Paiements", "👥 Utilisateurs", "💾 Maintenance"])
    
    with t1:
        st.subheader("Paramètres Globaux")
        current_aging = st.session_state.db.get_config_value("AGING_FACTOR", "1.05")
        c1, c2 = st.columns([3, 1])
        new_aging = c1.slider("Facteur Vieillissement", 1.0, 1.3, float(current_aging), 0.01)
        c2.metric("Actuel", f"x{new_aging}")
        if st.button("💾 Sauvegarder la Configuration"):
            st.session_state.db.set_config_value("AGING_FACTOR", new_aging)
            st.success("Mis à jour !"); time.sleep(1); st.rerun()

    with t2:
        st.subheader("1. En Attente")
        pendings = st.session_state.db.execute_read("SELECT * FROM transactions WHERE status = 'PENDING'")
        if not pendings: st.info("Aucun paiement en attente.")
        for p in pendings:
            c1, c2, c3 = st.columns([2,1,1])
            c1.write(f"📅 {p['timestamp']} | {p['username']} | {p['amount']}F (ID: {p['mobile_money_id']})")
            
            if c2.button("✅", key=f"v_{p['tx_ref']}"):
                st.session_state.db.approve_transaction(p['tx_ref'])
                st.rerun()
                
            if c3.button("❌", key=f"x_{p['tx_ref']}"):
                st.session_state.db.reject_transaction(p['tx_ref'])
                st.rerun()
            
        st.markdown("---")
        st.subheader("2. Historique")
        history = st.session_state.db.execute_read("SELECT * FROM transactions WHERE status != 'PENDING' ORDER BY timestamp DESC LIMIT 50")
        if history: st.dataframe(history, use_container_width=True)

    with t3: 
        st.dataframe(st.session_state.db.execute_read("SELECT * FROM users"), use_container_width=True)
        
    with t4:
        db_files = [f for f in os.listdir('.') if f.endswith('.db')]
        if db_files:
            with open(db_files[0], "rb") as f: 
                st.download_button("⬇️ Backup", f, file_name="BACKUP.db")
        up = st.file_uploader("Restaurer .db")
        if up and st.button("RESTAURER"):
            with open("gen_control_v1_1_secure.db", "wb") as f: f.write(up.getbuffer())
            st.success("Restauré !"); time.sleep(2); st.rerun()

# --- POINT D'ENTRÉE ---
def main():
    init_session()
    
    if 'auth_token' not in st.session_state:
        render_auth()
        return

    menu = render_sidebar()

    if menu == "📱 Audit Terrain": render_audit_page()
    elif menu == "🎯 Calibration": render_calibration_page()
    elif menu == "👤 Mon Profil": render_profile_page() # <--- LIEN VERS LA PAGE
    elif menu == "🧠 Intelligence": render_learning_page()
    elif menu == "🔐 Admin": render_admin_page()
    elif menu == "💎 Offres & Licences": render_payment_page_local()

if __name__ == "__main__":
    main()