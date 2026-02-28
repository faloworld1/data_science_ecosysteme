"""
Kafka Producer for Blood Pressure Observations
Publishes FHIR observations to Kafka topic
"""

import json
import logging
import time
from typing import List, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class BPObservationProducer:
    """
    Kafka Producer for publishing blood pressure observations.
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "blood-pressure-observations",
        **kafka_kwargs
    ):
        """
        Initialize the Kafka producer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            topic: Topic name for publishing observations
            **kafka_kwargs: Additional Kafka producer arguments
        """
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                **kafka_kwargs
            )
            logger.info(f"Connected to Kafka at {bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    def publish_observation(
        self,
        observation: dict,
        patient_id: Optional[str] = None
    ) -> bool:
        """
        Publish a single observation to Kafka.
        
        Args:
            observation: FHIR Observation resource
            patient_id: Optional patient ID for partitioning
        
        Returns:
            True if published successfully, False otherwise
        """
        try:
            key = patient_id.encode('utf-8') if patient_id else None
            
            future = self.producer.send(
                self.topic,
                value=observation,
                key=key,
                timestamp_ms=int(time.time() * 1000)
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            logger.info(
                f"Published observation {observation.get('id')} "
                f"to topic {record_metadata.topic} "
                f"partition {record_metadata.partition} "
                f"at offset {record_metadata.offset}"
            )
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish observation: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing observation: {e}")
            return False

    def publish_batch(self, observations: List[dict]) -> int:
        """
        Publish multiple observations to Kafka.
        
        Args:
            observations: List of FHIR Observation resources
        
        Returns:
            Number of successfully published observations
        """
        published_count = 0
        
        for observation in observations:
            # Extract patient ID for partitioning
            subject = observation.get("subject", {})
            patient_ref = subject.get("reference", "")
            patient_id = patient_ref.split("/")[-1] if "/" in patient_ref else None
            
            if self.publish_observation(observation, patient_id):
                published_count += 1
            else:
                logger.warning(
                    f"Failed to publish observation {observation.get('id')}"
                )
        
        # Ensure all messages are sent
        self.producer.flush()
        
        logger.info(
            f"Published {published_count}/{len(observations)} observations"
        )
        return published_count

    def close(self):
        """Close the Kafka producer connection."""
        try:
            self.producer.close()
            logger.info("Kafka producer closed")
        except Exception as e:
            logger.error(f"Error closing producer: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Example usage
    import sys
    sys.path.insert(0, '/src')
    from fhir_generator import FHIRBPObservationGenerator
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Generate sample observations
    generator = FHIRBPObservationGenerator(num_patients=5, data_points_per_patient=2)
    observations = generator.generate_batch(batch_size=10)
    
    # Publish to Kafka
    with BPObservationProducer() as producer:
        producer.publish_batch(observations)
        print(f"Published sample observations to Kafka")
