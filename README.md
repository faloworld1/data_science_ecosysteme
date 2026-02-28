# Système de Surveillance des Données de Pression Artérielle avec Kafka, Elasticsearch et Kibana

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Utilisation](#utilisation)
6. [Documentation API](#documentation-api)
7. [Kibana Dashboard](#kibana-dashboard)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'ensemble

Ce projet implémente une architecture complète pour la surveillance en temps réel des données de pression artérielle des patients. Le système:

- **Génère** des données médicales au format FHIR (Fast Healthcare Interoperability Resources)
- **Traite** les données en temps réel via Apache Kafka
- **Analyse** les anomalies basée sur des seuils médicaux et/ou un modèle ML
- **Stocke** les cas anormaux dans Elasticsearch pour alertes et visualisation
- **Archive** les cas normaux dans des fichiers JSON locaux
- **Visualise** les données via Kibana

### Catégories de Pression Artérielle

| Catégorie | Systolique (mmHg) | Diastolique (mmHg) | Action |
|-----------|-------------------|-------------------|--------|
| **NORMAL** | < 120 | et | < 80 | Continuer surveillance |
| **ELEVATED** | 120-129 | et | < 80 | Réévaluation en 3-6 mois |
| **HBP STAGE 1** | 130-139 | ou | 80-89 | Prise en charge non-pharmacologique |
| **HBP STAGE 2** | ≥ 140 | ou | ≥ 90 | Pharmacothérapie recommandée |
| **HYPERTENSIVE CRISIS** | > 180 | et/ou | > 120 | **ALERTE IMMÉDIATE** |
| **HYPOTENSION** | < 90 | ou | < 60 | Investigation requise |

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FHIR Data Generator                          │
│        (Génère des observations FHIR pseudo-réalistes)         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │     Kafka Producer                 │
        │  (Publie sur topic)                │
        └────────┬─────────────────────────┬─┘
                 │                         │
        ┌────────▼──────────────────────┐  │
        │   Kafka Broker                │  │
        │   (Topic: blood-pressure-     │  │
        │    observations)              │  │
        └────────┬──────────────────────┘  │
                 │                         │
        ┌────────▼──────────────────────┐  │
        │   Kafka Consumer              │  │
        └────┬───────────────────────┬──┘  │
             │                       │      │
    ┌────────▼──────────┐    ┌──────▼──────────────┐
    │ Anomaly Detector  │    │  Normal Cases       │
    │ (Seuils + ML)     │    │  Storage (JSON)     │
    └────┬───────────┬──┘    └─────────────────────┘
         │           │
    ┌────▼──────┐    │
    │ Elasticsearch   │
    │ (Index anomalies)
    └────┬──────┘
         │
    ┌────▼──────┐
    │  Kibana   │
    │ Dashboard │
    └───────────┘
```

---

## 📦 Installation

### Prérequis

- Docker & Docker Compose
- Python 3.8+
- Git

### Étape 1: Cloner et configurer

```bash
# Naviguer vers le dossier du projet
cd "c:\Users\Dell\Documents\ibou\USPN_BIDABI1\semestre 1\data science ecosysteme\projet1"

# Installer les dépendances Python
pip install -r requirements.txt
```

> **Remarque** : la librairie `elasticsearch` est spécifiée comme `<9.0.0`
> dans `requirements.txt`. Si votre environnement installe la version
> 9.x (ce qui est arrivé dans votre cas), le code applique automatiquement
> un en‑tête de compatibilité afin de fonctionner avec Elasticsearch 8
> (voir `src/elasticsearch_handler.py`). Vous pouvez aussi forcer
> manuellement `pip install "elasticsearch==8.11.0"` pour rester
> strictement sur la gamme 8.x.


### Étape 2: Démarrer les services Docker

```bash
# Démarrer Kafka, Elasticsearch et Kibana
docker-compose up -d

# Vérifier le statut
docker-compose ps

# Consulter les logs
docker-compose logs -f
```

**Services démarrés:**
- ✅ **Kafka**: http://localhost:9092
- ✅ **Elasticsearch**: http://localhost:9200
- ✅ **Kibana**: http://localhost:5601
- ✅ **Kafka UI** (optionnel): http://localhost:8080

### Étape 3: Initialiser les sujets Kafka

```bash
# Créer le topic pour les observations BP
docker exec -it $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-topics --create \
  --topic blood-pressure-observations \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

---

## ⚙️ Configuration

### Fichier `config/app_config.py`

```python
# Kafka
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC_BP_OBSERVATIONS = "blood-pressure-observations"

# Elasticsearch
ELASTICSEARCH_HOSTS = ["localhost:9200"]
ELASTICSEARCH_INDEX = "blood-pressure-anomalies"

# Générateur
NUM_PATIENTS = 10
BATCH_SIZE = 20

# Modèle ML
USE_ML_MODEL = True  # Optionnel
ML_MODEL_PATH = "models/trained_model.pkl"

# Mode
DEMO_MODE = False  # True pour test rapide
```

### Variables d'environnement

```bash
# .env (optionnel)
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export ELASTICSEARCH_HOSTS=localhost:9200
export LOG_LEVEL=INFO
```

---

## 🚀 Utilisation

### 1. Mode Demo (Rapide - Test)

```bash
# Modifier config/app_config.py
DEMO_MODE = True
DEMO_NUM_MESSAGES = 50

# Lancer
python main.py
```

### 2. Mode Production (Temps Réel)

```python
# Modifier config/app_config.py
DEMO_MODE = False

# Lancer
python main.py
```

### 3. Utiliser les modules individuellement

#### Générer des observations FHIR

```python
from src.fhir_generator import FHIRBPObservationGenerator
import json

generator = FHIRBPObservationGenerator(num_patients=5)
observations = generator.generate_batch(batch_size=10)

for obs in observations:
    print(json.dumps(obs, indent=2))
```

#### Publier via Kafka

```python
from src.kafka_producer import BPObservationProducer

producer = BPObservationProducer(
    bootstrap_servers="localhost:9092",
    topic="blood-pressure-observations"
)

producer.publish_batch(observations)
producer.close()
```

#### Détecter les anomalies

```python
from src.anomaly_detector import BloodPressureAnomalyDetector

detector = BloodPressureAnomalyDetector(
    ml_model_path="models/trained_model.pkl"  # optionnel
)

analysis = detector.detect_anomalies(observation)
print(f"Classification: {analysis['classification']}")
print(f"Is Anomalous: {analysis['is_anomalous']}")
print(f"Risk Level: {analysis['risk_level']}")
```

#### Indexer dans Elasticsearch

```python
from src.elasticsearch_handler import ElasticsearchHandler

es = ElasticsearchHandler(hosts=["localhost:9200"])
es.create_index()
es.index_anomaly(analysis)
```

#### Stocker les cas normaux

```python
from src.data_storage import NormalCasesStorage

storage = NormalCasesStorage(storage_dir="data/normal_cases")
storage.save_case(analysis)

stats = storage.get_statistics()
print(stats)
```

#### Entraîner un modèle ML

```python
from src.ml_model import BPAnomalyMLModel

model = BPAnomalyMLModel(model_type="logistic_regression")

# Générer données d'entraînement
systolic, diastolic, labels = BPAnomalyMLModel.generate_synthetic_training_data(
    num_samples=1000,
    abnormal_ratio=0.35
)

# Entraîner
metrics = model.train(systolic, diastolic, labels)
print(metrics)

# Sauvegarder
model.save_model("models/trained_model.pkl")

# Prédire
prediction, probability = model.predict(systolic=145, diastolic=95)
print(f"Prédiction: {prediction}, Probabilité: {probability:.2f}")
```

#### Consommer et traiter en temps réel

```python
from src.kafka_consumer import BPObservationConsumer

consumer = BPObservationConsumer(
    bootstrap_servers="localhost:9092",
    topic="blood-pressure-observations"
)

def handle_anomaly(analysis):
    print(f"[ANOMALY] {analysis}")

def handle_normal(analysis):
    print(f"[NORMAL] Patient {analysis['patient_id']}")

consumer.start_consuming(
    anomaly_callback=handle_anomaly,
    normal_callback=handle_normal,
    max_messages=100
)
```

---

## 📚 Documentation API

### `FHIRBPObservationGenerator`

```python
generator = FHIRBPObservationGenerator(
    num_patients=10,
    data_points_per_patient=5
)

# Générer batch
observations = generator.generate_batch(batch_size=20)

# Générer basé sur catégorie
observations = generator.generate_observations(category="NORMAL")
```

### `BloodPressureAnomalyDetector`

```python
detector = BloodPressureAnomalyDetector(ml_model_path=None)

# Analyser observation
analysis = detector.detect_anomalies(observation)

# Classification seule
classification = detector.classify_blood_pressure(145, 95)

# Vérifier anomalie
is_anomalous = detector.is_anomalous(145, 95)

# Statistiques batch
stats = detector.get_summary_stats(observations)
```

### `ElasticsearchHandler`

```python
es = ElasticsearchHandler(hosts=["localhost:9200"])

# Créer index
es.create_index(force_recreate=False)

# Indexer anomalies
es.index_batch(anomalies)

# Chercher
results = es.search_anomalies(risk_level="CRITICAL", limit=100)

# Statistiques
stats = es.get_statistics()
```

### `NormalCasesStorage`

```python
storage = NormalCasesStorage(storage_dir="data/normal_cases")

# Sauvegarder
storage.save_case(analysis)
storage.save_batch([analysis_1, analysis_2])

# Lire statistiques
stats = storage.get_statistics()

# Lister fichiers
files = storage.list_files()
```

---

## 📊 Kibana Dashboard

### Configuration

1. **Accéder à Kibana**: http://localhost:5601

2. **Créer l'index pattern**:
   - Aller à: Stack Management → Index Patterns
   - Créer nouveau: `blood-pressure-anomalies`
   - Time field: `indexed_time`

3. **Créer Dashboard**:
   - Analytics → Dashboards → Create
   - Ajouter visualisations:

#### Visualisations recommandées

**1. Distribution des Niveaux de Risque (Pie Chart)**
```json
{
  "query": { "match_all": {} },
  "aggs": {
    "risk_levels": {
      "terms": { "field": "risk_level" }
    }
  }
}
```

**2. Évolution Temporelle des Anomalies (Time Series)**
```json
{
  "aggs": {
    "anomalies_over_time": {
      "date_histogram": {
        "field": "indexed_time",
        "interval": "1h"
      }
    }
  }
}
```

**3. Classification des Anomalies (Bar Chart)**
```json
{
  "aggs": {
    "by_classification": {
      "terms": { "field": "classification" }
    }
  }
}
```

**4. Cas Critiques (Table)**
```json
{
  "query": {
    "term": { "risk_level": "CRITICAL" }
  },
  "size": 100,
  "sort": [{ "indexed_time": { "order": "desc" } }]
}
```

**5. Statistiques de Pression (Metric)**
```
Avg Systolic: avg(systolic_pressure)
Avg Diastolic: avg(diastolic_pressure)
Max Systolic: max(systolic_pressure)
```

**6. Probabilité ML (Scatter Plot)**
- X axis: systolic_pressure
- Y axis: diastolic_pressure
- Color: ml_probability_abnormal

---

## 🔧 Fichiers et Modules

```
projet1/
├── src/
│   ├── __init__.py
│   ├── fhir_generator.py          # Génération FHIR
│   ├── kafka_producer.py          # Publication Kafka
│   ├── kafka_consumer.py          # Consommation Kafka
│   ├── anomaly_detector.py        # Détection des anomalies
│   ├── elasticsearch_handler.py   # Gestion Elasticsearch
│   ├── data_storage.py            # Stockage JSON local
│   └── ml_model.py                # Modèles ML (optionnel)
├── config/
│   └── app_config.py              # Configuration centralisée
├── data/
│   └── normal_cases/              # Stockage des cas normaux
├── models/
│   └── trained_model.pkl          # Modèle ML persisté
├── logs/
│   └── app.log                    # Logs d'application
├── main.py                        # Script principal
├── requirements.txt               # Dépendances Python
├── docker-compose.yml             # Stack Docker
└── README.md                      # Cette documentation
```

---

## 🧪 Tests et Exemples

### Test Unitaire - Anomaly Detection

```bash
cd src
python anomaly_detector.py
```

### Test Unitaire - FHIR Generator

```bash
cd src
python fhir_generator.py
```

### Test Unitaire - ML Model

```bash
cd src
python ml_model.py
```

### Test d'intégration - Full Pipeline

```bash
# En deux terminaux parallèles:

# Terminal 1: Lancer le système principal
python main.py

# Terminal 2: Monitorer Kafka
docker exec -it $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-console-consumer --topic blood-pressure-observations \
  --bootstrap-server localhost:9092 --from-beginning
```

---

## 📈 Métriques et KPIs

Le système suivit:
- **Anomaly Rate**: % de cas anormaux
- **Risk Distribution**: Répartition des niveaux de risque
- **Processing Latency**: Temps de traitement par observation
- **Model Accuracy**: Précision du modèle ML (si utilisé)
- **Data Quality**: % d'observations valides

---

## ⚠️ Troubleshooting

### Kafka n'est pas accessible

```bash
# Vérifier si le conteneur tourne
docker ps

# Voir les logs Kafka
docker-compose logs kafka

# Redémarrer
docker-compose restart kafka
```

### Erreur de connexion Elasticsearch

```bash
# Vérifier la santé du cluster
curl http://localhost:9200/_cluster/health

# Vérifier l'espace disque
curl http://localhost:9200/_cat/nodes?v

# Redémarrer
docker-compose restart elasticsearch
```

### Index Elasticsearch introuvable

```bash
# Créer l'index manuellement
curl -X PUT http://localhost:9200/blood-pressure-anomalies

# Vérifier les index existants
curl http://localhost:9200/_cat/indices
```

### Erreur d'importation Python

```bash
# Réinstaller les packages
pip install -r requirements.txt --upgrade

# Vérifier la version de Python
python --version  # >= 3.8
```

### Logs et déboggage

```bash
# Voir tous les logs
tail -f logs/app.log

# Filtrer par niveau
grep ERROR logs/app.log

# Compter les anomalies détectées
grep "ANOMALY DETECTED" logs/app.log | wc -l
```

---

## 🔐 Points de sécurité

- ✅ Validation FHIR des données
- ✅ Contrôle d'accès Elasticsearch (à implémenter en prod)
- ✅ Chiffrage des données sensibles (à implémenter)
- ✅ Audit logs (implémentation dans app.log)
- ✅ Rate limiting Kafka (configurable)

### Pour la production:

1. Activer l'authentification Elasticsearch
2. Déployer avec VPN/SSL
3. Implémenter le chiffrement TLS
4. Configurer les sauvegardes automatiques
5. Monitorer les ressources système

---

## 📝 Livrables

- ✅ `src/fhir_generator.py` - Générateur FHIR
- ✅ `src/kafka_producer.py` - Producer Kafka
- ✅ `src/kafka_consumer.py` - Consumer Kafka
- ✅ `src/anomaly_detector.py` - Détection anomalies
- ✅ `src/elasticsearch_handler.py` - Gestion ES
- ✅ `src/data_storage.py` - Stockage local
- ✅ `src/ml_model.py` - Modèles ML
- ✅ `config/app_config.py` - Configuration
- ✅ `main.py` - Orchestration
- ✅ `docker-compose.yml` - Stack complète
- ✅ `requirements.txt` - Dépendances
- ✅ `README.md` - Documentation

---

## 📞 Support et Contactez

Pour des questions ou problèmes:
1. Consulter les logs: `tail -f logs/app.log`
2. Vérifier la santé des services: `docker-compose ps`
3. Tester les connexions individuellement

---

## 📄 Licence et Attribution

Ce projet est développé pour usage éducatif dans le cadre du cursus Data Science.

Basé sur les standards:
- **FHIR**: HL7 Fast Healthcare Interoperability Resources
- **Kafka**: Apache Kafka Distributed Streaming
- **Elasticsearch**: Elastic Stack for Search & Analytics

---

**Version**: 1.0.0  
**Dernière mise à jour**: 2024  
**Auteur**: Health Data Science Team
