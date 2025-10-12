from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide6.QtCore import QSize
from PiiScanner import Ui_Form
import sys, os


class MainWindow(QMainWindow, Ui_Form):
    def __init__(self):
        super().__init__()

        self.setupUi(self)

        self.setFixedSize(QSize(650,500))

        self.FileBrowseButton.clicked.connect(self.open_file_browser)

        self.ScanFilesButton.clicked.connect(self.SwitchToFilePanel(2))

        self.FileMainMenuButton.clicked.connect(self.SwitchToFilePanel(0))

    def open_file_browser(self):
        fileName = QFileDialog.getOpenFileName(self, "Find Files..", os.getcwd(), "Text Files(*.txt)")
    
    def SwitchToFilePanel(self, index):
        self.stackedWidget.setCurrentIndex(index)