from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QWidget, QLabel, QPushButton
from PySide6.QtCore import QSize, QObject, QRect
from piiscanner import Ui_Form
from functools import partial
import argparse, json, os, fnmatch, glob, pathlib, time, yaml, sys, os
from rich.progress import track
from extract import read_txt, read_docx, read_pdf
from infer import PiiModel
from utils import read_any, merge_findings, iter_files
import logging
import datetime as dt
import re




class PopUpForWarning(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(397, 219)
        self.setWindowTitle("Warning")
        self.WarningLabel = QLabel(self)
        self.WarningLabel.setObjectName("WarningLabel")
        self.WarningLabel.setGeometry(10, 10, 381, 111)
        self.WarningLabel.setText("Please make sure you have a File or Directory selected before scanning!")
    
        self.OkayButton = QPushButton(self)
        self.OkayButton.setObjectName("OkayButton")
        self.OkayButton.setGeometry(148, 153, 91, 41)
        self.OkayButton.setText("Okay")
        self.OkayButton.clicked.connect(self.close)


class MainWindow(QMainWindow, Ui_Form, QObject):
    def __init__(self):
        super().__init__()

        self.popUpWindow = None
        
        if os.path.isfile(os.getcwd() + "\config.yaml"): 
            self.cfg = yaml.safe_load(open(os.getcwd() + "\config.yaml", "r", encoding="utf-8"))

        
        if os.path.isdir(self.cfg["output"]["path"]) is not True:
            out_dir = pathlib.Path(self.cfg["output"]["path"])
            out_dir.mkdir(parents=True, exist_ok=True)
            
        if os.path.isdir(self.cfg["logging"]["file"]) is not True:
            os.makedirs(self.cfg["logging"]["file"])

        #Setting up log file.

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

        self.FileScanNowButton.clicked.connect(self.scan)

        self.DirectoryScanNowButton.clicked.connect(self.scan)
        
        # self.DirectoriesAllPiiButton.clicked.connect(self.grab_all_pii_button_value)

    
    def open_file_browser(self):
        fileName = QFileDialog.getOpenFileName(self, "Find Files..", os.getcwd(), "Text Files (*.txt);;Word Files (*.docx);;PDF Files(*.pdf)")
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
        try:
            pattern = "^(.+[/\\\\])?([^/\\\\]+)$"
            if re.match(pattern, self.FileLineEdit.text()) or re.match(pattern, self.DirectoryLineEdit.text()):
                
                
                self.stackedWidget.setCurrentIndex(3)

                model = PiiModel(
                    model_dir=self.cfg.get("model_dir", "model"),
                    thresholds=self.cfg.get("thresholds", {}),
                    batch_size=self.cfg.get("batch_size", 8),
                )
        
                self.ProgressBar.setValue(25)

        #     #Build File List 
        #     paths = []
        #     if len(self.FileLineEdit.text()) > 0:
        #         if os.path.isfile(p):
        #             paths.append(p)
        #     elif len(self.DirectoryLineEdit.text()) > 0:
        #         if os.path.isdir(self.DirectoryLineEdit.text()):
        #             for root, _, files in os.walk(p):
        #                 if any(fnmatch.fnmatch(root, ex) for ex in self.cfg.get("exclude_globs", [])):
        #                     continue
        #                 for f in files:
        #                     paths.append(os.path.join(root, f))
        
        #     self.ProgressBar.setValue(50)
        # # else:
        # #     paths = list(iter_files(self.cfg.get("targets", []), self.cfg.get("exclude_globs", [])))

        #     for p in paths:
        #         text = read_any(p)
        #         if not text:
        #             continue
        #         findings = model.predict(text)
        #         merged = merge_findings(findings, max_gap=self.cfg.get("merge_gap", 0))
                
        #         self.ProgressBar.setValue(75)

        #         if merged:
        #             record = {
        #                 "ts": time.time(),
        #                 "file": p,
        #                 "findings": merged,
        #             }
        #             (out_dir / (pathlib.Path(p).name + ".json")).write_text(
        #                 json.dumps(record, indent=2), encoding="utf-8"
        #             )
        #         self.ProgressBar.setValue(100)
            else:
                if len(self.FileLineEdit.text()) == 0 or len(self.FileLineEdit.text()) == 0:
                    self.popUpWindow = PopUpForWarning()
                    self.popUpWindow.show()
        except Exception as E:
            logging.basicConfig(filename=self.cfg["logging"]["file"] + os.path.sep + str(dt.datetime.now().strftime('%y-%m-%d-Time-%H-%M')) + ".log" , filemode="a", format="%(asctime)s - %(levelname)s - %(message)s" )
            self.logger = logging.getLogger(__name__)
        
            self.logger.error("Houston, this is a %s", E, exc_info=True)
            

            
    
    # def grab_all_pii_button_value(self):
    #     self.all_pii_value = "max"

    # def grab_some_pii_button_value(self):
    #     self.some_pii_value = "mean"
    
    # def grab_sensitive_pii_button_value(self):
    #     self.sensitive_pii_value = "low"
