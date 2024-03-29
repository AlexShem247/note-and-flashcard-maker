import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QIcon
from PyQt5 import uic
import os
import fitz
import json


class Window(qt.QMainWindow):
    back = True

    def __init__(self, superClass, course, color, textbookPath, reDirect, fileNeeded=True):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/addTextbook.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.textbookPath = textbookPath
        self.reDirect = reDirect
        self.fileNeeded = fileNeeded
        self.change = textbookPath[2]

        # Get widgets
        self.selectBtn = self.findChild(qt.QPushButton, "selectBtn")
        self.pathLabel = self.findChild(qt.QLabel, "pathLabel")
        self.pageBox = self.findChild(qt.QSpinBox, "pageBox")
        self.removeBtn = self.findChild(qt.QPushButton, "removeBtn")
        self.confirmBtn = self.findChild(qt.QPushButton, "confirmBtn")
        self.displayCheck = self.findChild(qt.QCheckBox, "displayCheck")

        # Change label text
        if self.textbookPath[0]:
            self.pathLabel.setText(os.path.basename(self.textbookPath[0]))
            self.enableWidgets()

        # Check checkbox
        self.displayCheck.setChecked(self.textbookPath[2])
        self.pageBox.setValue(self.textbookPath[1] + 1)

        # Bind buttons
        self.selectBtn.clicked.connect(self.selectPDF)
        self.removeBtn.clicked.connect(self.removePDF)
        self.confirmBtn.clicked.connect(self.confirm)

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
        self.textbookPath[2] = False
        self.displayCheck.setChecked(False)
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
        self.textbookPath[2] = self.displayCheck.isChecked()

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
        if self.change != self.textbookPath[2]:
            self.reDirect()
        else:
            self.superClass.show()
        self.close()
