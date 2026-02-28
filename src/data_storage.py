"""
Data Storage Handler for normal blood pressure cases
Saves normal cases to local JSON files with metadata
"""

import json
import logging
import os
from typing import Dict, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class NormalCasesStorage:
    """
    Handles storage of normal blood pressure cases to local JSON files.
    """
    
    def __init__(self, storage_dir: str = "data/normal_cases"):
        """
        Initialize storage handler.
        
        Args:
            storage_dir: Directory to store normal cases
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Normal cases storage directory: {self.storage_dir}")

    def save_case(self, analysis: Dict, create_daily_file: bool = True) -> bool:
        """
        Save a normal case to file.
        
        Args:
            analysis: Result from AnomalyDetector.detect_anomalies()
            create_daily_file: Save to date-based file (True) or general file (False)
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Skip if not normal
            if analysis.get("is_anomalous"):
                return False
            
            # Determine filename
            if create_daily_file:
                date_str = datetime.now().strftime("%Y-%m-%d")
                filename = f"normal_cases_{date_str}.json"
            else:
                filename = "normal_cases_all.json"
            
            filepath = self.storage_dir / filename
            
            # Prepare record
            record = {
                "observation_id": analysis.get("observation_id"),
                "patient_id": analysis.get("patient_id"),
                "patient_name": analysis.get("patient_name"),
                "systolic_pressure": analysis.get("systolic"),
                "diastolic_pressure": analysis.get("diastolic"),
                "classification": analysis.get("classification"),
                "observation_time": analysis.get("observation_time"),
                "saved_time": datetime.utcnow().isoformat()
            }
            
            # Load existing data or create new
            data = []
            if filepath.exists():
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode existing file {filepath}, starting fresh")
                    data = []
            
            # Append new record
            data.append(record)
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved normal case for patient {analysis.get('patient_id')} to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save normal case: {e}")
            return False

    def save_batch(self, analyses: List[Dict], create_daily_file: bool = True) -> int:
        """
        Save multiple normal cases.
        
        Args:
            analyses: List of analysis results
            create_daily_file: Save to date-based files
        
        Returns:
            Number of cases saved
        """
        saved_count = 0
        
        for analysis in analyses:
            if not analysis.get("is_anomalous") and self.save_case(analysis, create_daily_file):
                saved_count += 1
        
        logger.info(f"Saved {saved_count}/{len(analyses)} normal cases")
        return saved_count

    def get_statistics(self) -> Dict:
        """
        Get statistics about stored normal cases.
        
        Returns:
            Dictionary with statistics
        """
        try:
            total_cases = 0
            all_files = list(self.storage_dir.glob("normal_cases_*.json"))
            
            patients = set()
            pressure_values = {"systolic": [], "diastolic": []}
            
            for filepath in all_files:
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    for record in data:
                        total_cases += 1
                        patients.add(record.get("patient_id"))
                        pressure_values["systolic"].append(record.get("systolic_pressure", 0))
                        pressure_values["diastolic"].append(record.get("diastolic_pressure", 0))
                except Exception as e:
                    logger.warning(f"Could not read {filepath}: {e}")
            
            stats = {
                "total_normal_cases": total_cases,
                "unique_patients": len(patients),
                "avg_systolic": sum(pressure_values["systolic"]) / len(pressure_values["systolic"]) 
                                if pressure_values["systolic"] else 0,
                "avg_diastolic": sum(pressure_values["diastolic"]) / len(pressure_values["diastolic"])
                                 if pressure_values["diastolic"] else 0,
                "storage_files": len(all_files)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

    def list_files(self) -> List[str]:
        """
        List all stored normal case files.
        
        Returns:
            List of filenames
        """
        try:
            files = list(self.storage_dir.glob("normal_cases_*.json"))
            return [f.name for f in sorted(files)]
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def clear_storage(self, confirm: bool = False) -> bool:
        """
        Clear all stored normal cases (use with caution).
        
        Args:
            confirm: Must be True to execute
        
        Returns:
            True if cleared successfully
        """
        if not confirm:
            logger.warning("Clear operation requires confirm=True")
            return False
        
        try:
            for filepath in self.storage_dir.glob("normal_cases_*.json"):
                filepath.unlink()
            logger.info("All normal case files cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear storage: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    storage = NormalCasesStorage()
    
    # List files
    files = storage.list_files()
    print(f"Stored files: {files}")
    
    # Get statistics
    stats = storage.get_statistics()
    print(json.dumps(stats, indent=2))
