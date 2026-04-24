from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
    QStatusBar, QMessageBox, QFileDialog, QLabel
)
from PyQt6.QtCore import Qt
from app.gui.control_panel import ControlPanel
from app.gui.plot_widget import PlotWidget
from app.gui.widgets.calculator_dialog import CalculatorDialog

class MainWindow(QMainWindow):
    """The main application window (View component)."""
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Abaqus ODB Automation Expert")
        self.resize(1200, 800)
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Initializes the main layout with split panels and status bar."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Splitter for adjustable panel sizes
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel (Control)
        self.control_panel = ControlPanel(self.controller)
        self.splitter.addWidget(self.control_panel)
        
        # Right Panel (Visualization)
        self.plot_widget = PlotWidget()
        self.splitter.addWidget(self.plot_widget)
        
        # Set initial sizes (30% / 70%)
        self.splitter.setSizes([360, 840])
        
        self.main_layout.addWidget(self.splitter)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _connect_signals(self):
        """Links UI signals to controller actions."""
        # Load ODB
        self.control_panel.load_odb_clicked.connect(self.controller.handle_load_odb)
        
        # Field/History Selection
        self.control_panel.field_selected.connect(self.controller.handle_field_selection)
        self.control_panel.history_selected.connect(self.controller.handle_history_selection)
        
        # Calculator
        self.control_panel.calc_clicked.connect(self._open_calculator)
        
        # Plot settings
        self.control_panel.plot_settings_changed.connect(self._apply_plot_settings)

        self.control_panel.series_visibility_changed.connect(self._on_series_visibility_changed)
        
        # Export
        self.control_panel.export_clicked.connect(self.controller.export_data_to_csv)
        self.control_panel.export_xlsx_clicked.connect(self.controller.export_data_to_xlsx)
        self.control_panel.export_plot_image_clicked.connect(self.controller.export_plot_image)
        self.control_panel.session_save_clicked.connect(self.controller.save_session)
        self.control_panel.session_load_clicked.connect(self.controller.load_session)

    def update_tree_widget(self, structure):
        """Updates the object tree with new ODB structure."""
        self.control_panel.update_tree(structure)

    def plot_series(self, time, data, label):
        """Plots a new series on the visualization widget."""
        self.control_panel.add_x_axis_option(label)
        self.control_panel.add_series_toggle(label, checked=True)
        
        # Determine if we should plot against Time or something else
        x_label = self.control_panel.x_axis_combo.currentText()
        x_data = None
        if x_label != "Time":
            # Find data for the selected X-axis in controller
            if x_label in self.controller._current_plotted_data:
                x_data = self.controller._current_plotted_data[x_label]["data"]
        
        self.plot_widget.plot_series(time, data, label, x_data=x_data)
        self.plot_widget.set_labels(xlabel=x_label)

    def show_status(self, message):
        """Displays a message in the status bar."""
        self.status_bar.showMessage(message)

    def _open_calculator(self):
        """Opens the field calculator dialog."""
        # Get list of currently plotted series keys
        active_series = list(self.controller._current_plotted_data.keys())
        if not active_series:
            QMessageBox.warning(self, "Calculator", "No active data to perform calculations on.")
            return
            
        dialog = CalculatorDialog(active_series, self)
        if dialog.exec():
            payload = dialog.get_payload()
            if payload.get("mode") == "expression":
                expr = payload.get("expression") or ""
                name = payload.get("result") or "Result_Expression"
                success, msg = self.controller.handle_expression_calculator(expr, payload.get("token_map") or {}, name)
            else:
                var1 = payload.get("var1")
                var2 = payload.get("var2")
                op = payload.get("op")
                name = payload.get("result") or f"Result_{var1}_{op}_{var2}"
                success, msg = self.controller.handle_field_calculator(var1, var2, op, name)
            if success:
                self.show_status(msg)
            else:
                QMessageBox.critical(self, "Error", msg)

    def update_virtual_variables_list(self, name):
        """Updates the control panel with the newly created virtual variable."""
        self.control_panel.update_virtual_list(name)

    def _apply_plot_settings(self, settings):
        """Updates the plot widget based on control panel settings."""
        self.plot_widget.ax.grid(settings.get("grid", True))
        self.plot_widget.set_log_scale('x', settings.get("log_x", False))
        self.plot_widget.set_log_scale('y', settings.get("log_y", False))
        
        # Apply limits or autoscale
        if settings.get("autoscale", True):
            self.plot_widget.ax.set_autoscalex_on(True)
            self.plot_widget.ax.set_autoscaley_on(True)
            self.plot_widget.ax.relim()
            self.plot_widget.ax.autoscale_view()
        else:
            self.plot_widget.ax.set_xlim(settings.get("x_min", 0), settings.get("x_max", 100))
            self.plot_widget.ax.set_ylim(settings.get("y_min", 0), settings.get("y_max", 100))
        
        # Update line widths for all plotted series
        lw = settings.get("line_width", 1)
        for line in self.plot_widget._plotted_series.values():
            line.set_linewidth(lw)
        
        self.plot_widget.canvas.draw()

    def _on_series_visibility_changed(self, label, visible):
        self.plot_widget.set_series_visible(label, visible)
