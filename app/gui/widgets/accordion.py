from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QScrollArea, QFrame, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QAbstractAnimation, QParallelAnimationGroup

class Accordion(QWidget):
    """A custom collapsible accordion-style widget for organizing control sections."""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self._setup_ui(title)
        
    def _setup_ui(self, title):
        """Initializes the toggle button and the content area."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Toggle button
        self.toggle_button = QPushButton(f"▼ {title}")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:checked {
                background-color: #e0e0e0;
            }
        """)
        self.toggle_button.clicked.connect(self._toggle_content)
        
        # Content container
        self.content_area = QFrame()
        self.content_area.setStyleSheet("QFrame { border: 1px solid #d0d0d0; border-top: none; background: #ffffff; }")
        self.content_layout = QVBoxLayout(self.content_area)
        
        # Add to layout
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_area)
        
        # Ensure it fits within parent
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def add_widget(self, widget):
        """Adds a widget to the accordion content area."""
        self.content_layout.addWidget(widget)

    def _toggle_content(self):
        """Shows or hides the content area when the button is clicked."""
        checked = self.toggle_button.isChecked()
        self.content_area.setVisible(checked)
        self.toggle_button.setText(f"{'▼' if checked else '▶'} {self.toggle_button.text()[2:]}")
