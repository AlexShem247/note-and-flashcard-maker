import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt
from PyQt5 import uic
import os

import fitz
from PIL import Image

import modules.create.addTextbook as addTextbook
import modules.create.createNotesNoPDF as createNotesNoPDF
from modules.create.createMethods import CreateWindow


class Window(CreateWindow):
    w = None
    back = True
    pageCounter = 0
    noPages = 1
    doc = None

    def __init__(self, superClass, course, color, textbookPath, sendToNote=False, closeFunction=None):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/createNotes.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.textbookPath = textbookPath
        self.sendToNote = sendToNote
        self.closeFunction = closeFunction
        self.databasePath = "data/" + course + "/courseData.db"
        self.tempPath = f"images/temp/{self.courseName}.png"
        self.updateMenuBar()
        self.initWidgets()
        self.show()

        # Get widgets
        self.courseNameLabel = self.findChild(qt.QLabel, "courseNameLabel")
        self.pdfNameLabel = self.findChild(qt.QLabel, "pdfNameLabel")
        self.pageBox = self.findChild(qt.QSpinBox, "pageBox")
        self.pageLabel = self.findChild(qt.QLabel, "pageLabel")
        self.scrollArea = self.findChild(qt.QScrollArea, "scrollArea")
        self.prevPageBtn = self.findChild(qt.QToolButton, "prevPageBtn")
        self.nextPageBtn = self.findChild(qt.QToolButton, "nextPageBtn")

        self.widget = qt.QWidget()
        self.pdfBox = qt.QVBoxLayout()
        self.widget.setLayout(self.pdfBox)

        self.pdfLabel = qt.QLabel()
        self.pdfLabel.setAlignment(Qt.AlignCenter)
        self.pdfBox.addWidget(self.pdfLabel)

        # Scroll Area Properties
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.widget)

        # Change label text
        self.courseNameLabel.setText(course + " - Create Notes")
        self.pdfNameLabel.setText(os.path.basename(self.textbookPath[0]))

        # Bind buttons
        self.nextPageBtn.clicked.connect(lambda: self.changePage(1))
        self.prevPageBtn.clicked.connect(lambda: self.changePage(-1))
        self.pageBox.valueChanged.connect(self.gotToPage)

        # Show PDF
        self.showPDF()

    def closeEvent(self, event):
        """ Run when window gets closed """
        if self.back:
            self.superClass.show()
            if self.closeFunction:
                self.closeFunction()

    def resizeEvent(self, event):
        """ Run when window gets resized """
        # Resize page
        if self.doc:
            self.updatePage()

    def updateMenuBar(self):
        """ Updates menu bar with course title """
        # Load widgets
        self.courseNameLabel = self.findChild(qt.QLabel, "courseNameLabel")
        self.menuBar = self.findChild(qt.QWidget, "menuBar")
        self.settingsBtn = self.findChild(qt.QPushButton, "settingsBtn")

        # Bind buttons
        self.settingsBtn.clicked.connect(self.addPDF)

        # Add icons
        self.settingsBtn.setIcon(QIcon("images/spanner.png"))

        self.menuBar.setStyleSheet(f"background-color:{self.color};border-style: outset;border-width: 2px;border-radius: "
                              "10px;border-color: #303545;")
        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        courseNameLabel.setText(self.courseName + " - View Notes")
        courseNameLabel.setStyleSheet(f"color:{fontColor};border-width:0px")

    def addPDF(self):
        """ Navigate user to add PDF window """
        self.w = addTextbook.Window(self, self.courseName, self.color, self.textbookPath, self.reDirect, fileNeeded=False)
        self.w.show()
        self.hide()

    def reDirect(self):
        """ Navigates user to no PDF view """
        self.back = False
        self.w = createNotesNoPDF.Window(self.superClass, self.courseName, self.color, self.textbookPath)
        self.w.show()
        self.close()

    def updatePage(self):
        """ Updates page on screen """
        # Load page
        page = self.doc.load_page(self.pageCounter)
        pdfSize = self.prevPageBtn.size().width() * 2 / 596
        pix = page.get_pixmap(matrix=fitz.Matrix(pdfSize, pdfSize))
        pix.save(self.tempPath)

        # Resize image
        img = Image.open(self.tempPath)
        img = img.resize((903, 1277))
        img.save(self.tempPath)

        # Display page
        image = QPixmap(self.tempPath)
        self.pdfLabel.setPixmap(image)
        self.scrollArea.verticalScrollBar().setValue(self.scrollArea.verticalScrollBar().minimum())

    def showPDF(self):
        """ Loads first page of PDF """
        # Load pdf
        self.doc = fitz.open(self.textbookPath[0])
        self.noPages = self.doc.page_count
        minVal = 1 - self.textbookPath[1]
        maxVal = self.noPages - self.textbookPath[1]

        # Set page values
        self.pageBox.setMinimum(minVal)
        self.pageBox.setMaximum(maxVal)
        self.pageBox.setValue(self.pageCounter - self.textbookPath[1] + 1)
        self.pageLabel.setText("out of " + str(maxVal))

        # Create first page
        self.updatePage()

        # Enable next page btn
        if self.noPages > 1:
            self.nextPageBtn.setEnabled(True)

    def changePage(self, delta):
        """ Changes the displayed page of PDF """
        self.pageCounter += delta
        self.pageBox.setValue(self.pageCounter - self.textbookPath[1] + 1)

        # Configure buttons
        self.nextPageBtn.setEnabled(True)
        self.prevPageBtn.setEnabled(True)

        if self.pageCounter >= self.noPages - 1:
            self.nextPageBtn.setEnabled(False)
        if self.pageCounter <= 0:
            self.prevPageBtn.setEnabled(False)

        self.updatePage()

    def gotToPage(self):
        """ Goes to page set by spinbox """
        self.pageCounter = self.pageBox.value() + self.textbookPath[1] - 1

        # Configure buttons
        self.nextPageBtn.setEnabled(True)
        self.prevPageBtn.setEnabled(True)

        if self.pageCounter >= self.noPages - 1:
            self.nextPageBtn.setEnabled(False)
        if self.pageCounter <= 0:
            self.prevPageBtn.setEnabled(False)

        self.updatePage()
