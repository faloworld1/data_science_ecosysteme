"""
Application Configuration Module
Central configuration for the Blood Pressure Monitoring System
"""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_BP_OBSERVATIONS = "blood-pressure-observations"
KAFKA_CONSUMER_GROUP = "bp-anomaly-detection-group"

# Elasticsearch Configuration
ELASTICSEARCH_HOSTS = os.getenv("ELASTICSEARCH_HOSTS", "http://localhost:9200").split(",")
ELASTICSEARCH_INDEX = "blood-pressure-anomalies"

# FHIR Generator Configuration
NUM_PATIENTS = 10
DATA_POINTS_PER_PATIENT = 5
BATCH_SIZE = 20

# ML Model Configuration
ML_MODEL_PATH = MODELS_DIR / "trained_model.pkl"
USE_ML_MODEL = True

# Storage Configuration
NORMAL_CASES_DIR = DATA_DIR / "normal_cases"
SAVE_NORMAL_CASES_DAILY = True

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "app.log"

# Blood Pressure Thresholds (mmHg)
BP_THRESHOLDS = {
    "SYSTOLIC_NORMAL_MAX": 120,
    "SYSTOLIC_HBP_STAGE1_MIN": 130,
    "SYSTOLIC_HBP_STAGE2_MIN": 140,
    "SYSTOLIC_CRISIS_MIN": 180,
    "DIASTOLIC_NORMAL_MAX": 80,
    "DIASTOLIC_HBP_STAGE1_MIN": 80,
    "DIASTOLIC_HBP_STAGE2_MIN": 90,
    "DIASTOLIC_CRISIS_MIN": 120,
    "HYPOTENSION_SYSTOLIC": 90,
    "HYPOTENSION_DIASTOLIC": 60,
}

# Processing Configuration
PROCESS_MODE = "realtime"  # "batch" or "realtime"
BATCH_PROCESS_SIZE = 100
MESSAGE_TIMEOUT = 10  # seconds

# Features
ENABLE_KAFKA_PRODUCER = True
ENABLE_KAFKA_CONSUMER = True
ENABLE_ELASTICSEARCH = True
ENABLE_ML_MODEL = USE_ML_MODEL

# Demo mode (for testing without actual Kafka/ES)
DEMO_MODE = False
DEMO_NUM_MESSAGES = 50


def setup_directories():
    """Create necessary directories if they don't exist."""
    for directory in [DATA_DIR, MODELS_DIR, LOGS_DIR, NORMAL_CASES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_config_summary() -> dict:
    """Get configuration summary."""
    return {
        "kafka": {
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
            "topic": KAFKA_TOPIC_BP_OBSERVATIONS,
            "consumer_group": KAFKA_CONSUMER_GROUP
        },
        "elasticsearch": {
            "hosts": ELASTICSEARCH_HOSTS,
            "index": ELASTICSEARCH_INDEX
        },
        "generator": {
            "num_patients": NUM_PATIENTS,
            "data_points_per_patient": DATA_POINTS_PER_PATIENT,
            "batch_size": BATCH_SIZE
        },
        "features": {
            "kafka_producer": ENABLE_KAFKA_PRODUCER,
            "kafka_consumer": ENABLE_KAFKA_CONSUMER,
            "elasticsearch": ENABLE_ELASTICSEARCH,
            "ml_model": ENABLE_ML_MODEL,
            "demo_mode": DEMO_MODE
        },
        "paths": {
            "project_root": str(PROJECT_ROOT),
            "models": str(MODELS_DIR),
            "logs": str(LOGS_DIR),
            "normal_cases": str(NORMAL_CASES_DIR)
        }
    }


if __name__ == "__main__":
    import json
    setup_directories()
    print(json.dumps(get_config_summary(), indent=2))
