# ARCHITECTURE TECHNIQUE DÉTAILLÉE

## 📐 Vue d'ensemble de l'Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION LAYER                            │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │          FHIR Observation Generator                              │  │
│  │  - Génère des observations Observation FHIR pseudo-réalistes     │  │
│  │  - 10 patients, 5 observations par patient                       │  │
│  │  - Mix de catégories: Normal (60%), Elevated (20%), Anormal (20) │  │
│  └────────────┬─────────────────────────────────────────────────────┘  │
└─────────────┼──────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   MESSAGE STREAMING LAYER (KAFKA)                       │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Kafka Producer                    Kafka Broker                  │  │
│  │  ┌──────────────┐               ┌─────────────────┐             │  │
│  │  │ Publish FHIR │──────────────▶│ Topic: blood-   │             │  │
│  │  │ Observations │               │ pressure-       │             │  │
│  │  └──────────────┘               │ observations    │             │  │
│  │                                 │                 │             │  │
│  │                                 │ Partitions: 3   │             │  │
│  │  Kafka Consumer                 │ RF: 1           │             │  │
│  │  ┌──────────────┐               │                 │             │  │
│  │  │ Consume from │◀──────────────│ (JSON messages) │             │  │
│  │  │ Topic        │               └─────────────────┘             │  │
│  │  └──────────────┘                                               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER (ANOMALY DETECTION)                 │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Anomaly Detector                                               │  │
│  │  ├─ Extract BP values from FHIR                                 │  │
│  │  ├─ Classify using medical thresholds                          │  │
│  │  │  └─ NORMAL, ELEVATED, HBP_STAGE_1, HBP_STAGE_2,            │  │
│  │  │     HYPERTENSIVE_CRISIS, HYPOTENSION                        │  │
│  │  ├─ Calculate risk level (LOW, MODERATE, HIGH, CRITICAL)       │  │
│  │  └─ Optional: ML model prediction (if available)               │  │
│  │      ├─ Load trained model (Logistic Regression or RF)         │  │
│  │      ├─ Get probability of abnormality                         │  │
│  │      └─ Combine with threshold-based classification            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────────┘
              ┌─────────────┼──────────────────┐
              │             │                  │
        (Anomalous)   (Normal)          (Invalid)
              │             │                  │
              ▼             ▼                  ▼
┌──────────────────────┐   │         (Log & Skip)
│   ELASTICSEARCH      │   │
│   (Anomalies        │   │
│   Storage)           │   │
│                      │   │
│ ┌────────────────┐  │   │
│ │Index Creation  │  │   │
│ │ - Doc ID       │  │   │
│ │ - Patient Info │  │   │
│ │ - BP Values    │  │   │
│ │ - Classification│ │   │
│ │ - Risk Level   │  │   │
│ │ - Timestamp    │  │   │
│ │ - ML Score     │  │   │
│ └────────────────┘  │   │
└──────────────────────┘   │
                           │
                           ▼
                ┌──────────────────────┐
                │  LOCAL JSON STORAGE  │
                │                      │
                │ data/normal_cases/   │
                │ ├─ normal_cases_     │
                │ │   2024-01-15.json  │
                │ ├─ normal_cases_     │
                │ │   2024-01-16.json  │
                │ └─ statistics.json   │
                │                      │
                │ (Daily files)        │
                └──────────────────────┘

              (Anomalies)
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    VISUALIZATION LAYER (KIBANA)                         │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  Index: blood-pressure-anomalies                              │   │
│  │                                                                │   │
│  │  Visualizations:                                             │   │
│  │  ├─ Risk Level Distribution (Pie Chart)                       │   │
│  │  ├─ Anomalies Over Time (Time Series)                        │   │
│  │  ├─ Classification Distribution (Bar Chart)                   │   │
│  │  ├─ Critical Cases (Table)                                    │   │
│  │  ├─ BP Statistics (Metrics)                                   │   │
│  │  ├─ ML Prediction Accuracy (Scatter)                          │   │
│  │  └─ Patient Distribution (Map, if geo data)                   │   │
│  │                                                                │   │
│  │  Dashboard Features:                                          │   │
│  │  ├─ Real-time alerts for CRITICAL cases                       │   │
│  │  ├─ Filtering by risk level, patient, date range              │   │
│  │  ├─ Drill-down on individual cases                            │   │
│  │  └─ Export reports (CSV, PDF)                                 │   │
│  └────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flux de Données Détaillé

### 1. INGESTION (FHIR Generator → Kafka Producer)

```python
# 1. Generator crée observations FHIR
observation = {
    "resourceType": "Observation",
    "id": "uuid-1234",
    "status": "final",
    "code": { "coding": [{"code": "85354-9", ...}] },  # BP Panel code
    "subject": { "reference": "Patient/patient-uuid" },
    "effectiveDateTime": "2024-01-15T10:30:00Z",
    "component": [
        {
            "code": { "coding": [{"code": "8480-6"}] },  # Systolic
            "valueQuantity": {
                "value": 145,  # Systolic pressure
                "unit": "mmHg"
            }
        },
        {
            "code": { "coding": [{"code": "8462-4"}] },  # Diastolic
            "valueQuantity": {
                "value": 95,  # Diastolic pressure
                "unit": "mmHg"
            }
        }
    ]
}

# 2. Producer publie sur Kafka
producer.send(
    topic="blood-pressure-observations",
    value=observation,
    key=patient_id,  # Pour partitioning par patient
    timestamp_ms=millis()
)
```

### 2. STREAMING (Kafka Broker)

```
Topic: blood-pressure-observations
├─ Partition 0: Messages pour patients groupe 1
├─ Partition 1: Messages pour patients groupe 2
└─ Partition 2: Messages pour patients groupe 3

Configuration:
├─ Replication Factor: 1
├─ Min Insync Replicas: 1
├─ Retention: 7 jours (par défaut)
├─ Compression: SNAPPY
└─ Acks: all (garantie de durabilité)
```

### 3. PROCESSING (Anomaly Detection)

```python
# Consumer reçoit le message
message = consumer.next()
observation = json.loads(message.value)

# Detecteur analyse
analysis = detector.detect_anomalies(observation)

# Résultat
{
    "is_valid": True,
    "observation_id": "uuid-1234",
    "patient_id": "patient-uuid",
    "systolic": 145,
    "diastolic": 95,
    "classification": "HYPERTENSION_STAGE_2",
    "is_anomalous": True,
    "risk_level": "HIGH",
    "anomaly_type": "HYPERTENSION_STAGE_2",
    
    # ML (si disponible)
    "ml_probability_abnormal": 0.87,
    "ml_recommendation": "ALERT",
    
    "observation_time": "2024-01-15T10:30:00Z"
}
```

### 4. STORAGE

#### Pour les Anomalies (→ Elasticsearch):
```json
{
    "observation_id": "uuid-1234",
    "patient_id": "patient-uuid",
    "patient_name": "John Doe",
    "systolic_pressure": 145,
    "diastolic_pressure": 95,
    "classification": "HYPERTENSION_STAGE_2",
    "anomaly_type": "HYPERTENSION_STAGE_2",
    "risk_level": "HIGH",
    "severity_score": 0.75,
    "observation_time": "2024-01-15T10:30:00Z",
    "indexed_time": "2024-01-15T10:31:00Z",
    "ml_probability_abnormal": 0.87,
    "ml_recommendation": "ALERT"
}
```

#### Pour les Cas Normaux (→ JSON local):
```json
[
    {
        "observation_id": "uuid-5678",
        "patient_id": "patient-uuid-2",
        "patient_name": "Jane Doe",
        "systolic_pressure": 115,
        "diastolic_pressure": 72,
        "classification": "NORMAL",
        "observation_time": "2024-01-15T10:45:00Z",
        "saved_time": "2024-01-15T10:46:00Z"
    }
]
```

---

## 🏗️ Composants Clés

### 1. FHIR Generator (`src/fhir_generator.py`)

**Responsabilités:**
- Génération d'observations FHIR conformes au standard
- Création de patients pseudo-réalistes (Faker)
- Mix de catégories de BP

**Classes:**
- `FHIRBPObservationGenerator`: Générateur principal

**Méthodes clés:**
- `generate_observations(category)`: Générer batch basé sur catégorie
- `generate_batch(batch_size)`: Générer batch mixte

**Output:** Liste des observations FHIR en JSON

---

### 2. Kafka Producer (`src/kafka_producer.py`)

**Responsabilités:**
- Connexion à Kafka
- Publication des observations
- Gestion des erreurs et retries

**Classes:**
- `BPObservationProducer`: Producer Kafka

**Méthodes clés:**
- `publish_observation(observation, patient_id)`: Publier message unique
- `publish_batch(observations)`: Publier batch

**Configuration:**
- Bootstrap servers: `localhost:9092`
- Topic: `blood-pressure-observations`
- Partitioning: Par patient ID
- Acks: all (durabilité garantie)

---

### 3. Anomaly Detector (`src/anomaly_detector.py`)

**Responsabilités:**
- Extraction des valeurs BP de FHIR
- Classification basée sur seuils médicaux
- Calcul du niveau de risque
- Prédiction ML optionnelle

**Classes:**
- `BloodPressureAnomalyDetector`: Détecteur principal

**Seuils médicaux:**

| Catégorie | Systolic | Diastolic |
|-----------|----------|-----------|
| NORMAL | < 120 | < 80 |
| ELEVATED | 120-129 | < 80 |
| HBP STAGE 1 | 130-139 | 80-89 |
| HBP STAGE 2 | ≥ 140 | ≥ 90 |
| HYPERTENSIVE CRISIS | > 180 | > 120 |
| HYPOTENSION | < 90 | < 60 |

**Méthodes clés:**
- `extract_bp_values(observation)`: Extraire Sys/Dia
- `classify_blood_pressure(sys, dia)`: Classifier
- `is_anomalous(sys, dia)`: Vérifier anomalie
- `detect_anomalies(observation)`: Analyse complète
- `_predict_with_ml(sys, dia)`: Prédiction ML

---

### 4. Kafka Consumer (`src/kafka_consumer.py`)

**Responsabilités:**
- Consommation des messages Kafka
- Appel des callbacks pour traitement
- Gestion de la réconciliation

**Classes:**
- `BPObservationConsumer`: Consumer Kafka

**Méthodes clés:**
- `start_consuming(anomaly_callback, normal_callback)`: Boucle de consommation
- `process_message(observation, ...)`: Traiter message unique

**Consumer Group:** `bp-anomaly-detection-group`

---

### 5. Elasticsearch Handler (`src/elasticsearch_handler.py`)

**Responsabilités:**
- Connexion à Elasticsearch
- Création et gestion d'index
- Indexation des documents
- Recherche et agrégations

**Classes:**
- `ElasticsearchHandler`: Gestionnaire ES

**Index Configuration:**
- Nom: `blood-pressure-anomalies`
- Shards: 1
- Replicas: 0
- Refresh: 1s

**Méthodes clés:**
- `create_index()`: Créer l'index
- `index_anomaly(analysis)`: Indexer anomalie
- `search_anomalies(risk_level, patient_id)`: Chercher
- `get_statistics()`: Agrégations

---

### 6. Data Storage (`src/data_storage.py`)

**Responsabilités:**
- Sauvegarde des cas normaux en JSON
- Organisation par date
- Gestion des statistiques

**Classes:**
- `NormalCasesStorage`: Gestionnaire stockage local

**Méthodes clés:**
- `save_case(analysis)`: Sauvegarder cas unique
- `save_batch(analyses)`: Sauvegarder batch
- `get_statistics()`: Stats

---

### 7. ML Model (`src/ml_model.py`)

**Responsabilités:**
- Entraînement du modèle
- Prédictions
- Persistence

**Classes:**
- `BPAnomalyMLModel`: Modèle ML

**Modèles supportés:**
- Logistic Regression
- Random Forest

**Méthodes clés:**
- `train(systolic, diastolic, labels)`: Entraîner
- `predict(systolic, diastolic)`: Prédire
- `save_model(filepath)`: Sauvegarder
- `load_model(filepath)`: Charger

---

## 📊 Schémas de Données

### Elasticsearch Index Mapping

```json
{
  "properties": {
    "observation_id": { "type": "keyword" },
    "patient_id": { "type": "keyword" },
    "patient_name": { "type": "text" },
    "systolic_pressure": { "type": "integer" },
    "diastolic_pressure": { "type": "integer" },
    "classification": { "type": "keyword" },
    "anomaly_type": { "type": "keyword" },
    "risk_level": { "type": "keyword" },
    "observation_time": { "type": "date" },
    "indexed_time": { "type": "date" },
    "ml_probability_abnormal": { "type": "float" },
    "ml_recommendation": { "type": "keyword" },
    "severity_score": { "type": "float" }
  }
}
```

---

## 🔌 Intégrations Externes

### Kafka
- Version: 7.5.0
- Cluster: Single broker
- Replication: 1
- Port: 9092

### Elasticsearch
- Version: 8.10.0
- Cluster: Single node
- Port: 9200

### Kibana
- Version: 8.10.0
- Port: 5601

---

## ⚙️ Configuration Système

### Memory & Resources
```
Kafka: 1GB heap
Elasticsearch: 512MB min, 512MB max
Kibana: 1GB
```

### Network
```
Kafka: 9092 (broker), 29092 (internal)
Elasticsearch: 9200 (REST), 9300 (node)
Kibana: 5601 (web)
```

---

## 🔍 Monitoring & Observabilité

### Logs
- Application: `logs/app.log`
- Format: Timestamp | Logger | Level | Message
- Rotation: À implémenter

### Métriques
- Messages publiés/consommés
- Anomalies détectées
- Latence de traitement
- Accuracy du modèle ML

### Alertes
- Cases CRITICAL: Urgent
- Cases HIGH: Important
- Erreurs de connexion

---

## 🚀 Performance & Scalabilité

### Capacité actuelle
- ~1000 observations/minute
- Latence: < 100ms par observation
- Rétention ES: Illimitée

### Optimisations possibles
1. Augmenter partitions Kafka (→ 10)
2. Ajouter réplicas ES (→ 3)
3. Sharding par patient ID
4. Batch indexing ES
5. Caching Redis pour requêtes fréquentes
6. Archivage historique (ILM policy)

---

## 🔐 Sécurité

### Points à implémenter
- [ ] Authentification Kafka (SASL)
- [ ] TLS/SSL pour Elasticsearch
- [ ] X-Pack Security (ES)
- [ ] API Keys pour Kibana
- [ ] Audit logging
- [ ] Chiffrement des données sensibles

---

**Version**: 1.0.0  
**Dernière mise à jour**: 2024
