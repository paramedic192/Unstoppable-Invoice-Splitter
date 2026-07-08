import sys

import fitz  # PyMuPDF

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.doc = None
        self.current_file = None

        self.setWindowTitle("Unstoppable Invoice Splitter")
        self.resize(1400, 900)

        ###################################################
        # LEFT PANEL
        ###################################################

        self.openButton = QPushButton("📂 Open PDF")
        self.openButton.clicked.connect(self.open_pdf)

        self.pageList = QListWidget()
        self.pageList.currentRowChanged.connect(self.preview_page)

        leftLayout = QVBoxLayout()
        leftLayout.addWidget(self.openButton)
        leftLayout.addWidget(self.pageList)

        ###################################################
        # CENTER PREVIEW PANEL
        ###################################################

        self.previewLabel = QLabel("Open a PDF, then click a page to preview it.")
        self.previewLabel.setAlignment(Qt.AlignCenter)
        self.previewLabel.setStyleSheet("font-size: 18px; color: #555; padding: 20px;")

        self.previewScroll = QScrollArea()
        self.previewScroll.setWidgetResizable(True)
        self.previewScroll.setAlignment(Qt.AlignCenter)
        self.previewScroll.setWidget(self.previewLabel)

        ###################################################
        # RIGHT INFO PANEL
        ###################################################

        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setText("Ready. Open a scanned invoice PDF to begin.")

        ###################################################
        # MAIN LAYOUT
        ###################################################

        mainLayout = QHBoxLayout()
        mainLayout.addLayout(leftLayout, 1)
        mainLayout.addWidget(self.previewScroll, 3)
        mainLayout.addWidget(self.info, 2)

        widget = QWidget()
        widget.setLayout(mainLayout)

        self.setCentralWidget(widget)

    #######################################################

    def open_pdf(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Invoice PDF",
            "",
            "PDF Files (*.pdf)",
        )

        if not filename:
            return

        self.doc = fitz.open(filename)
        self.current_file = filename

        self.pageList.clear()

        for page_index in range(self.doc.page_count):
            self.pageList.addItem(f"Page {page_index + 1}")

        self.info.setText(
            f"""
PDF Loaded

File:
{filename}

Pages:
{self.doc.page_count}

Click a page on the left to preview it.
"""
        )

        if self.doc.page_count > 0:
            self.pageList.setCurrentRow(0)

    #######################################################

    def preview_page(self, page_index):
        if self.doc is None or page_index < 0:
            return

        page = self.doc.load_page(page_index)

        # Render at higher scale so the preview is readable.
        zoom = 1.5
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        image = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format_RGB888,
        )

        pixmap = QPixmap.fromImage(image)

        self.previewLabel.setPixmap(pixmap)
        self.previewLabel.adjustSize()

        self.info.setText(
            f"""
PDF Loaded

File:
{self.current_file}

Pages:
{self.doc.page_count}

Currently Previewing:
Page {page_index + 1}
"""
        )


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()
