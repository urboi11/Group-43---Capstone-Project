
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PII")
        button = QPushButton("Press Me!")

        self.setFixedSize(QSize(500,500))

        self.setCentralWidget(button)

def main():

    app = QApplication([])

    window = MainWindow()

    window.show()

    app.exec()

if __name__ == "__main__":
    main()
