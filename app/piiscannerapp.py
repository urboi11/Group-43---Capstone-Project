from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide6.QtCore import QSize, QObject
from PiiScanner import Ui_Form
from functools import partial
import sys, os



"""
    TODO: 
    1. Grab the file location from the browse buttons, and also fill in the text field with the selected file location
    2. Then Select the values that will be the for the PII, 
        2.a. Full PII button needs to have a specified value
        2.b. Some PII Button 
        2.c. Only Sensitive PII button. 
    3. Tie the Scan Now Button to the operation of the scanning of files. 
        3.a With each operation that is passed, make sure to update the percentage of the Progress Bar. 
    4. Once completed, display the results of the findings in the Results Pane. 
"""

class MainWindow(QMainWindow, Ui_Form, QObject):
    def __init__(self):
        super().__init__()

        self.setupUi(self)

        self.setFixedSize(QSize(650,500))

        self.ProgressBar.setMinimum(0)
        
        self.ProgressBar.setMaximum(100)

        self.FileBrowseButton.clicked.connect(self.open_file_browser)

        self.DirectoriesBrowseButton.clicked.connect(self.open_directory_browser)


        self.ScanFilesButton.clicked.connect(lambda: self.SwitchToFilePanel(2))

        self.ScanDirectoryButton.clicked.connect(lambda: self.SwitchToFilePanel(1))
        
        self.FileMainMenuButton.clicked.connect(lambda: self.SwitchToMainMenuPanel(0))

        self.DirectoriesMainMenuButton.clicked.connect(lambda: self.SwitchToMainMenuPanel(0))

        self.FileScanNowButton.clicked.connect(lambda: self.SwitchToFilePanel_Scan(3, self.scan))

        self.DirectoryScanNowButton.clicked.connect(lambda: self.SwitchToFilePanel_Scan(3, self.scan))
        
        self.DirectoriesAllPiiButton.clicked.connect(self.grab_all_pii_button_value)

    
    def open_file_browser(self):
        fileName = QFileDialog.getOpenFileName(self, "Find Files..", os.getcwd(), "All Files(*.*)")
        fileNameLength = len(fileName[0].split("/"))
        
        self.FileLineEdit.setText(fileName[0].split("/")[fileNameLength-1])
        
    def open_directory_browser(self):
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.DirectoryLineEdit.setText(directory)

    def SwitchToFilePanel(self, index):
        self.stackedWidget.setCurrentIndex(index)
    
    def SwitchToFilePanel_Scan(self, index, scan):
        self.ProgressBar.setValue(0)
        self.stackedWidget.setCurrentIndex(index)
        scan()
    
    def SwitchToMainMenuPanel(self, index):
        self.stackedWidget.setCurrentIndex(index)
        self.FileLineEdit.setText("")
        self.DirectoryLineEdit.setText("")

    ## TODO: Work on this one. 
    def scan(self):
        print("Hello!")
            
    
    def grab_all_pii_button_value(self):
        self.all_pii_value = 3

    def grab_some_pii_button_value(self):
        self.some_pii_value = 4
    
    def grab_sensitive_pii_button_value(self):
        self.sensitive_pii_value = 5
