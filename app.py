import sys

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QListWidget,
    QTextEdit,
)

import fitz


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Unstoppable Invoice Splitter")
        self.resize(1400, 900)

        ###################################################
        # LEFT PANEL
        ###################################################

        self.openButton = QPushButton("📂 Open PDF")
        self.openButton.clicked.connect(self.open_pdf)

        self.pageList = QListWidget()

        leftLayout = QVBoxLayout()
        leftLayout.addWidget(self.openButton)
        leftLayout.addWidget(self.pageList)

        ###################################################
        # RIGHT PANEL
        ###################################################

        self.info = QTextEdit()
        self.info.setReadOnly(True)

        ###################################################
        # MAIN
        ###################################################

        mainLayout = QHBoxLayout()
        mainLayout.addLayout(leftLayout, 1)
        mainLayout.addWidget(self.info, 3)

        widget = QWidget()
        widget.setLayout(mainLayout)

        self.setCentralWidget(widget)

    #######################################################

    def open_pdf(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Invoice PDF",
            "",
            "PDF Files (*.pdf)"
        )

        if not filename:
            return

        self.doc = fitz.open(filename)

        self.pageList.clear()

        for page in range(self.doc.page_count):
            self.pageList.addItem(f"Page {page+1}")

        self.info.setText(
            f"""
PDF Loaded

File:
{filename}

Pages:
{self.doc.page_count}
"""
        )


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()