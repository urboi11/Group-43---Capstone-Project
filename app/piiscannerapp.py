from PySide6.QtWidgets import QMainWindow, QFileDialog, QWidget, QLabel, QPushButton
from PySide6.QtCore import QSize, QObject
from piiscanner import Ui_Form
import json, os, fnmatch, pathlib, time, yaml, os, webbrowser
from infer import PiiModel
from utils import read_any, merge_findings
import logging
import datetime as dt
import re
from os import startfile




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

        self.fileLocation = None
        
        if os.path.isfile(os.getcwd() + "\config.yaml"): 
            self.cfg = yaml.safe_load(open(os.getcwd() + "\config.yaml", "r", encoding="utf-8"))
        
        if os.path.isdir(self.cfg["output"]["path"]) is not True:
            out_dir = pathlib.Path(self.cfg["output"]["path"])
            out_dir.mkdir(parents=True, exist_ok=True)
        
            
        if os.path.isdir(self.cfg["logging"]["path"]) is not True:
            os.makedirs(self.cfg["logging"]["path"])

        self.outputDir = self.cfg["output"]["path"]
        self.loggingDir = self.cfg["logging"]["path"]

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

        self.ResultsMainMenuButton.clicked.connect(self.SwitchToMainMenuPanel)
        
        self.FindingsFolderButton.clicked.connect(lambda: self.open_external_document(self.fileLocation))

        

    
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
        self.FileResults.setText("")
    
    def open_external_document(self, fileName):
        print("In Function" , fileName)
        startfile(fileName)

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

                #Build File List 
                paths = []
                if len(self.FileLineEdit.text()) > 0:
                    if os.path.isfile(self.FileLineEdit.text()):
                        paths.append(self.FileLineEdit.text())
                elif len(self.DirectoryLineEdit.text()) > 0:
                    if os.path.isdir(self.DirectoryLineEdit.text()):
                        for root, _, files in os.walk(self.DirectoryLineEdit.text()):
                            if any(fnmatch.fnmatch(root, ex) for ex in self.cfg.get("exclude_globs", [])):
                                continue
                            for f in files:
                                paths.append(os.path.join(root, f))
                print(paths)
        
                self.ProgressBar.setValue(50)
        ##TODO: Figure out what to do with this else statement. 
        # else:
        #     paths = list(iter_files(self.cfg.get("targets", []), self.cfg.get("exclude_globs", [])))

                for p in paths:
                    text = read_any(p)
                    if not text:
                        continue
                    findings = model.predict(text)
                    merged = merge_findings(findings, max_gap=self.cfg.get("merge_gap", 0))
                
                    self.ProgressBar.setValue(75)
                    print(str(self.outputDir + os.path.sep + (pathlib.Path(p).name + ".json")))
                    if merged:
                        record = {
                            "ts": time.time(),
                            "file": p,
                            "findings": merged,
                        }
                        with open(str(self.outputDir + os.path.sep + (pathlib.Path(p).name + ".json")), "a") as file:
                            file.write(json.dumps(record, indent=2))
                            self.FileResults.setText(json.dumps(record, indent=2))
                            ##Testing...
                            print(type(self.outputDir + os.path.sep + (pathlib.Path(p).name + ".json")))
                            self.fileLocation = self.outputDir + os.path.sep + (pathlib.Path(p).name + ".json")
                            
                            file.close()
                        self.stackedWidget.setCurrentIndex(4)

                        # (str(self.outputDir + os.path.sep + (pathlib.Path(p).name + ".json"))).write_text(
                        #     json.dumps(record, indent=2), encoding="utf-8"
                        # )
                self.ProgressBar.setValue(100)
            else:
                if len(self.FileLineEdit.text()) == 0 or len(self.FileLineEdit.text()) == 0:
                    self.popUpWindow = PopUpForWarning()
                    self.popUpWindow.show()
        except Exception as E:
            logging.basicConfig(filename=self.cfg["logging"]["file"] + os.path.sep + str(dt.datetime.now().strftime('%y-%m-%d-Time-%H-%M')) + ".log" , filemode="a", format="%(asctime)s - %(levelname)s - %(message)s" )
            self.logger = logging.getLogger(__name__)
        
            self.logger.error("%s", E, exc_info=True)
            
