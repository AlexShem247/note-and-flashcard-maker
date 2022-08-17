import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QIcon
from PyQt5 import uic
import os
import json
import sqlite3
from random import choice

COURSE_COLORS = ["#C0392B", "#3498DB", "#27AE60", "#1ABC9C", "#2980B9",
                 "#8E44AD", "#F1C40F", "#E67E22", "#D35400", "#2ECC71"]


class Window(qt.QMainWindow):
    color = "#FFFFFF"
    pdfPath = None
    topics = []

    def __init__(self, superClass, loadCourses):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/createCourse.ui", self)
        self.superClass = superClass
        self.loadCourses = loadCourses
        self.setWindowIcon(QIcon("images/logo.png"))

        # Get widgets
        nameEdit = self.findChild(qt.QLineEdit, "nameEdit")
        colorBtn = self.findChild(qt.QPushButton, "colorBtn")
        colorLabel = self.findChild(qt.QLabel, "colorLabel")
        pdfBtn = self.findChild(qt.QPushButton, "pdfBtn")
        pathLabel = self.findChild(qt.QLabel, "pathLabel")
        topicEdit = self.findChild(qt.QLineEdit, "topicEdit")
        addTopicBtn = self.findChild(qt.QPushButton, "addTopicBtn")
        topicListWidget = self.findChild(qt.QListWidget, "topicListWidget")
        createCourseBtn = self.findChild(qt.QPushButton, "createCourseBtn")

        # Bind buttons
        colorBtn.clicked.connect(self.selectColor)
        pdfBtn.clicked.connect(self.selectPDF)
        nameEdit.textChanged.connect(self.validateCourse)
        topicEdit.textChanged.connect(self.validateTopic)
        addTopicBtn.clicked.connect(self.addTopic)
        topicListWidget.clicked.connect(self.deleteTopic)
        createCourseBtn.clicked.connect(self.createCourse)

        self.nameEdit.setFocus()

    def closeEvent(self, event):
        """ Run when window gets closed """
        self.superClass.show()

    def selectColor(self):
        """ Opens colour picker window to select colour """
        color = qt.QColorDialog.getColor()  # Opens colour picker window
        if color.isValid():
            self.color = color.name()
            self.colorLabel.setStyleSheet(f"background-color: {self.color};border-style: outset;border-width: "
                                          f"2px;border-radius: 5px;border-color: #303545;")

    def selectPDF(self):
        """ Opens file dialog to select textbox pdf path """
        with open("text/currentSettings.json") as f:
            data = json.load(f)

        fName, _ = qt.QFileDialog.getOpenFileName(self, "Select Document", data["textbookPath"],
                                                  "PDF files (*.pdf)")
        if fName:
            self.pdfPath = fName
        else:
            self.pdfPath = None

        # Show path on screen
        self.pathLabel.setText(os.path.basename(fName))

    def validateTopic(self):
        """ Checks whether topic name is valid """
        name = self.topicEdit.text().lower().strip()
        if name and name not in [topic.lower() for topic in self.topics]:
            self.addTopicBtn.setEnabled(True)
        else:
            self.addTopicBtn.setEnabled(False)

    def addTopic(self):
        """ Adds topic to topic widget"""
        name = self.topicEdit.text()
        self.topicListWidget.addItem(name)
        self.topics.append(name)
        self.topicEdit.clear()
        self.validateCourse()

    def deleteTopic(self):
        """ Confirms whether to delete topic """
        topic = self.topicListWidget.currentItem().text()

        # Show popup message
        msg = qt.QMessageBox()
        msg.setWindowTitle("Are you Sure?")
        msg.setText(f"Are you sure you want to delete '{topic}' ?")
        msg.setIcon(qt.QMessageBox.Question)
        msg.setStandardButtons(qt.QMessageBox.Yes | qt.QMessageBox.No)
        msg.setDefaultButton(qt.QMessageBox.No)
        msg.buttonClicked.connect(self.confirmDelete)
        msg.exec_()

    def confirmDelete(self, i):
        """ Deletes topic """
        option = i.text()[1:]
        topic = self.topicListWidget.currentItem().text()

        if option == "Yes":
            self.topics.remove(topic)

            # Re-add topics
            self.topicListWidget.clear()
            for topic in self.topics:
                self.topicListWidget.addItem(topic)

            self.validateCourse()

    def validateCourse(self):
        """ Checks whether criteria is met before creating course """
        name = self.nameEdit.text()
        courses = [course.lower() for course in os.listdir("data")]

        if name and self.topics and name.lower() not in courses:
            self.createCourseBtn.setEnabled(True)
        else:
            self.createCourseBtn.setEnabled(False)

    def createCourse(self):
        """ Creates files for course """
        coursePath = "data/" + self.nameEdit.text()
        if self.color == "#FFFFFF":
            # Select a random colour
            self.color = choice(COURSE_COLORS).strip()

        data = {
            "name": self.nameEdit.text(),
            "color": self.color,
            "textbookPath": [self.pdfPath, 0, self.pdfPath is not None],
            "dateStudied": [],
            "averageScores": [0],
        }

        # Create files
        os.mkdir(coursePath)
        os.mkdir(coursePath + "/images")
        with open(coursePath + "/courseInfo.json", "w") as f:
            json.dump(data, f, indent=4)

        # Create database
        conn = sqlite3.connect(coursePath + "/courseData.db")
        c = conn.cursor()  # Creates cursor for executing commands
        c.execute("CREATE TABLE topics (topicID integer, topicName text)")
        conn.commit()

        for i, topic in enumerate(self.topics, start=1):
            c.execute(f"INSERT INTO topics (topicID, topicName) VALUES ({i}, '{topic}')")
            conn.commit()

        conn.close()  # Closes connection

        # Close window
        self.superClass.show()
        self.loadCourses()
        self.close()
