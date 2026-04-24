from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QComboBox, 
    QLabel, QScrollArea, QHBoxLayout, QGroupBox, QSpinBox, QCheckBox, QFileDialog, QHeaderView,
    QProgressBar, QDoubleSpinBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QBrush, QFont
import os
from app.gui.widgets.accordion import Accordion

class ControlPanel(QWidget):
    """The left-side control panel (View component)."""
    
    # Signals for controller to handle
    load_odb_clicked = pyqtSignal(str)
    load_parsed_clicked = pyqtSignal(str) # New signal for loading existing CSVs
    clear_plot_clicked = pyqtSignal()     # New signal for clearing plot
    field_selected = pyqtSignal(str, str, str, str, str)  # instance, body_key, field, variant, aggregation
    history_selected = pyqtSignal(str, str)     # rp_name, variable
    calc_clicked = pyqtSignal()
    export_clicked = pyqtSignal(str)
    export_xlsx_clicked = pyqtSignal(str)
    export_plot_image_clicked = pyqtSignal(str)
    session_save_clicked = pyqtSignal(str)
    session_load_clicked = pyqtSignal(str)
    plot_settings_changed = pyqtSignal(dict)
    series_visibility_changed = pyqtSignal(str, bool)
    
    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._active_tree_item = None
        self._series_checkboxes = {}
        self._label_to_item = {}
        self._setup_ui()
        
    def _setup_ui(self):
        """Builds the control panel layout with load button, tree, and accordions."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        
        # 1. Load Data Block
        self.load_btn = QPushButton("📂 Load ODB File")
        self.load_btn.setFixedHeight(40)
        self.load_btn.setStyleSheet("QPushButton { background-color: #2ecc71; color: white; font-weight: bold; border-radius: 5px; }")
        self.load_btn.clicked.connect(self._on_load_clicked)
        self.layout.addWidget(self.load_btn)
        
        # Load Parsed Data
        self.load_parsed_btn = QPushButton("📂 Load Parsed CSVs")
        self.load_parsed_btn.clicked.connect(self._on_load_parsed_clicked)
        self.layout.addWidget(self.load_parsed_btn)
        
        # Clear Plot Button
        self.clear_plot_btn = QPushButton("🗑️ Clear Plot")
        self.clear_plot_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-weight: bold; }")
        self.clear_plot_btn.clicked.connect(lambda: self.clear_plot_clicked.emit())
        self.layout.addWidget(self.clear_plot_btn)
        
        # ODB Info
        self.odb_info_label = QLabel("No ODB Loaded")
        self.odb_info_label.setStyleSheet("font-weight: bold; color: #34495e;")
        self.layout.addWidget(self.odb_info_label)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m")
        self.layout.addWidget(self.progress_bar)
        
        # Progress Status
        self.progress_status = QLabel("")
        self.progress_status.setVisible(False)
        self.progress_status.setWordWrap(True)
        self.layout.addWidget(self.progress_status)
        
        # 2. Object Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Object", "Variable", "Aggregation", "Series"])
        self.tree.setColumnCount(4)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.layout.addWidget(self.tree)
        
        # 3. Accordion Sections
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(5)
        
        # - Plot Settings
        self.plot_acc = Accordion("Plot Settings")
        self._add_plot_settings(self.plot_acc)
        self.scroll_layout.addWidget(self.plot_acc)
        
        # - Field Calculator
        self.calc_acc = Accordion("Field Calculator")
        self._add_calculator_settings(self.calc_acc)
        self.scroll_layout.addWidget(self.calc_acc)
        
        # - Export & Session
        self.export_acc = Accordion("Export & Session")
        self._add_export_settings(self.export_acc)
        self.scroll_layout.addWidget(self.export_acc)
        
        self.scroll_layout.addStretch()
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)
        
        # Set fixed width for control panel
        self.setMinimumWidth(300)

    def _add_plot_settings(self, accordion):
        """Adds controls to the plot settings section."""
        layout = QVBoxLayout()
        
        # X-Axis selection
        x_axis_layout = QHBoxLayout()
        x_axis_layout.addWidget(QLabel("X-Axis:"))
        self.x_axis_combo = QComboBox()
        self.x_axis_combo.addItem("Time")
        self.x_axis_combo.currentIndexChanged.connect(self._on_plot_settings_changed)
        x_axis_layout.addWidget(self.x_axis_combo)
        layout.addLayout(x_axis_layout)

        # Grid settings
        self.grid_cb = QCheckBox("Show Grid")
        self.grid_cb.setChecked(True)
        self.grid_cb.stateChanged.connect(self._on_plot_settings_changed)
        layout.addWidget(self.grid_cb)
        
        # Scale settings
        self.log_x_cb = QCheckBox("Logarithmic X-axis")
        self.log_y_cb = QCheckBox("Logarithmic Y-axis")
        self.log_x_cb.stateChanged.connect(self._on_plot_settings_changed)
        self.log_y_cb.stateChanged.connect(self._on_plot_settings_changed)
        layout.addWidget(self.log_x_cb)
        layout.addWidget(self.log_y_cb)
        
        # Line width
        lw_layout = QHBoxLayout()
        lw_layout.addWidget(QLabel("Line Width:"))
        self.lw_spin = QSpinBox()
        self.lw_spin.setRange(1, 10)
        self.lw_spin.setValue(1)
        self.lw_spin.valueChanged.connect(self._on_plot_settings_changed)
        lw_layout.addWidget(self.lw_spin)
        layout.addLayout(lw_layout)

        # Axis Limits
        layout.addWidget(QLabel("<b>Axis Limits:</b>"))
        
        # X Limits
        x_lim_layout = QHBoxLayout()
        x_lim_layout.addWidget(QLabel("X Min:"))
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1e9, 1e9)
        self.x_min_spin.setValue(0.0)
        self.x_min_spin.valueChanged.connect(self._on_plot_settings_changed)
        x_lim_layout.addWidget(self.x_min_spin)
        
        x_lim_layout.addWidget(QLabel("X Max:"))
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1e9, 1e9)
        self.x_max_spin.setValue(100.0)
        self.x_max_spin.valueChanged.connect(self._on_plot_settings_changed)
        x_lim_layout.addWidget(self.x_max_spin)
        layout.addLayout(x_lim_layout)

        # Y Limits
        y_lim_layout = QHBoxLayout()
        y_lim_layout.addWidget(QLabel("Y Min:"))
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1e9, 1e9)
        self.y_min_spin.setValue(0.0)
        self.y_min_spin.valueChanged.connect(self._on_plot_settings_changed)
        y_lim_layout.addWidget(self.y_min_spin)
        
        y_lim_layout.addWidget(QLabel("Y Max:"))
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1e9, 1e9)
        self.y_max_spin.setValue(100.0)
        self.y_max_spin.valueChanged.connect(self._on_plot_settings_changed)
        y_lim_layout.addWidget(self.y_max_spin)
        layout.addLayout(y_lim_layout)

        # Auto-scale toggle
        self.autoscale_cb = QCheckBox("Auto-scale Axes")
        self.autoscale_cb.setChecked(True)
        self.autoscale_cb.stateChanged.connect(self._on_plot_settings_changed)
        layout.addWidget(self.autoscale_cb)
        
        accordion.add_widget(QWidget())
        accordion.content_layout.addLayout(layout)

    def _add_calculator_settings(self, accordion):
        """Adds controls to the field calculator section."""
        layout = QVBoxLayout()
        
        self.calc_btn = QPushButton("🧮 Open Field Calculator")
        self.calc_btn.clicked.connect(lambda: self.calc_clicked.emit())
        layout.addWidget(self.calc_btn)
        
        # List for virtual variables
        self.virtual_list = QLabel("No virtual variables added.")
        self.virtual_list.setWordWrap(True)
        layout.addWidget(self.virtual_list)
        
        accordion.add_widget(QWidget())
        accordion.content_layout.addLayout(layout)

    def _add_export_settings(self, accordion):
        """Adds controls to the export & session section."""
        layout = QVBoxLayout()
        
        self.export_csv_btn = QPushButton("📄 Export to CSV")
        self.export_csv_btn.clicked.connect(self._on_export_csv_clicked)
        layout.addWidget(self.export_csv_btn)
        
        self.export_xlsx_btn = QPushButton("📊 Export to Excel")
        self.export_xlsx_btn.clicked.connect(self._on_export_xlsx_clicked)
        layout.addWidget(self.export_xlsx_btn)

        self.export_plot_btn = QPushButton("🖼️ Save Plot Image")
        self.export_plot_btn.clicked.connect(self._on_export_plot_clicked)
        layout.addWidget(self.export_plot_btn)
        
        self.save_session_btn = QPushButton("💾 Save Session")
        self.save_session_btn.clicked.connect(self._on_save_session_clicked)
        layout.addWidget(self.save_session_btn)
        
        self.load_session_btn = QPushButton("📂 Load Session")
        self.load_session_btn.clicked.connect(self._on_load_session_clicked)
        layout.addWidget(self.load_session_btn)
        
        accordion.add_widget(QWidget())
        accordion.content_layout.addLayout(layout)

    def set_progress(self, current, total, message):
        """Updates the progress bar and status text."""
        self.progress_bar.setVisible(True)
        self.progress_status.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_status.setText(message)
        
    def hide_progress(self):
        """Hides the progress bar and status text."""
        self.progress_bar.setVisible(False)
        self.progress_status.setVisible(False)

    def update_tree(self, structure):
        """Populates the tree widget with ODB structure."""
        self.odb_info_label.setText(f"ODB: {os.path.basename(self.controller.model.odb_path)}")
        self.tree.clear()
        self._active_tree_item = None
        self._label_to_item = {}
        self._series_checkboxes = {}
        
        instances_item = QTreeWidgetItem(self.tree, ["Instances", "", ""])
        for inst_name, inst_info in (structure.get("Instances", {}) or {}).items():
            inst_node = QTreeWidgetItem(instances_item, [inst_name, "", ""])
            bodies = (inst_info.get("Bodies") or {})
            for body_key, body_info in bodies.items():
                body_node = QTreeWidgetItem(inst_node, [body_key, "", ""])
                fields = (body_info.get("Fields") or {})
                for field_name, field_info in fields.items():
                    field_node = QTreeWidgetItem(body_node, ["", field_name, ""])
                    variants = (field_info.get("Variants") or {})
                    for variant_name, variant_info in variants.items():
                        variant_node = QTreeWidgetItem(field_node, ["", variant_name, ""])
                        aggs = variant_info.get("Aggregations") or []
                        for agg in aggs:
                            agg_item = QTreeWidgetItem(variant_node, ["", "", agg])
                            series_label = f"{inst_name}__{body_key}__{field_name}__{variant_name}__{agg}"
                            self._label_to_item[series_label] = agg_item
                            agg_item.setData(
                                0,
                                Qt.ItemDataRole.UserRole,
                                {
                                    "kind": "field",
                                    "instance": inst_name,
                                    "body_key": body_key,
                                    "field": field_name,
                                    "variant": variant_name,
                                    "aggregation": agg,
                                },
                            )

        history_item = QTreeWidgetItem(self.tree, ["History Outputs", "", ""])
        history = structure.get("HistoryOutputs") or {}
        for region_name, vars_map in history.items():
            region_node = QTreeWidgetItem(history_item, [region_name, "", ""])
            if isinstance(vars_map, dict):
                var_names = list(vars_map.keys())
            else:
                var_names = vars_map or []
            for var_name in var_names:
                var_node = QTreeWidgetItem(region_node, ["", var_name, "History"])
                series_label = f"{region_name}_{var_name}"
                self._label_to_item[series_label] = var_node
                var_node.setData(0, Qt.ItemDataRole.UserRole, {"kind": "history", "region": region_name, "variable": var_name})

        self.tree.expandAll()

    def _on_load_clicked(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open ODB File", "", "Abaqus ODB (*.odb);;All Files (*)")
        if filename:
            self.load_odb_clicked.emit(filename)

    def _on_load_parsed_clicked(self):
        """Opens a directory dialog to select an already extracted folder."""
        directory = QFileDialog.getExistingDirectory(self, "Select Extracted Data Folder")
        if directory:
            self.load_parsed_clicked.emit(directory)

    def _on_tree_item_double_clicked(self, item, column):
        """Triggers data extraction and plotting when an item is double-clicked."""
        meta = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(meta, dict):
            if meta.get("kind") == "field":
                self._set_active_tree_item(item)
                self.field_selected.emit(
                    meta.get("instance"),
                    meta.get("body_key"),
                    meta.get("field"),
                    meta.get("variant"),
                    meta.get("aggregation"),
                )
                return
            if meta.get("kind") == "history":
                self._set_active_tree_item(item)
                self.history_selected.emit(meta.get("region"), meta.get("variable"))
                return

    def _on_plot_settings_changed(self):
        settings = {
            "grid": self.grid_cb.isChecked(),
            "log_x": self.log_x_cb.isChecked(),
            "log_y": self.log_y_cb.isChecked(),
            "line_width": self.lw_spin.value(),
            "x_axis": self.x_axis_combo.currentText(),
            "autoscale": self.autoscale_cb.isChecked(),
            "x_min": self.x_min_spin.value(),
            "x_max": self.x_max_spin.value(),
            "y_min": self.y_min_spin.value(),
            "y_max": self.y_max_spin.value()
        }
        self.plot_settings_changed.emit(settings)

    def get_plot_settings(self):
        return {
            "grid": self.grid_cb.isChecked(),
            "log_x": self.log_x_cb.isChecked(),
            "log_y": self.log_y_cb.isChecked(),
            "line_width": self.lw_spin.value(),
            "x_axis": self.x_axis_combo.currentText(),
            "autoscale": self.autoscale_cb.isChecked(),
            "x_min": self.x_min_spin.value(),
            "x_max": self.x_max_spin.value(),
            "y_min": self.y_min_spin.value(),
            "y_max": self.y_max_spin.value(),
        }

    def apply_plot_settings(self, settings):
        if not isinstance(settings, dict):
            return

        old = self.blockSignals(True)
        try:
            if "grid" in settings:
                self.grid_cb.setChecked(bool(settings["grid"]))
            if "log_x" in settings:
                self.log_x_cb.setChecked(bool(settings["log_x"]))
            if "log_y" in settings:
                self.log_y_cb.setChecked(bool(settings["log_y"]))
            if "line_width" in settings:
                self.lw_spin.setValue(int(settings["line_width"]))
            if "autoscale" in settings:
                self.autoscale_cb.setChecked(bool(settings["autoscale"]))
            if "x_min" in settings:
                self.x_min_spin.setValue(float(settings["x_min"]))
            if "x_max" in settings:
                self.x_max_spin.setValue(float(settings["x_max"]))
            if "y_min" in settings:
                self.y_min_spin.setValue(float(settings["y_min"]))
            if "y_max" in settings:
                self.y_max_spin.setValue(float(settings["y_max"]))
            if "x_axis" in settings:
                txt = str(settings["x_axis"])
                idx = self.x_axis_combo.findText(txt)
                if idx >= 0:
                    self.x_axis_combo.setCurrentIndex(idx)
        finally:
            self.blockSignals(old)

    def _on_export_csv_clicked(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if filename:
            self.export_clicked.emit(filename)

    def _on_export_xlsx_clicked(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Excel", "", "Excel Files (*.xlsx)")
        if filename:
            self.export_xlsx_clicked.emit(filename)

    def _on_export_plot_clicked(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Plot Image", "", "PNG Image (*.png);;SVG Image (*.svg);;PDF (*.pdf)")
        if filename:
            self.export_plot_image_clicked.emit(filename)

    def _on_save_session_clicked(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Session", "", "LNB ODB Session (*.lnbodb)")
        if filename:
            self.session_save_clicked.emit(filename)

    def _on_load_session_clicked(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Session", "", "LNB ODB Session (*.lnbodb)")
        if filename:
            self.session_load_clicked.emit(filename)
            
    def add_x_axis_option(self, label):
        """Adds a new option to the X-axis selection dropdown."""
        if self.x_axis_combo.findText(label) == -1:
            self.x_axis_combo.addItem(label)

    def add_series_toggle(self, label, checked=True):
        if label in self._series_checkboxes:
            cb = self._series_checkboxes[label]
            cb.setChecked(checked)
            return

        item = self._label_to_item.get(label)
        if item is None:
            return

        cb = QCheckBox()
        cb.setChecked(checked)
        cb.toggled.connect(lambda state, l=label: self.series_visibility_changed.emit(l, state))
        self.tree.setItemWidget(item, 3, cb)
        self._series_checkboxes[label] = cb

    def clear_series_toggles(self):
        for label, cb in list(self._series_checkboxes.items()):
            item = self._label_to_item.get(label)
            if item is not None:
                self.tree.removeItemWidget(item, 3)
            cb.deleteLater()
        self._series_checkboxes = {}

    def _set_active_tree_item(self, item):
        if self._active_tree_item is not None:
            for col in range(self.tree.columnCount()):
                self._active_tree_item.setBackground(col, QBrush())
            f = self._active_tree_item.font(0)
            f.setBold(False)
            for col in range(self.tree.columnCount()):
                self._active_tree_item.setFont(col, f)

        self._active_tree_item = item
        if self._active_tree_item is None:
            return

        brush = QBrush(QColor(255, 245, 196))
        for col in range(self.tree.columnCount()):
            self._active_tree_item.setBackground(col, brush)

        f = self._active_tree_item.font(0)
        f.setBold(True)
        for col in range(self.tree.columnCount()):
            self._active_tree_item.setFont(col, f)

    def update_virtual_list(self, name):
        """Updates the text showing available virtual variables."""
        current = self.virtual_list.text()
        if "No virtual" in current:
            self.virtual_list.setText(f"Active: {name}")
        else:
            self.virtual_list.setText(f"{current}, {name}")
