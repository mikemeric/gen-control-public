# ==============================================================================
# PAYMENTS.PY - Guichet Manuel "Low-Tech"
# ==============================================================================
import uuid
import streamlit as st
import time

def render_payment_page():
    st.markdown("## 💎 Abonnement GEN-CONTROL PRO")
    st.info("Débloquez les audits illimités et supprimez le filigrane 'Démonstration'.")
    
    # Vérifier si l'utilisateur a déjà une demande en attente
    user = st.session_state['user']
    db = st.session_state.db
    pending = db.execute_read("SELECT * FROM transactions WHERE username = ? AND status = 'PENDING'", (user,))
    
    if pending:
        st.warning("⏳ **Votre paiement est en cours de vérification.**")
        st.write(f"Référence : `{pending[0]['tx_ref']}`")
        st.write("Dès réception de votre transfert, l'accès sera débloqué (Délai : ~1 heure).")
        if st.button("🔄 Rafraîchir le statut"):
            st.rerun()
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### Offre Mensuelle
        - **Audits Illimités**
        - **Rapports PDF Propres**
        - **Support Prioritaire**
        
        # 15 000 FCFA <small>/ mois</small>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("### 📲 Comment payer ?")
        st.success("""
        **1. Effectuez un transfert Mobile Money de 15 000 F :**
        
        👉 **Orange Money / MTN**
        👉 Numéro : **671 89 40 95**
        👉 Nom : **Dr Tchamdjio (DI-SOLUTIONS)**
        """)
        
        with st.form("manual_pay_form"):
            st.write("**2. Confirmez votre paiement ici :**")
            mobile_id = st.text_input("ID de la Transaction (Reçu par SMS)", placeholder="Ex: PP231209.1542.A87654")
            
            if st.form_submit_button("✅ J'ai envoyé l'argent"):
                if len(mobile_id) < 5:
                    st.error("Veuillez saisir un ID de transaction valide.")
                else:
                    tx_ref = f"MAN-{uuid.uuid4().hex[:6].upper()}"
                    db.declare_manual_payment(tx_ref, user, 15000, mobile_id)
                    st.balloons()
                    st.success("Demande enregistrée ! Nous vérifions et activons votre compte.")
                    time.sleep(2)
                    st.rerun()