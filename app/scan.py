# scan.py
import sys
import argparse, json, os, fnmatch, glob, pathlib, time, yaml
from PySide6.QtWidgets import QApplication
from piiscannerapp import MainWindow
from rich.progress import track
from extract import read_txt, read_docx, read_pdf
from infer import PiiModel


def main():

    app = QApplication([])
    
    window = MainWindow()
    
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
