import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize
from PyQt5 import uic
import os
import sqlite3
import string
import re
from PIL import Image
import matplotlib.pyplot as plt

import modules.create.createNotesNoPDF as createNotesNoPDF
import modules.create.createNotes as createNotes
from modules.modImage import getCentralCoordinates


POWER_SYMBOL = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
                "-": "⁻"}


def title(phrase):
    phrase = " ".join([word.title() if len(word) > 3 and word.upper() != word else word for word in phrase.split()])
    phrase = phrase.replace("`", "'")
    phrase = phrase.replace("'S", "'s")
    try:
        return phrase[0].upper() + phrase[1:]
    except IndexError:
        return phrase


class Window(qt.QMainWindow):
    noteList = []
    isQImage = None
    imageList = []
    selectedTopic = None
    starOnly = False
    back = True
    changeSizeBack = None

    def __init__(self, superClass, course, color, textbookPath, notes=None):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/viewNotes.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
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

        # Get widgets
        self.editBtn = self.findChild(qt.QPushButton, "editBtn")
        self.starBtn = self.findChild(qt.QPushButton, "starBtn")
        self.noteNoLabel = self.findChild(qt.QLabel, "noteNoLabel")
        self.noteNoBox = self.findChild(qt.QSpinBox, "noteNoBox")
        self.scoreLabel = self.findChild(qt.QLabel, "scoreLabel")
        self.leftBtn = self.findChild(qt.QToolButton, "leftBtn")
        self.rightBtn = self.findChild(qt.QToolButton, "rightBtn")
        self.noteEdit = self.findChild(qt.QTextEdit, "noteEdit")
        self.topicLabel = self.findChild(qt.QLabel, "topicLabel")
        self.subtopicLabel = self.findChild(qt.QLabel, "subtopicLabel")
        self.diagramLabel = self.findChild(qt.QLabel, "diagramLabel")
        self.flipBtn = self.findChild(qt.QPushButton, "flipBtn")

        # Set button icons
        self.editBtn.setIcon(QIcon("images/edit.png"))
        self.editBtn.setIconSize(QSize(50, 50))
        self.starBtn.setIcon(QIcon("images/star.png"))
        self.starBtn.setIconSize(QSize(40, 40))

        # Bind buttons
        self.leftBtn.clicked.connect(lambda: self.nextNote(-1))
        self.rightBtn.clicked.connect(lambda: self.nextNote(1))
        self.flipBtn.clicked.connect(self.flipNote)
        self.starBtn.clicked.connect(self.starNote)
        self.editBtn.clicked.connect(self.sendToEdit)
        self.noteNoBox.valueChanged.connect(self.spinboxUpdate)

        # Bind arrows
        self.goLeftAction = qt.QAction("Go left", self)
        self.goLeftAction.setShortcut("left")
        self.goLeftAction.triggered.connect(lambda: self.nextNote(-1))
        self.addAction(self.goLeftAction)

        self.goRightAction = qt.QAction("Go right", self)
        self.goRightAction.setShortcut("right")
        self.goRightAction.triggered.connect(lambda: self.nextNote(1))
        self.addAction(self.goRightAction)

        self.goUpAction = qt.QAction("Go up", self)
        self.goUpAction.setShortcut("up")
        self.goUpAction.triggered.connect(self.flipNote)
        self.addAction(self.goUpAction)

        self.goDownAction = qt.QAction("Go down", self)
        self.goDownAction.setShortcut("down")
        self.goDownAction.triggered.connect(self.flipNote)
        self.addAction(self.goDownAction)

        self.updateNavigation()
        self.show()

    def spinboxUpdate(self):
        """ Runs when spinbox is updated """
        self.nextNote(self.noteNoBox.value() - self.noteID)

    def sendToEdit(self):
        """ Navigates user to create notes menu """
        if self.textbookPath[0]:
            self.w = createNotes.Window(self, self.courseName, self.color, self.textbookPath,
                                        sendToNote=self.noteList[self.noteID-1]["noteID"], closeFunction=self.loadNotes)
        else:
            self.w = createNotesNoPDF.Window(self, self.courseName, self.color, self.textbookPath,
                                             sendToNote=self.noteList[self.noteID-1]["noteID"], closeFunction=self.loadNotes)
        self.w.show()
        self.hide()

    def starNote(self):
        """ Stars note """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"UPDATE notes SET starred = {int(self.starBtn.isChecked())} WHERE noteID = " +
                  f"{self.noteList[self.noteID - 1]['noteID']}")
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
                if word[0] == "*" and word[-1] == "*" and len(word) > 1:
                    # Word is bold
                    newText += f"<b>{word[1:-1]}</b> "
                else:
                    # Regular word
                    newText += f"{word} "

            # Clean text
            newText = newText.replace(" * ", "")
            newText = newText.replace("`", "'")

            # Clean powers
            powers = re.findall(r"\^\-?\d*", newText)
            for power in powers:
                newPower = "".join([POWER_SYMBOL[i] for i in power[1:]])
                newText = newText.replace(power, newPower)

            self.noteEdit.insertHtml("<html>" + newText + "<html>")
            self.noteEdit.setAlignment(Qt.AlignLeft)
            self.noteEdit.setStyleSheet("padding-top:10;padding-left:10;padding-right:10;padding-bottom:10;")

            # Add diagram
            if note["aImageNo"] == 0:
                self.isQImage = None
                self.diagramLabel.clear()
            else:
                self.noteEdit.insertHtml("<html><b>" + title(note["question"]) + "</b><html>")
                self.noteEdit.setAlignment(Qt.AlignCenter)
                self.noteEdit.setStyleSheet("padding-top:30;padding-left:10;padding-right:10;padding-bottom:10;")

                self.isQImage = False
                if note["aImageNo"] not in self.imageList:
                    self.reshapeImage(note["aImageNo"])
                self.resizeEvent(None)

        elif self.flipBtn.text() == " View Question ":
            # Show question
            self.flipBtn.setText(" View Answer ")
            self.updateNavigation()

    def loadNotes(self):
        """ Imports notes from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT type, question, answer, qImageNo, subtopicID, correctCount, practiceCount, starred, noteID, \
        aImageNo FROM notes ORDER BY noteID")
        self.noteList = [{"type": note[0], "question": note[1], "answer": note[2], "qImageNo": note[3],
                          "subtopicID": note[4], "correctCount": note[5], "practiceCount": note[6],
                          "starred": bool(note[7]), "noteID": note[8], "aImageNo": note[9]} for note in c.fetchall()]

        # Generate answer for processes
        for i, note in enumerate(self.noteList):
            if note["type"] == "Process":
                c.execute(f"SELECT processID FROM notes WHERE noteID = {note['noteID']}")
                processID = c.fetchone()[0]
                c.execute(f"SELECT step FROM processes WHERE processID = {processID} ORDER BY stepNo")
                self.noteList[i]["answer"] = "<br>".join([f"{i}. {line}" for i, line in
                                                          enumerate([step[0] for step in c.fetchall()], start=1)])

            elif note["type"] == "Table":
                c.execute(f"SELECT tableID FROM notes WHERE noteID = {note['noteID']}")
                tableID = c.fetchone()[0]
                c.execute(f"SELECT rowNo, colNo, textVal, userFill FROM tableElements WHERE tableID = {tableID} "
                          "ORDER BY rowNo, colNo")
                values = c.fetchall()
                noRows, noCols = values[-1][0] + 1, values[-1][1] + 1

                tableValues = [[{"text": "", "userFill": False} for _ in range(noCols)] for _ in range(noRows)]
                questTableData = [["" for _ in range(noCols)] for _ in range(noRows)]
                ansTableData = [["" for _ in range(noCols)] for _ in range(noRows)]

                for cell in values:
                    a, b = cell[0], cell[1]
                    tableValues[a][b]["text"] = cell[2].replace("`", "'")
                    tableValues[a][b]["userFill"] = cell[3]
                    if not cell[3]:
                        questTableData[a][b] = cell[2].replace("`", "'")
                    ansTableData[a][b] = cell[2].replace("`", "'")

                # Create table image
                for n, table_data in enumerate([questTableData, ansTableData], start=1):
                    fig = plt.figure(dpi=360)
                    ax = fig.add_subplot(1, 1, 1)
                    table = ax.table(cellText=table_data, loc="center", cellLoc="center")
                    for a, row in enumerate(table_data):
                        for b, item in enumerate(row):
                            table[(a, b)].set_linewidth(2)
                    table.set_fontsize(18)
                    table.scale(1, 4)
                    ax.axis("off")

                    fig.canvas.draw()
                    bbox = table.get_window_extent(fig.canvas.get_renderer())
                    bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

                    plt.savefig(f"images/temp/{note['noteID']}-{n}.png", bbox_inches=bbox_inches, dpi=360)
                    plt.close()

                self.noteList[i]["qImageNo"] = f"{note['noteID']}-1"
                self.noteList[i]["aImageNo"] = f"{note['noteID']}-2"

        conn.commit()
        conn.close()

    def determineFormQuest(self):
        """ Determines type of formula and returns question """
        note = self.noteList[self.noteID - 1]
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"SELECT name, symbol, unit, min, max, step FROM formulas f JOIN notes n ON \
        f.formulaID = n.formulaID WHERE noteID = {note['noteID']}")
        formulaVariables = [{"name": term[0], "symbol": term[1], "unit": term[2], "min": term[3], "max": term[4],
                             "step": term[5]} for term in c.fetchall()]
        conn.commit()
        conn.close()

        # Determine if formula is in the form, x=...
        text = note["answer"]
        for index, char in enumerate(note["answer"]):
            if char.lower() not in list(string.ascii_lowercase) + list(string.digits) + ["_", "="]:
                text = text[:index] + " " + text[index + 1:]
        text = text.replace("=", " = ")
        terms = [var for var in text.split() if not var.isnumeric()]
        terms = list(dict.fromkeys(terms))

        sep = terms.index("=")
        lhs, rhs = terms[:sep], terms[sep + 1:]

        # Reorganise formulaVariables
        formulaVariables = [[term for term in formulaVariables if term["symbol"] == var][0] for var in lhs + rhs]

        if len(lhs) == 1:
            # Left hand side only consists of one term
            return "State the Formula for " + \
                   [term for term in formulaVariables if term["symbol"] == lhs[0]][0]["name"].title()
        elif len(rhs) == 1:
            # Right hand side only consists of one term
            return "State the Formula for " + \
                   [term for term in formulaVariables if term["symbol"] == rhs[0]][0]["name"].title()
        else:
            # Equation
            return "State the Equation consisting of<br>" + ", ".join([term["name"].title() for term in
                                                                       formulaVariables[:-1]]) + " and " + \
                   formulaVariables[-1]["name"].title()

    def updateNavigation(self):
        """ Update buttons and label depending on note index """
        note = self.noteList[self.noteID - 1]
        if note["practiceCount"] == 0:
            score = ""
        else:
            score = f" - {round(100 * note['correctCount'] / note['practiceCount'])} %"

        # Get topic and subtopic name
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"SELECT subtopicName, topicID FROM subtopics WHERE subtopicID = {note['subtopicID']}")
        subtopicName, topicID = c.fetchone()
        c.execute(f"SELECT topicName FROM topics WHERE topicID = {topicID}")
        topicName = c.fetchone()[0]
        conn.commit()
        conn.close()

        # Determine what to write as the question
        if note["type"] == "Formula":
            # Determine formula question
            text = self.determineFormQuest()
        else:
            text = title(note["question"])

        # Insert question
        self.noteEdit.clear()
        self.noteEdit.insertHtml("<html><b>" + text + "</b><html>")
        self.noteEdit.setAlignment(Qt.AlignCenter)
        self.topicLabel.setText(title(topicName))
        self.subtopicLabel.setText(title(subtopicName))
        self.noteEdit.setStyleSheet("padding-top:30;padding-left:10;padding-right:10;padding-bottom:10;")

        # Add diagram
        if note["qImageNo"] == 0:
            self.isQImage = None
            self.diagramLabel.clear()
        else:
            self.isQImage = True
            if note["qImageNo"] not in self.imageList:
                self.reshapeImage(note["qImageNo"])
            self.resizeEvent(None)

        # Update labels
        self.noteNoBox.setMinimum(1)
        self.noteNoBox.setMaximum(len(self.noteList))
        self.noteNoBox.setValue(self.noteID)
        self.noteNoLabel.setText(f"/{len(self.noteList)}")
        self.scoreLabel.setText(f"Note Score: {note['correctCount']}/{note['practiceCount']}{score}")

        # Update buttons
        self.rightBtn.setEnabled(self.noteID < len(self.noteList))
        self.leftBtn.setEnabled(self.noteID >= 2)
        self.starBtn.setChecked(bool(note["starred"]))

    def nextNote(self, i):
        """ Move to next note """
        if i < 0 and self.leftBtn.isEnabled() or i > 0 and self.rightBtn.isEnabled():
            self.noteID += i
            self.flipBtn.setText(" View Answer ")
            if self.changeSizeBack and self.noteList[self.noteID-1]["type"] != "Table":
                self.resize(*self.changeSizeBack)
                self.changeSizeBack = None
            self.updateNavigation()

    def reshapeImage(self, path):
        """ Reshapes image to best fit """
        note = self.noteList[self.noteID - 1]
        if note["type"] == "Table":
            imgPath = f"images/temp/{path}.png"
        else:
            imgPath = f"data/{self.courseName}/images/{path}.png"
        img = Image.open(imgPath)
        WIDTH, HEIGHT = 720, 542
        if img.width == WIDTH and img.height == HEIGHT:
            # Standard image
            t = 20

            # Find coordinates of main image
            n, s, w, e = getCentralCoordinates(img, t)
            img = img.crop((w, n, e, s))

        elif img.width > WIDTH or img.height > HEIGHT:
            scale = min([WIDTH/img.width, HEIGHT/img.height])
            img = img.resize((int(img.width*scale), int(img.height*scale)))

        img.save(f"images/temp/{path}.png")
        self.imageList.append(path)

    def resizeEvent(self, event):
        """ Run when window gets resized """
        # Resize image
        if self.isQImage is not None:
            note = self.noteList[self.noteID - 1]
            if self.isQImage:
                path = note['qImageNo']
            else:
                path = note['aImageNo']

            if note["type"] == "Table":
                h = self.height() // (-0.002 * self.height() + 4)
                if h < 270:
                    h = 270
                if self.height() < 700:
                    self.changeSizeBack = (self.width(), self.height())
                    self.resize(self.width(), 700)
            else:
                h = self.height() // 2.5

            pixmap = QPixmap(f"images/temp/{path}.png")

            if h < pixmap.height() or note["type"] == "Table":
                pixmap = pixmap.scaledToHeight(int(h))

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
        self.courseNameLabel = self.findChild(qt.QLabel, "courseNameLabel")
        self.menuBar = self.findChild(qt.QWidget, "menuBar")
        self.optionsBtn = self.findChild(qt.QPushButton, "optionsBtn")

        # Add icons
        self.optionsBtn.setIcon(QIcon("images/options.png"))
        self.optionsBtn.clicked.connect(self.showOptions)

        self.menuBar.setStyleSheet(f"background-color:{self.color};border-style: outset;border-width: 2px;border-radius: "
                              "10px;border-color: #303545;")
        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        self.courseNameLabel.setText(self.courseName + " - View Notes")
        self.courseNameLabel.setStyleSheet(f"color:{fontColor};border-width:0px")

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
        self.topicCombo = self.findChild(qt.QComboBox, "topicCombo")
        self.starBox = self.findChild(qt.QCheckBox, "starBox")
        self.okBtn = self.findChild(qt.QPushButton, "okBtn")
        self.cancelBtn = self.findChild(qt.QPushButton, "cancelBtn")

        # Bind buttons
        self.okBtn.clicked.connect(self.applyFilter)
        self.cancelBtn.clicked.connect(self.close)

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
