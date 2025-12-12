# ==============================================================================
# PAYMENTS.PY - V1.1.3 (Correction Tarifaire)
# ==============================================================================
import uuid
import streamlit as st
import time

def render_payment_page():
    st.markdown("## 💎 Abonnement GEN-CONTROL PRO")
    st.info("Débloquez les audits illimités et supprimez le filigrane 'Démonstration'.")
    
    user = st.session_state['user']
    db = st.session_state.db
    pending = db.execute_read("SELECT * FROM transactions WHERE username = ? AND status = 'PENDING'", (user,))
    
    if pending:
        st.warning(f"⏳ **Paiement en cours de validation** (Réf: `{pending[0]['tx_ref']}`)")
        if st.button("🔄 Rafraîchir"): st.rerun()
        return

    # TABLEAU COMPARATIF (ANCRAGE PRIX CORRIGÉ)
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("""
        <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; border:1px solid #ddd; opacity:0.8">
            <h3 style="color:#003366">🏢 CORPORATE</h3>
            <p><strong>Usines, Mines & Grandes Flottes</strong></p>
            <ul>
                <li>IA Active & Apprentissage</li>
                <li>Déploiement Serveur Local</li>
                <li>Support Ingénieur Dédié</li>
            </ul>
            <h2 style="color:#003366">100 000 F <small>/ mois</small></h2>
            <em style="font-size:0.8em">Facturation annuelle (1.2M) ou sur devis</em>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div style="background-color:#fff3cd; padding:20px; border-radius:10px; border:2px solid #ffc107; box-shadow: 0 4px 6px rgba(0,0,0,0.1)">
            <h3 style="color:#856404">🚀 PRO (Standard)</h3>
            <p><strong>PME, Transporteurs & Experts</strong></p>
            <ul>
                <li>✅ <strong>Audits Illimités</strong></li>
                <li>✅ <strong>Rapports PDF Certifiés</strong></li>
                <li>✅ <strong>Maintenance Predictor</strong></li>
            </ul>
            <h2 style="color:#d39e00">15 000 F <small>/ mois</small></h2>
            <p><em>Sans engagement</em></p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    st.success("""
    **POUR ACTIVER LA VERSION PRO (15 000 F) :**
    1. Faites un dépôt OM (Bientôt) / MOMO au **671 89 40 95** (Emeri Tchamdjio Nkouetcha).
    2. Entrez l'ID de la transaction ci-dessous.
    """)
    
    with st.form("manual_pay_form"):
        mobile_id = st.text_input("ID Transaction (Reçu par SMS)", placeholder="Ex: PP231209.1542.A87654")
        if st.form_submit_button("✅ Valider mon paiement"):
            if len(mobile_id) < 5:
                st.error("ID invalide.")
            else:
                tx_ref = f"MAN-{uuid.uuid4().hex[:6].upper()}"
                db.declare_manual_payment(tx_ref, user, 15000, mobile_id)
                st.balloons()
                st.success("Demande envoyée ! Activation sous 1h.")
                time.sleep(2)
                st.rerun()