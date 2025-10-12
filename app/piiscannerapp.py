from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PiiScanner import Ui_Form
import sys, os


class MainWindow(QMainWindow, Ui_Form):
    def __init__(self):
        super().__init__()

        self.setupUi(self)

        self.browseButton.clicked.connect(self.open_file_browser)

    def open_file_browser(self):
        fileName = QFileDialog.getOpenFileName(self, "Find Files..", os.getcwd(), "Text Files(*.txt)")