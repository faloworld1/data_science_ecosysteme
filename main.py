"""
Main Application Script - Continuous Monitoring Version
Orchestrates the complete Blood Pressure Monitoring Pipeline with Concurrent Threads
"""

import json
import logging
import sys
import time
import threading
from pathlib import Path
from typing import Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "config"))

# Import configuration
import app_config

# Import application modules
from fhir_generator import FHIRBPObservationGenerator
from kafka_producer import BPObservationProducer
from kafka_consumer import BPObservationConsumer
from anomaly_detector import BloodPressureAnomalyDetector
from elasticsearch_handler import ElasticsearchHandler
from data_storage import NormalCasesStorage
from ml_model import BPAnomalyMLModel

# Setup logging
logging.basicConfig(
    level=getattr(logging, app_config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(app_config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class BloodPressureMonitoringSystem:
    """
    Main orchestrator for the Blood Pressure Monitoring System.
    Uses threading to handle continuous production and consumption.
    """
    
    def __init__(self):
        app_config.setup_directories()
        logger.info("Blood Pressure Monitoring System Initializing...")
        
        self.generator = None
        self.producer = None
        self.consumer = None
        self.detector = None
        self.elasticsearch = None
        self.storage = None
        self.stop_event = threading.Event() # Pour arrêter proprement les threads

    # --- Initialisations ---
    def initialize_generator(self) -> bool:
        try:
            self.generator = FHIRBPObservationGenerator(
                num_patients=app_config.NUM_PATIENTS,
                data_points_per_patient=app_config.DATA_POINTS_PER_PATIENT
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize generator: {e}")
            return False

    def initialize_kafka_producer(self) -> bool:
        try:
            self.producer = BPObservationProducer(
                bootstrap_servers=app_config.KAFKA_BOOTSTRAP_SERVERS,
                topic=app_config.KAFKA_TOPIC_BP_OBSERVATIONS
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            return False

    def initialize_kafka_consumer(self) -> bool:
        try:
            ml_model = str(app_config.ML_MODEL_PATH) if app_config.USE_ML_MODEL and app_config.ML_MODEL_PATH.exists() else None
            self.consumer = BPObservationConsumer(
                bootstrap_servers=app_config.KAFKA_BOOTSTRAP_SERVERS,
                topic=app_config.KAFKA_TOPIC_BP_OBSERVATIONS,
                ml_model_path=ml_model
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            return False

    def initialize_anomaly_detector(self) -> bool:
        try:
            ml_model = str(app_config.ML_MODEL_PATH) if app_config.USE_ML_MODEL and app_config.ML_MODEL_PATH.exists() else None
            self.detector = BloodPressureAnomalyDetector(ml_model_path=ml_model)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize anomaly detector: {e}")
            return False

    def initialize_elasticsearch(self) -> bool:
        try:
            self.elasticsearch = ElasticsearchHandler(
                hosts=app_config.ELASTICSEARCH_HOSTS,
                index_name=app_config.ELASTICSEARCH_INDEX
            )
            self.elasticsearch.create_index()
            return True
        except Exception as e:
            logger.warning(f"Elasticsearch not available: {e}")
            return False

    def initialize_storage(self) -> bool:
        try:
            self.storage = NormalCasesStorage(storage_dir=str(app_config.NORMAL_CASES_DIR))
            return True
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            return False

    # --- Logique de Flux Continu ---

    def continuous_production_loop(self, interval: float = 2.0):
        """Boucle infinie de génération de données."""
        logger.info(f"Starting CONTINUOUS PRODUCTION (Interval: {interval}s)")
        batch_size = app_config.BATCH_SIZE
        
        while not self.stop_event.is_set():
            try:
                observations = self.generator.generate_batch(batch_size=batch_size)
                if self.producer:
                    self.producer.publish_batch(observations)
                    logger.debug(f"Published {len(observations)} observations to Kafka")
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in production loop: {e}")
                time.sleep(5) # Pause en cas d'erreur Kafka

    def start_realtime_processing(self):
        """Démarre la consommation des messages Kafka."""
        if not self.consumer:
            logger.error("Consumer not initialized")
            return
        
        logger.info("Starting CONTINUOUS CONSUMPTION...")

        def anomaly_callback(analysis):
            if self.elasticsearch:
                self.elasticsearch.index_anomaly(analysis)
            logger.warning(f"!!! ANOMALY DETECTED - Patient: {analysis.get('patient_id')} - Level: {analysis.get('risk_level')}")
        
        def normal_callback(analysis):
            if self.storage:
                self.storage.save_case(analysis)

        self.consumer.start_consuming(
            anomaly_callback=anomaly_callback,
            normal_callback=normal_callback,
            batch_size=50
        )

    # --- Modes d'exécution ---

    def run_production(self):
        """Lancement du pipeline complet en mode continu."""
        # Initialisation de tous les composants
        if not all([
            self.initialize_generator(),
            self.initialize_kafka_producer(),
            self.initialize_kafka_consumer(),
            self.initialize_anomaly_detector(),
            self.initialize_storage()
        ]):
            logger.error("Critical initialization failed. Exiting.")
            return

        self.initialize_elasticsearch() # Optionnel

        # 1. Créer le thread pour le Producer (Génération)
        producer_thread = threading.Thread(
            target=self.continuous_production_loop,
            args=(2.0,), # Intervalle de 2 secondes
            name="ProducerThread",
            daemon=True
        )

        # 2. Lancer la production en arrière-plan
        producer_thread.start()

        # 3. Lancer la consommation (Bloquant sur le thread principal)
        try:
            self.start_realtime_processing()
        except KeyboardInterrupt:
            logger.info("Shutdown signal received.")
            self.stop_event.set()

    def cleanup(self):
        logger.info("Cleaning up resources...")
        self.stop_event.set()
        if self.producer: self.producer.close()
        if self.consumer: self.consumer.close()
        if self.elasticsearch: self.elasticsearch.close()
        logger.info("Cleanup complete")

def main():
    logger.info("="*80)
    logger.info("BLOOD PRESSURE MONITORING SYSTEM - CONTINUOUS MODE")
    logger.info("="*80)
    
    system = BloodPressureMonitoringSystem()
    
    try:
        system.run_production()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
    finally:
        system.cleanup()

if __name__ == "__main__":
    main()