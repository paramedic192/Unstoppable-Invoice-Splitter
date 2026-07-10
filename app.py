import os
import re
import sys
from datetime import datetime

import fitz
import pytesseract
from PIL import Image

from PySide6.QtCore import QSettings, QSize, Qt
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.doc = None
        self.current_file = None
        self.ocr_cache = {}
        self.settings = QSettings(
            "FM Web Solutions",
            "Unstoppable Invoice Splitter",
        )
        self.last_output_folder = self.settings.value(
            "last_output_folder",
            "",
            type=str,
        )

        self.setWindowTitle("Unstoppable Invoice Splitter")
        self.resize(1500, 900)

        self.openButton = QPushButton("Open PDF")
        self.openButton.clicked.connect(self.open_pdf)

        self.ocrButton = QPushButton("OCR Current Page")
        self.ocrButton.clicked.connect(self.ocr_current_page)
        self.ocrButton.setEnabled(False)

        self.splitButton = QPushButton("Split Each Page")
        self.splitButton.clicked.connect(self.split_each_page)
        self.splitButton.setEnabled(False)

        self.openOutputButton = QPushButton("Open Output Folder")
        self.openOutputButton.clicked.connect(self.open_output_folder)
        self.openOutputButton.setEnabled(
            bool(self.last_output_folder and os.path.isdir(self.last_output_folder))
        )

        self.pageList = QListWidget()
        self.pageList.setIconSize(QSize(140, 180))
        self.pageList.setSpacing(10)
        self.pageList.currentRowChanged.connect(self.preview_page)

        leftPanel = QFrame()
        leftPanel.setMinimumWidth(225)
        leftPanel.setMaximumWidth(285)

        leftLayout = QVBoxLayout()
        leftLayout.addWidget(self.openButton)
        leftLayout.addWidget(self.ocrButton)
        leftLayout.addWidget(self.splitButton)
        leftLayout.addWidget(self.openOutputButton)
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
        detailsBox.setMinimumWidth(320)
        detailsBox.setMaximumWidth(420)

        self.fileLabel = QLabel("No file loaded")
        self.fileLabel.setWordWrap(True)
        self.pageCountLabel = QLabel("0")
        self.currentPageLabel = QLabel("None")
        self.vendorLabel = QLabel("Not detected yet")
        self.invoiceNumberLabel = QLabel("Not detected yet")
        self.invoiceDateLabel = QLabel("Not detected yet")
        self.statusLabel = QLabel("Ready")

        self.ocrText = QTextEdit()
        self.ocrText.setReadOnly(True)
        self.ocrText.setPlaceholderText("OCR text will appear here.")

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
        detailsLayout.addWidget(QLabel("OCR Text:"), 7, 0, 1, 2)
        detailsLayout.addWidget(self.ocrText, 8, 0, 1, 2)
        detailsLayout.setRowStretch(8, 1)
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

        if self.doc is not None:
            self.doc.close()

        self.doc = fitz.open(filename)
        self.current_file = filename
        self.ocr_cache = {}
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
        self.ocrText.clear()
        self.statusLabel.setText("PDF loaded")
        self.ocrButton.setEnabled(True)
        self.splitButton.setEnabled(True)

        if self.doc.page_count > 0:
            self.pageList.setCurrentRow(0)

    def preview_page(self, page_index):
        if self.doc is None or page_index < 0:
            return

        pixmap = self.create_page_pixmap(page_index, zoom=1.5)
        self.previewLabel.setPixmap(pixmap)
        self.previewLabel.adjustSize()

        self.currentPageLabel.setText(f"{page_index + 1} of {self.doc.page_count}")

        if page_index in self.ocr_cache:
            self.update_invoice_details(self.ocr_cache[page_index])
            self.statusLabel.setText("OCR loaded from cache")
        else:
            self.vendorLabel.setText("Not detected yet")
            self.invoiceNumberLabel.setText("Not detected yet")
            self.invoiceDateLabel.setText("Not detected yet")
            self.ocrText.clear()
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

    def get_unique_filename(self, folder, filename):
        base_name, extension = os.path.splitext(filename)
        output_path = os.path.join(folder, filename)
        counter = 1

        while os.path.exists(output_path):
            output_path = os.path.join(folder, f"{base_name}_{counter}{extension}")
            counter += 1

        return output_path

    def split_each_page(self):
        if self.doc is None or not self.current_file:
            return

        starting_folder = self.last_output_folder
        if not starting_folder or not os.path.isdir(starting_folder):
            starting_folder = os.path.dirname(self.current_file)

        output_folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Output Folder",
            starting_folder,
        )

        if not output_folder:
            return

        self.last_output_folder = output_folder
        self.settings.setValue("last_output_folder", output_folder)
        self.openOutputButton.setEnabled(True)

        self.statusLabel.setText("Splitting PDF...")
        QApplication.processEvents()

        source_name = os.path.splitext(os.path.basename(self.current_file))[0]
        safe_source_name = re.sub(r"[^A-Za-z0-9_-]+", "_", source_name).strip("_")
        if not safe_source_name:
            safe_source_name = "invoice"

        batch_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for page_index in range(self.doc.page_count):
            new_pdf = fitz.open()
            new_pdf.insert_pdf(
                self.doc,
                from_page=page_index,
                to_page=page_index,
            )

            filename = (
                f"{safe_source_name}_{batch_timestamp}_"
                f"page_{page_index + 1:03}.pdf"
            )
            output_path = self.get_unique_filename(output_folder, filename)

            new_pdf.save(output_path)
            new_pdf.close()

        self.statusLabel.setText(
            f"Done! {self.doc.page_count} pages saved to the remembered folder."
        )

    def open_output_folder(self):
        if not self.last_output_folder or not os.path.isdir(self.last_output_folder):
            self.statusLabel.setText("No output folder is available yet.")
            self.openOutputButton.setEnabled(False)
            return

        try:
            os.startfile(self.last_output_folder)
            self.statusLabel.setText("Output folder opened.")
        except OSError as error:
            self.statusLabel.setText(f"Could not open output folder: {error}")

    def ocr_current_page(self):
        if self.doc is None:
            return

        page_index = self.pageList.currentRow()
        if page_index < 0:
            return

        self.statusLabel.setText("Running OCR...")
        QApplication.processEvents()

        text = self.extract_text_from_page(page_index)
        self.ocr_cache[page_index] = text

        self.update_invoice_details(text)
        self.statusLabel.setText("OCR complete")

    def extract_text_from_page(self, page_index):
        page = self.doc.load_page(page_index)
        matrix = fitz.Matrix(2.5, 2.5)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        text = pytesseract.image_to_string(image)

        return text.strip()

    def update_invoice_details(self, text):
        self.vendorLabel.setText(self.detect_vendor(text))
        self.invoiceNumberLabel.setText(self.detect_invoice_number(text))
        self.invoiceDateLabel.setText(self.detect_invoice_date(text))
        self.ocrText.setPlainText(text[:3000])

    def detect_vendor(self, text):
        upper_text = text.upper()

        if "GORDON" in upper_text or "GFS" in upper_text:
            return "Gordon Food Service"
        if "PECK" in upper_text:
            return "Peck Food Service"
        if "VALLEY" in upper_text and "WHOLESALE" in upper_text:
            return "Valley Wholesale Foods"
        if "RITCHIE" in upper_text:
            return "Ritchie's Food Distribution"

        return "Unknown"

    def detect_invoice_number(self, text):
        patterns = [
            r"Invoice\s*(?:No\.?|Number|#)?\s*[:\-]?\s*([A-Z0-9\-]{5,})",
            r"Inv\s*(?:No\.?|#)?\s*[:\-]?\s*([A-Z0-9\-]{5,})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return "Not detected yet"

    def detect_invoice_date(self, text):
        patterns = [
            r"(?:Invoice\s*)?Date\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return "Not detected yet"


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
