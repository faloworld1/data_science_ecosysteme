"""
Test Suite pour le Système de Surveillance BP
Tests unitaires et d'intégration
"""

import json
import sys
import unittest
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fhir_generator import FHIRBPObservationGenerator
from anomaly_detector import BloodPressureAnomalyDetector
from data_storage import NormalCasesStorage
from ml_model import BPAnomalyMLModel


class TestFHIRGenerator(unittest.TestCase):
    """Tests pour le générateur FHIR."""
    
    def setUp(self):
        self.generator = FHIRBPObservationGenerator(num_patients=5, data_points_per_patient=2)
    
    def test_generator_initialization(self):
        """Test l'initialisation du générateur."""
        self.assertIsNotNone(self.generator.patients)
        self.assertEqual(len(self.generator.patients), 5)
    
    def test_generate_batch(self):
        """Test la génération d'un batch."""
        observations = self.generator.generate_batch(batch_size=10)
        self.assertEqual(len(observations), 10)
    
    def test_observation_structure(self):
        """Test la structure d'une observation."""
        observations = self.generator.generate_batch(batch_size=1)
        obs = observations[0]
        
        self.assertEqual(obs["resourceType"], "Observation")
        self.assertIn("id", obs)
        self.assertIn("subject", obs)
        self.assertIn("component", obs)
        self.assertEqual(len(obs["component"]), 2)  # Systolic + Diastolic
    
    def test_bp_values_format(self):
        """Test le format des valeurs BP."""
        observations = self.generator.generate_batch(batch_size=5)
        
        for obs in observations:
            components = obs.get("component", [])
            for comp in components:
                value = comp.get("valueQuantity", {}).get("value")
                self.assertIsInstance(value, int)
                self.assertGreaterEqual(value, 50)
                self.assertLessEqual(value, 250)


class TestAnomalyDetector(unittest.TestCase):
    """Tests pour le détecteur d'anomalies."""
    
    def setUp(self):
        self.detector = BloodPressureAnomalyDetector()
        self.generator = FHIRBPObservationGenerator(num_patients=3)
    
    def test_normal_classification(self):
        """Test la classification NORMAL."""
        classification = self.detector.classify_blood_pressure(110, 70)
        self.assertEqual(classification, "NORMAL")
    
    def test_elevated_classification(self):
        """Test la classification ELEVATED."""
        classification = self.detector.classify_blood_pressure(125, 75)
        self.assertEqual(classification, "ELEVATED")
    
    def test_hypertension_stage1(self):
        """Test la classification HYPERTENSION STAGE 1."""
        classification = self.detector.classify_blood_pressure(135, 85)
        self.assertEqual(classification, "HYPERTENSION_STAGE_1")
    
    def test_hypertension_stage2(self):
        """Test la classification HYPERTENSION STAGE 2."""
        classification = self.detector.classify_blood_pressure(145, 95)
        self.assertEqual(classification, "HYPERTENSION_STAGE_2")
    
    def test_hypertensive_crisis(self):
        """Test la classification HYPERTENSIVE CRISIS."""
        classification = self.detector.classify_blood_pressure(190, 125)
        self.assertEqual(classification, "HYPERTENSIVE_CRISIS")
    
    def test_hypotension(self):
        """Test la classification HYPOTENSION."""
        classification = self.detector.classify_blood_pressure(85, 55)
        self.assertEqual(classification, "HYPOTENSION")
    
    def test_is_anomalous(self):
        """Test la détection d'anomalies."""
        # Normal
        self.assertFalse(self.detector.is_anomalous(110, 70))
        # Anomalies
        self.assertTrue(self.detector.is_anomalous(145, 95))
        self.assertTrue(self.detector.is_anomalous(85, 55))
    
    def test_detect_anomalies_from_observation(self):
        """Test l'analyse complète d'une observation."""
        observations = self.generator.generate_batch(batch_size=1)
        analysis = self.detector.detect_anomalies(observations[0])
        
        self.assertTrue(analysis["is_valid"])
        self.assertIn("systolic", analysis)
        self.assertIn("diastolic", analysis)
        self.assertIn("classification", analysis)
        self.assertIn("is_anomalous", analysis)
        self.assertIn("risk_level", analysis)
    
    def test_risk_level_calculation(self):
        """Test le calcul du niveau de risque."""
        # LOW risk
        risk = self.detector._calculate_risk_level(110, 70)
        self.assertEqual(risk, "LOW")
        
        # HIGH risk
        risk = self.detector._calculate_risk_level(145, 95)
        self.assertEqual(risk, "HIGH")
        
        # CRITICAL risk
        risk = self.detector._calculate_risk_level(190, 125)
        self.assertEqual(risk, "CRITICAL")
    
    def test_summary_stats(self):
        """Test les statistiques de batch."""
        observations = self.generator.generate_batch(batch_size=10)
        stats = self.detector.get_summary_stats(observations)
        
        self.assertEqual(stats["total_observations"], 10)
        self.assertGreaterEqual(stats["valid_observations"], 0)
        self.assertGreaterEqual(stats["anomalous_count"], 0)
        self.assertLessEqual(stats["anomaly_rate"], 1.0)


class TestMLModel(unittest.TestCase):
    """Tests pour le modèle ML."""
    
    def test_synthetic_data_generation(self):
        """Test la génération de données synthétiques."""
        systolic, diastolic, labels = BPAnomalyMLModel.generate_synthetic_training_data(
            num_samples=100,
            abnormal_ratio=0.3
        )
        
        self.assertEqual(len(systolic), 100)
        self.assertEqual(len(diastolic), 100)
        self.assertEqual(len(labels), 100)
        
        # Vérifier le ratio
        abnormal_count = sum(labels)
        self.assertAlmostEqual(abnormal_count / 100, 0.3, delta=0.15)
    
    def test_model_training(self):
        """Test l'entraînement du modèle."""
        model = BPAnomalyMLModel(model_type="logistic_regression")
        
        systolic, diastolic, labels = BPAnomalyMLModel.generate_synthetic_training_data(
            num_samples=200,
            abnormal_ratio=0.35
        )
        
        metrics = model.train(systolic, diastolic, labels, verbose=False)
        
        self.assertTrue(model.is_trained)
        self.assertIn("train_accuracy", metrics)
        self.assertIn("test_accuracy", metrics)
        self.assertGreater(metrics["train_accuracy"], 0.5)
    
    def test_model_prediction(self):
        """Test les prédictions du modèle."""
        model = BPAnomalyMLModel(model_type="logistic_regression")
        
        systolic, diastolic, labels = BPAnomalyMLModel.generate_synthetic_training_data(
            num_samples=200,
            abnormal_ratio=0.35
        )
        
        model.train(systolic, diastolic, labels, verbose=False)
        
        # Tester une prédiction
        prediction, probability = model.predict(145, 95)
        
        self.assertIn(prediction, [0, 1])
        self.assertGreaterEqual(probability, 0.0)
        self.assertLessEqual(probability, 1.0)


class TestDataStorage(unittest.TestCase):
    """Tests pour le stockage de données."""
    
    def setUp(self):
        self.storage_dir = "test_storage"
        self.storage = NormalCasesStorage(storage_dir=self.storage_dir)
    
    def test_storage_initialization(self):
        """Test l'initialisation du stockage."""
        self.assertTrue(Path(self.storage_dir).exists())
    
    def test_save_normal_case(self):
        """Test la sauvegarde d'un cas normal."""
        analysis = {
            "observation_id": "test-001",
            "patient_id": "patient-001",
            "patient_name": "John Doe",
            "systolic": 110,
            "diastolic": 70,
            "classification": "NORMAL",
            "is_anomalous": False,
            "observation_time": "2024-01-01T00:00:00Z"
        }
        
        result = self.storage.save_case(analysis, create_daily_file=True)
        self.assertTrue(result)
    
    def test_save_anomalous_case_not_saved(self):
        """Test qu'un cas anomalies n'est pas sauvegardé."""
        analysis = {
            "observation_id": "test-002",
            "patient_id": "patient-002",
            "systolic": 145,
            "diastolic": 95,
            "classification": "HYPERTENSION_STAGE_2",
            "is_anomalous": True
        }
        
        result = self.storage.save_case(analysis)
        self.assertFalse(result)  # Ne doit pas être sauvegardé
    
    def tearDown(self):
        """Nettoyer après les tests."""
        import shutil
        if Path(self.storage_dir).exists():
            shutil.rmtree(self.storage_dir)


def run_tests():
    """Lancer tous les tests."""
    print("\n" + "="*70)
    print("  TEST SUITE - Système de Surveillance BP")
    print("="*70 + "\n")
    
    # Créer une suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter tous les tests
    suite.addTests(loader.loadTestsFromTestCase(TestFHIRGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestAnomalyDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestMLModel))
    suite.addTests(loader.loadTestsFromTestCase(TestDataStorage))
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*70)
    print(f"Tests: {result.testsRun}")
    print(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    print("="*70 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
