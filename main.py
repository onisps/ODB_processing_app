import sys
from PyQt6.QtWidgets import QApplication
from app.gui.main_window import MainWindow
from app.core.controller import Controller
from app.core.model import Model

def main():
    app = QApplication(sys.argv)
    
    # MVC initialization
    model = Model()
    controller = Controller(model)
    window = MainWindow(controller)
    
    # Connect controller to window if needed
    controller.set_view(window)
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
