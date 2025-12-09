# ==============================================================================
# REPORTS.PY - Générateur PDF (Watermark & Branding)
# ==============================================================================
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import grey, black, red, green, orange
from datetime import datetime

class PDFReportGenerator:
    
    def generate_audit_report(self, data, license_tier='DISCOVERY'):
        """
        Génère un rapport PDF avec marquage commercial.
        license_tier: 'DISCOVERY' (Filigrane), 'PRO' (Standard), 'CORPORATE' (Certifié)
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # --- 1. EN-TÊTE & LOGO ---
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(black)
        c.drawString(50, height - 50, "DI-SOLUTIONS | GEN-CONTROL")
        
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 65, "Expertise Audit & Efficacité Énergétique")
        
        # Sous-titre dynamique
        if license_tier == 'CORPORATE':
            subtitle = "RAPPORT CERTIFIÉ - LICENCE ENTREPRISE"
            c.setFillColor(green)
        elif license_tier == 'PRO':
            subtitle = "RAPPORT D'AUDIT CARBURANT (PRO)"
            c.setFillColor(black)
        else: # Discovery
            subtitle = "RAPPORT D'ÉVALUATION (GRATUIT)"
            c.setFillColor(grey)
            
        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(width - 50, height - 50, subtitle)
        
        c.setStrokeColor(grey)
        c.line(50, height - 80, width - 50, height - 80)
        
        # --- 2. WATERMARK ANTI-COMMERCIAL (DISCOVERY) ---
        if license_tier == 'DISCOVERY':
            c.saveState()
            c.translate(width / 2, height / 2)
            c.rotate(45)
            c.setFont("Helvetica-Bold", 60)
            c.setFillColor(grey, alpha=0.15) # Gris transparent léger
            c.drawCentredString(0, 0, "DÉMONSTRATION")
            c.setFont("Helvetica-Bold", 40)
            c.drawCentredString(0, -50, "NON VALIDE COMMERCIALEMENT")
            c.restoreState()

        # --- 3. CONTENU ---
        y = height - 120
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "1. INFORMATIONS GÉNÉRALES")
        y -= 20
        
        info_data = [
            ("ID Audit:", data['audit_uuid']),
            ("Date:", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Opérateur:", data['user']),
            ("Licence:", license_tier),
            ("Équipement:", data['equipment_name']),
            ("Scénario:", data['scenario'])
        ]
        
        c.setFont("Helvetica", 10)
        for label, val in info_data:
            c.drawString(70, y, label)
            c.drawString(200, y, str(val))
            y -= 15

        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "2. RÉSULTATS ANALYSE")
        y -= 30
        
        verdict = data['verdict']
        box_color = green if verdict == 'NORMAL' else (orange if verdict == 'SUSPECT' else red)
        
        c.setFillColor(box_color)
        c.rect(50, y - 10, width - 100, 30, fill=1, stroke=0)
        c.setFillColor(black if verdict == 'SUSPECT' else (1,1,1))
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2, y, f"VERDICT : {verdict}")
        
        y -= 40
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        
        metrics = [
            ("Carburant Déclaré:", f"{data['fuel_declared']:.1f} L"),
            ("Estimation Théorique:", f"{data['fuel_estimated']:.1f} L"),
            ("Écart:", f"{data['deviation']:+.1f} %"),
            ("Heures moteur:", f"{data['hours']:.1f} h")
        ]
        
        for label, val in metrics:
            c.drawString(70, y, label)
            c.drawRightString(width - 70, y, str(val))
            y -= 20

        # --- 4. FOOTER ---
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(grey)
        footer_text = f"Généré par GEN-CONTROL V1.1 ({license_tier}) - DI-SOLUTIONS"
        c.drawCentredString(width / 2, 30, footer_text)
        
        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer