import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QSizePolicy
from PyQt6.QtCore import pyqtSignal, pyqtSlot
import numpy as np

class PlotWidget(QWidget):
    """Matplotlib-based visualization widget (View component)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._plotted_series = {}  # {label: line_obj}
        self._series_artists = {}  # {label: [artist, ...]}
        
    def _setup_ui(self):
        """Initializes the matplotlib canvas and toolbar."""
        self.layout = QVBoxLayout(self)
        
        # Create figure and canvas
        self.figure, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.updateGeometry()
        
        # Navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Add to layout
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        
        # Initial plot setup
        self.ax.set_title("ODB Plot Area")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Value")
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.canvas.draw()

    @pyqtSlot(object, object, str)
    def plot_series(self, time, data, label="Series", x_data=None):
        """Plots or updates a time-series or statistical range on the canvas."""
        x_vals = x_data if x_data is not None else time
        
        if isinstance(data, dict):
            old_artists = self._series_artists.get(label) or []
            for a in old_artists:
                try:
                    a.remove()
                except Exception:
                    pass

            line, = self.ax.plot(x_vals, data["median"], label=label)
            fill_q = self.ax.fill_between(x_vals, data["q1"], data["q3"], alpha=0.3)
            fill_m = self.ax.fill_between(x_vals, data["min"], data["max"], alpha=0.1)
            self._plotted_series[label] = line
            self._series_artists[label] = [line, fill_q, fill_m]
        else:
            if label in self._plotted_series:
                line = self._plotted_series[label]
                line.set_data(x_vals, data)
            else:
                line, = self.ax.plot(x_vals, data, label=label)
                self._plotted_series[label] = line
            self._series_artists[label] = [self._plotted_series[label]]
            
        # Adjust axis limits automatically
        self.ax.relim()
        self.ax.autoscale_view()
        self._refresh_legend()
        self.canvas.draw()

    def _refresh_legend(self):
        handles = []
        labels = []
        for label, line in self._plotted_series.items():
            if line.get_visible():
                handles.append(line)
                labels.append(label)
        if handles:
            self.ax.legend(handles, labels, loc="best")
        else:
            leg = self.ax.get_legend()
            if leg is not None:
                leg.remove()

    def set_series_visible(self, label, visible):
        artists = self._series_artists.get(label) or []
        for a in artists:
            try:
                a.set_visible(bool(visible))
            except Exception:
                pass
        self._refresh_legend()
        self.canvas.draw()

    def clear_plot(self):
        """Clears all series from the plot."""
        self.ax.clear()
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self._plotted_series = {}
        self._series_artists = {}
        self.canvas.draw()

    def set_labels(self, title=None, xlabel=None, ylabel=None):
        """Updates axis labels and title."""
        if title: self.ax.set_title(title)
        if xlabel: self.ax.set_xlabel(xlabel)
        if ylabel: self.ax.set_ylabel(ylabel)
        self.canvas.draw()

    def set_log_scale(self, axis='y', enabled=True):
        """Sets logarithmic scale for an axis."""
        scale = 'log' if enabled else 'linear'
        if axis == 'x':
            self.ax.set_xscale(scale)
        else:
            self.ax.set_yscale(scale)
        self.canvas.draw()

    def save_figure(self, filename):
        """Saves the current plot to a file (PNG, PDF, SVG)."""
        self.figure.savefig(filename, dpi=300, bbox_inches='tight')
        return True
