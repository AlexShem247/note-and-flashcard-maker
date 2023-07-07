import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QIcon
from PyQt5 import uic

import modules.create.addTextbook as addTextbook
import modules.create.createNotes as createNotes
from modules.create.createMethods import CreateWindow


class Window(CreateWindow):
    w = None
    back = True

    def __init__(self, superClass, course, color, textbookPath, sendToNote=False, closeFunction=None):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/createNotesNoPDF.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.textbookPath = textbookPath
        self.sendToNote = sendToNote
        self.closeFunction = closeFunction
        self.databasePath = "data/" + course + "/courseData.db"
        self.updateMenuBar()
        self.initWidgets()

        # Get widgets
        courseNameLabel = self.findChild(qt.QLabel, "courseNameLabel")
        addPDFBtn = self.findChild(qt.QPushButton, "addPDFBtn")

        # Change label text
        courseNameLabel.setText(course + " - Create Notes")

        # Bind buttons
        addPDFBtn.clicked.connect(self.addPDF)


    def closeEvent(self, event):
        """ Run when window gets closed """
        if self.back:
            self.superClass.show()
            if self.closeFunction:
                self.closeFunction()

    def updateMenuBar(self):
        """ Updates menu bar with course title """
        # Load widgets
        courseNameLabel = self.findChild(qt.QLabel, "courseNameLabel")
        menuBar = self.findChild(qt.QWidget, "menuBar")
        btn1 = self.findChild(qt.QPushButton, "btn1")
        btn2 = self.findChild(qt.QPushButton, "btn2")
        btn3 = self.findChild(qt.QPushButton, "btn3")
        settingsBtn = self.findChild(qt.QPushButton, "settingsBtn")

        # Bind buttons
        settingsBtn.clicked.connect(self.addPDF)

        # Add icons
        settingsBtn.setIcon(QIcon("images/spanner.png"))

        menuBar.setStyleSheet(f"background-color:{self.color};border-style: outset;border-width: 2px;border-radius: "
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
        self.w = addTextbook.Window(self, self.courseName, self.color, self.textbookPath, self.reDirect)
        self.w.show()
        self.hide()

    def reDirect(self):
        """ Navigates user to PDF view """
        self.back = False
        self.w = createNotes.Window(self.superClass, self.courseName, self.color, self.textbookPath)
        self.w.show()
        self.close()
