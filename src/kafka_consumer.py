"""
Kafka Consumer for Blood Pressure Observations
Consumes observations, detects anomalies, and routes to appropriate storage
"""

import json
import logging
import time
from typing import Optional, Callable
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from anomaly_detector import BloodPressureAnomalyDetector

logger = logging.getLogger(__name__)


class BPObservationConsumer:
    """
    Kafka Consumer for processing blood pressure observations.
    Routes anomalous cases to Elasticsearch and normal cases to local storage.
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "blood-pressure-observations",
        group_id: str = "bp-anomaly-detection-group",
        ml_model_path: Optional[str] = None,
        **kafka_kwargs
    ):
        """
        Initialize the Kafka consumer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            topic: Topic name to consume from
            group_id: Consumer group ID
            ml_model_path: Path to trained ML model (optional)
            **kafka_kwargs: Additional Kafka consumer arguments
        """
        self.topic = topic
        self.anomaly_detector = BloodPressureAnomalyDetector(ml_model_path)
        
        try:
            self.consumer = KafkaConsumer(
                topic,
                bootstrap_servers=bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                max_poll_records=10,
                **kafka_kwargs
            )
            logger.info(f"Connected to Kafka topic: {topic}, group: {group_id}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    def process_message(
        self,
        observation: dict,
        anomaly_callback: Optional[Callable] = None,
        normal_callback: Optional[Callable] = None
    ) -> bool:
        """
        Process a single observation message.
        
        Args:
            observation: FHIR Observation resource
            anomaly_callback: Function to call for anomalous cases
            normal_callback: Function to call for normal cases
        
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Detect anomalies
            analysis = self.anomaly_detector.detect_anomalies(observation)
            
            if not analysis.get("is_valid"):
                logger.warning(f"Invalid observation: {analysis.get('error')}")
                return False
            
            # Route to appropriate handler
            if analysis.get("is_anomalous"):
                logger.warning(
                    f"ANOMALY DETECTED - Patient: {analysis.get('patient_id')}, "
                    f"Risk: {analysis.get('risk_level')}, "
                    f"BP: {analysis.get('systolic')}/{analysis.get('diastolic')}"
                )
                if anomaly_callback:
                    anomaly_callback(analysis)
            else:
                logger.info(
                    f"NORMAL - Patient: {analysis.get('patient_id')}, "
                    f"BP: {analysis.get('systolic')}/{analysis.get('diastolic')}"
                )
                if normal_callback:
                    normal_callback(analysis)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return False

    def start_consuming(
        self,
        anomaly_callback: Optional[Callable] = None,
        normal_callback: Optional[Callable] = None,
        batch_size: int = 100,
        max_messages: Optional[int] = None
    ):
        """
        Start consuming and processing messages from Kafka.
        
        Args:
            anomaly_callback: Function to call for anomalous cases
            normal_callback: Function to call for normal cases
            batch_size: Number of messages to process before logging stats
            max_messages: Maximum messages to process (None = infinite)
        """
        logger.info("Starting consumer...")
        message_count = 0
        processed_count = 0
        
        try:
            for message in self.consumer:
                try:
                    observation = message.value
                    
                    if self.process_message(
                        observation,
                        anomaly_callback,
                        normal_callback
                    ):
                        processed_count += 1
                    
                    message_count += 1
                    
                    # Log progress
                    if message_count % batch_size == 0:
                        logger.info(
                            f"Processed {message_count} messages "
                            f"({processed_count} successfully)"
                        )
                    
                    # Stop if max reached
                    if max_messages and message_count >= max_messages:
                        logger.info(f"Reached max messages limit: {max_messages}")
                        break
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                    continue
                
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
        finally:
            self.close()
            logger.info(
                f"Consumer stopped. Total: {message_count}, "
                f"Processed: {processed_count}"
            )

    def close(self):
        """Close the Kafka consumer connection."""
        try:
            self.consumer.close()
            logger.info("Kafka consumer closed")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Define callbacks
    def handle_anomaly(analysis):
        """Handle anomalous case."""
        print(f"[ANOMALY] {json.dumps(analysis, indent=2)}")
    
    def handle_normal(analysis):
        """Handle normal case."""
        print(f"[NORMAL] Patient {analysis.get('patient_id')}: "
              f"{analysis.get('systolic')}/{analysis.get('diastolic')}")
    
    # Start consumer
    consumer = BPObservationConsumer(
         bootstrap_servers="localhost:9092",
    topic="blood-pressure-observations",
    )
    consumer.start_consuming(
        anomaly_callback=handle_anomaly,
        normal_callback=handle_normal
    )
