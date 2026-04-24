import numpy as np
import pandas as pd
import json
import ast
import os
import sys
import zipfile
import tempfile
import shutil
from datetime import datetime
from app.core.abaqus_bridge import AbaqusBridge

class Controller:
    """Manages UI actions, coordinates model updates, and interacts with view (Controller in MVC)."""
    
    def __init__(self, model):
        self.model = model
        self.view = None
        self.bridge = AbaqusBridge()
        self._current_plotted_data = {}  # Store currently plotted series for X-Y mapping
        
        # Connect bridge signals
        self.bridge.progress_updated.connect(self._on_bridge_progress)
        self.bridge.finished.connect(self._on_bridge_finished)
        
    def set_view(self, view):
        """Link the controller to the main view."""
        self.view = view
        # Connect view signals to controller actions
        self.view.control_panel.clear_plot_clicked.connect(self.handle_clear_plot)
        self.view.control_panel.load_parsed_clicked.connect(self.handle_load_parsed)

    def handle_load_odb(self, path=None):
        """Action for ODB loading button."""
        if not path:
            # For demo/mock mode if user cancels or we want mock
            self.model.odb_path = "mock_odb_file.odb"
            structure = self.model.load_odb("mock_odb_file.odb", {})
            if self.view:
                self.view.update_tree_widget(structure)
                self.view.show_status("Loaded MOCK ODB structure")
            return

        self.model.odb_path = path
        if self.view:
            self.view.show_status(f"Scanning available outputs for {path}...")
            self.view.control_panel.set_progress(0, 1, "Scanning ODB...")

        self.bridge.run_scan(path)

    def _on_bridge_progress(self, current, total, message):
        """Updates progress in the view."""
        if self.view:
            self.view.control_panel.set_progress(current, total, message)

    def _on_bridge_finished(self, structure, error):
        """Handles completion of ODB extraction."""
        if self.view:
            self.view.control_panel.hide_progress()
            
            if error:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self.view, "Extraction Error", f"Abaqus error:\n{error}")
                self.view.show_status("Extraction failed.")
                return

            cmd = structure.get("command")
            if cmd == "scan":
                from app.gui.widgets.export_selection_dialog import ExportSelectionDialog
                dialog = ExportSelectionDialog(structure, self.view)
                if dialog.exec():
                    selection = dialog.get_selection()
                    if not selection.get("fields") and not selection.get("history"):
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.warning(self.view, "Export Selection", "Nothing selected for export.")
                        self.view.show_status("Export cancelled.")
                        return
                    self.view.show_status("Starting extraction...")
                    self.view.control_panel.set_progress(0, 100, "Initializing Abaqus...")
                    self.bridge.run_extraction(self.model.odb_path, selection=selection)
                else:
                    self.view.show_status("Export cancelled.")
                return

            self.model.load_odb(self.model.odb_path, structure)
            self.view.update_tree_widget(structure)
            self.view.show_status(f"Extraction complete. Data saved to {structure.get('csv_root')}")

    def handle_load_parsed(self, directory):
        """Loads data from an existing directory of CSVs."""
        structure = self.model.load_from_csv_root(directory)
        if self.view:
            self.view.update_tree_widget(structure)
            self.view.show_status(f"Loaded existing data from {directory}")

    def handle_clear_plot(self):
        """Clears the plot and resets active data mapping."""
        self._current_plotted_data = {}
        if self.view:
            self.view.plot_widget.clear_plot()
            self.view.control_panel.clear_series_toggles()
            self.view.show_status("Plot cleared.")

    def handle_field_selection(self, instance, body_key, field, variant, aggregation, plot=True):
        """Action for selecting a field to plot."""
        try:
            time, data = self.model.get_field_data(instance, body_key, field, variant, aggregation)
            key = f"{instance}__{body_key}__{field}__{variant}__{aggregation}"
            self._current_plotted_data[key] = {
                "time": time,
                "data": data,
                "meta": {"kind": "field", "instance": instance, "body_key": body_key, "field": field, "variant": variant, "aggregation": aggregation},
            }
            
            if plot and self.view:
                self.view.plot_series(time, data, label=key)
        except Exception as e:
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self.view, "Data Error", f"Could not load field data:\n{str(e)}")
                self.view.show_status(f"Error loading {field}")

    def handle_history_selection(self, rp_name, variable, plot=True):
        """Action for selecting history data."""
        try:
            time, data = self.model.get_history_data(rp_name, variable)
            key = f"{rp_name}_{variable}"
            self._current_plotted_data[key] = {"time": time, "data": data, "meta": {"kind": "history", "region": rp_name, "variable": variable}}
            
            if plot and self.view:
                self.view.plot_series(time, data, label=key)
        except Exception as e:
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self.view, "Data Error", f"Could not load history data:\n{str(e)}")
                self.view.show_status(f"Error loading {variable}")

    def handle_field_calculator(self, var1_key, var2_key, operation, result_name):
        """Calculates a new virtual variable based on existing ones."""
        # Check if keys exist in currently active data
        if var1_key not in self._current_plotted_data or var2_key not in self._current_plotted_data:
            return False, "Selected variables not found in active data."
            
        data1 = self._current_plotted_data[var1_key]["data"]
        data2 = self._current_plotted_data[var2_key]["data"]
        time = self._current_plotted_data[var1_key]["time"]
        
        # Simple broadcasting if shapes don't match, but here we assume they do.
        try:
            if operation == "+":
                result = data1 + data2
            elif operation == "-":
                result = data1 - data2
            elif operation == "*":
                result = data1 * data2
            elif operation == "/":
                result = data1 / data2
            else:
                return False, "Unsupported operation."
                
            self.model.add_virtual_variable(result_name, time, result)
            self._current_plotted_data[result_name] = {"time": time, "data": result, "meta": {"kind": "virtual", "source": "binary"}}
            
            if self.view:
                self.view.update_virtual_variables_list(result_name)
                self.view.plot_series(time, result, label=result_name)
            return True, "Calculation successful."
        except Exception as e:
            return False, f"Error in calculation: {str(e)}"

    def handle_expression_calculator(self, expression, token_map, result_name):
        if not expression:
            return False, "Expression is empty."

        if not self._current_plotted_data:
            return False, "No active data to perform calculations on."

        try:
            parsed = ast.parse(expression, mode="eval")
        except Exception as e:
            return False, f"Invalid expression: {str(e)}"

        names = set()

        class _Visitor(ast.NodeVisitor):
            def visit_Name(self, node):
                names.add(node.id)

        _Visitor().visit(parsed)

        env = {}
        time = None
        for token in names:
            label = token_map.get(token)
            if not label:
                return False, f"Unknown variable: {token}"
            if label not in self._current_plotted_data:
                return False, f"Variable not found in active data: {label}"
            series = self._current_plotted_data[label]
            if time is None:
                time = series["time"]
            env[token] = series["data"]

        funcs = {
            "sin": np.sin,
            "cos": np.cos,
            "tan": np.tan,
            "sqrt": np.sqrt,
            "log": np.log,
            "exp": np.exp,
            "abs": np.abs,
        }

        allowed_binops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
        allowed_unary = (ast.UAdd, ast.USub)

        def eval_node(node):
            if isinstance(node, ast.Expression):
                return eval_node(node.body)
            if isinstance(node, ast.Num):
                return node.n
            if hasattr(ast, "Constant") and isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError("Only numeric constants are allowed.")
            if isinstance(node, ast.Name):
                return env[node.id]
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, allowed_unary):
                val = eval_node(node.operand)
                if isinstance(node.op, ast.USub):
                    return -val
                return val
            if isinstance(node, ast.BinOp) and isinstance(node.op, allowed_binops):
                left = eval_node(node.left)
                right = eval_node(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div):
                    return left / right
                if isinstance(node.op, ast.Pow):
                    return left ** right
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in funcs:
                    if len(node.args) != 1:
                        raise ValueError("Functions take exactly one argument.")
                    return funcs[node.func.id](eval_node(node.args[0]))
                raise ValueError("Unsupported function call.")
            raise ValueError("Unsupported expression.")

        try:
            result = eval_node(parsed)
        except Exception as e:
            return False, f"Error in expression: {str(e)}"

        if time is None:
            return False, "Expression did not reference any variables."

        self.model.add_virtual_variable(result_name, time, result)
        self._current_plotted_data[result_name] = {"time": time, "data": result, "meta": {"kind": "virtual", "source": "expression", "expression": expression}}
        if self.view:
            self.view.update_virtual_variables_list(result_name)
            self.view.plot_series(time, result, label=result_name)
        return True, "Calculation successful."

    def export_data_to_xlsx(self, filename):
        if not self._current_plotted_data:
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self.view, "Export", "No data to export.")
            return False, "No data to export."

        try:
            df_dict = {}
            for label, data_obj in self._current_plotted_data.items():
                if "Time" not in df_dict:
                    df_dict["Time"] = data_obj["time"]
                data = data_obj["data"]
                if isinstance(data, dict):
                    df_dict[label + "__min"] = data.get("min")
                    df_dict[label + "__q1"] = data.get("q1")
                    df_dict[label + "__median"] = data.get("median")
                    df_dict[label + "__q3"] = data.get("q3")
                    df_dict[label + "__max"] = data.get("max")
                else:
                    df_dict[label] = data

            df = pd.DataFrame(df_dict)
            if not filename.lower().endswith(".xlsx"):
                filename += ".xlsx"
            with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Data")
            if self.view:
                self.view.show_status(f"Data exported to {filename}")
            return True, f"Data exported to {filename}"
        except Exception as e:
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self.view, "Export Error", f"Export failed:\n{str(e)}")
            return False, f"Export failed: {str(e)}"

    def export_plot_image(self, filename):
        if not self.view:
            return False, "No view."
        try:
            self.view.plot_widget.save_figure(filename)
            if self.view:
                self.view.show_status(f"Image saved to {filename}")
            return True, f"Image saved to {filename}"
        except Exception as e:
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self.view, "Save Error", f"Save failed:\n{str(e)}")
            return False, f"Save failed: {str(e)}"

    def save_session(self, filename):
        if not filename.lower().endswith(".lnbodb"):
            filename += ".lnbodb"

        if not self.model.csv_root or not os.path.isdir(self.model.csv_root):
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self.view, "Session", "No extracted data loaded. Load/Extract ODB first.")
            return False, "No extracted data loaded. Load/Extract ODB first."

        try:
            session_dir = os.path.dirname(os.path.abspath(filename))
            os.makedirs(session_dir, exist_ok=True)

            session = {
                "format": "lnbodb",
                "version": 1,
                "saved_at": datetime.utcnow().isoformat() + "Z",
                "odb_path": self.model.odb_path,
                "structure": self.model.structure,
                "active_series": [],
                "series_visibility": {},
            }

            if self.view:
                session["plot_settings"] = self.view.control_panel.get_plot_settings()

            for label, data_obj in self._current_plotted_data.items():
                meta = data_obj.get("meta") or {"kind": "unknown"}
                entry = {"label": label, "meta": meta}
                session["active_series"].append(entry)

            if self.view:
                for label, cb in self.view.control_panel._series_checkboxes.items():
                    session["series_visibility"][label] = bool(cb.isChecked())

            tmp_dir = tempfile.mkdtemp(prefix="lnbodb_")
            try:
                session_json = os.path.join(tmp_dir, "session.json")
                with open(session_json, "w", encoding="utf-8") as f:
                    json.dump(session, f)

                virtual_dir = os.path.join(tmp_dir, "virtual")
                os.makedirs(virtual_dir, exist_ok=True)
                for name, vv in (self.model.virtual_variables or {}).items():
                    out_path = os.path.join(virtual_dir, f"{name}.csv")
                    df = pd.DataFrame({"Time": vv["time"], "Value": vv["data"]})
                    df.to_csv(out_path, index=False)

                with zipfile.ZipFile(filename, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.write(session_json, "session.json")
                    for root, _, files in os.walk(virtual_dir):
                        for fn in files:
                            abs_path = os.path.join(root, fn)
                            rel = os.path.relpath(abs_path, tmp_dir).replace("\\", "/")
                            zf.write(abs_path, rel)

                    data_root = os.path.abspath(self.model.csv_root)
                    for root, _, files in os.walk(data_root):
                        for fn in files:
                            abs_path = os.path.join(root, fn)
                            rel = os.path.relpath(abs_path, data_root).replace("\\", "/")
                            zf.write(abs_path, "data/" + rel)

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

            if self.view:
                self.view.show_status(f"Session saved to {filename}")
            return True, f"Session saved to {filename}"
        except Exception as e:
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self.view, "Session Error", f"Session save failed:\n{str(e)}")
            return False, f"Session save failed: {str(e)}"

    def load_session(self, filename):
        if not os.path.exists(filename):
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self.view, "Session", "Session file not found.")
            return False, "Session file not found."

        try:
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(filename))

            extract_root = os.path.join(base_dir, "lnbodb_sessions")
            os.makedirs(extract_root, exist_ok=True)
            target_dir = tempfile.mkdtemp(prefix="session_", dir=extract_root)

            with zipfile.ZipFile(filename, "r") as zf:
                zf.extractall(target_dir)

            session_path = os.path.join(target_dir, "session.json")
            with open(session_path, "r", encoding="utf-8") as f:
                session = json.load(f)

            data_dir = os.path.join(target_dir, "data")
            structure = self.model.load_from_csv_root(data_dir)

            if isinstance(session.get("structure"), dict):
                structure = session["structure"]
                structure["csv_root"] = data_dir
                self.model.structure = structure
                self.model.csv_root = data_dir

            if self.view:
                self.view.update_tree_widget(structure)
                self.handle_clear_plot()

            virtual_dir = os.path.join(target_dir, "virtual")
            if os.path.isdir(virtual_dir):
                for fn in os.listdir(virtual_dir):
                    if not fn.lower().endswith(".csv"):
                        continue
                    name = os.path.splitext(fn)[0]
                    df = pd.read_csv(os.path.join(virtual_dir, fn))
                    if "Time" in df.columns and "Value" in df.columns:
                        self.model.add_virtual_variable(name, df["Time"].values, df["Value"].values)

            for entry in session.get("active_series") or []:
                label = entry.get("label")
                meta = (entry.get("meta") or {})
                kind = meta.get("kind")
                if kind == "field":
                    self.handle_field_selection(meta.get("instance"), meta.get("body_key"), meta.get("field"), meta.get("variant"), meta.get("aggregation"), plot=True)
                elif kind == "history":
                    self.handle_history_selection(meta.get("region"), meta.get("variable"), plot=True)
                elif kind == "virtual":
                    vv = self.model.virtual_variables.get(label)
                    if vv and self.view:
                        self._current_plotted_data[label] = {"time": vv["time"], "data": vv["data"], "meta": meta}
                        self.view.plot_series(vv["time"], vv["data"], label=label)

            if self.view:
                vis = session.get("series_visibility") or {}
                for label, is_on in vis.items():
                    self.view.control_panel.add_series_toggle(label, checked=bool(is_on))
                    self.view.plot_widget.set_series_visible(label, bool(is_on))

                plot_settings = session.get("plot_settings")
                self.view.control_panel.apply_plot_settings(plot_settings or {})
                self.view._apply_plot_settings(self.view.control_panel.get_plot_settings())

                self.view.show_status(f"Session loaded from {filename}")
            return True, f"Session loaded from {filename}"
        except Exception as e:
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self.view, "Session Error", f"Session load failed:\n{str(e)}")
            return False, f"Session load failed: {str(e)}"

    def export_data_to_csv(self, filename):
        if not self._current_plotted_data:
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self.view, "Export", "No data to export.")
            return False, "No data to export."
            
        try:
            df_dict = {}
            for label, data_obj in self._current_plotted_data.items():
                if "Time" not in df_dict:
                    df_dict["Time"] = data_obj["time"]
                data = data_obj["data"]
                if isinstance(data, dict):
                    df_dict[label + "__min"] = data.get("min")
                    df_dict[label + "__q1"] = data.get("q1")
                    df_dict[label + "__median"] = data.get("median")
                    df_dict[label + "__q3"] = data.get("q3")
                    df_dict[label + "__max"] = data.get("max")
                else:
                    df_dict[label] = data
                
            df = pd.DataFrame(df_dict)
            if not filename.lower().endswith(".csv"):
                filename += ".csv"
            df.to_csv(filename, index=False)
            if self.view:
                self.view.show_status(f"Data exported to {filename}")
            return True, f"Data exported to {filename}"
        except Exception as e:
            if self.view:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self.view, "Export Error", f"Export failed:\n{str(e)}")
            return False, f"Export failed: {str(e)}"
