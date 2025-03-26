import sys
from PySide6.QtWidgets import QApplication
from src.components.Application import Application

if __name__ == "__main__":
    app = QApplication([])
    window = Application()
    window.show()
    sys.exit(app.exec())