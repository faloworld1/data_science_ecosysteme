"""
Blood Pressure Anomaly Detection Module
Detects anomalies based on medical thresholds and optionally uses ML model
"""

import json
import logging
from typing import Dict, Tuple, Optional
import pickle
import os

logger = logging.getLogger(__name__)


class BloodPressureAnomalyDetector:
    """
    Detects blood pressure anomalies using medical thresholds.
    
    Reference categories:
    - NORMAL: SBP < 120 and DBP < 80
    - ELEVATED: SBP 120-129 and DBP < 80
    - HYPERTENSION STAGE 1: SBP 130-139 or DBP 80-89
    - HYPERTENSION STAGE 2: SBP ≥ 140 or DBP ≥ 90
    - HYPERTENSIVE CRISIS: SBP > 180 and/or DBP > 120
    - HYPOTENSION: SBP < 90 or DBP < 60
    """
    
    # Medical thresholds (mmHg)
    THRESHOLDS = {
        "SYSTOLIC_NORMAL_MAX": 120,
        "SYSTOLIC_ELEVATED_MIN": 120,
        "SYSTOLIC_ELEVATED_MAX": 129,
        "SYSTOLIC_HBP_STAGE1_MIN": 130,
        "SYSTOLIC_HBP_STAGE1_MAX": 139,
        "SYSTOLIC_HBP_STAGE2_MIN": 140,
        "SYSTOLIC_CRISIS_MIN": 180,
        
        "DIASTOLIC_NORMAL_MAX": 80,
        "DIASTOLIC_ELEVATED_MAX": 79,
        "DIASTOLIC_HBP_STAGE1_MIN": 80,
        "DIASTOLIC_HBP_STAGE1_MAX": 89,
        "DIASTOLIC_HBP_STAGE2_MIN": 90,
        "DIASTOLIC_CRISIS_MIN": 120,
        
        "HYPOTENSION_SYSTOLIC": 90,
        "HYPOTENSION_DIASTOLIC": 60,
    }
    
    def __init__(self, ml_model_path: Optional[str] = None):
        """
        Initialize the anomaly detector.
        
        Args:
            ml_model_path: Path to trained ML model (optional)
        """
        self.ml_model = None
        if ml_model_path and os.path.exists(ml_model_path):
            try:
                with open(ml_model_path, 'rb') as f:
                    self.ml_model = pickle.load(f)
                logger.info(f"Loaded ML model from {ml_model_path}")
            except Exception as e:
                logger.warning(f"Could not load ML model: {e}")

    def extract_bp_values(self, observation: Dict) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract systolic and diastolic pressure from FHIR Observation.
        
        Args:
            observation: FHIR Observation resource
        
        Returns:
            Tuple of (systolic, diastolic) values or (None, None) if not found
        """
        try:
            components = observation.get("component", [])
            systolic = None
            diastolic = None
            
            for component in components:
                code = component.get("code", {}).get("coding", [{}])[0].get("code", "")
                value = component.get("valueQuantity", {}).get("value")
                
                if code == "8480-6":  # Systolic code
                    systolic = value
                elif code == "8462-4":  # Diastolic code
                    diastolic = value
            
            return systolic, diastolic
        except Exception as e:
            logger.error(f"Error extracting BP values: {e}")
            return None, None

    def classify_blood_pressure(self, systolic: int, diastolic: int) -> str:
        """
        Classify blood pressure based on medical thresholds.
        
        Args:
            systolic: Systolic pressure in mmHg
            diastolic: Diastolic pressure in mmHg
        
        Returns:
            Classification string
        """
        # Hypertensive Crisis
        if systolic > self.THRESHOLDS["SYSTOLIC_CRISIS_MIN"] or \
           diastolic > self.THRESHOLDS["DIASTOLIC_CRISIS_MIN"]:
            return "HYPERTENSIVE_CRISIS"
        
        # Hypotension
        if systolic < self.THRESHOLDS["HYPOTENSION_SYSTOLIC"] or \
           diastolic < self.THRESHOLDS["HYPOTENSION_DIASTOLIC"]:
            return "HYPOTENSION"
        
        # Hypertension Stage 2
        if systolic >= self.THRESHOLDS["SYSTOLIC_HBP_STAGE2_MIN"] or \
           diastolic >= self.THRESHOLDS["DIASTOLIC_HBP_STAGE2_MIN"]:
            return "HYPERTENSION_STAGE_2"
        
        # Hypertension Stage 1
        if systolic >= self.THRESHOLDS["SYSTOLIC_HBP_STAGE1_MIN"] or \
           diastolic >= self.THRESHOLDS["DIASTOLIC_HBP_STAGE1_MIN"]:
            return "HYPERTENSION_STAGE_1"
        
        # Elevated
        if systolic >= self.THRESHOLDS["SYSTOLIC_ELEVATED_MIN"] or \
           diastolic <= self.THRESHOLDS["DIASTOLIC_ELEVATED_MAX"]:
            return "ELEVATED"
        
        # Normal
        return "NORMAL"

    def is_anomalous(self, systolic: int, diastolic: int) -> bool:
        """
        Determine if blood pressure is anomalous.
        Anomalous = anything other than NORMAL or ELEVATED.
        
        Args:
            systolic: Systolic pressure in mmHg
            diastolic: Diastolic pressure in mmHg
        
        Returns:
            True if anomalous, False otherwise
        """
        classification = self.classify_blood_pressure(systolic, diastolic)
        return classification not in ["NORMAL", "ELEVATED"]

    def get_anomaly_type(self, systolic: int, diastolic: int) -> Optional[str]:
        """
        Get the type of anomaly if present.
        
        Args:
            systolic: Systolic pressure in mmHg
            diastolic: Diastolic pressure in mmHg
        
        Returns:
            Anomaly type or None if normal
        """
        classification = self.classify_blood_pressure(systolic, diastolic)
        if classification not in ["NORMAL", "ELEVATED"]:
            return classification
        return None

    def detect_anomalies(self, observation: Dict) -> Dict:
        """
        Analyze a FHIR Observation and detect anomalies.
        
        Args:
            observation: FHIR Observation resource
        
        Returns:
            Dictionary with analysis results
        """
        systolic, diastolic = self.extract_bp_values(observation)
        
        if systolic is None or diastolic is None:
            return {
                "is_valid": False,
                "error": "Could not extract BP values",
                "observation_id": observation.get("id"),
                "patient_id": None
            }
        
        classification = self.classify_blood_pressure(systolic, diastolic)
        is_anomalous = self.is_anomalous(systolic, diastolic)
        
        # Get patient info
        subject = observation.get("subject", {})
        patient_ref = subject.get("reference", "")
        patient_id = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
        
        result = {
            "is_valid": True,
            "observation_id": observation.get("id"),
            "patient_id": patient_id,
            "patient_name": subject.get("display", "Unknown"),
            "systolic": systolic,
            "diastolic": diastolic,
            "classification": classification,
            "is_anomalous": is_anomalous,
            "anomaly_type": self.get_anomaly_type(systolic, diastolic),
            "observation_time": observation.get("effectiveDateTime"),
            "risk_level": self._calculate_risk_level(systolic, diastolic)
        }
        
        # Add ML prediction if model is available
        if self.ml_model is not None:
            try:
                ml_probability = self._predict_with_ml(systolic, diastolic)
                result["ml_probability_abnormal"] = ml_probability
                result["ml_recommendation"] = "ALERT" if ml_probability > 0.7 else "MONITOR"
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
        
        return result

    def _calculate_risk_level(self, systolic: int, diastolic: int) -> str:
        """
        Calculate risk level based on BP values.
        
        Args:
            systolic: Systolic pressure in mmHg
            diastolic: Diastolic pressure in mmHg
        
        Returns:
            Risk level: LOW, MODERATE, HIGH, CRITICAL
        """
        classification = self.classify_blood_pressure(systolic, diastolic)
        
        risk_mapping = {
            "NORMAL": "LOW",
            "ELEVATED": "LOW",
            "HYPERTENSION_STAGE_1": "MODERATE",
            "HYPERTENSION_STAGE_2": "HIGH",
            "HYPERTENSIVE_CRISIS": "CRITICAL",
            "HYPOTENSION": "HIGH"
        }
        
        return risk_mapping.get(classification, "UNKNOWN")

    def _predict_with_ml(self, systolic: int, diastolic: int) -> float:
        """
        Get ML model probability that BP is abnormal.
        
        Args:
            systolic: Systolic pressure in mmHg
            diastolic: Diastolic pressure in mmHg
        
        Returns:
            Probability that BP is abnormal (0.0 to 1.0)
        """
        if self.ml_model is None:
            raise ValueError("No ML model loaded")
        
        # Prepare features for model
        features = [[systolic, diastolic]]
        
        # Predict probability
        if hasattr(self.ml_model, 'predict_proba'):
            probabilities = self.ml_model.predict_proba(features)[0]
            # Return probability of abnormal class (usually class 1)
            return float(probabilities[-1])
        else:
            # If model doesn't have predict_proba, use decision function
            score = self.ml_model.decision_function(features)[0]
            # Normalize to 0-1 range using sigmoid
            return 1 / (1 + abs(score) ** -1)

    def get_summary_stats(self, observations: list) -> Dict:
        """
        Calculate summary statistics for a batch of observations.
        
        Args:
            observations: List of FHIR Observation resources
        
        Returns:
            Dictionary with summary statistics
        """
        analyses = [self.detect_anomalies(obs) for obs in observations]
        valid_analyses = [a for a in analyses if a.get("is_valid", False)]
        
        if not valid_analyses:
            return {
                "total_observations": len(observations),
                "valid_observations": 0,
                "anomalous_count": 0,
                "anomaly_rate": 0.0
            }
        
        anomalous_count = sum(1 for a in valid_analyses if a.get("is_anomalous", False))
        
        return {
            "total_observations": len(observations),
            "valid_observations": len(valid_analyses),
            "anomalous_count": anomalous_count,
            "anomaly_rate": anomalous_count / len(valid_analyses) if valid_analyses else 0,
            "avg_systolic": sum(a.get("systolic", 0) for a in valid_analyses) / len(valid_analyses),
            "avg_diastolic": sum(a.get("diastolic", 0) for a in valid_analyses) / len(valid_analyses),
        }


if __name__ == "__main__":
    # Example usage
    from fhir_generator import FHIRBPObservationGenerator
    
    logging.basicConfig(level=logging.INFO)
    
    detector = BloodPressureAnomalyDetector()
    generator = FHIRBPObservationGenerator(num_patients=3, data_points_per_patient=2)
    observations = generator.generate_batch(batch_size=5)
    
    for obs in observations:
        result = detector.detect_anomalies(obs)
        print(json.dumps(result, indent=2))
        print("-" * 80)
