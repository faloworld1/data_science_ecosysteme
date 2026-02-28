# GUIDE COMPLET DE DÉPANNAGE

## 🔧 Problèmes Courants et Solutions

---

## 1. KAFKA

### ✗ Kafka ne démarre pas

**Symptôme:**
```
ERROR: Unable to start Kafka
Connection refused
```

**Solutions:**

```bash
# 1. Vérifier si Docker est actif
docker --version
docker ps

# 2. Regarder les logs
docker-compose logs kafka

# 3. Vérifier le port 9092
netstat -an | grep 9092  # macOS/Linux
netstat -an | find "9092"  # Windows

# 4. Redémarrer Zookeeper avant Kafka
docker-compose restart zookeeper
sleep 5
docker-compose restart kafka

# 5. Réinitialiser complètement
docker-compose down -v
docker-compose up -d kafka zookeeper
```

---

### ✗ Topic ne peut pas être créé

**Symptôme:**
```
Error: Topic already exists / Topic not found
```

**Solutions:**

```bash
# Vérifier les topics existants
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-topics --list --bootstrap-server localhost:9092

# Supprimer le topic
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-topics --delete \
  --topic blood-pressure-observations \
  --bootstrap-server localhost:9092

# Créer depuis zéro
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-topics --create \
  --topic blood-pressure-observations \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 \
  --if-not-exists
```

---

### ✗ Messages ne sont pas consommés

**Symptôme:**
```
No messages received from Kafka
Consumer hangs indefinitely
```

**Solutions:**

```python
# 1. Vérifier que le topic a des messages
# Terminal 1: Publier des messages
python -c "
from src.fhir_generator import FHIRBPObservationGenerator
from src.kafka_producer import BPObservationProducer

gen = FHIRBPObservationGenerator(num_patients=2)
obs = gen.generate_batch(5)

with BPObservationProducer() as prod:
    prod.publish_batch(obs)
"

# Terminal 2: Lire les messages
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-console-consumer \
  --topic blood-pressure-observations \
  --bootstrap-server localhost:9092 \
  --from-beginning \
  --max-messages 5
```

---

### ✗ Offset invalide

**Symptôme:**
```
java.lang.IllegalArgumentException: Valid offsets for partition 0 are from 0 to 42
```

**Solution:**

```bash
# Réinitialiser le consumer group
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group bp-anomaly-detection-group \
  --reset-offsets \
  --to-earliest \
  --execute \
  --topic blood-pressure-observations
```

---

## 2. ELASTICSEARCH

### ✗ Elasticsearch ne démarre pas

#### Client Python incompatible
Si vous voyez une erreur de type `media_type_header_exception` ou un
message précisant que la version `Accept` est 9, cela signifie que
le paquet `elasticsearch` installé est de la série 9.x. Cette version
est incompatible avec un cluster Elasticsearch 8.

```text
RuntimeError: Installed elasticsearch client is version 9.x, which is not \
compatible with an Elasticsearch 8 cluster. Please downgrade: pip install 'elasticsearch<9'
```

Solution : réinstallez une version 8.x :

```bash
pip install "elasticsearch==8.11.0"
```

Le code tente d'ajouter un en‑tête de compatibilité mais cela ne fonctionne
pas toujours; la façon la plus robuste est de rester sur la gamme 8.x.


### ✗ Elasticsearch ne démarre pas

**Symptôme:**
```
ERROR: Failed to connect to Elasticsearch
Connection refused on port 9200
```

**Solutions:**

```bash
# Vérifier les logs
docker-compose logs elasticsearch

# Vérifier la santé
curl http://localhost:9200/_cluster/health

# Redémarrer
docker-compose restart elasticsearch

# Vérifier la mémoire
docker stats elasticsearch

# Augmenter la mémoire si nécessaire
# Dans docker-compose.yml:
# environment:
#   - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
```

---

### ✗ Index ne peut pas être créé

**Symptôme:**
```
Error: Index already exists / Mapping already exists
```

**Solutions:**

```bash
# Supprimer l'index
curl -X DELETE http://localhost:9200/blood-pressure-anomalies

# Créer depuis zéro
python setup_elasticsearch.py

# Ou manuellement
curl -X PUT http://localhost:9200/blood-pressure-anomalies \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "observation_id": {"type": "keyword"},
        "systolic_pressure": {"type": "integer"},
        "diastolic_pressure": {"type": "integer"},
        ...
      }
    }
  }'
```

---

### ✗ Index devient read-only

**Symptôme:**
```
Error: Index is read-only (cannot write)
Disk space low
```

**Solutions:**

```bash
# Vérifier la santé du cluster
curl http://localhost:9200/_cluster/health?pretty

# Vérifier l'espace disque
curl http://localhost:9200/_cat/nodes?v

# Libérer le mode read-only
curl -X PUT http://localhost:9200/blood-pressure-anomalies/_settings \
  -H "Content-Type: application/json" \
  -d '{
    "index.blocks.read_only_allow_delete": null
  }'

# Nettoyer les indices anciens
curl -X DELETE "http://localhost:9200/*-old"

# Réduire la rétention
curl -X PUT http://localhost:9200/_all/_settings \
  -H "Content-Type: application/json" \
  -d '{
    "index.refresh_interval": "30s"
  }'
```

---

### ✗ Requêtes lentes

**Symptôme:**
```
Search takes > 1 second
High CPU usage
```

**Solutions:**

```bash
# Vérifier le nombre de docs
curl http://localhost:9200/blood-pressure-anomalies/_count

# Analyser les requêtes lentes
curl http://localhost:9200/_all/_search?explain \
  -H "Content-Type: application/json" \
  -d '{
    "query": {...}
  }' | jq '.slow_log'

# Ajouter des index
curl -X PUT http://localhost:9200/blood-pressure-anomalies/_mapping \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "risk_level": {
        "type": "keyword"
      }
    }
  }'

# Réduire la taille des shards
# Archiver les données anciennes
```

---

## 3. KIBANA

### ✗ Kibana ne démarre pas

**Symptôme:**
```
Kibana failed to start
Cannot connect to Elasticsearch
```

**Solutions:**

```bash
# Vérifier les logs
docker-compose logs kibana

# Vérifier la connexion ES
docker exec kibana_container \
  curl http://elasticsearch:9200

# Redémarrer
docker-compose restart kibana

# Vérifier le port
curl http://localhost:5601
```

---

### ✗ Index pattern introuvable

**Symptôme:**
```
No matches found in time range
No data to display
```

**Solutions:**

```bash
# Vérifier l'index existe
curl http://localhost:9200/_cat/indices

# Créer l'index pattern manuellement:
# 1. Stack Management → Index Patterns
# 2. Create Index Pattern
# 3. Name: blood-pressure-anomalies
# 4. Time field: indexed_time

# Ou via API
curl -X POST http://localhost:5601/api/saved_objects/index-pattern \
  -H "Content-Type: application/json" \
  -H "kbn-xsrf: true" \
  -d '{
    "attributes": {
      "title": "blood-pressure-anomalies",
      "timeFieldName": "indexed_time"
    }
  }'
```

---

### ✗ Visualisations ne se chargent pas

**Symptôme:**
```
Error loading visualization
Cannot read property 'buckets'
```

**Solutions:**

```bash
# Vérifier qu'il y a des données
curl http://localhost:9200/blood-pressure-anomalies/_count

# Attendre plus longtemps (index nouveaux)
# Les données prennent 1-2 secondes à être indexées

# Forcer un refresh
curl -X POST http://localhost:9200/blood-pressure-anomalies/_refresh

# Recréer la visualisation:
# 1. Analytics → Create Visualization
# 2. Sélectionner l'index
# 3. Choisir le type de visualisation
```

---

## 4. PYTHON & APPLICATION

### ✗ Erreur d'import

**Symptôme:**
```
ModuleNotFoundError: No module named 'kafka'
ImportError: cannot import name 'KafkaProducer'
```

**Solutions:**

```bash
# Réinstaller les dépendances
pip install -r requirements.txt --upgrade

# Vérifier la version de Python
python --version  # >= 3.8

# Utiliser un virtual environment
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows

# Réinstaller
pip install -r requirements.txt
```

---

### ✗ Connexion Kafka échoue

**Symptôme:**
```
Connection refused to localhost:9092
Broker list may be empty
```

**Solutions:**

```python
# Vérifier la connexion
import socket
sock = socket.socket()
try:
    sock.connect(('localhost', 9092))
    print("OK: Port 9092 accessible")
except:
    print("ERROR: Cannot connect to port 9092")

# Ou
from src.kafka_producer import BPObservationProducer
try:
    prod = BPObservationProducer()
    print("✓ Connected to Kafka")
except Exception as e:
    print(f"✗ Kafka error: {e}")
```

---

### ✗ Elasticsearch non trouvé

**Symptôme:**
```
ConnectionError: Connection refused (localhost:9200)
```

**Solutions:**

```python
# Vérifier la connexion
import requests
try:
    r = requests.get('http://localhost:9200/_cluster/health')
    print("OK: Elasticsearch is up")
except:
    print("ERROR: Cannot connect to Elasticsearch")

# Ou
from src.elasticsearch_handler import ElasticsearchHandler
try:
    es = ElasticsearchHandler()
    print("✓ Connected to Elasticsearch")
except Exception as e:
    print(f"✗ ES error: {e}")
    # Continue en mode dégradé
```

---

### ✗ Modèle ML non trouvé

**Symptôme:**
```
FileNotFoundError: models/trained_model.pkl
```

**Solutions:**

```bash
# Entraîner un nouveau modèle
python -c "
from src.ml_model import BPAnomalyMLModel

model = BPAnomalyMLModel()
sys, dia, labels = BPAnomalyMLModel.generate_synthetic_training_data(1000)
metrics = model.train(sys, dia, labels)
model.save_model('models/trained_model.pkl')
print('✓ Model trained and saved')
"

# Ou désactiver dans config/app_config.py:
# USE_ML_MODEL = False
```

---

### ✗ Pas de données générées

**Symptôme:**
```
Generated 0 observations
Empty batch
```

**Solutions:**

```python
# Tester le générateur
from src.fhir_generator import FHIRBPObservationGenerator

gen = FHIRBPObservationGenerator(num_patients=5)
obs = gen.generate_batch(10)

print(f"Generated: {len(obs)} observations")
for o in obs:
    print(f"  - Patient: {o['subject']['display']}")
```

---

### ✗ Anomalies non détectées

**Symptôme:**
```
All cases classified as NORMAL
Detector not working
```

**Solutions:**

```python
# Tester le détecteur avec des valeurs connues
from src.anomaly_detector import BloodPressureAnomalyDetector

detector = BloodPressureAnomalyDetector()

# Test systolic
print(detector.is_anomalous(145, 95))  # True
print(detector.is_anomalous(115, 75))  # False

# Test extraction
from src.fhir_generator import FHIRBPObservationGenerator
gen = FHIRBPObservationGenerator()
obs = gen.generate_batch(1)[0]

sys_val, dia_val = detector.extract_bp_values(obs)
print(f"Extracted: {sys_val}/{dia_val}")

if sys_val and dia_val:
    is_anom = detector.is_anomalous(sys_val, dia_val)
    print(f"Is anomalous: {is_anom}")
```

---

## 5. DOCKER & INFRASTRUCTURE

### ✗ Port déjà utilisé

**Symptôme:**
```
Error: address already in use
Port 9092 already allocated
```

**Solutions:**

```bash
# Windows
netstat -ano | findstr :9092
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :9092
kill -9 <PID>

# Ou changer le port dans docker-compose.yml
# ports:
#   - "9093:9092"  # Utiliser 9093 à la place

# Puis recréer
docker-compose restart kafka
```

---

### ✗ Volume Docker occupé

**Symptôme:**
```
Error: volume already exists
Cannot remove container, volume in use
```

**Solutions:**

```bash
# Voir les volumes
docker volume ls

# Supprimer un volume spécifique
docker volume rm elasticsearch_data

# Ou nettoyer complètement
docker-compose down -v
docker system prune -a --volumes
```

---

### ✗ Insuffisant espace disque

**Symptôme:**
```
No space left on device
Disk quota exceeded
```

**Solutions:**

```bash
# Vérifier l'espace
docker system df

# Nettoyer les images/containers inutilisées
docker system prune

# Nettoyer les archives logs
docker system prune --volumes

# Vérifier la taille des index ES
curl http://localhost:9200/_cat/shards

# Archiver/supprimer les données anciennes
```

---

## 6. PERFORMANCE & OPTIMIZATION

### ⚠️ Haute latence

**Symptômes:**
- Traitement lent (> 1s par message)
- High CPU
- High memory

**Solutions:**

```bash
# Monit les ressources
docker stats

# Augmenter les limites
# docker-compose.yml:
# services:
#   elasticsearch:
#     environment:
#       ES_JAVA_OPTS: "-Xms2g -Xmx2g"

# Ou en Python:
# Réduire la taille des batches
BATCH_SIZE = 10  # au lieu de 100

# Augmenter les partitions Kafka
kafka-topics --alter \
  --topic blood-pressure-observations \
  --partitions 6

# Indexer en batch
es.index_batch(anomalies)  # au lieu de index_anomaly()
```

---

### ⚠️ Queue Kafka pleine

**Symptômes:**
```
Queue is full
Cannot send message timeout
```

**Solutions:**

```python
# Réduire la taille des messages
BATCH_SIZE = 10

# Augmenter les consumer threads
# config/app_config.py:
# CONSUMER_THREADS = 3

# Ou utiliser async KafkaProducer
producer = KafkaProducer(
    ...,
    acks='1',  # au lieu de 'all'
    compression_type='snappy'
)
```

---

## 7. TESTING & VALIDATION

### Tester chaque composant

```bash
# Test FHIR Generator
python src/fhir_generator.py

# Test Anomaly Detector  
python src/anomaly_detector.py

# Test ML Model
python src/ml_model.py

# Test Elasticsearch
python src/elasticsearch_handler.py

# Test Data Storage
python src/data_storage.py

# Test All
python tests.py
```

---

## 8. PROFIL DE DÉPANNAGE

Pour un diagnostic complet, exécutez:

```bash
# Health Check Script
cat << 'EOF' > diag.sh
#!/bin/bash

echo "=== SYSTEM DIAGNOSIS ==="

echo -n "Docker: "
docker --version

echo -n "Python: "
python --version

echo -n "Kafka: "
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-broker-api-versions --bootstrap-server localhost:9092 \
  > /dev/null && echo "OK" || echo "FAIL"

echo -n "Elasticsearch: "
curl -s http://localhost:9200/_cluster/health | grep -q '"status"' \
  && echo "OK" || echo "FAIL"

echo -n "Kibana: "
curl -s http://localhost:5601/api/status | grep -q '"state"' \
  && echo "OK" || echo "FAIL"

echo ""
echo "=== LOGS ==="
tail -20 logs/app.log

echo ""
echo "=== RESOURCES ==="
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}"

EOF

chmod +x diag.sh
./diag.sh
```

---

## 🆘 Contacter le Support

Si le problème persiste:

1. Collecter les logs:
   ```bash
   docker-compose logs > logs.txt
   tail -100 logs/app.log >> logs.txt
   ```

2. Inclure l'output du diagnostic:
   ```bash
   ./diag.sh > diag.txt
   ```

3. Fournir:
   - OS et version
   - Docker version
   - Python version
   - Les steps pour reproduire le problème

---

**Version**: 1.0.0
