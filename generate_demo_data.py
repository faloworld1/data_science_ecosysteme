"""
Générateur de données de démonstration
Crée de faux patients avec des historiques de pression artérielle variés
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os
# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
os.chdir("/src")

from fhir_generator import FHIRBPObservationGenerator
from anomaly_detector import BloodPressureAnomalyDetector

def generate_demo_data(num_patients=10, days_back=30):
    """
    Générer des données de démonstration réalistes.
    
    Args:
        num_patients: Nombre de patients à générer
        days_back: Nombre de jours d'historique
    """
    print(f"\n{'='*70}")
    print(f"  Générateur de Données de Démonstration")
    print(f"{'='*70}")
    
    # Générer les observations
    print(f"\n[1] Génération de {num_patients} patients avec données...")
    generator = FHIRBPObservationGenerator(
        num_patients=num_patients,
        data_points_per_patient=5
    )
    
    observations = generator.generate_batch(batch_size=50)
    print(f"✓ Généré {len(observations)} observations FHIR")
    
    # Analyser les observations
    print(f"\n[2] Analyse des observations...")
    detector = BloodPressureAnomalyDetector()
    
    analyses = []
    anomalies = []
    normal = []
    
    for obs in observations:
        analysis = detector.detect_anomalies(obs)
        analyses.append(analysis)
        
        if analysis.get("is_anomalous"):
            anomalies.append(analysis)
        else:
            normal.append(analysis)
    
    print(f"✓ Total: {len(analyses)} observations")
    print(f"  → Anomalies: {len(anomalies)} ({len(anomalies)/len(analyses)*100:.1f}%)")
    print(f"  → Normales: {len(normal)} ({len(normal)/len(analyses)*100:.1f}%)")
    
    # Sauvegarder les données
    output_dir = Path("demo_data")
    output_dir.mkdir(exist_ok=True)
    
    # Sauvegarder les observations FHIR
    print(f"\n[3] Sauvegarde des données...")
    
    fhir_file = output_dir / "fhir_observations.json"
    with open(fhir_file, 'w') as f:
        json.dump(observations, f, indent=2)
    print(f"✓ Observations FHIR: {fhir_file}")
    
    # Sauvegarder les analyses
    analyses_file = output_dir / "analyses.json"
    with open(analyses_file, 'w') as f:
        json.dump(analyses, f, indent=2)
    print(f"✓ Analyses: {analyses_file}")
    
    # Sauvegarder les anomalies
    anomalies_file = output_dir / "anomalies.json"
    with open(anomalies_file, 'w') as f:
        json.dump(anomalies, f, indent=2)
    print(f"✓ Anomalies: {anomalies_file}")
    
    # Sauvegarder les cas normaux
    normal_file = output_dir / "normal_cases.json"
    with open(normal_file, 'w') as f:
        json.dump(normal, f, indent=2)
    print(f"✓ Cas normaux: {normal_file}")
    
    # Statistiques détaillées
    print(f"\n[4] Statistiques détaillées...")
    
    risk_levels = {}
    classifications = {}
    
    for analysis in anomalies:
        risk = analysis.get("risk_level", "UNKNOWN")
        cls = analysis.get("classification", "UNKNOWN")
        
        risk_levels[risk] = risk_levels.get(risk, 0) + 1
        classifications[cls] = classifications.get(cls, 0) + 1
    
    stats_file = output_dir / "statistics.json"
    stats = {
        "total_observations": len(observations),
        "total_analyses": len(analyses),
        "anomalies_count": len(anomalies),
        "normal_count": len(normal),
        "anomaly_rate": len(anomalies) / len(analyses),
        "risk_level_distribution": risk_levels,
        "classification_distribution": classifications,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"✓ Statistiques: {stats_file}")
    
    # Afficher le summary
    print(f"\n{'='*70}")
    print(f"  RÉSUMÉ")
    print(f"{'='*70}")
    print(f"\nPatients générés: {num_patients}")
    print(f"Total observations: {len(observations)}")
    print(f"Observations normales: {len(normal)} ({len(normal)/len(analyses)*100:.1f}%)")
    print(f"Observations anormales: {len(anomalies)} ({len(anomalies)/len(analyses)*100:.1f}%)")
    
    if risk_levels:
        print(f"\nDistribution des risques:")
        for risk, count in sorted(risk_levels.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {risk}: {count}")
    
    if classifications:
        print(f"\nDistribution des classifications:")
        for cls, count in sorted(classifications.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {cls}: {count}")
    
    print(f"\nDonnées sauvegardées dans: {output_dir}")
    print(f"{'='*70}\n")
    
    return observations, analyses

if __name__ == "__main__":
    generate_demo_data(num_patients=15, days_back=30)
