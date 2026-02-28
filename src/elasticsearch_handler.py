"""
Elasticsearch Handler for storing and managing blood pressure anomalies
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from elasticsearch import Elasticsearch


logger = logging.getLogger(__name__)


class ElasticsearchHandler:
    """
    Handles indexing and querying anomalous blood pressure data in Elasticsearch.
    """
    
    INDEX_NAME = "blood-pressure-anomalies"
    INDEX_MAPPING = {
        "mappings": {
            "properties": {
                "observation_id": {"type": "keyword"},
                "patient_id": {"type": "keyword"},
                "patient_name": {"type": "text"},
                "systolic_pressure": {"type": "integer"},
                "diastolic_pressure": {"type": "integer"},
                "classification": {"type": "keyword"},
                "anomaly_type": {"type": "keyword"},
                "risk_level": {"type": "keyword"},
                "observation_time": {"type": "date"},
                "indexed_time": {"type": "date"},
                "ml_probability_abnormal": {"type": "float"},
                "ml_recommendation": {"type": "keyword"},
                "severity_score": {"type": "float"}
            }
        }
    }

    def __init__(self, hosts: List[str] = None, index_name: str = None, **kwargs):
        """
        Initialize Elasticsearch handler.
        
        Args:
            hosts: List of Elasticsearch hosts (default: ['localhost:9200'])
            index_name: Custom index name
            **kwargs: Additional Elasticsearch client arguments
        """
        if hosts is None:
            hosts = ['localhost:9200']

        # ensure each host contains a scheme (http/https)
        normalized = []
        for h in hosts:
            if not h.startswith('http://') and not h.startswith('https://'):
                normalized.append('http://' + h)
            else:
                normalized.append(h)
        hosts = normalized
        
        self.hosts = hosts
        self.index_name = index_name or self.INDEX_NAME

        # check client version compatibility
        try:
            import elasticsearch as _es_module
            ver = getattr(_es_module, '__version__', None)
            if ver is not None:
                # convert to string and parse major component
                ver_str = str(ver)
                try:
                    major = int(ver_str.split('.')[0])
                except Exception:
                    major = None
                if major is not None and major >= 9:
                    raise RuntimeError(
                        "Installed elasticsearch client is version 9.x, which is not "
                        "compatible with an Elasticsearch 8 cluster. "
                        "Please downgrade: pip install 'elasticsearch<9'"
                    )
        except RuntimeError:
            # re-raise so caller can handle
            raise
        except Exception:
            # if we can't import or examine version, continue anyway
            pass
        
        try:
            # apply compatibility settings for ES8 when using client 9+
            client_kwargs = kwargs.copy()
            try:
                import elasticsearch as _es_module
                ver = getattr(_es_module, '__version__', None)
                if ver is not None and isinstance(ver, tuple) and ver[0] >= 9:
                    # override default mimetype so Accept header uses version 8
                    client_kwargs['default_mimetype'] = (
                        'application/vnd.elasticsearch+json;compatible-with=8'
                    )
            except Exception:
                # ignore if cannot inspect version
                pass

            self.client = Elasticsearch(hosts, **client_kwargs)
            info = self.client.info()
            logger.info(f"Connected to Elasticsearch: {info['version']['number']}")
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise

    def create_index(self, force_recreate: bool = False) -> bool:
        """
        Create Elasticsearch index with proper mappings.
        
        Args:
            force_recreate: Delete existing index and recreate
        
        Returns:
            True if index created/exists, False otherwise
        """
        try:
            if self.client.indices.exists(index=self.index_name):
                if force_recreate:
                    logger.info(f"Deleting existing index: {self.index_name}")
                    self.client.indices.delete(index=self.index_name)
                else:
                    logger.info(f"Index {self.index_name} already exists")
                    return True
            
            logger.info(f"Creating index: {self.index_name}")
            self.client.indices.create(index=self.index_name, body=self.INDEX_MAPPING)
            logger.info(f"Index {self.index_name} created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False

    def index_anomaly(
        self,
        anomaly_analysis: Dict,
        document_id: Optional[str] = None
    ) -> bool:
        """
        Index an anomalous blood pressure reading.
        
        Args:
            anomaly_analysis: Result from AnomalyDetector.detect_anomalies()
            document_id: Optional custom document ID
        
        Returns:
            True if indexed successfully, False otherwise
        """
        try:
            # Skip if not valid or not anomalous
            if not anomaly_analysis.get("is_valid") or not anomaly_analysis.get("is_anomalous"):
                return False
            
            # Prepare document
            document = {
                "observation_id": anomaly_analysis.get("observation_id"),
                "patient_id": anomaly_analysis.get("patient_id"),
                "patient_name": anomaly_analysis.get("patient_name"),
                "systolic_pressure": anomaly_analysis.get("systolic"),
                "diastolic_pressure": anomaly_analysis.get("diastolic"),
                "classification": anomaly_analysis.get("classification"),
                "anomaly_type": anomaly_analysis.get("anomaly_type"),
                "risk_level": anomaly_analysis.get("risk_level"),
                "observation_time": anomaly_analysis.get("observation_time"),
                "indexed_time": datetime.utcnow().isoformat(),
                "ml_probability_abnormal": anomaly_analysis.get("ml_probability_abnormal"),
                "ml_recommendation": anomaly_analysis.get("ml_recommendation"),
                "severity_score": self._calculate_severity_score(anomaly_analysis)
            }
            
            doc_id = document_id or anomaly_analysis.get("observation_id")
            
            response = self.client.index(
                index=self.index_name,
                id=doc_id,
                body=document
            )
            
            logger.info(
                f"Indexed anomaly for patient {anomaly_analysis.get('patient_id')} "
                f"with risk level {anomaly_analysis.get('risk_level')}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to index anomaly: {e}")
            return False

    def index_batch(self, anomalies: List[Dict]) -> int:
        """
        Index multiple anomalies in batch.
        
        Args:
            anomalies: List of anomaly analyses
        
        Returns:
            Number of successfully indexed anomalies
        """
        indexed_count = 0
        
        for anomaly in anomalies:
            if self.index_anomaly(anomaly):
                indexed_count += 1
        
        logger.info(f"Indexed {indexed_count}/{len(anomalies)} anomalies")
        return indexed_count

    def search_anomalies(
        self,
        risk_level: Optional[str] = None,
        patient_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search for anomalies with optional filters.
        
        Args:
            risk_level: Filter by risk level (HIGH, CRITICAL, etc.)
            patient_id: Filter by patient ID
            limit: Maximum results to return
        
        Returns:
            List of matching anomalies
        """
        try:
            query = {"match_all": {}}
            
            if risk_level or patient_id:
                filters = []
                
                if risk_level:
                    filters.append({"term": {"risk_level": risk_level}})
                
                if patient_id:
                    filters.append({"term": {"patient_id": patient_id}})
                
                query = {"bool": {"must": filters}} if filters else query
            
            response = self.client.search(
                index=self.index_name,
                body={
                    "query": query,
                    "size": limit,
                    "sort": [{"indexed_time": {"order": "desc"}}]
                }
            )
            
            return [hit["_source"] for hit in response["hits"]["hits"]]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_statistics(self) -> Dict:
        """
        Get statistics about indexed anomalies.
        
        Returns:
            Dictionary with statistics
        """
        try:
            aggregations = {
                "aggs": {
                    "risk_levels": {
                        "terms": {"field": "risk_level", "size": 10}
                    },
                    "classifications": {
                        "terms": {"field": "classification", "size": 10}
                    },
                    "avg_systolic": {
                        "avg": {"field": "systolic_pressure"}
                    },
                    "avg_diastolic": {
                        "avg": {"field": "diastolic_pressure"}
                    }
                }
            }
            
            response = self.client.search(
                index=self.index_name,
                body=aggregations,
                size=0
            )
            
            aggs = response.get("aggregations", {})
            
            return {
                "total_anomalies": response["hits"]["total"]["value"],
                "risk_level_distribution": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in aggs.get("risk_levels", {}).get("buckets", [])
                },
                "classification_distribution": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in aggs.get("classifications", {}).get("buckets", [])
                },
                "avg_systolic": aggs.get("avg_systolic", {}).get("value"),
                "avg_diastolic": aggs.get("avg_diastolic", {}).get("value")
            }
            
        except Exception as e:
            logger.error(f"Statistics query failed: {e}")
            return {}

    def delete_index(self) -> bool:
        """
        Delete the index (use with caution).
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            self.client.indices.delete(index=self.index_name)
            logger.info(f"Index {self.index_name} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False

    def close(self):
        """Close Elasticsearch connection."""
        try:
            self.client.close()
            logger.info("Elasticsearch connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    @staticmethod
    def _calculate_severity_score(anomaly: Dict) -> float:
        """
        Calculate severity score for an anomaly (0.0 to 1.0).
        
        Args:
            anomaly: Anomaly analysis dictionary
        
        Returns:
            Severity score
        """
        risk_weights = {
            "CRITICAL": 1.0,
            "HIGH": 0.75,
            "MODERATE": 0.5,
            "LOW": 0.25
        }
        
        base_score = risk_weights.get(anomaly.get("risk_level", "LOW"), 0.25)
        
        # Adjust based on ML probability if available
        ml_prob = anomaly.get("ml_probability_abnormal")
        if ml_prob is not None:
            base_score = (base_score + ml_prob) / 2
        
        return min(base_score, 1.0)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    handler = ElasticsearchHandler()
    handler.create_index()
    
    # Search examples
    critical_cases = handler.search_anomalies(risk_level="CRITICAL")
    print(f"Found {len(critical_cases)} critical cases")
    
    # Get statistics
    stats = handler.get_statistics()
    print(json.dumps(stats, indent=2))
