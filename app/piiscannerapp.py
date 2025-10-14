from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide6.QtCore import QSize, QObject
from PiiScanner import Ui_Form
from functools import partial
import argparse, json, os, fnmatch, glob, pathlib, time, yaml, sys, os
from rich.progress import track
from extract import read_txt, read_docx, read_pdf
from infer import PiiModel
from scan import read_any, merge_findings, iter_files



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
            #Test this config location to make sure that it works. 
        cfg = yaml.safe_load(open(os.getcwd() + "\config.yaml", "r", encoding="utf-8"))
        out_dir = pathlib.Path(cfg["output"]["path"])
        out_dir.mkdir(parents=True, exist_ok=True)

        model = PiiModel(
            model_dir=cfg.get("model_dir", "model"),
            thresholds=cfg.get("thresholds", {}),
            batch_size=cfg.get("batch_size", 8),
        )

        # Build file list
        # if args.input:
        # Verify that this logic works correctly
        if len(self.FileLineEdit.text()) > 0 or len(self.DirectoryLineEdit.text()) > 0:
            paths = []
            # for p in args.input:
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    if any(fnmatch.fnmatch(root, ex) for ex in cfg.get("exclude_globs", [])):
                        continue
                    for f in files:
                        paths.append(os.path.join(root, f))
            elif os.path.isfile(p):
                paths.append(p)
        else:
            #TODO: Work on this one, targets config property will not exist. 
            paths = list(iter_files(cfg.get("targets", []), cfg.get("exclude_globs", [])))

        for p in track(paths, description="Scanning"):
            try:
                text = read_any(p)
                if not text:
                    continue
                findings = model.predict(text)
                merged = merge_findings(findings, max_gap=cfg.get("merge_gap", 0))
                if merged:
                    record = {
                        "ts": time.time(),
                        "file": p,
                        "findings": merged,
                    }
                    (out_dir / (pathlib.Path(p).name + ".json")).write_text(
                        json.dumps(record, indent=2), encoding="utf-8"
                    )
            except Exception:
                # In production: log errors to a file; for now, continue scanning next file.
                continue

            
    
    def grab_all_pii_button_value(self):
        self.all_pii_value = 3

    def grab_some_pii_button_value(self):
        self.some_pii_value = 4
    
    def grab_sensitive_pii_button_value(self):
        self.sensitive_pii_value = 5
