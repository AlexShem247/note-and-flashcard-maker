import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QIcon
from PyQt5 import uic
import sqlite3


class Window(qt.QMainWindow):
    back = True

    def __init__(self, superClass, databasePath, fillComboBoxes):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/editSubtopics.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.databasePath = databasePath
        self.fillComboBoxes = fillComboBoxes

        # Get widgets
        self.subtopicNameEdit = self.findChild(qt.QLineEdit, "subtopicNameEdit")
        self.addSubtopicBtn = self.findChild(qt.QPushButton, "addSubtopicBtn")
        self.subtopicListWidget = self.findChild(qt.QListWidget, "subtopicListWidget")
        self.topicCombo = self.findChild(qt.QComboBox, "topicCombo")
        self.backBtn = self.findChild(qt.QPushButton, "backBtn")

        # Add topics
        self.getTopics()
        self.getSubtopics()

        # Bind widgets
        self.backBtn.clicked.connect(self.close)
        self.subtopicListWidget.clicked.connect(self.modifyTopic)
        self.topicCombo.currentTextChanged.connect(self.getSubtopics)
        self.subtopicNameEdit.textChanged.connect(self.validateTopic)
        self.addSubtopicBtn.clicked.connect(self.addTopic)

    def closeEvent(self, event):
        """ Run when window gets closed """
        if self.back:
            self.superClass.show()
        self.fillComboBoxes()

    def getSubtopics(self):
        """ Get subtopics from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        topic = self.topicCombo.currentText()

        # Get topicID
        c.execute(f"SELECT topicID FROM topics WHERE topicName = '{topic}'")
        j = c.fetchone()[0]

        # Get subtopics
        c.execute(f"SELECT subtopicName FROM subtopics WHERE topicID = '{j}'")
        self.subtopicList = [subtopic[0] for subtopic in c.fetchall()]
        conn.close()

        self.subtopicListWidget.clear()
        for subtopic in self.subtopicList:
            self.subtopicListWidget.addItem(subtopic)

    def getTopics(self):
        """ Get topics from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT topicName FROM topics")
        self.topicList = [topic[0] for topic in c.fetchall()]
        conn.close()

        self.topicCombo.clear()
        for topic in self.topicList:
            self.topicCombo.addItem(topic)

    def modifyTopic(self):
        """ Opens widget to modify topic """
        self.back = False
        self.subtopicName = self.subtopicListWidget.currentItem().text()
        self.w = Widget(self, self.subtopicName, self.changeTopicName, self.databasePath,
                        self.allowBack, self.removeTopic, self.changeSubtopicTopic)
        self.w.show()
        self.close()

    def allowBack(self, val):
        """ Change value of back """
        self.back = val

    def changeTopicName(self, newName):
        """ Updates database with new values of topic name """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"UPDATE subtopics SET subtopicName = '{newName}' WHERE subtopicName = '{self.subtopicName}'")
        conn.commit()
        conn.close()
        self.getSubtopics()

    def changeSubtopicTopic(self, topic):
        """ Updates database with new topic value for subtopic """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()

        # Get topicID
        c.execute(f"SELECT topicID FROM topics WHERE topicName = '{topic}'")
        j = c.fetchone()[0]

        # Update subtopic
        c.execute(f"UPDATE subtopics SET topicID = '{j}' WHERE subtopicName = '{self.subtopicName}'")
        conn.commit()
        conn.close()
        self.getSubtopics()

    def removeTopic(self):
        """ Removes topic from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"DELETE from subtopics WHERE subtopicName = '{self.subtopicName}'")
        conn.commit()
        conn.close()
        self.getSubtopics()

    def validateTopic(self):
        """ Checks whether topic name is valid """
        name = self.subtopicNameEdit.text().lower().strip()
        if name and name not in [subtopic.lower() for subtopic in self.subtopicList]:
            self.addSubtopicBtn.setEnabled(True)
        else:
            self.addSubtopicBtn.setEnabled(False)

    def addTopic(self):
        """ Adds topic to topic widget"""
        name = self.subtopicNameEdit.text()
        topic = self.topicCombo.currentText()
        self.subtopicListWidget.addItem(name)
        self.subtopicList.append(name)
        self.subtopicNameEdit.clear()

        # Add topic to database
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()

        # Get topicID
        c.execute(f"SELECT topicID FROM topics WHERE topicName = '{topic}'")
        j = c.fetchone()[0]

        # Get subtopicID
        c.execute("SELECT subtopicID FROM subtopics ORDER BY subtopicID DESC")
        i = c.fetchone()
        if i:
            i = i[0] + 1
        else:
            i = 1

        # Add Subtopic
        c.execute(f"INSERT INTO subtopics (subtopicID, subtopicName, topicID) VALUES ({i}, '{name}', '{j}')")
        conn.commit()
        conn.close()  # Closes connection


class Widget(qt.QWidget):

    def __init__(self, superClass, subtopicName, changeTopicName, databasePath, allowBack,
                 removeTopic, changeSubtopicTopic):
        """ Main Window """
        super(Widget, self).__init__()
        uic.loadUi("gui/modifySubtopic.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.subtopicName = subtopicName
        self.changeTopicName = changeTopicName
        self.databasePath = databasePath
        self.allowBack = allowBack
        self.removeTopic = removeTopic
        self.changeSubtopicTopic = changeSubtopicTopic

        # Get widgets
        self.subtopicEdit = self.findChild(qt.QLineEdit, "subtopicEdit")
        self.topicCombo = self.findChild(qt.QComboBox, "topicCombo")
        self.confirmBtn = self.findChild(qt.QPushButton, "confirmBtn")
        self.deleteBtn = self.findChild(qt.QPushButton, "deleteBtn")

        self.subtopicEdit.setText(subtopicName)
        self.subtopicEdit.textChanged.connect(self.validateTopicName)
        self.confirmBtn.clicked.connect(self.updateTopicName)
        self.deleteBtn.clicked.connect(self.deleteTopic)

        self.loadTopics()
        self.loadSubtopics()

    def closeEvent(self, event):
        """ Run when window gets closed """
        self.allowBack(True)
        self.superClass.show()

    def validateTopicName(self):
        """ Allows confirm button if topic name is valid """
        name = self.subtopicEdit.text().strip().lower()
        self.confirmBtn.setEnabled(bool(name) and name not in self.subtopicList)

    def loadTopics(self):
        """ Gets topics from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT topicName FROM topics")
        self.topicList = [topic[0] for topic in c.fetchall()]
        for topic in self.topicList:
            self.topicCombo.addItem(topic)

        # Get current topic of subtopic
        c.execute(f"SELECT topicName FROM topics INNER JOIN subtopics ON topics.topicID = subtopics.topicID \
        WHERE subtopicName = '{self.subtopicName}'")
        self.currentTopic = c.fetchone()[0]
        self.topicCombo.setCurrentText(self.currentTopic)
        conn.close()

    def loadSubtopics(self):
        """ Loads existing subtopics """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT subtopicName FROM subtopics")
        self.subtopicList = [topic[0].lower() for topic in c.fetchall()]
        conn.close()

    def updateTopicName(self):
        """ If line edit is changed, then update database """
        newName = self.subtopicEdit.text()
        newTopic = self.topicCombo.currentText()
        if newTopic != self.currentTopic:
            self.changeSubtopicTopic(newTopic)
        if newName != self.subtopicName:
            self.changeTopicName(newName)

        self.close()

    def deleteTopic(self):
        """ Confirms whether to delete topic """
        # Show popup message
        msg = qt.QMessageBox()
        msg.setWindowTitle("Are you Sure?")
        msg.setText(f"Are you sure you want to delete '{self.subtopicName}' ?")
        msg.setIcon(qt.QMessageBox.Question)
        msg.setStandardButtons(qt.QMessageBox.Yes | qt.QMessageBox.No)
        msg.setDefaultButton(qt.QMessageBox.No)
        msg.buttonClicked.connect(self.confirmDelete)
        msg.exec_()

    def confirmDelete(self, i):
        """ Deletes topic """
        option = i.text()[1:]

        if option == "Yes":
            self.removeTopic()
            self.close()
