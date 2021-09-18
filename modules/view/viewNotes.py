import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize
from PyQt5 import uic
import os
import sys
import sqlite3
from PIL import Image

sys.path.append("modules")
sys.path.append("modules/create")

import createNotesNoPDF
import createNotes
from modImage import getCentralCoordinates


def title(phrase):
    return " ".join([word.title() if len(word) > 3 else word for word in phrase.split()])


class Window(qt.QMainWindow):
    noteList = []
    isImage = False
    imageList = []
    selectedTopic = None
    starOnly = False
    back = True

    def __init__(self, superClass, course, color, textbookPath, notes=None):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/viewNotes.ui", self)
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.textbookPath = textbookPath
        self.databasePath = "data/" + course + "/courseData.db"
        self.noteID = 1
        self.updateMenuBar()

        # Load Notes
        if notes:
            self.noteList = notes
        else:
            self.loadNotes()

        self.updateNavigation()
        self.show()

        # Get widgets
        editBtn = self.findChild(qt.QPushButton, "editBtn")
        starBtn = self.findChild(qt.QPushButton, "starBtn")
        noteNoLabel = self.findChild(qt.QLabel, "noteNoLabel")
        scoreLabel = self.findChild(qt.QLabel, "scoreLabel")
        leftBtn = self.findChild(qt.QToolButton, "leftBtn")
        rightBtn = self.findChild(qt.QToolButton, "rightBtn")
        noteEdit = self.findChild(qt.QTextEdit, "noteEdit")
        topicLabel = self.findChild(qt.QLabel, "topicLabel")
        subtopicLabel = self.findChild(qt.QLabel, "subtopicLabel")
        diagramLabel = self.findChild(qt.QLabel, "diagramLabel")
        flipBtn = self.findChild(qt.QPushButton, "flipBtn")

        # Set button icons
        editBtn.setIcon(QIcon("images/edit.png"))
        editBtn.setIconSize(QSize(50, 50))
        starBtn.setIcon(QIcon("images/star.png"))
        starBtn.setIconSize(QSize(40, 40))

        # Bind buttons
        leftBtn.clicked.connect(lambda: self.nextNote(-1))
        rightBtn.clicked.connect(lambda: self.nextNote(1))
        flipBtn.clicked.connect(self.flipNote)
        starBtn.clicked.connect(self.starNote)
        editBtn.clicked.connect(self.sendToEdit)

    def sendToEdit(self):
        """ Navigates user to create notes menu """
        if self.textbookPath[0]:
            self.w = createNotes.Window(self, self.courseName, self.color, self.textbookPath,
                                        sendToNote=self.noteID, closeFunction=self.loadNotes)
        else:
            self.w = createNotesNoPDF.Window(self, self.courseName, self.color, self.textbookPath,
                                             sendToNote=self.noteID, closeFunction=self.loadNotes)
        self.w.show()
        self.hide()

    def starNote(self):
        """ Stars note """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"UPDATE notes SET starred = {int(self.starBtn.isChecked())} WHERE noteID = {self.noteID}")
        conn.commit()
        conn.close()
        self.noteList[self.noteID - 1]["starred"] = int(self.starBtn.isChecked())

    def flipNote(self):
        """ Flips note from question to answer or vice versa """
        note = self.noteList[self.noteID - 1]

        if self.flipBtn.text() == " View Answer ":
            # Show answer
            self.flipBtn.setText(" View Question ")

            self.diagramLabel.clear()
            self.noteEdit.clear()

            newText = ""
            for word in note["answer"].split():
                if word[0] == "*" and word[-1] == "*":
                    # Word is bold
                    newText += f"<b>{word[1:-1]}</b> "
                else:
                    # Regular word
                    newText += f"{word} "

            self.noteEdit.insertHtml("<html>" + newText + "<html>")
            self.noteEdit.setAlignment(Qt.AlignLeft)
            self.noteEdit.setStyleSheet("padding-top:10;padding-left:10;padding-right:10;padding-bottom:10;")

        elif self.flipBtn.text() == " View Question ":
            # Show question
            self.flipBtn.setText(" View Answer ")
            self.updateNavigation()

    def loadNotes(self):
        """ Imports notes from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT type, question, answer, qImageNo, subtopicID, correctCount, practiceCount, starred \
        FROM notes ORDER BY noteID")
        self.noteList = [{"type": note[0], "question": note[1], "answer": note[2], "qImageNo": note[3],
                          "subtopicID": note[4], "correctCount": note[5], "practiceCount": note[6],
                          "starred": bool(note[7])} for note in c.fetchall()]
        conn.commit()
        conn.close()

    def updateNavigation(self):
        """ Update buttons and label depending on note index """
        note = self.noteList[self.noteID - 1]
        if note["practiceCount"] == 0:
            score = ""
        else:
            score = f" - {round(100*note['correctCount']/note['practiceCount'])} %"

        # Get topic and subtopic name
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"SELECT subtopicName, topicID FROM subtopics WHERE subtopicID = {note['subtopicID']}")
        subtopicName, topicID = c.fetchone()
        c.execute(f"SELECT topicName FROM topics WHERE topicID = {topicID}")
        topicName = c.fetchone()[0]
        conn.commit()
        conn.close()

        # Insert question
        self.noteEdit.clear()
        self.noteEdit.insertHtml("<html><b>" + title(note["question"]) + "</b><html>")
        self.noteEdit.setAlignment(Qt.AlignCenter)
        self.topicLabel.setText(title(topicName))
        self.subtopicLabel.setText(title(subtopicName))
        self.noteEdit.setStyleSheet("padding-top:30;padding-left:10;padding-right:10;padding-bottom:10;")

        # Add diagram
        if note["qImageNo"] == 0:
            self.isImage = False
            self.diagramLabel.clear()
        else:
            self.isImage = True
            if note["qImageNo"] not in self.imageList:
                self.reshapeImage()
            self.resizeEvent(None)

        # Update labels
        self.noteNoLabel.setText(f"{self.noteID}/{len(self.noteList)}")
        self.scoreLabel.setText(f"Note Score: {note['correctCount']}/{note['practiceCount']}{score}")

        # Update buttons
        self.rightBtn.setEnabled(self.noteID < len(self.noteList))
        self.leftBtn.setEnabled(self.noteID >= 2)
        self.starBtn.setChecked(bool(note["starred"]))

    def nextNote(self, i):
        """ Move to next note """
        self.noteID += i
        self.flipBtn.setText(" View Answer ")
        self.updateNavigation()

    def reshapeImage(self):
        """ Reshapes image to best fit """
        note = self.noteList[self.noteID - 1]
        imgPath = f"data/{self.courseName}/images/{note['qImageNo']}.png"
        img = Image.open(imgPath)
        t = 20

        # Find coordinates of main image
        n, s, w, e = getCentralCoordinates(img, t)
        img = img.crop((w, n, e, s))
        img.save(f"images/temp/{note['qImageNo']}.png")
        self.imageList.append(note['qImageNo'])

    def resizeEvent(self, event):
        """ Run when window gets resized """
        # Resize image
        if self.isImage:
            note = self.noteList[self.noteID - 1]
            pixmap = QPixmap(f"images/temp/{note['qImageNo']}.png")
            h = self.height()//2.5
            if h < pixmap.height():
                pixmap = pixmap.scaledToHeight(self.height()//2.5)

            self.diagramLabel.setScaledContents(True)
            self.diagramLabel.setPixmap(pixmap)

    def keyPressEvent(self, event):
        """ Bind keys to note movement """
        if event.key() == Qt.Key_A and self.leftBtn.isEnabled():
            self.nextNote(-1)
        elif event.key() == Qt.Key_D and self.rightBtn.isEnabled():
            self.nextNote(1)
        elif event.key() == Qt.Key_W or event.key() == Qt.Key_S:
            self.flipNote()

    def closeEvent(self, event):
        """ Run when window gets closed """
        if self.back:
            files = [f"images/temp/{file}" for file in os.listdir("images/temp")]
            for file in files:
                os.remove(file)
            self.superClass.show()

    def updateMenuBar(self):
        """ Updates menu bar with course title """
        # Load widgets
        courseNameLabel = self.findChild(qt.QLabel, "courseNameLabel")
        menuBar = self.findChild(qt.QWidget, "menuBar")
        optionsBtn = self.findChild(qt.QPushButton, "optionsBtn")

        # Add icons
        optionsBtn.setIcon(QIcon("images/options.png"))
        optionsBtn.clicked.connect(self.showOptions)

        menuBar.setStyleSheet(f"background-color:{self.color}")
        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        courseNameLabel.setText(self.courseName + " - View Notes")
        courseNameLabel.setStyleSheet(f"color:{fontColor}")

    def showOptions(self):
        """ Opens filter menu """
        self.w = Widget(self.databasePath, self.selectedTopic, self.starOnly, self.filterOptions)
        self.w.show()

    def filterOptions(self, selectedTopic, starOnly):
        """ Gets notes based on arguments """
        # Apply filter on notes
        self.loadNotes()

        if selectedTopic:
            # Get subtopic ids
            conn = sqlite3.connect(self.databasePath)
            c = conn.cursor()
            c.execute(f"SELECT topicID FROM topics WHERE topicName = '{selectedTopic}'")
            topicID = c.fetchone()[0]
            c.execute(f"SELECT subtopicID FROM subtopics WHERE topicID = {topicID}")
            subtopicList = [subtopic[0] for subtopic in c.fetchall()]
            conn.close()

            for note in self.noteList.copy():
                if note["subtopicID"] not in subtopicList:
                    self.noteList.remove(note)


        if starOnly:
            for note in self.noteList.copy():
                if not note["starred"]:
                    self.noteList.remove(note)

        if self.noteList:
            self.back = False
            self.close()
            self.__init__(self.superClass, self.courseName, self.color, self.textbookPath, notes=self.noteList)
            self.back = True
            self.selectedTopic = selectedTopic
            self.starOnly = starOnly

        else:
            # No notes to display
            error = qt.QMessageBox.critical(self, "Cannot View Notes",
                                            "There are no notes that match the selected filters", qt.QMessageBox.Ok)



class Widget(qt.QWidget):

    def __init__(self, databasePath, selectedTopic, starOnly, filterOptions):
        """ Main Window """
        super(Widget, self).__init__()
        uic.loadUi("gui/modifyViewNotes.ui", self)
        self.databasePath = databasePath
        self.selectedTopic = selectedTopic
        self.starOnly = starOnly
        self.filterOptions = filterOptions

        # Get widgets
        topicCombo = self.findChild(qt.QComboBox, "topicCombo")
        starBox = self.findChild(qt.QCheckBox, "starBox")
        okBtn = self.findChild(qt.QPushButton, "okBtn")
        cancelBtn = self.findChild(qt.QPushButton, "cancelBtn")

        # Bind buttons
        okBtn.clicked.connect(self.applyFilter)
        cancelBtn.clicked.connect(self.close)

        self.fillWidgets()

    def applyFilter(self):
        """ Applies filter for notes """
        self.selectedTopic = self.topicCombo.currentText()
        if self.selectedTopic == "All Topics":
            self.selectedTopic = None

        self.starOnly = self.starBox.isChecked()
        self.filterOptions(self.selectedTopic, self.starOnly)
        self.close()


    def fillWidgets(self):
        """ Gets topic list from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"SELECT topicName FROM topics")
        topicList = [topic[0] for topic in c.fetchall()]
        conn.close()

        self.topicCombo.addItem("All Topics")
        for topic in topicList:
            self.topicCombo.addItem(topic)

        if self.selectedTopic:
            self.topicCombo.setCurrentText(self.selectedTopic)

        self.starBox.setChecked(self.starOnly)
