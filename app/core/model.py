import pandas as pd
import numpy as np
import os
from app.utils.mock_data import MockODBData

class Model:
    """Handles data storage, retrieval, and calculations (Model in MVC)."""
    
    def __init__(self):
        self.odb_path = None
        self.structure = None
        self.csv_root = None # Path to the extracted CSV structure
        self.active_data = {}  # {name: {time: [], data: [], ...}}
        self.virtual_variables = {}  # {name: {time: [], data: []}}
        
    def load_odb(self, path, structure):
        """Sets ODB file structure and CSV root."""
        self.odb_path = path
        self.structure = structure
        self.csv_root = structure.get("csv_root")
        return self.structure

    def load_from_csv_root(self, csv_root):
        """Reconstructs the structure from an existing CSV root folder."""
        self.csv_root = csv_root
        self.odb_path = os.path.basename(csv_root)
        
        structure = {"command": "extract", "Instances": {}, "HistoryOutputs": {}, "csv_root": csv_root}

        def sanitize_name(name):
            forbidden = r'\/:*?"<>|'
            for ch in forbidden:
                name = name.replace(ch, "_")
            return name

        history_root = os.path.join(csv_root, "history")
        if os.path.isdir(history_root):
            for region in os.listdir(history_root):
                region_path = os.path.join(history_root, region)
                if not os.path.isdir(region_path):
                    continue
                vars_map = {}
                for var in os.listdir(region_path):
                    var_path = os.path.join(region_path, var)
                    if os.path.isdir(var_path):
                        vars_map[var] = True
                if vars_map:
                    structure["HistoryOutputs"][region] = vars_map

        for inst in os.listdir(csv_root):
            inst_path = os.path.join(csv_root, inst)
            if not os.path.isdir(inst_path):
                continue
            if inst == "history":
                continue
            inst_out = {"Bodies": {}}
            for body in os.listdir(inst_path):
                body_path = os.path.join(inst_path, body)
                if not os.path.isdir(body_path):
                    continue
                body_out = {"Fields": {}}
                for field in os.listdir(body_path):
                    field_path = os.path.join(body_path, field)
                    if not os.path.isdir(field_path):
                        continue
                    field_out = {"Variants": {}}
                    for variant in os.listdir(field_path):
                        variant_path = os.path.join(field_path, variant)
                        if not os.path.isdir(variant_path):
                            continue
                        aggs = []
                        for f in os.listdir(variant_path):
                            if f.lower().endswith(".csv"):
                                aggs.append(os.path.splitext(f)[0])
                        if aggs:
                            field_out["Variants"][variant] = {"Aggregations": aggs}
                    if field_out["Variants"]:
                        body_out["Fields"][field] = field_out
                if body_out["Fields"]:
                    inst_out["Bodies"][body] = body_out
            if inst_out["Bodies"]:
                structure["Instances"][inst] = inst_out
        
        self.structure = structure
        return structure

    def get_field_data(self, instance, body_key, field, variant, aggregation):
        """Fetches data for a specific field output from CSV."""
        if not self.csv_root:
            # Fallback to mock for development if no CSVs
            time, data = MockODBData.generate_field_data(instance, field, aggregation)
            return time, data

        def sanitize_name(name):
            forbidden = r'\/:*?"<>|'
            for ch in forbidden:
                name = name.replace(ch, "_")
            return name

        csv_path = os.path.join(
            self.csv_root,
            sanitize_name(instance),
            sanitize_name(body_key),
            sanitize_name(field),
            sanitize_name(variant),
            f"{sanitize_name(aggregation)}.csv",
        )
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            time = df["Time"].values
            
            if aggregation == "Boxplot stats":
                # Returns a dictionary for plotting statistical ranges
                return time, {
                    "min": df["Min"].values,
                    "q1": df["Q1"].values,
                    "median": df["Median"].values,
                    "q3": df["Q3"].values,
                    "max": df["Max"].values
                }
            
            col_name = df.columns[1]
            data = df[col_name].values
            return time, data
        else:
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

    def get_history_data(self, rp_name, variable):
        """Fetches data for a history output from CSV."""
        if not self.csv_root:
            time, data = MockODBData.generate_history_data(rp_name, variable)
            return time, data

        def sanitize_name(name):
            forbidden = r'\/:*?"<>|'
            for ch in forbidden:
                name = name.replace(ch, "_")
            return name

        csv_path = os.path.join(self.csv_root, "history", sanitize_name(rp_name), sanitize_name(variable), "History.csv")
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            time = df["Time"].values
            col_name = df.columns[1]
            data = df[col_name].values
            return time, data
        else:
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

    def add_virtual_variable(self, name, time, data):
        """Adds a calculated (virtual) variable to the model."""
        self.virtual_variables[name] = {"time": time, "data": data}
        return name

    def clear_data(self):
        """Clears all loaded data."""
        self.active_data = {}
        self.virtual_variables = {}
        self.odb_path = None
        self.structure = None
