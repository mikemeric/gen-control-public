# ==============================================================================
# GEN-CONTROL - Moteur Physique Hybride "ISO-EXPERT"
# Combinaison : Régression Polyfit + ISO 15550 Complexe + Sécurité Métier
# ==============================================================================
import math
import numpy as np
import logging

# Configuration logging silencieux pour l'interface
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class AtmosphericParams:
    """
    Modèle atmosphérique avancé.
    Convertit l'altitude en Pression Atmosphérique (kPa) pour les formules ISO.
    """
    T_REF_K = 298.15  # 25°C en Kelvin
    P_REF_KPA = 100.0 # Pression ref ISO

    def __init__(self, altitude_m=0, temperature_c=25, humidity_pct=30):
        self.altitude_m = altitude_m
        self.temperature_c = temperature_c
        self.humidity_pct = humidity_pct
        # Température liquide refroidissement (Hypothèse standard si pas de capteur)
        self.coolant_temp_c = 80.0 

    @property
    def pressure_kpa(self):
        """
        Calcule la pression atmosphérique standard en fonction de l'altitude.
        Formule Barométrique Internationale.
        """
        # P0 * (1 - 2.25577e-5 * h)^5.25588
        p0 = 101.325
        if self.altitude_m < 0: return p0
        return p0 * math.pow(1 - 2.25577e-5 * self.altitude_m, 5.25588)

class ReferenceEngineLibrary:
    _ENGINES = {
        # ==========================================
        # 1. GROUPES ÉLECTROGÈNES (GE)
        # ==========================================
        
        # PROFIL GÉNÉRIQUE
        "GENERIC_GE": {
            "name": "🟢 GÉNÉRIQUE GE (Saisie Manuelle)", 
            "type": "GE", 
            "fixed_power_kw": None 
        },

        # PROFILS CONSTRUCTEURS
        "PERKINS_1104_100": {
            "name": "Perkins 1104C-44TAG2 (100 kVA)", "type": "GE",
            "fixed_power_kw": 80.0, "display_rating": 100.0,
            "calibration_points": [(40.0, 11.8), (80.0, 22.6)] # (kW, L/h) -> 50%, 100%
        },
        "PERKINS_1106_200": {
            "name": "Perkins 1106A-70TAG3 (200 kVA)", "type": "GE",
            "fixed_power_kw": 160.0, "display_rating": 200.0,
            "calibration_points": [(80.0, 20.6), (160.0, 41.6)]
        },
        "BAUDOUIN_6M21_400": {
            "name": "Baudouin 6M21G440/5 (400 kVA)", "type": "GE",
            "fixed_power_kw": 320.0, "display_rating": 400.0,
            "calibration_points": [(160.0, 42.1), (320.0, 84.6)]
        },
        "CUMMINS_KTA19_450": {
            "name": "Cummins KTA19-G3 (450 kVA)", "type": "GE",
            "fixed_power_kw": 360.0, "display_rating": 450.0,
            "calibration_points": [(180.0, 49.0), (360.0, 97.0)]
        },
        "CAT_C15_500": {
            "name": "Caterpillar C15 ACERT (500 kVA)", "type": "GE",
            "fixed_power_kw": 400.0, "display_rating": 500.0,
            "calibration_points": [(200.0, 53.0), (400.0, 104.0)]
        },
        
        # ==========================================
        # 2. CAMIONS (TRUCK)
        # ==========================================

        # PROFIL GÉNÉRIQUE
        "GENERIC_TRUCK": {
            "name": "🟢 GÉNÉRIQUE CAMION (Saisie Manuelle)", 
            "type": "TRUCK", 
            "fixed_power_kw": None 
        },

        # PROFILS CONSTRUCTEURS
        "SINOTRUK_HOWO_371": {
            "name": "Sinotruk HOWO 371 (Weichai WD615)", "type": "TRUCK",
            "fixed_power_kw": 273.0, "display_rating": 371.0,
            "calibration_points": [(136.5, 31.5), (273.0, 68.5)]
        },
        "MERCEDES_ACTROS_V6": {
            "name": "Mercedes Actros 2044 (OM501 LA)", "type": "TRUCK",
            "fixed_power_kw": 320.0, "display_rating": 435.0,
            "calibration_points": [(160.0, 34.2), (320.0, 76.0)]
        },
        "VOLVO_D13_FMX": {
            "name": "Volvo FMX 440 (D13)", "type": "TRUCK",
            "fixed_power_kw": 324.0, "display_rating": 440.0,
            "calibration_points": [(162.0, 33.0), (324.0, 71.5)]
        },
        "RENAULT_KERAX_DXI11": {
            "name": "Renault Kerax 380 DXi", "type": "TRUCK",
            "fixed_power_kw": 280.0, "display_rating": 380.0,
            "calibration_points": [(140.0, 29.5), (280.0, 65.8)]
        },

        # ==========================================
        # 3. ENGINS (OTHER)
        # ==========================================
        "GENERIC_ISO_DIESEL": {
            "name": "🟢 GÉNÉRIQUE ENGIN (Saisie Manuelle)", 
            "type": "OTHER", 
            "fixed_power_kw": None
        }
    }

    @classmethod
    def list_engines_by_type(cls, cat_code):
        filtered = {}
        for code, data in cls._ENGINES.items():
            if cat_code == "OTHER":
                if data["type"] == "OTHER": filtered[code] = data["name"]
            elif data["type"] == cat_code:
                filtered[code] = data["name"]
        
        # Sécurité anti-liste vide
        if not filtered:
             filtered["GENERIC_ISO_DIESEL"] = "Générique Standard"
             
        return filtered

    @classmethod
    def get_metadata(cls, profile_code):
        return cls._ENGINES.get(profile_code, cls._ENGINES["GENERIC_ISO_DIESEL"])

class IsoWillansModel:
    """
    Modèle Hybride:
    1. Calibration: Régression Linéaire (Polyfit) sur les points ISO.
    2. Correction: Formules complexes ISO 15550 (Vapeur, Pression partielle).
    3. Sécurité: Plancher technique (Min 2.0 L/h).
    4. Business: Facteur Cameroun (+5%).
    """
    
    def __init__(self, a: float, b: float, nominal_power_kw: float):
        self.a = float(a) # Pente (Slope)
        self.b = float(b) # Intercepte (Frottements)
        self.nominal_power_kw = float(nominal_power_kw)

    @classmethod
    def from_reference_data(cls, profile_code: str, client_power_kw: float) -> 'IsoWillansModel':
        meta = ReferenceEngineLibrary.get_metadata(profile_code)
        
        # 1. CALIBRATION AVANCÉE (POLYFIT)
        if 'calibration_points' in meta:
            points = meta['calibration_points']
            # Séparation X (Puissance) et Y (Conso)
            powers = np.array([p[0] for p in points])
            consumptions = np.array([p[1] for p in points])
            
            # Régression Linéaire (Degré 1)
            # y = ax + b
            coeffs = np.polyfit(powers, consumptions, 1)
            a = coeffs[0]
            b = coeffs[1]
            
            # Mise à l'échelle si la puissance client diffère du profil de base
            # (Ex: Client a un moteur 400CV mais on utilise le profil 440CV)
            ref_power = meta.get('fixed_power_kw')
            if ref_power and ref_power != client_power_kw:
                scale = client_power_kw / ref_power
                b = b * scale # On adapte les frottements à la taille du moteur
            
            return cls(a, b, client_power_kw)
            
        else:
            # Mode Générique (Fallback)
            est_max = client_power_kw * 0.24
            b = est_max * 0.08
            a = (est_max - b) / client_power_kw
            return cls(a, b, client_power_kw)

    # --- SOUS-FONCTIONS COMPLEXES ISO 15550 ---
    
    def _calculate_vapor_pressure(self, temp_k):
        """Formule d'Antoine simplifiée (ISO 15550 Annexe C)"""
        T_c = temp_k - 273.15
        if T_c < -50: T_c = -50
        if T_c > 100: T_c = 100
        
        num = 17.625 * T_c
        den = T_c + 243.04
        return 0.61094 * np.exp(num / den)

    def _calculate_iso_correction(self, atm: AtmosphericParams, qc=45.0):
        """Calcul du facteur Alpha (Complex)"""
        T_air_k = atm.temperature_c + 273.15
        T_cool_k = atm.coolant_temp_c + 273.15
        
        # 1. Pression de vapeur
        P_vap = self._calculate_vapor_pressure(T_air_k)
        
        # 2. Pression sèche (P_dry)
        P_dry = atm.pressure_kpa - P_vap
        if P_dry <= 0: P_dry = 0.1
        
        # 3. Facteur fa (Atmosphère)
        # fa = (P_dry/100)^0.7 * (298/T_air)^1.2 * (298/T_cool)^1.0
        term_p = np.power(P_dry / 100.0, 0.7)
        term_t = np.power(298.15 / T_air_k, 1.2)
        # On simplifie le terme coolant (souvent constant)
        
        fa = term_p * term_t
        
        # 4. Facteur fm (Moteur)
        fm = 0.036 * (qc - 1.14)
        fm = max(0.2, min(1.2, fm))
        
        # Alpha total
        alpha = np.power(fa, fm)
        return alpha

    def predict_consumption(self, load_pct: float, atmospheric_conditions: AtmosphericParams = None):
        if load_pct < 0: load_pct = 0
        if load_pct > 110: load_pct = 110
        
        # 1. Calcul Puissance Demandée
        p_load = self.nominal_power_kw * (load_pct / 100.0)
        
        # 2. Modèle de Willans (Base)
        base_consumption = (self.a * p_load) + self.b
        
        # 3. SAFETY FLOOR (Sécurité Métier)
        # Empêche les résultats négatifs ou absurdes à très faible charge
        if base_consumption < 2.0:
            base_consumption = 2.0
            
        # 4. CORRECTION ISO COMPLEXE
        correction = 1.0
        if atmospheric_conditions:
            # ISO calcule alpha (facteur de puissance disponible). 
            # Si alpha < 1 (il fait chaud/haut), le moteur perd de la puissance.
            # Pour maintenir la MÊME charge (p_load), il doit injecter plus.
            # Donc Conso_Corrigée = Conso_Base / Alpha
            alpha = self._calculate_iso_correction(atmospheric_conditions)
            
            # Sécurité anti-divergence
            if alpha < 0.5: alpha = 0.5
            if alpha > 1.5: alpha = 1.5
            
            correction = 1.0 / alpha

        # 5. BUSINESS LOGIC : AGING FACTOR
        # Le facteur Cameroun (+5%)
        AGING_FACTOR = 1.05
        
        final_consumption = base_consumption * correction * AGING_FACTOR
        
        return {
            'consumption_corrected_l_h': final_consumption,
            'correction_factor': correction
        }