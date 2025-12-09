# ==============================================================================
# GEN-CONTROL LITE V1.1 - Module Analytics & Intelligence Artificielle
# Comprend : Détection Statistique (Z-Score) & Apprentissage Adaptatif (ML)
# ==============================================================================

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# 1. MODÈLES DE DONNÉES
# =============================================================================

@dataclass
class LoadScenario:
    code: str
    category: str
    description: str
    load_min: float
    load_typ: float
    load_max: float
    power_range_kw: Tuple[float, float]
    typical_duration_h: float

@dataclass
class AnomalyDetectionResult:
    verdict: str
    z_score: float
    deviation_pct: float
    confidence: float
    recommendations: List[str]
    severity: str
    threshold_exceeded: Dict[str, float]
    historical_baseline: Optional[float] = None
    historical_std: Optional[float] = None

@dataclass
class EquipmentLearningOverride:
    equipment_id: str
    scenario_code: str
    learned_load_typ: float
    learned_load_min: float
    learned_load_max: float
    n_samples: int
    confidence_score: float
    last_updated: datetime
    is_active: bool = True

# =============================================================================
# 2. GESTIONNAIRE DE SCÉNARIOS (SOURCES ISO)
# =============================================================================

class DetailedLoadFactorManager:
    
    LOAD_SCENARIOS: Dict[str, LoadScenario] = {
        # --- GROUPE ELECTROGENE (GE) ---
        'GE_OFFICE_AC': LoadScenario('GE_OFFICE_AC', 'GE', 'Bureaux avec climatisation', 0.30, 0.40, 0.50, (20, 500), 8.0),
        'GE_HOSPITAL': LoadScenario('GE_HOSPITAL', 'GE', 'Hôpital - Charge critique', 0.60, 0.75, 0.85, (100, 2000), 24.0),
        'GE_INDUSTRY_HEAVY': LoadScenario('GE_INDUSTRY_HEAVY', 'GE', 'Industrie lourde continue', 0.75, 0.85, 0.95, (500, 10000), 24.0),
        
        # --- CAMIONS (TRUCK) ---
        'TRUCK_CITY_DELIVERY': LoadScenario('TRUCK_CITY_DELIVERY', 'TRUCK', 'Livraison urbaine / Toupie', 0.15, 0.25, 0.35, (150, 450), 6.0),
        'TRUCK_HIGHWAY': LoadScenario('TRUCK_HIGHWAY', 'TRUCK', 'Autoroute chargé', 0.60, 0.70, 0.80, (300, 600), 4.0),
        'TRUCK_MOUNTAIN': LoadScenario('TRUCK_MOUNTAIN', 'TRUCK', 'Route de montagne / Charge lourde', 0.75, 0.85, 0.95, (350, 650), 3.0),
        'TRUCK_OFFROAD': LoadScenario('TRUCK_OFFROAD', 'TRUCK', 'Tout-terrain minier', 0.80, 0.90, 1.05, (400, 800), 8.0),
        
        # --- ENGINS (TP) ---
        'TP_EXCAVATION': LoadScenario('TP_EXCAVATION', 'TP', 'Excavation intensive', 0.60, 0.75, 0.85, (100, 500), 6.0),
        'TP_CRANE': LoadScenario('TP_CRANE', 'TP', 'Grue de levage (Intermittent)', 0.20, 0.30, 0.45, (50, 300), 8.0),
    }
    
    @classmethod
    def get_scenario(cls, scenario_code: str) -> Optional[LoadScenario]:
        return cls.LOAD_SCENARIOS.get(scenario_code)
    
    @classmethod
    def get_scenarios_by_category(cls, category_prefix: str) -> Dict[str, LoadScenario]:
        filtered = {}
        for code, scenario in cls.LOAD_SCENARIOS.items():
            if scenario.category == category_prefix:
                filtered[code] = scenario
            # Fallback : si on demande 'OTHER', on donne accès aux scénarios TP
            elif category_prefix == 'OTHER' and scenario.category == 'TP':
                filtered[code] = scenario
        return filtered

# =============================================================================
# 3. DÉTECTEUR D'ANOMALIES (Z-SCORE + COLD START)
# =============================================================================

class IntelligentAnomalyDetector:
    
    # Seuils de sensibilité
    Z_THRESHOLD_CRITICAL = 3.0
    Z_THRESHOLD_WARNING = 2.0
    
    # Seuils absolus (Cold Start)
    ABS_THRESHOLD_CRITICAL = 25.0 # %
    ABS_THRESHOLD_WARNING = 15.0 # %
    
    RECOMMENDATIONS = {
        'FUEL_THEFT': ["Vérifier la traçabilité carburant", "Contrôler le bouchon de réservoir", "Confronter le chauffeur"],
        'FUEL_LEAK': ["Inspecter le réservoir (fuite)", "Vérifier les joints injecteurs", "Contrôler le circuit de retour"],
        'COLD_START': ["Continuez à enregistrer des audits pour affiner la précision de l'IA"]
    }
    
    def detect_anomaly(self, equipment_id, deviation_pct, historical_deviations=None, scenario_code=None) -> AnomalyDetectionResult:
        if historical_deviations is None: historical_deviations = []
        
        # 1. Calcul Z-Score (Si historique suffisant)
        if len(historical_deviations) >= 3:
            mean_val = np.mean(historical_deviations)
            std_val = np.std(historical_deviations, ddof=1)
            if std_val < 1e-10: std_val = 1.0 # Éviter division par zéro
            z_score = (deviation_pct - mean_val) / std_val
            has_history = True
        else:
            z_score = 0.0
            has_history = False
            
        abs_dev = abs(deviation_pct)
        abs_z = abs(z_score)
        
        # 2. Logique de Décision Hybride
        verdict = "NORMAL"
        severity = "LOW"
        confidence = 0.5
        
        if has_history:
            # Mode Expert : On se fie à la statistique (Habitude de la machine)
            if abs_z > self.Z_THRESHOLD_CRITICAL:
                verdict = "ANOMALIE"
                severity = "CRITICAL"
                confidence = 0.95
            elif abs_z > self.Z_THRESHOLD_WARNING:
                verdict = "SUSPECT"
                severity = "HIGH"
                confidence = 0.80
            else:
                # Filet de sécurité : Si Z-score OK mais écart énorme (>30%), on signale quand même
                if abs_dev > 30.0:
                    verdict = "ANOMALIE"
                    confidence = 0.70
        else:
            # Mode Cold Start : On se fie à la physique pure (seuils fixes)
            if abs_dev > self.ABS_THRESHOLD_CRITICAL:
                verdict = "ANOMALIE"
                severity = "CRITICAL"
                confidence = 0.90
            elif abs_dev > self.ABS_THRESHOLD_WARNING:
                verdict = "SUSPECT"
                severity = "MEDIUM"
                confidence = 0.60
        
        # 3. Génération des recommandations
        recs = []
        if verdict != "NORMAL":
            if deviation_pct < -5.0: # Conso déclarée < Théorie (Peu probable sauf erreur saisie)
                 recs = ["Vérifier calibration compteur (Sous-consommation anormale)"]
            elif deviation_pct > 5.0: # Conso déclarée > Théorie (Vol ou Fuite)
                 recs = self.RECOMMENDATIONS['FUEL_THEFT'] + self.RECOMMENDATIONS['FUEL_LEAK']
        
        return AnomalyDetectionResult(verdict, z_score, deviation_pct, confidence, recs, severity, {})

# =============================================================================
# 4. MOTEUR D'APPRENTISSAGE ADAPTATIF (LE CERVEAU)
# =============================================================================

class AdaptiveLearningEngine:
    """
    Analyse les audits passés pour ajuster les facteurs de charge théoriques (Learning).
    """
    
    def __init__(self, min_samples=1): 
        # min_samples=1 pour la démo (permet d'apprendre dès le 1er audit valide)
        # En production, on mettrait 5 ou 10.
        self.learning_cache = {}
        self.min_samples = min_samples

    def get_equipment_override(self, equipment_id, scenario_code, db_connection) -> Optional[EquipmentLearningOverride]:
        """Récupère le profil appris s'il existe"""
        try:
            query = """
            SELECT load_typ, learned_from_n_samples, confidence_score, last_updated 
            FROM equipment_load_overrides
            WHERE equipment_id = ? AND scenario_code = ? AND is_active = 1
            """
            rows = db_connection.execute_read(query, (equipment_id, scenario_code))
            if rows:
                r = rows[0]
                return EquipmentLearningOverride(
                    equipment_id, scenario_code, 
                    r['load_typ'], 0.0, 0.0, 
                    r['learned_from_n_samples'], r['confidence_score'],
                    datetime.fromisoformat(r['last_updated']), True
                )
        except Exception as e:
            logger.error(f"Erreur lecture override: {e}")
        return None

    def batch_learn_from_all_equipment(self, db) -> Dict[str, int]:
        """
        L'ALGORITHME D'APPRENTISSAGE :
        1. Cherche les équipements avec des audits 'NORMAL'.
        2. Calcule le ratio moyen (Réel / Théorique).
        3. Met à jour la charge théorique pour coller à la réalité.
        """
        stats = {'successful': 0, 'failed': 0}
        
        try:
            # 1. Identifier les candidats (Couple Equipement/Scenario avec assez d'audits NORMAUX)
            query_candidates = """
            SELECT equipment_id, scenario_code, COUNT(*) as n_samples
            FROM audits
            WHERE verdict = 'NORMAL' 
            GROUP BY equipment_id, scenario_code
            HAVING n_samples >= ?
            """
            candidates = db.execute_read(query_candidates, (self.min_samples,))
            
            for cand in candidates:
                eq_id = cand['equipment_id']
                sc_code = cand['scenario_code']
                n = cand['n_samples']
                
                # 2. Analyser les performances réelles
                # On ne prend QUE les audits validés comme "NORMAL" (on n'apprend pas des vols !)
                query_data = """
                SELECT fuel_declared_l, estimated_typ
                FROM audits
                WHERE equipment_id = ? AND scenario_code = ? AND verdict = 'NORMAL'
                """
                audits = db.execute_read(query_data, (eq_id, sc_code))
                
                ratios = []
                for a in audits:
                    if a['estimated_typ'] > 0:
                        # Ratio > 1.0 signifie que la machine consomme plus que la théorie
                        # Ratio < 1.0 signifie qu'elle consomme moins
                        ratios.append(a['fuel_declared_l'] / a['estimated_typ'])

                if ratios:
                    # Calcul de la moyenne des ratios
                    avg_ratio = sum(ratios) / len(ratios)
                    
                    # On charge le scénario de base pour avoir le point de départ
                    base_scenario = DetailedLoadFactorManager.get_scenario(sc_code)
                    if base_scenario:
                        base_load = base_scenario.load_typ
                        
                        # APPRENTISSAGE : Nouvelle Charge = Charge Base * Ratio Observé
                        learned_load = base_load * avg_ratio
                        
                        # Bornes de sécurité (pour éviter des dérives absurdes)
                        learned_load = max(0.05, min(1.0, learned_load))
                        
                        # 3. Sauvegarde dans la base de connaissances
                        timestamp = datetime.now().isoformat()
                        
                        db.execute_write("""
                        INSERT OR REPLACE INTO equipment_load_overrides 
                        (equipment_id, scenario_code, load_min, load_typ, load_max, learned_from_n_samples, confidence_score, last_updated, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """, (eq_id, sc_code, learned_load*0.8, learned_load, learned_load*1.2, n, 0.9, timestamp))
                        
                        stats['successful'] += 1
                        
        except Exception as e:
            logger.error(f"Erreur Learning Batch: {e}")
            stats['failed'] += 1
            
        return stats