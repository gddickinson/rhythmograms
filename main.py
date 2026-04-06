"""Entry point for the Heidersberger Rhythmogram Simulator."""

import sys
from PyQt6.QtWidgets import QApplication
from gui.app import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Rhythmogram Simulator")
    app.setOrganizationName("Heidersberger")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
