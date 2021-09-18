import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
from PyQt5 import uic
import os
import sys
import fitz
import json


class Window(qt.QMainWindow):
    back = True

    def __init__(self, superClass, course, color, textbookPath, reDirect, fileNeeded=True):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/addTextbook.ui", self)
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.textbookPath = textbookPath
        self.reDirect = reDirect
        self.fileNeeded = fileNeeded

        # Get widgets
        selectBtn = self.findChild(qt.QPushButton, "selectBtn")
        pathLabel = self.findChild(qt.QLabel, "pathLabel")
        pageBox = self.findChild(qt.QSpinBox, "pageBox")
        removeBtn = self.findChild(qt.QPushButton, "removeBtn")
        confirmBtn = self.findChild(qt.QPushButton, "confirmBtn")

        # Change label text
        if self.textbookPath[0]:
            pathLabel.setText(os.path.basename(self.textbookPath[0]))
            self.enableWidgets()

        pageBox.setValue(self.textbookPath[1] + 1)

        # Bind buttons
        selectBtn.clicked.connect(self.selectPDF)
        removeBtn.clicked.connect(self.removePDF)
        confirmBtn.clicked.connect(self.confirm)

        self.changeTitleColor()

    def changeTitleColor(self):
        """ Changes colour depending on saved preferences """
        menuTitle = self.findChild(qt.QLabel, "menuTitle")
        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        menuTitle.setStyleSheet(f"background-color:{self.color}; color:{fontColor}")

    def closeEvent(self, event):
        """ Run when window gets closed """
        if self.back:
            self.superClass.show()

    def selectPDF(self):
        """ Opens file dialog to select textbox pdf path """
        with open("text/currentSettings.json") as f:
            data = json.load(f)

        fName, _ = qt.QFileDialog.getOpenFileName(self, "Select Document", data["textbookPath"],
                                                  "PDF files (*.pdf)")
        if fName:
            self.textbookPath[0] = fName
        else:
            self.textbookPath[0] = None

        # Show path on screen
        self.pathLabel.setText(os.path.basename(fName))

        # Checks if PDF has been selected and to enable widgets
        self.pageBox.setEnabled(bool(self.textbookPath[0]))
        self.removeBtn.setEnabled(bool(self.textbookPath[0]))

        # Update spinbox
        if self.textbookPath[0]:
            self.enableWidgets()

    def removePDF(self):
        """ Removes selected PDF """
        self.textbookPath[0] = None
        self.pathLabel.setText(None)
        self.pageBox.setValue(1)
        self.pageBox.setEnabled(False)
        self.removeBtn.setEnabled(False)

    def enableWidgets(self):
        """ Enables spinbox and delete button """
        self.pageBox.setEnabled(True)
        self.removeBtn.setEnabled(True)
        doc = fitz.open(self.textbookPath[0])
        maxVal = doc.page_count
        self.pageBox.setMaximum(maxVal)

    def confirm(self):
        """ Updates JSON file with PDF value """
        self.textbookPath[1] = self.pageBox.value() - 1

        with open("data/" + self.courseName + "/courseInfo.json") as f:
            content = json.load(f)
            color = content["color"]
            visitDates = content["dateStudied"]
            scores = content["averageScores"]

        # Update json
        with open("data/" + self.courseName + "/courseInfo.json", "w") as f:
            data = {
                "name": self.courseName,
                "color": color,
                "textbookPath": self.textbookPath,
                "dateStudied": visitDates,
                "averageScores": scores
            }

            json.dump(data, f, indent=4)

        # Close window
        self.back = False
        if (self.textbookPath[0] and self.fileNeeded) or (not self.textbookPath[0] and not self.fileNeeded):
            self.reDirect()
        else:
            self.superClass.show()
        self.close()
