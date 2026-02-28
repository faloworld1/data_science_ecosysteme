"""
Elasticsearch Setup Script
Crée l'index avec les paramètres de mapping optimisés
"""

import json
import requests
import time
import sys

ES_HOST = "http://localhost:9200"
INDEX_NAME = "blood-pressure-anomalies"

def wait_for_elasticsearch(max_retries=30, timeout=2):
    """Attendre que Elasticsearch soit prêt."""
    print("Attente du démarrage d'Elasticsearch...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{ES_HOST}/_cluster/health", timeout=timeout)
            if response.status_code == 200:
                print(f"✓ Elasticsearch est prêt")
                return True
        except requests.exceptions.ConnectionError:
            print(f"  Tentative {i+1}/{max_retries}...")
            time.sleep(timeout)
    
    print("✗ Elasticsearch n'a pas pu démarrer")
    return False

def create_index():
    """Créer l'index avec les mappings."""
    mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "index": {
                "lifecycle.name": "bp-policy",
                "refresh_interval": "1s"
            }
        },
        "mappings": {
            "properties": {
                "observation_id": {
                    "type": "keyword"
                },
                "patient_id": {
                    "type": "keyword"
                },
                "patient_name": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "systolic_pressure": {
                    "type": "integer"
                },
                "diastolic_pressure": {
                    "type": "integer"
                },
                "classification": {
                    "type": "keyword"
                },
                "anomaly_type": {
                    "type": "keyword"
                },
                "risk_level": {
                    "type": "keyword"
                },
                "observation_time": {
                    "type": "date"
                },
                "indexed_time": {
                    "type": "date"
                },
                "ml_probability_abnormal": {
                    "type": "float"
                },
                "ml_recommendation": {
                    "type": "keyword"
                },
                "severity_score": {
                    "type": "float"
                }
            }
        }
    }
    
    # Vérifier si l'index existe
    response = requests.head(f"{ES_HOST}/{INDEX_NAME}")
    if response.status_code == 200:
        print(f"Index '{INDEX_NAME}' existe déjà")
        return True
    
    # Créer l'index
    response = requests.put(
        f"{ES_HOST}/{INDEX_NAME}",
        json=mapping,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        print(f"✓ Index '{INDEX_NAME}' créé avec succès")
        return True
    else:
        print(f"✗ Erreur création index: {response.text}")
        return False

def create_ilm_policy():
    """Créer une politique de gestion du cycle de vie (optionnel)."""
    policy = {
        "policy": "bp-policy",
        "phases": {
            "hot": {
                "min_age": "0d",
                "actions": {
                    "rollover": {
                        "max_primary_shard_size": "50gb",
                        "max_age": "1d"
                    }
                }
            },
            "warm": {
                "min_age": "7d",
                "actions": {
                    "set_priority": {
                        "priority": 50
                    }
                }
            },
            "delete": {
                "min_age": "90d",
                "actions": {
                    "delete": {}
                }
            }
        }
    }
    
    response = requests.put(
        f"{ES_HOST}/_ilm/policy/bp-policy",
        json=policy,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code in [200, 201]:
        print("✓ Politique ILM créée")
        return True
    else:
        print(f"! Politique ILM: {response.text}")
        return False

def verify_setup():
    """Vérifier la configuration."""
    # Vérifier l'index
    response = requests.get(f"{ES_HOST}/{INDEX_NAME}")
    if response.status_code == 200:
        index_info = response.json()[INDEX_NAME]
        docs = requests.get(f"{ES_HOST}/{INDEX_NAME}/_count").json()
        print(f"\n✓ Index stats:")
        print(f"  - Documents: {docs['count']}")
        print(f"  - Shards: {index_info['settings']['index']['number_of_shards']}")
        return True
    
    return False

def main():
    """Fonction principale."""
    print("="*60)
    print("  Elasticsearch Setup")
    print("="*60)
    
    # Attendre Elasticsearch
    if not wait_for_elasticsearch():
        sys.exit(1)
    
    print("\nConfiguration de l'index...")
    if not create_index():
        sys.exit(1)
    
    print("\nCréation de la politique ILM...")
    create_ilm_policy()
    
    print("\nVérification...")
    if verify_setup():
        print("\n✓ Configuration réussie!")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
