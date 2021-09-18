import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QPen, QBrush
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QCategoryAxis
from PyQt5 import uic
import os
import sys
import sqlite3
import json


class Window(qt.QMainWindow):

    def __init__(self, superClass, course, color):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/courseOptions.ui", self)
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.newColor = color
        self.databasePath = "data/" + course + "/courseData.db"
        self.updateTitleColor()
        self.show()

        # Get widgets
        nameEdit = self.findChild(qt.QLineEdit, "nameEdit")
        colorLabel = self.findChild(qt.QLabel, "colorLabel")
        selectBtn = self.findChild(qt.QPushButton, "selectBtn")
        saveBtn = self.findChild(qt.QPushButton, "saveBtn")
        resetBtn = self.findChild(qt.QPushButton, "resetBtn")
        deleteBtn = self.findChild(qt.QPushButton, "deleteBtn")

        # Insert current data
        nameEdit.setText(self.courseName)
        colorLabel.setStyleSheet(f"background-color:{self.color}; border:2px solid #000000")

        # Bind buttons
        selectBtn.clicked.connect(self.selectColor)
        saveBtn.clicked.connect(self.saveOptions)
        nameEdit.textChanged.connect(self.validateCourse)
        resetBtn.clicked.connect(self.resetProgress)
        deleteBtn.clicked.connect(self.deleteNotes)

    def deleteNotes(self):
        """ Deletes all notes """
        reply = qt.QMessageBox.warning(self, "Are you sure?", "This cannot be undone",
                                       qt.QMessageBox.Yes | qt.QMessageBox.Cancel)

        if reply == qt.QMessageBox.Yes:
            conn = sqlite3.connect(self.databasePath)
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
            notes = c.fetchall()

            if notes:
                c.execute("DELETE FROM notes")

            conn.commit()
            conn.close()


    def resetProgress(self):
        """ Resets progress """
        reply = qt.QMessageBox.warning(self, "Are you sure?", "This cannot be undone",
                                       qt.QMessageBox.Yes | qt.QMessageBox.Cancel)

        if reply == qt.QMessageBox.Yes:
            # Reset progress
            conn = sqlite3.connect(self.databasePath)
            c = conn.cursor()
            c.execute("UPDATE notes SET practiceCount = 0, correctCount = 0, userScore = 0, starred = 0")
            conn.commit()
            conn.close()

            qt.QMessageBox.warning(self, "Changes have been made",
                                   "Application needs to restart to make these changes", qt.QMessageBox.Ok)

    def validateCourse(self):
        """ Disables save button if course name is blank """
        self.saveBtn.setEnabled(bool(self.nameEdit.text().strip()))

    def saveOptions(self):
        """ Makes changes if settings were changed """
        if self.nameEdit.text() != self.courseName or self.newColor != self.color:
            # Changes need to be made
            with open(f"data/{self.courseName}/courseInfo.json") as f:
                content = json.load(f)
                textbookPath = content["textbookPath"]
                visitDates = content["dateStudied"]
                scores = content["averageScores"]

            with open(f"data/{self.courseName}/courseInfo.json", "w") as f:
                data = {
                    "name": self.nameEdit.text(),
                    "color": self.newColor,
                    "textbookPath": textbookPath,
                    "dateStudied": visitDates,
                    "averageScores": scores
                }

                json.dump(data, f, indent=4)

            qt.QMessageBox.warning(self, "Changes have been made",
                                   "Application needs to restart to make these changes", qt.QMessageBox.Ok)

            with open("images/temp/courseNameChange.json", "w") as f:
                json.dump([f"data/{self.courseName}", f"data/{self.nameEdit.text()}"], f,)

            sys.exit(0)

        else:
            self.close()


    def selectColor(self):
        """ Opens colour picker window to select colour """
        color = qt.QColorDialog.getColor()  # Opens colour picker window
        if color.isValid():
            self.newColor = color.name()
            self.colorLabel.setStyleSheet(f"background-color:{self.newColor}; border:1px solid #000000")


    def closeEvent(self, event):
        """ Run when window gets closed """
        self.superClass.show()

    def updateTitleColor(self):
        """ Updates title with course colour """
        titleLabel = self.findChild(qt.QLabel, "titleLabel")

        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        titleLabel.setStyleSheet(f"background-color:{self.color}; color:{fontColor}")
