import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QSize
from PyQt5 import uic
import os
import sys
import sqlite3
from itertools import chain

import learnNotes


class Window(qt.QWidget):
    back = True
    topicList = []
    subtopicList = {}
    currentTopicList = {}
    topicIndex = 0

    def __init__(self, superClass, course, color):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/learnFilter.ui", self)
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.databasePath = "data/" + course + "/courseData.db"
        self.updateMenuBar()

        # Enable multi select
        subtopicWidget = self.findChild(qt.QListWidget, "subtopicWidget")
        subtopicWidget.setSelectionMode(qt.QAbstractItemView.ExtendedSelection)

        self.loadTopics()
        self.nextTopic()
        self.show()

        # Get widgets
        topicCombo = self.findChild(qt.QComboBox, "topicCombo")
        leftBtn = self.findChild(qt.QToolButton, "leftBtn")
        rightBtn = self.findChild(qt.QToolButton, "rightBtn")
        selectAllBtn = self.findChild(qt.QPushButton, "selectAllBtn")
        starBox = self.findChild(qt.QCheckBox, "starBox")
        weakBox = self.findChild(qt.QCheckBox, "weakBox")
        startBtn = self.findChild(qt.QPushButton, "startBtn")
        unselectBtn = self.findChild(qt.QPushButton, "unselectBtn")

        # Bind Buttons
        leftBtn.clicked.connect(lambda: self.changeTopic(-1))
        rightBtn.clicked.connect(lambda: self.changeTopic(1))
        topicCombo.currentTextChanged.connect(self.nextTopic)
        subtopicWidget.itemClicked.connect(self.subtopicUpdate)
        selectAllBtn.clicked.connect(self.resetTopics)
        startBtn.clicked.connect(self.startLearning)
        unselectBtn.clicked.connect(self.unselectList)

    def unselectList(self):
        """ Unselects all subtopics selected """
        self.subtopicWidget.clearSelection()
        self.currentTopicList[self.topicList[self.topicIndex]] = []

    def startLearning(self):
        """ Opens learn window """
        subtopics = list(chain.from_iterable(self.currentTopicList.values()))
        starred = self.starBox.isChecked()
        focusWeak = self.weakBox.isChecked()
        self.back = False

        # Send user to learn window
        self.w = learnNotes.Window(self.superClass, self.courseName, self.color, subtopics, starred, focusWeak)
        self.w.show()
        self.close()

    def resetTopics(self):
        """ Sets current topic list to default value """
        self.currentTopicList = dict(self.subtopicList)
        self.nextTopic()

    def subtopicUpdate(self):
        """ A subtopic has been added or removed """
        topic = self.topicList[self.topicIndex]
        self.currentTopicList[topic] = [item.text() for item in self.subtopicWidget.selectedItems()]

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
        title = self.findChild(qt.QLabel, "title")
        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        title.setStyleSheet(f"background-color:{self.color}; color:{fontColor}")



