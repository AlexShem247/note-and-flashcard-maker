import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QIcon
from PyQt5 import uic
import sqlite3
from itertools import chain

import modules.learn.learnNotes as learnNotes


class Window(qt.QWidget):
    back = True
    topicList = []
    subtopicList = {}
    currentTopicList = {}
    topicIndex = 0

    def __init__(self, superClass, course, color, textbookPath):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/learnFilter.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.textbookPath = textbookPath
        self.databasePath = "data/" + course + "/courseData.db"
        self.updateMenuBar()

        # Enable multi select
        self.subtopicWidget = self.findChild(qt.QListWidget, "subtopicWidget")
        self.subtopicWidget.setSelectionMode(qt.QAbstractItemView.ExtendedSelection)

        self.loadTopics()
        self.nextTopic()
        self.show()

        # Get widgets
        self.topicCombo = self.findChild(qt.QComboBox, "topicCombo")
        self.leftBtn = self.findChild(qt.QToolButton, "leftBtn")
        self.rightBtn = self.findChild(qt.QToolButton, "rightBtn")
        self.selectAllBtn = self.findChild(qt.QPushButton, "selectAllBtn")
        self.starBox = self.findChild(qt.QCheckBox, "starBox")
        self.weakBox = self.findChild(qt.QCheckBox, "weakBox")
        self.startBtn = self.findChild(qt.QPushButton, "startBtn")
        self.unselectBtn = self.findChild(qt.QPushButton, "unselectBtn")

        # Bind Buttons
        self.leftBtn.clicked.connect(lambda: self.changeTopic(-1))
        self.rightBtn.clicked.connect(lambda: self.changeTopic(1))
        self.topicCombo.currentTextChanged.connect(self.nextTopic)
        self.subtopicWidget.itemClicked.connect(self.subtopicUpdate)
        self.selectAllBtn.clicked.connect(self.resetTopics)
        self.startBtn.clicked.connect(self.startLearning)
        self.unselectBtn.clicked.connect(self.unselectList)

    def unselectList(self):
        """ Unselects all subtopics selected """
        selectedItems = [item.text() for item in self.subtopicWidget.selectedItems()]
        if selectedItems:
            # Unselect list
            self.subtopicWidget.clearSelection()
            self.currentTopicList[self.topicList[self.topicIndex]] = []
            self.unselectBtn.setText("Unselect All Topics")
        else:
            reply = qt.QMessageBox.warning(self, "Are you Sure?", "Are you sure you want to unselect all topics and " +
                                           "subtopics?", qt.QMessageBox.Yes, qt.QMessageBox.No)

            if reply == qt.QMessageBox.Yes:
                for topic in self.currentTopicList:
                    self.currentTopicList[topic] = []

    def startLearning(self):
        """ Opens learn window """
        subtopics = list(chain.from_iterable(self.currentTopicList.values()))
        starred = self.starBox.isChecked()
        focusWeak = self.weakBox.isChecked()

        # Connect to database
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()

        if len(subtopics) == 1:
            # If only one subtopic is selected
            c.execute(f"SELECT subtopicID, subtopicName FROM subtopics")
            result = c.fetchall()
            for record in result:
                if record[1] == subtopics[0]:
                    condition = f"WHERE n.subtopicID = {record[0]}"
                    break

        else:
            # If more than one subtopic is selected
            c.execute(f"SELECT subtopicID FROM subtopics WHERE subtopicName IN {tuple(subtopics)}")
            subtopicIDs = tuple([i[0] for i in c.fetchall()])
            condition = f"WHERE n.subtopicID IN {subtopicIDs}"

        c.execute(f"SELECT type, question, answer, qImageNo, correctCount, practiceCount, starred, subtopicName, "
                  f"topicName, noteID FROM notes n JOIN subtopics s ON n.subtopicID = s.subtopicID JOIN topics t ON "
                  f"s.topicID = t.topicID {condition} ORDER BY userScore "
                  f"ASC, practiceCount DESC, noteID ASC")

        noteList = [{"type": note[0], "question": note[1], "answer": note[2], "qImageNo": note[3],
                          "correctCount": note[4], "practiceCount": note[5], "starred": bool(note[6]),
                          "subtopicName": note[7], "topicName": note[8], "noteID": note[9],
                          "count": 0} for note in c.fetchall()]
        conn.close()

        if starred:
            newNotes = []
            for note in noteList:
                if note["starred"]:
                    newNotes.append(note)
            noteList = newNotes

        if len(noteList) == 0:
            error = qt.QMessageBox.critical(self, "Cannot Learn Notes",
                                            "There are no notes that match selected filters", qt.QMessageBox.Ok)
        else:
            # Send user to learn window
            self.back = False
            self.w = learnNotes.Window(self.superClass, self.courseName, self.color, self.textbookPath, subtopics,
                                       starred, focusWeak)
            self.w.show()
            self.close()

    def resetTopics(self):
        """ Sets current topic list to default value """
        self.currentTopicList = dict(self.subtopicList)
        self.unselectBtn.setText("Unselect")
        self.nextTopic()

    def subtopicUpdate(self):
        """ A subtopic has been added or removed """
        selectedItems = [item.text() for item in self.subtopicWidget.selectedItems()]
        topic = self.topicList[self.topicIndex]
        self.currentTopicList[topic] = [item.text() for item in self.subtopicWidget.selectedItems()]
        if selectedItems:
            self.unselectBtn.setText("Unselect")
        else:
            self.unselectBtn.setText("Unselect All Topics")

    def changeTopic(self, i):
        """ Changes the topic combo value """
        topic = self.topicList[self.topicIndex + i]
        self.leftBtn.setEnabled(self.topicIndex + i > 0)
        self.rightBtn.setEnabled(self.topicIndex + i < len(self.topicList) - 1)
        self.topicCombo.setCurrentText(topic)

    def nextTopic(self):
        """ Insert data into widgets """
        j = self.topicList.index(self.topicCombo.currentText())
        i = j - self.topicIndex

        self.topicIndex += i
        topic = self.topicList[self.topicIndex]

        # Clear Widgets
        self.subtopicWidget.clear()

        # Insert data
        for subtopic in self.subtopicList[topic]:
            item = qt.QListWidgetItem(subtopic)
            self.subtopicWidget.addItem(item)
            item.setSelected(subtopic in self.currentTopicList[topic])

        # Enable buttons
        self.leftBtn.setEnabled(self.topicIndex > 0)
        self.rightBtn.setEnabled(self.topicIndex < len(self.topicList) - 1)

        selectedItems = [item.text() for item in self.subtopicWidget.selectedItems()]
        if selectedItems:
            self.unselectBtn.setText("Unselect")
        else:
            self.unselectBtn.setText("Unselect All Topics")

    def loadTopics(self):
        """ Gets list of topics """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"SELECT topicID, topicName FROM topics")
        topics = c.fetchall()
        self.topicList = [topic[1] for topic in topics]

        for topic in topics:
            c.execute(f"SELECT subtopicName FROM subtopics WHERE topicID = {topic[0]}")
            self.subtopicList[topic[1]] = [subtopic[0] for subtopic in c.fetchall()]
            self.topicCombo.addItem(topic[1])

        self.currentTopicList = dict(self.subtopicList)
        conn.close()


    def closeEvent(self, event):
        """ Run when window gets closed """
        if self.back:
            self.superClass.show()

    def updateMenuBar(self):
        """ Updates menu bar with course title """
        # Load widgets
        self.title = self.findChild(qt.QLabel, "title")
        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        self.title.setStyleSheet(f"background-color:{self.color}; color:{fontColor};border-style:outset;border-width: "
                            f"2px;border-radius:10px;border-color: #303545;")
