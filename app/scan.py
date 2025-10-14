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

    # ap = argparse.ArgumentParser()
    # ap.add_argument("--config", default="config.yaml")
    # ap.add_argument("--input", nargs="*", help="Optional explicit files/dirs to scan (overrides targets in config)")
    # ap.add_argument("--merge_gap", type=int, default=0, help="Max char gap to merge adjacent fragments")
    # args = ap.parse_args()

if __name__ == "__main__":
    main()
