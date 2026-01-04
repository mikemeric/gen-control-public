# ==============================================================================
# PHYSICS.PY - VERSION CORRECTIVE (Données Réelles)
# ==============================================================================
import math

class AtmosphericParams:
    def __init__(self, altitude_m, temperature_c):
        self.altitude_m = altitude_m
        self.temperature_c = temperature_c

class ReferenceEngineLibrary:
    ENGINE_DB = {
        "GENERIC_GE": {"name": "GÉNÉRIQUE GE (Saisie Manuelle)", "type": "GE", "power": 80.0, "cylinders": "Variable", "aspiration": "Variable", "injection": "Standard", "desc": "Profil universel."},
        "CAT_C15_GEN": {"name": "CATERPILLAR C15 (500 kVA)", "type": "GE", "power": 400.0, "cylinders": "6 en ligne (15.2L)", "aspiration": "Turbo AA", "injection": "MEUI", "desc": "Standard Industriel & Minier."},
        "PERKINS_1104": {"name": "PERKINS 1104C-44TAG2 (100 kVA)", "type": "GE", "power": 80.0, "cylinders": "4 en ligne (4.4L)", "aspiration": "Turbo Intercooler", "injection": "Directe", "desc": "Standard PME."},
        "CUMMINS_KTA19": {"name": "CUMMINS KTA19-G4 (600 kVA)", "type": "GE", "power": 480.0, "cylinders": "6 en ligne (19L)", "aspiration": "Turbo Aftercooled", "injection": "PT", "desc": "Moteur lourd."},
        "GENERIC_TRUCK": {"name": "GÉNÉRIQUE CAMION (Saisie Manuelle)", "type": "TRUCK", "power": 294.0, "cylinders": "Variable", "aspiration": "Turbo", "injection": "Directe", "desc": "Tracteurs routiers."},
        "SINOTRUK_WD615": {"name": "SINOTRUK HOWO 371 (WD615.47)", "type": "TRUCK", "power": 273.0, "cylinders": "6 en ligne (9.7L)", "aspiration": "Turbo Intercooler", "injection": "Directe", "desc": "Bennes HOWO."},
        "VOLVO_D13": {"name": "VOLVO D13 (440 CV)", "type": "TRUCK", "power": 324.0, "cylinders": "6 en ligne (12.8L)", "aspiration": "Turbo VGT", "injection": "UIS", "desc": "Tracteurs FMX/FH."},
        "MERCEDES_OM501": {"name": "MERCEDES ACTROS (V6 400 CV)", "type": "TRUCK", "power": 294.0, "cylinders": "V6 (11.9L)", "aspiration": "Turbo", "injection": "PLD", "desc": "Actros MP2/MP3."},
        "GENERIC_OTHER": {"name": "GÉNÉRIQUE ENGIN (Saisie Manuelle)", "type": "OTHER", "power": 150.0, "cylinders": "Variable", "aspiration": "Turbo", "injection": "Directe", "desc": "Pelles, Chargeuses."},
        "CAT_336": {"name": "PELLE CAT 336 (C9.3)", "type": "OTHER", "power": 234.0, "cylinders": "6 en ligne (9.3L)", "aspiration": "Turbo", "injection": "Common Rail", "desc": "Pelle carrière."}
    }

    @staticmethod
    def list_engines_by_type(type_filter):
        return {k: v['name'] for k, v in ReferenceEngineLibrary.ENGINE_DB.items() if v['type'] == type_filter}

    @staticmethod
    def get_metadata(code):
        return ReferenceEngineLibrary.ENGINE_DB.get(code, {})

class IsoWillansModel:
    def __init__(self, k_factor=0.25, b_factor=0.08, p_nom_kw=100):
        self.k = k_factor; self.b = b_factor; self.p_nom = p_nom_kw

    @classmethod
    def from_reference_data(cls, engine_code, power_override_kw=None):
        meta = ReferenceEngineLibrary.get_metadata(engine_code)
        base_power = power_override_kw if power_override_kw else meta.get('power', 100)
        eng_type = meta.get('type', 'GE')
        if eng_type == 'GE': return cls(k=0.24, b=0.07, p_nom_kw=base_power)
        elif eng_type == 'TRUCK': return cls(k=0.22, b=0.09, p_nom_kw=base_power)
        else: return cls(k=0.26, b=0.10, p_nom_kw=base_power)

    def predict_consumption(self, load_pct, atmospheric_params, aging_factor=1.05):
        load_decimal = load_pct / 100.0
        alt_factor = 1 + (max(0, atmospheric_params.altitude_m - 1000) / 10000)
        temp_factor = 1 + (max(0, atmospheric_params.temperature_c - 25) / 500)
        fuel_kwh = (self.k * load_decimal) + self.b
        fuel_l_h = self.p_nom * fuel_kwh * alt_factor * temp_factor * aging_factor
        return {"consumption_corrected_l_h": fuel_l_h, "load_factor_used": load_decimal}