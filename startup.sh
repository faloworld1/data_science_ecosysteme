#!/bin/bash
# Script de démarrage complet du système

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Blood Pressure Monitoring System - Startup Script"
echo "════════════════════════════════════════════════════════════════"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "\n${YELLOW}[1/5] Vérification de Docker${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker n'est pas installé${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker trouvé${NC}"

echo -e "\n${YELLOW}[2/5] Démarrage des services Docker...${NC}"
docker-compose down --remove-orphans 2>/dev/null || true
docker-compose up -d

echo -e "${GREEN}✓ Services Docker lancés${NC}"

# Attendre que Kafka soit prêt
echo -e "\n${YELLOW}[3/5] Attente de Kafka...${NC}"
KAFKA_READY=0
for i in {1..30}; do
    if docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
        kafka-broker-api-versions --bootstrap-server localhost:9092 &> /dev/null; then
        KAFKA_READY=1
        break
    fi
    echo "  Tentative $i/30..."
    sleep 2
done

if [ $KAFKA_READY -eq 0 ]; then
    echo -e "${RED}✗ Kafka n'a pas pu démarrer${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Kafka prêt${NC}"

# Créer le topic Kafka
echo -e "\n${YELLOW}[4/5] Configuration de Kafka...${NC}"
docker exec $(docker ps -q -f "ancestor=confluentinc/cp-kafka:*") \
    kafka-topics --create \
    --topic blood-pressure-observations \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists 2>/dev/null || true

echo -e "${GREEN}✓ Topic Kafka créé/existe${NC}"

# Vérifier Python
echo -e "\n${YELLOW}[5/5] Vérification de l'environnement Python...${NC}"
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 n'est pas installé${NC}"
    exit 1
fi

PYTHON_CMD=$(which python3 || which python)
$PYTHON_CMD -m pip install -r requirements.txt --quiet 2>/dev/null || {
    echo -e "${YELLOW}! Installation des dépendances requises...${NC}"
    $PYTHON_CMD -m pip install -r requirements.txt
}

echo -e "${GREEN}✓ Environnement Python prêt${NC}"

# Summary
echo -e "\n════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✓ SYSTÈME PRÊT${NC}"
echo "════════════════════════════════════════════════════════════════"
echo -e "\n${YELLOW}Services disponibles:${NC}"
echo "  • Kafka: localhost:9092"
echo "  • Elasticsearch: http://localhost:9200"
echo "  • Kibana: http://localhost:5601"
echo "  • Kafka UI: http://localhost:8080"
echo -e "\n${YELLOW}Prochaines étapes:${NC}"
echo "  1. python main.py              # Lancer le système"
echo "  2. Ouvrir Kibana: http://localhost:5601"
echo "  3. Créer un index pattern: 'blood-pressure-anomalies'"
echo -e "\n${YELLOW}Commandes utiles:${NC}"
echo "  • docker-compose logs -f       # Voir les logs"
echo "  • docker-compose ps            # Statut des services"
echo "  • docker-compose down          # Arrêter les services"
echo "════════════════════════════════════════════════════════════════\n"
