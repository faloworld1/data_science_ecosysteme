# Commandes utiles pour le système de surveillance BP

## 🚀 Démarrage Rapide

```bash
# 1. Démarrer les services Docker
docker-compose up -d

# 2. Initialiser Elasticsearch
python setup_elasticsearch.py

# 3. Lancer le système
python main.py
```

## 📊 Kafka - Commandes

### Créer un topic
```bash
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-topics --create \
  --if-not-exists \
  --topic blood-pressure-observations \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

### Lister les topics
```bash
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-topics --list --bootstrap-server localhost:9092
```

### Consommer les messages
```bash
docker exec -it $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-console-consumer \
  --topic blood-pressure-observations \
  --bootstrap-server localhost:9092 \
  --from-beginning
```

### Voir les détails du topic
```bash
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-topics --describe \
  --topic blood-pressure-observations \
  --bootstrap-server localhost:9092
```

### Supprimer un topic
```bash
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-topics --delete \
  --topic blood-pressure-observations \
  --bootstrap-server localhost:9092
```

## 🔍 Elasticsearch - Commandes

### Vérifier la santé du cluster
```bash
curl http://localhost:9200/_cluster/health?pretty
```

### Lister les indices
```bash
curl http://localhost:9200/_cat/indices?v
```

### Informations sur un index
```bash
curl http://localhost:9200/blood-pressure-anomalies?pretty
```

### Résultats totaux dans l'index
```bash
curl http://localhost:9200/blood-pressure-anomalies/_count?pretty
```

### Supprimer un index
```bash
curl -X DELETE http://localhost:9200/blood-pressure-anomalies
```

### Recherche simple - Cas critiques
```bash
curl -X POST http://localhost:9200/blood-pressure-anomalies/_search?pretty \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "term": { "risk_level": "CRITICAL" }
    },
    "size": 10,
    "sort": [{ "indexed_time": { "order": "desc" } }]
  }'
```

### Agrégation - Distribution des risques
```bash
curl -X POST http://localhost:9200/blood-pressure-anomalies/_search?pretty \
  -H "Content-Type: application/json" \
  -d '{
    "aggs": {
      "risk_distribution": {
        "terms": { "field": "risk_level" }
      }
    },
    "size": 0
  }'
```

### Agrégation - Moyenne des pressures
```bash
curl -X POST http://localhost:9200/blood-pressure-anomalies/_search?pretty \
  -H "Content-Type: application/json" \
  -d '{
    "aggs": {
      "avg_systolic": {
        "avg": { "field": "systolic_pressure" }
      },
      "avg_diastolic": {
        "avg": { "field": "diastolic_pressure" }
      }
    },
    "size": 0
  }'
```

### Historique temporel par une heure
```bash
curl -X POST http://localhost:9200/blood-pressure-anomalies/_search?pretty \
  -H "Content-Type: application/json" \
  -d '{
    "aggs": {
      "anomalies_over_time": {
        "date_histogram": {
          "field": "indexed_time",
          "fixed_interval": "1h"
        }
      }
    },
    "size": 0
  }'
```

## 📈 Kibana - Configuration

### Accéder à Kibana
```
http://localhost:5601
```

### Créer Index Pattern
1. Allez à: Stack Management → Index Patterns
2. Créer nouveau: `blood-pressure-anomalies`
3. Time field: `indexed_time`

### Créer Dashboard
1. Analytics → Dashboards → Create new dashboard
2. Ajouter visualisations
3. Sauvegarder

## 🐳 Docker Compose - Commandes

### Démarrer tous les services
```bash
docker-compose up -d
```

### Arrêter tous les services
```bash
docker-compose down
```

### Voir les logs
```bash
docker-compose logs -f                    # Tous les services
docker-compose logs -f kafka              # Juste Kafka
docker-compose logs -f elasticsearch      # Juste ES
docker-compose logs -f kibana             # Juste Kibana
```

### Redémarrer un service
```bash
docker-compose restart kafka
docker-compose restart elasticsearch
docker-compose restart kibana
```

### Nettoyer complètement (attention!)
```bash
docker-compose down -v    # Supprime aussi les volumes
```

### Vérifier le statut
```bash
docker-compose ps
```

## 🐍 Python - Scripts de Test

### Test du générateur FHIR
```bash
cd src
python fhir_generator.py
```

### Test du détecteur d'anomalies
```bash
cd src
python anomaly_detector.py
```

### Test du modèle ML
```bash
cd src
python ml_model.py
```

### Test Elasticsearch
```bash
cd src
python elasticsearch_handler.py
```

### Test du stockage local
```bash
cd src
python data_storage.py
```

## 📝 Logs et Monitoring

### Voir les logs d'application
```bash
tail -f logs/app.log
```

### Filtrer les anomalies détectées
```bash
grep "ANOMALY DETECTED" logs/app.log
```

### Compter les cas anomalies
```bash
grep "ANOMALY DETECTED" logs/app.log | wc -l
```

### Voir les erreurs
```bash
grep ERROR logs/app.log
```

### Archiver les logs
```bash
gzip logs/app.log
```

## 🛠️ Dépannage

### Porter utilisé est déjà occupé
```bash
# Trouver le processus utilisant le port
lsof -i :9092              # Kafka
lsof -i :9200              # Elasticsearch
lsof -i :5601              # Kibana

# Tuer le processus (attention!)
kill -9 <PID>
```

### Réinitialiser complètement (attention!)
```bash
docker-compose down -v
rm -rf data/normal_cases/*.json
rm models/trained_model.pkl
docker-compose up -d
python setup_elasticsearch.py
python main.py
```

### Vérifier la connectivité
```bash
# Kafka
nc -zv localhost 9092

# Elasticsearch
curl -I http://localhost:9200

# Kibana
curl -I http://localhost:5601
```

## 📊 Monitoring en Temps Réel

### Terminal 1: Lancer le système
```bash
python main.py
```

### Terminal 2: Monitorer Kafka
```bash
docker exec -it $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
  kafka-console-consumer \
  --topic blood-pressure-observations \
  --bootstrap-server localhost:9092
```

### Terminal 3: Monitorer Elasticsearch
```bash
watch -n 1 'curl -s http://localhost:9200/blood-pressure-anomalies/_count | python -m json.tool'
```

### Terminal 4: Suivre les logs
```bash
tail -f logs/app.log
```

---

**💡 Astuce**: Créez un alias pour les commandes longues dans `.bashrc` ou `.zshrc`
