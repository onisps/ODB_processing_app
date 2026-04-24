import numpy as np
import pandas as pd
import random

class MockODBData:
    """Generates mock data for testing the GUI without Abaqus."""
    
    @staticmethod
    def get_mock_structure():
        """Returns a nested structure of instances, node sets, and available fields."""
        return {
            "Instances": {
                "PART-1-1": {
                    "FieldOutputs": ["U", "S", "LE", "PE"],
                    "ElementSets": ["SET-1", "SET-2", "ALL_ELEMENTS"],
                    "NodeSets": ["SET-1", "SET-2", "ALL_NODES"]
                },
                "PART-2-1": {
                    "FieldOutputs": ["U", "S"],
                    "ElementSets": ["SET-A", "SET-B"],
                    "NodeSets": ["SET-A", "SET-B"]
                }
            },
            "ReferencePoints": ["RP-1", "RP-2", "RP-3"],
            "HistoryOutputs": {
                "RP-1": ["U1", "U2", "U3", "RF1", "RF2", "RF3"],
                "RP-2": ["U1", "U2", "U3", "RF1", "RF2", "RF3"],
                "RP-3": ["U1", "U2", "U3", "RF1", "RF2", "RF3"]
            }
        }

    @staticmethod
    def generate_field_data(instance, field, aggregation, frames=20):
        """Generates mock time-series data for a field output."""
        time = np.linspace(0, 1.0, frames)
        
        # Base values depend on the field
        if field == "U":
            base = np.sin(time * np.pi) * 10
        elif field == "S":
            base = time * 200 + 50
        else:
            base = np.exp(time) * 5
            
        if aggregation == "Max":
            data = base + np.random.normal(0, 0.5, frames)
        elif aggregation == "Min":
            data = base * 0.8 + np.random.normal(0, 0.5, frames)
        elif aggregation == "Mean":
            data = base * 0.9 + np.random.normal(0, 0.2, frames)
        elif aggregation == "Boxplot stats":
            # Returns a dict of arrays for boxplot-like representation
            median = base * 0.9
            q1 = median * 0.85
            q3 = median * 1.15
            data = {
                "median": median,
                "q1": q1,
                "q3": q3,
                "min": q1 * 0.9,
                "max": q3 * 1.1
            }
        else:
            data = base
            
        return time, data

    @staticmethod
    def generate_history_data(rp_name, variable, frames=20):
        """Generates mock history data for a specific RP and variable."""
        time = np.linspace(0, 1.0, frames)
        
        if "U" in variable:
            data = np.linspace(0, 5, frames) + np.random.normal(0, 0.1, frames)
        elif "RF" in variable:
            # Load-displacement like curve
            data = 100 * (1 - np.exp(-5 * time)) + np.random.normal(0, 1.0, frames)
        else:
            data = np.random.random(frames) * 10
            
        return time, data
