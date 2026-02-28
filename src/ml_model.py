"""
Machine Learning Model for Blood Pressure Prediction
Optional module for training and using ML models for anomaly detection
"""

import json
import pickle
import logging
from typing import Tuple, List, Optional
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

logger = logging.getLogger(__name__)


class BPAnomalyMLModel:
    """
    Machine Learning model for blood pressure anomaly detection.
    Provides training and prediction capabilities.
    """
    
    def __init__(self, model_type: str = "logistic_regression"):
        """
        Initialize ML model.
        
        Args:
            model_type: Type of model ('logistic_regression' or 'random_forest')
        """
        self.model_type = model_type
        self.scaler = StandardScaler()
        self.model = None
        self.is_trained = False
        
        if model_type == "logistic_regression":
            self.model = LogisticRegression(random_state=42, max_iter=1000)
        elif model_type == "random_forest":
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def prepare_data(
        self,
        systolic_values: List[int],
        diastolic_values: List[int],
        labels: List[int]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data.
        
        Args:
            systolic_values: List of systolic pressures
            diastolic_values: List of diastolic pressures
            labels: Binary labels (0=normal, 1=abnormal)
        
        Returns:
            Tuple of (scaled_features, labels)
        """
        # Combine features
        features = np.array([systolic_values, diastolic_values]).T
        
        # Scale features
        scaled_features = self.scaler.fit_transform(features)
        
        return scaled_features, np.array(labels)

    def train(
        self,
        systolic_values: List[int],
        diastolic_values: List[int],
        labels: List[int],
        test_size: float = 0.2,
        verbose: bool = True
    ) -> dict:
        """
        Train the ML model.
        
        Args:
            systolic_values: Training systolic values
            diastolic_values: Training diastolic values
            labels: Binary labels (0=normal, 1=abnormal)
            test_size: Train/test split ratio
            verbose: Print training details
        
        Returns:
            Dictionary with training metrics
        """
        # Prepare data
        X, y = self.prepare_data(systolic_values, diastolic_values, labels)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Train model
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        # Get predictions
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        # Calculate metrics
        metrics = {
            "train_accuracy": float(train_score),
            "test_accuracy": float(test_score),
            "roc_auc": float(roc_auc_score(y_test, y_pred_proba)),
            "classification_report": classification_report(y_test, y_pred, output_dict=True),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist()
        }
        
        if verbose:
            logger.info(f"Model trained: {self.model_type}")
            logger.info(f"Train Accuracy: {train_score:.4f}")
            logger.info(f"Test Accuracy: {test_score:.4f}")
            logger.info(f"ROC AUC: {metrics['roc_auc']:.4f}")
        
        return metrics

    def predict(
        self,
        systolic: int,
        diastolic: int
    ) -> Tuple[int, float]:
        """
        Predict if a blood pressure reading is normal or abnormal.
        
        Args:
            systolic: Systolic pressure value
            diastolic: Diastolic pressure value
        
        Returns:
            Tuple of (prediction, probability_abnormal)
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet")
        
        # Prepare features
        features = np.array([[systolic, diastolic]])
        scaled_features = self.scaler.transform(features)
        
        # Predict
        prediction = self.model.predict(scaled_features)[0]
        probability = self.model.predict_proba(scaled_features)[0][1]
        
        return int(prediction), float(probability)

    def save_model(self, filepath: str) -> bool:
        """
        Save trained model to file.
        
        Args:
            filepath: Path to save the model
        
        Returns:
            True if saved successfully
        """
        if not self.is_trained:
            logger.error("Model not trained yet")
            return False
        
        try:
            with open(filepath, 'wb') as f:
                pickle.dump({'model': self.model, 'scaler': self.scaler}, f)
            logger.info(f"Model saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False

    def load_model(self, filepath: str) -> bool:
        """
        Load trained model from file.
        
        Args:
            filepath: Path to the saved model
        
        Returns:
            True if loaded successfully
        """
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.is_trained = True
            logger.info(f"Model loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    @staticmethod
    def generate_synthetic_training_data(
        num_samples: int = 1000,
        abnormal_ratio: float = 0.3
    ) -> Tuple[List[int], List[int], List[int]]:
        """
        Generate synthetic training data based on medical categories.
        
        Args:
            num_samples: Total number of samples to generate
            abnormal_ratio: Ratio of abnormal samples
        
        Returns:
            Tuple of (systolic_values, diastolic_values, labels)
        """
        systolic_values = []
        diastolic_values = []
        labels = []
        
        num_normal = int(num_samples * (1 - abnormal_ratio))
        num_abnormal = num_samples - num_normal
        
        # Generate normal samples
        for _ in range(num_normal):
            sys = np.random.normal(120, 10)
            dia = np.random.normal(75, 8)
            systolic_values.append(max(50, min(200, int(sys))))
            diastolic_values.append(max(30, min(130, int(dia))))
            labels.append(0)
        
        # Generate abnormal samples
        for _ in range(num_abnormal):
            # Random abnormal category
            category = np.random.choice([
                'hypertension_stage1',
                'hypertension_stage2',
                'hypertensive_crisis',
                'hypotension'
            ])
            
            if category == 'hypertension_stage1':
                sys = np.random.normal(135, 5)
                dia = np.random.normal(85, 5)
            elif category == 'hypertension_stage2':
                sys = np.random.normal(150, 10)
                dia = np.random.normal(95, 8)
            elif category == 'hypertensive_crisis':
                sys = np.random.normal(190, 15)
                dia = np.random.normal(120, 10)
            else:  # hypotension
                sys = np.random.normal(80, 8)
                dia = np.random.normal(50, 5)
            
            systolic_values.append(max(50, min(250, int(sys))))
            diastolic_values.append(max(30, min(180, int(dia))))
            labels.append(1)
        
        return systolic_values, diastolic_values, labels


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and train model
    model = BPAnomalyMLModel(model_type="logistic_regression")
    
    # Generate synthetic training data
    systolic, diastolic, labels = BPAnomalyMLModel.generate_synthetic_training_data(
        num_samples=1000,
        abnormal_ratio=0.35
    )
    
    # Train model
    metrics = model.train(systolic, diastolic, labels, verbose=True)
    print(f"\nTraining metrics:\n{json.dumps(metrics, indent=2)}")
    
    # Test prediction
    test_sys, test_dia = 145, 95
    prediction, probability = model.predict(test_sys, test_dia)
    print(f"\nTest prediction: BP {test_sys}/{test_dia}")
    print(f"Prediction: {'ABNORMAL' if prediction == 1 else 'NORMAL'}")
    print(f"Probability abnormal: {probability:.4f}")
    
    # Save model
    model.save_model("models/trained_model.pkl")
