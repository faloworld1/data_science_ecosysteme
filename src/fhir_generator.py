"""
FHIR Message Generator for Blood Pressure Observations
Generates realistic FHIR-compliant blood pressure measurement data
"""

import json
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List
from faker import Faker

fake = Faker()


class FHIRBPObservationGenerator:
    """
    Generates FHIR-compliant Observation resources for blood pressure measurements.
    Based on HL7 FHIR standard: https://www.hl7.org/fhir/observation.html
    """

    NORMAL_SYSTOLIC_RANGE = (90, 120)
    NORMAL_DIASTOLIC_RANGE = (60, 80)
    
    # Blood pressure categories (in mmHg)
    BP_CATEGORIES = {
        "NORMAL": {"systolic": (90, 120), "diastolic": (60, 80)},
        "ELEVATED": {"systolic": (120, 129), "diastolic": (60, 79)},
        "HYPERTENSION_STAGE_1": {"systolic": (130, 139), "diastolic": (80, 89)},
        "HYPERTENSION_STAGE_2": {"systolic": (140, 180), "diastolic": (90, 120)},
        "HYPERTENSIVE_CRISIS": {"systolic": (180, 250), "diastolic": (120, 180)},
        "HYPOTENSION": {"systolic": (50, 89), "diastolic": (30, 59)},
    }

    def __init__(self, num_patients: int = 10, data_points_per_patient: int = 5):
        """
        Initialize the FHIR generator.
        
        Args:
            num_patients: Number of unique patients to generate
            data_points_per_patient: Number of observations per patient
        """
        self.num_patients = num_patients
        self.data_points_per_patient = data_points_per_patient
        self.patients = self._generate_patients()

    def _generate_patients(self) -> List[Dict]:
        """Generate unique patient identifiers and data."""
        patients = []
        for _ in range(self.num_patients):
            patients.append({
                "patient_id": str(uuid.uuid4()),
                "name": fake.name(),
                "age": random.randint(18, 85),
                "gender": random.choice(["male", "female"]),
                "birth_date": fake.date_of_birth(minimum_age=18, maximum_age=85).isoformat(),
            })
        return patients

    def _generate_blood_pressure(self, category: str = None) -> tuple:
        """
        Generate blood pressure values based on category.
        
        Args:
            category: BP category (NORMAL, ELEVATED, HYPERTENSION_STAGE_1, etc.)
                     If None, chooses random category.
        
        Returns:
            Tuple of (systolic, diastolic) values
        """
        if category is None:
            category = random.choice(list(self.BP_CATEGORIES.keys()))
        
        bp_range = self.BP_CATEGORIES[category]
        systolic = random.randint(*bp_range["systolic"])
        diastolic = random.randint(*bp_range["diastolic"])
        
        return systolic, diastolic

    def _create_observation_resource(
        self,
        patient: Dict,
        systolic: int,
        diastolic: int,
        observation_time: datetime
    ) -> Dict:
        """
        Create a FHIR Observation resource for blood pressure.
        
        Args:
            patient: Patient dictionary
            systolic: Systolic pressure value
            diastolic: Diastolic pressure value
            observation_time: DateTime of observation
        
        Returns:
            FHIR Observation resource as dictionary
        """
        observation_id = str(uuid.uuid4())
        
        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "85354-9",
                        "display": "Blood pressure panel with all children optional"
                    }
                ],
                "text": "Blood Pressure"
            },
            "subject": {
                "reference": f"Patient/{patient['patient_id']}",
                "display": patient["name"]
            },
            "effectiveDateTime": observation_time.isoformat() + "Z",
            "issued": datetime.now().isoformat() + "Z",
            "performer": [
                {
                    "reference": "Practitioner/example",
                    "display": "Medical Device"
                }
            ],
            "component": [
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8480-6",
                                "display": "Systolic blood pressure"
                            }
                        ]
                    },
                    "valueQuantity": {
                        "value": systolic,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]"
                    }
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8462-4",
                                "display": "Diastolic blood pressure"
                            }
                        ]
                    },
                    "valueQuantity": {
                        "value": diastolic,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]"
                    }
                }
            ]
        }
        
        return observation

    def generate_observations(self, category: str = None) -> List[Dict]:
        """
        Generate FHIR Observation resources for blood pressure.
        
        Args:
            category: Optional BP category for all observations
        
        Returns:
            List of FHIR Observation resources
        """
        observations = []
        base_time = datetime.now() - timedelta(days=7)
        
        for patient in self.patients:
            for i in range(self.data_points_per_patient):
                systolic, diastolic = self._generate_blood_pressure(category)
                observation_time = base_time + timedelta(
                    hours=random.randint(0, 168),
                    minutes=random.randint(0, 59)
                )
                
                observation = self._create_observation_resource(
                    patient, systolic, diastolic, observation_time
                )
                observations.append(observation)
        
        return observations

    def generate_batch(self, batch_size: int = 5) -> List[Dict]:
        """
        Generate a batch of diverse blood pressure observations.
        Mix of normal and abnormal cases.
        
        Args:
            batch_size: Number of observations to generate
        
        Returns:
            List of FHIR Observation resources
        """
        observations = []
        
        # 60% normal, 20% elevated, 20% abnormal
        normal_count = int(batch_size * 0.6)
        elevated_count = int(batch_size * 0.2)
        abnormal_count = batch_size - normal_count - elevated_count
        
        # Generate normal observations
        for _ in range(normal_count):
            patient = random.choice(self.patients)
            systolic, diastolic = self._generate_blood_pressure("NORMAL")
            observation_time = datetime.now() - timedelta(minutes=random.randint(0, 1440))
            observation = self._create_observation_resource(
                patient, systolic, diastolic, observation_time
            )
            observations.append(observation)
        
        # Generate elevated observations
        for _ in range(elevated_count):
            patient = random.choice(self.patients)
            systolic, diastolic = self._generate_blood_pressure("ELEVATED")
            observation_time = datetime.now() - timedelta(minutes=random.randint(0, 1440))
            observation = self._create_observation_resource(
                patient, systolic, diastolic, observation_time
            )
            observations.append(observation)
        
        # Generate abnormal observations
        abnormal_categories = ["HYPERTENSION_STAGE_1", "HYPERTENSION_STAGE_2", 
                              "HYPERTENSIVE_CRISIS", "HYPOTENSION"]
        for _ in range(abnormal_count):
            patient = random.choice(self.patients)
            category = random.choice(abnormal_categories)
            systolic, diastolic = self._generate_blood_pressure(category)
            observation_time = datetime.now() - timedelta(minutes=random.randint(0, 1440))
            observation = self._create_observation_resource(
                patient, systolic, diastolic, observation_time
            )
            observations.append(observation)
        
        return observations


if __name__ == "__main__":
    # Example usage
    generator = FHIRBPObservationGenerator(num_patients=15, data_points_per_patient=3)
    observations = generator.generate_batch(batch_size=100)
    
    print(f"Generated {len(observations)} observations")
    print("\nSample observation:")
    print(json.dumps(observations[0], indent=2))
