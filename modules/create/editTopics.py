import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QIcon
from PyQt5 import uic
import sqlite3


class Window(qt.QMainWindow):
    back = True

    def __init__(self, superClass, databasePath, fillComboBoxes):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/editTopics.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.databasePath = databasePath
        self.fillComboBoxes = fillComboBoxes

        # Get widgets
        topicNameEdit = self.findChild(qt.QLineEdit, "topicNameEdit")
        addTopicBtn = self.findChild(qt.QPushButton, "addTopicBtn")
        topicListWidget = self.findChild(qt.QListWidget, "topicListWidget")
        backBtn = self.findChild(qt.QPushButton, "backBtn")

        # Add topics
        self.getTopics()

        # Bind widgets
        backBtn.clicked.connect(self.close)
        topicListWidget.clicked.connect(self.modifyTopic)
        topicNameEdit.textChanged.connect(self.validateTopic)
        addTopicBtn.clicked.connect(self.addTopic)


    def closeEvent(self, event):
        """ Run when window gets closed """
        if self.back:
            self.superClass.show()
        self.fillComboBoxes()

    def getTopics(self):
        """ Get topics from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT topicName FROM topics")
        self.topicList = [topic[0] for topic in c.fetchall()]
        conn.close()

        self.topicListWidget.clear()
        for topic in self.topicList:
            self.topicListWidget.addItem(topic)

    def modifyTopic(self):
        """ Opens widget to modify topic """
        self.back = False
        self.topicName = self.topicListWidget.currentItem().text()
        self.w = Widget(self, self.topicName, self.changeTopicName, self.databasePath, self.allowBack, self.removeTopic)
        self.w.show()
        self.close()

    def allowBack(self, val):
        """ Change value of back """
        self.back = val

    def changeTopicName(self, newName):
        """ Updates database with new values of topic name """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"UPDATE topics SET topicName = '{newName}' WHERE topicName = '{self.topicName}'")
        conn.commit()
        conn.close()
        self.getTopics()

    def removeTopic(self):
        """ Removes topic from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"DELETE from topics WHERE topicName = '{self.topicName}'")
        conn.commit()
        conn.close()
        self.getTopics()

    def validateTopic(self):
        """ Checks whether topic name is valid """
        name = self.topicNameEdit.text().lower().strip()
        if name and name not in [topic.lower() for topic in self.topicList]:
            self.addTopicBtn.setEnabled(True)
        else:
            self.addTopicBtn.setEnabled(False)

    def addTopic(self):
        """ Adds topic to topic widget"""
        name = self.topicNameEdit.text()
        self.topicListWidget.addItem(name)
        self.topicList.append(name)
        self.topicNameEdit.clear()

        # Add topic to database
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT topicID FROM topics ORDER BY topicID DESC")
        i = c.fetchone()
        if i:
            i = i[0] + 1
        else:
            i = 1
        c.execute(f"INSERT INTO topics (topicID, topicName) VALUES ({i}, '{name}')")
        conn.commit()
        conn.close()  # Closes connection


class Widget(qt.QWidget):

    def __init__(self, superClass, topicName, changeTopicName, databasePath, allowBack, removeTopic):
        """ Main Window """
        super(Widget, self).__init__()
        uic.loadUi("gui/modifyTopic.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.topicName = topicName
        self.changeTopicName = changeTopicName
        self.databasePath = databasePath
        self.allowBack = allowBack
        self.removeTopic = removeTopic

        # Get widgets
        topicEdit = self.findChild(qt.QLineEdit, "topicEdit")
        confirmBtn = self.findChild(qt.QPushButton, "confirmBtn")
        deleteBtn = self.findChild(qt.QPushButton, "deleteBtn")

        topicEdit.setText(topicName)
        topicEdit.textChanged.connect(self.validateTopicName)
        confirmBtn.clicked.connect(self.updateTopicName)
        deleteBtn.clicked.connect(self.deleteTopic)

        self.getTopicList()


    def closeEvent(self, event):
        """ Run when window gets closed """
        self.allowBack(True)
        self.superClass.show()

    def getTopicList(self):
        """ Gets list of topics """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT topicName FROM topics")
        self.topicList = [topic[0].lower() for topic in c.fetchall()]
        conn.close()

    def validateTopicName(self):
        """ Allows confirm button if topic name is valid """
        name = self.topicEdit.text().strip().lower()
        self.confirmBtn.setEnabled(bool(name) and name not in self.topicList)

    def updateTopicName(self):
        """ If line edit is changed, then update database """
        newName = self.topicEdit.text()
        if newName != self.topicName:
            self.changeTopicName(newName)
        self.close()

    def deleteTopic(self):
        """ Confirms whether to delete topic """
        # Show popup message
        msg = qt.QMessageBox()
        msg.setWindowTitle("Are you Sure?")
        msg.setText(f"Are you sure you want to delete '{self.topicName}' ?")
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


