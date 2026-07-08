import sys

import fitz

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
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

        self.openButton = QPushButton("Open PDF")
        self.openButton.clicked.connect(self.open_pdf)

        self.pageList = QListWidget()
        self.pageList.setIconSize(QSize(140, 180))
        self.pageList.setSpacing(10)
        self.pageList.currentRowChanged.connect(self.preview_page)

        leftPanel = QFrame()
        leftPanel.setMinimumWidth(225)
        leftPanel.setMaximumWidth(285)
        leftLayout = QVBoxLayout()
        leftLayout.addWidget(self.openButton)
        leftLayout.addWidget(self.pageList)
        leftPanel.setLayout(leftLayout)

        self.previewLabel = QLabel("Open a PDF, then click a page to preview it.")
        self.previewLabel.setAlignment(Qt.AlignCenter)
        self.previewLabel.setStyleSheet("font-size: 18px; color: #555; padding: 20px;")

        self.previewScroll = QScrollArea()
        self.previewScroll.setWidgetResizable(True)
        self.previewScroll.setAlignment(Qt.AlignCenter)
        self.previewScroll.setWidget(self.previewLabel)

        detailsBox = QGroupBox("Invoice Details")
        detailsBox.setMinimumWidth(260)
        detailsBox.setMaximumWidth(340)

        self.fileLabel = QLabel("No file loaded")
        self.fileLabel.setWordWrap(True)
        self.pageCountLabel = QLabel("0")
        self.currentPageLabel = QLabel("None")
        self.vendorLabel = QLabel("Not detected yet")
        self.invoiceNumberLabel = QLabel("Not detected yet")
        self.invoiceDateLabel = QLabel("Not detected yet")
        self.statusLabel = QLabel("Ready")

        detailsLayout = QGridLayout()
        detailsLayout.addWidget(QLabel("File:"), 0, 0)
        detailsLayout.addWidget(self.fileLabel, 0, 1)
        detailsLayout.addWidget(QLabel("Total Pages:"), 1, 0)
        detailsLayout.addWidget(self.pageCountLabel, 1, 1)
        detailsLayout.addWidget(QLabel("Current Page:"), 2, 0)
        detailsLayout.addWidget(self.currentPageLabel, 2, 1)
        detailsLayout.addWidget(QLabel("Vendor:"), 3, 0)
        detailsLayout.addWidget(self.vendorLabel, 3, 1)
        detailsLayout.addWidget(QLabel("Invoice #:"), 4, 0)
        detailsLayout.addWidget(self.invoiceNumberLabel, 4, 1)
        detailsLayout.addWidget(QLabel("Date:"), 5, 0)
        detailsLayout.addWidget(self.invoiceDateLabel, 5, 1)
        detailsLayout.addWidget(QLabel("Status:"), 6, 0)
        detailsLayout.addWidget(self.statusLabel, 6, 1)
        detailsLayout.setRowStretch(7, 1)
        detailsBox.setLayout(detailsLayout)

        mainLayout = QHBoxLayout()
        mainLayout.addWidget(leftPanel)
        mainLayout.addWidget(self.previewScroll, 1)
        mainLayout.addWidget(detailsBox)

        widget = QWidget()
        widget.setLayout(mainLayout)
        self.setCentralWidget(widget)

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
        self.statusLabel.setText("Generating thumbnails...")
        QApplication.processEvents()

        for page_index in range(self.doc.page_count):
            thumbnail = self.create_page_pixmap(page_index, zoom=0.18)
            item = QListWidgetItem(QIcon(thumbnail), f"Page {page_index + 1}")
            item.setTextAlignment(Qt.AlignCenter)
            item.setSizeHint(QSize(180, 220))
            self.pageList.addItem(item)

        self.fileLabel.setText(filename)
        self.pageCountLabel.setText(str(self.doc.page_count))
        self.currentPageLabel.setText("None")
        self.vendorLabel.setText("Not detected yet")
        self.invoiceNumberLabel.setText("Not detected yet")
        self.invoiceDateLabel.setText("Not detected yet")
        self.statusLabel.setText("PDF loaded")

        if self.doc.page_count > 0:
            self.pageList.setCurrentRow(0)

    def preview_page(self, page_index):
        if self.doc is None or page_index < 0:
            return

        pixmap = self.create_page_pixmap(page_index, zoom=1.5)
        self.previewLabel.setPixmap(pixmap)
        self.previewLabel.adjustSize()

        self.currentPageLabel.setText(f"{page_index + 1} of {self.doc.page_count}")
        self.vendorLabel.setText("Not detected yet")
        self.invoiceNumberLabel.setText("Not detected yet")
        self.invoiceDateLabel.setText("Not detected yet")
        self.statusLabel.setText("Preview ready")

    def create_page_pixmap(self, page_index, zoom):
        page = self.doc.load_page(page_index)
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        image = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format_RGB888,
        )
        return QPixmap.fromImage(image)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
