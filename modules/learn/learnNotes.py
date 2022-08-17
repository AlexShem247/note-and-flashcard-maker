import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtMultimedia import QSound
from PyQt5 import uic
import os
import sys
import sqlite3
import json
import random
import enchant
import collections
from time import sleep, time
from PIL import Image
import string
from difflib import SequenceMatcher
import math
import pyttsx3
import sympy
import decimal
import re
import subprocess
from math import *

sys.path.append("modules")
sys.path.append("modules/create")

import createNotesNoPDF
import createNotes
import paint
from modImage import getCentralCoordinates
import showScore
import showSummary

# Define constants
PUNCTUATION = ["!", "#", "$", "%", "&", "(", ")", "+", ",", "^", ".", "/", ":", ";", "=", "?", "@", "[", "\\", "]",
               "{", "|", "}", "~"]

POWER_SYMBOL = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
                "-": "⁻"}

window = None
# Initialise Text-to-speech engine
engine = pyttsx3.init()


def deleteItemsOfLayout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            else:
                deleteItemsOfLayout(item.layout())


def similar(a, b, r=0.8):
    """ Returns whether two words are at least 80% similar to each other """
    a = a.lower().replace(" ", "").replace("<br>", "").translate(str.maketrans("", "", string.punctuation))
    b = b.lower().replace(" ", "").replace("<br>", "").translate(str.maketrans("", "", string.punctuation))
    return SequenceMatcher(None, a, b).ratio() > r


def title(phrase):
    phrase = " ".join([word.title() if len(word) > 3 and word.upper() != word else word for word in phrase.split()])
    phrase = phrase.replace("`", "'")
    phrase = phrase.replace("'S", "'s")
    phrase = phrase[0].upper() + phrase[1:]
    return phrase


def roundTo3Sf(num):
    """ Round the number of significant figures """
    if type(num) == int or num.is_integer():
        return int(round(num, -(len(str(int(num))) - 3)))
    else:
        i = str(num).index(".")
        l, r = str(num)[:i], str(num)[i + 1:]

        if l == "0":
            l = ""

        if len(l) >= 3:
            return int(round(num, -(len(l) - 3)))
        else:
            return round(num, 3 - len(l))


def drange(x, y, jump):
    x = decimal.Decimal(str(x))
    y += jump / 2
    while x < y:
        yield float(x)
        x += decimal.Decimal(str(jump))


class ReadThread(QThread):
    """ Reads question answers """

    def run(self):
        global window
        text = window.currentNote["question"]
        engine.say(text)

        try:
            engine.runAndWait()
        except RuntimeError:
            pass


class DefinitionThread(QThread):
    """ Reveals Answer for few seconds thread """

    change_value = pyqtSignal(int)  # Create signal object

    def run(self):
        global window
        duration = window.numOfSec
        for i in reversed(range(duration)):
            self.change_value.emit(i + 1)
            sleep(1)
        self.change_value.emit(0)


class FactThread(QThread):
    """ Fill in the blanks thread """

    change_value = pyqtSignal(str)  # Create signal object

    def run(self):
        global window

        for _ in range(len(window.missingWords)):
            blankWord = window.currentMissingWord
            currentBlankWord = blankWord
            text = window.answerText

            if not blankWord:
                break
            else:
                i = blankWord["index"]

            j = 0
            fillWord = window.answerText[i]
            colors = ["#000000", "#FFFFFF"]

            while True:
                try:
                    k = text[i].index("_")
                except ValueError:
                    k = len(text[i])

                html = " ".join(window.answerText[:i]) + \
                       f" {text[i][:k]}<span style=\" color:{colors[j]};\" >|</span>{text[i][k + 1:]} " + \
                       " ".join(window.answerText[i + 1:])

                self.change_value.emit(html)
                for x in range(50):
                    sleep(0.01)

                    try:
                        if fillWord != window.answerText[i]:
                            fillWord = window.answerText[i]
                            break
                    except Exception:
                        break

                # Change colour
                j += 1
                if j > 1:   j = 0

                if window.breakThread:
                    break

                if not window.answerText:
                    break

                if currentBlankWord != window.currentMissingWord:
                    html = " ".join(window.answerText[:])
                    self.change_value.emit(html)
                    break


class Window(qt.QMainWindow):
    noteList = []
    missingWords = []
    blankWords = []
    prevWord = []
    calcFormulaList = []
    fillProcessList = []
    correctStepOrder = ()

    currentNote = None
    currentMissingWord = None
    thread = None
    noteUpdateNeeded = None
    numOfSec = None
    answerText = [None]

    back = True
    isImage = False
    activateKeyPress = False
    breakThread = False
    allowNextNote = False
    readQuestion = False
    activateTableThread = False

    def __init__(self, superClass, course, color, textbookPath, subtopics, starred, focusWeak):
        """ Main Window """
        global window
        super(Window, self).__init__()
        uic.loadUi("gui/learnNotes.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.textbookPath = textbookPath
        self.databasePath = "data/" + course + "/courseData.db"
        self.subtopics = subtopics
        self.starred = starred
        self.focusWeak = focusWeak
        self.noteList = []
        self.notesCompleted = 0
        self.totalNotesCompleted = 0
        self.correctCounter = 0
        self.incorrectCounter = 0
        self.timeStarted = time()
        self.factCorrect = 0
        self.defCorrect = 0
        self.formCorrect = 0
        self.processCorrect = 0
        self.diagramCorrect = 0
        self.tableCorrect = 0
        self.scorePerTopic = {}
        self.spellCheck = enchant.Dict("en_UK")

        # Define variables
        window = self
        self.resetValues()
        self.ding = QSound("audio/ding.wav")

        with open("text/currentSettings.json") as f:
            data = json.load(f)

        self.MAX_NOTES = data["maxNotes"]
        self.SWAP_NOTES = data["nNotes"]
        self.MAX_TYPOS = data["typoLimit"]

        self.updateMenuBar()
        self.show()
        self.loadNotes()

        # Bind arrows
        self.ReturnAction = qt.QAction("Go Return", self)
        self.ReturnAction.setShortcut("return")
        self.ReturnAction.triggered.connect(self.showNextNote)

        # Get widgets
        noteBox = self.findChild(qt.QVBoxLayout, "noteBox")
        topicLabel = self.findChild(qt.QLabel, "topicLabel")
        subtopicLabel = self.findChild(qt.QLabel, "subtopicLabel")
        questionEdit = self.findChild(qt.QTextEdit, "questionEdit")
        diagramLabel = self.findChild(qt.QLabel, "diagramLabel")
        answerEdit = self.findChild(qt.QTextEdit, "answerEdit")
        buttonLayout = self.findChild(qt.QHBoxLayout, "buttonLayout")
        finishBtn = self.findChild(qt.QPushButton, "finishBtn")
        audioBtn = self.findChild(qt.QPushButton, "audioBtn")
        audioBtn.setIcon(QIcon("images/no_audio.png"))
        audioBtn.setIconSize(QSize(35, 35))

        # Create widgets
        self.stepListWidget = qt.QListWidget()  # Create List Widget
        self.stepListWidget.setFont(QFont("Neue Haas Grotesk Text Pro", 14))
        self.stepListWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.tableWidget = qt.QTableWidget()  # Create Table Widget
        self.tableWidget.setFont(QFont("Neue Haas Grotesk Text Pro", 14))
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(qt.QHeaderView.ResizeToContents)

        self.diagramLayout = qt.QHBoxLayout()  # Create horizontal layout
        self.drawnImage = qt.QLabel(self)
        self.correctImage = qt.QLabel(self)

        # Create fonts
        self.boldFont = QFont("Neue Haas Grotesk Text Pro")
        self.boldFont.setBold(True)

        # Bind Buttons
        finishBtn.clicked.connect(self.finishStudying)
        finishBtn.setFocusPolicy(Qt.NoFocus)
        audioBtn.clicked.connect(self.toggleAudio)
        audioBtn.setFocusPolicy(Qt.NoFocus)
        self.stepListWidget.itemChanged.connect(self.stepListModified)
        self.stepListWidget.currentItemChanged.connect(self.showProcessStep)

        self.showNextNote()

    def tableChanged(self):
        if self.activateTableThread:
            if self.tableHasCorrectAnswers():
                self.revealTableAnswer()

    def toggleAudio(self):
        """ Changes whether audio is read during a question """
        self.readQuestion = not self.readQuestion
        self.audioBtn.setIcon(QIcon(["images/no_audio.png", "images/audio.png"][int(self.readQuestion)]))
        self.audioBtn.setIconSize(QSize(35, 35))
        if self.readQuestion:
            self.readThread.start()

    def areTextsSimilar(self, inputAns, correctAns):
        """ Uses spell checker to check whether the texts are similar"""
        ratio = math.exp(-0.05 * self.MAX_TYPOS)
        d = 5

        # Clean text
        inputAns = inputAns.lower().replace(" ", "").replace("<br>", "")
        inputAns = inputAns.translate(str.maketrans("", "", string.punctuation))
        correctAns = correctAns.lower().replace(" ", "").replace("<br>", "")
        correctAns = correctAns.translate(str.maketrans("", "", string.punctuation))

        return similar(inputAns, correctAns, r=ratio) and len(correctAns) - d <= len(inputAns) <= len(correctAns) + d

    def updateWordDatabase(self):
        """ Adds synonyms to word database """
        # Connect to database
        conn = sqlite3.connect("text/words.db")
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS words (wordID int, word text)")
        c.execute("CREATE TABLE IF NOT EXISTS synonyms (word1 int, word2 int)")
        self.noteUpdateNeeded = True

        conn2 = sqlite3.connect(self.databasePath)
        c2 = conn2.cursor()

        # Ask user for words
        for pair in self.blankWords:
            word1, word2 = pair
            dicUpdate = True

            if not self.spellCheck.check(word1):
                # Word is incorrectly spelt when creating the note
                reply = qt.QMessageBox.question(self, "Spelling mistake?",
                                                f"The word '{word1}' seems to be incorrectly spelt.\n\nShould it be " +
                                                f"replaced with '{word2}' in the future?",
                                                qt.QMessageBox.Yes, qt.QMessageBox.No)

                if reply == qt.QMessageBox.Yes:
                    # Update note answer
                    noteID, answer = self.currentNote["noteID"], self.currentNote["answer"]
                    for word in answer.split():
                        if word.lower() == word1:
                            # When it finds the right word
                            if word == word1.title():
                                # Title case word
                                answer = answer.replace(word, word2.title())
                            elif word == word1.upper():
                                # Upper case word
                                answer = answer.replace(word, word2.upper())
                            else:
                                # Lower case word
                                answer = answer.replace(word, word2.lower())

                    c2.execute(f"UPDATE notes SET answer = '{answer}' WHERE noteID = {noteID}")
                    dicUpdate = False

            if dicUpdate:
                reply = qt.QMessageBox.question(self, "Update Personal Database",
                                                f"Should the word '{word2}' be allowed to be used " +
                                                f"in place of '{word1}'?", qt.QMessageBox.Yes, qt.QMessageBox.No)

                c.execute(f"SELECT wordID FROM words WHERE word = '{word1}'")
                i = c.fetchone()
                if i: i = i[0]

                c.execute(f"SELECT wordID FROM words WHERE word = '{word2}'")
                j = c.fetchone()
                if j: j = j[0]

                if i and j and reply == qt.QMessageBox.No:
                    c.execute(f"DELETE FROM  synonyms WHERE word1 IN ({i}, {j}) AND word2 IN ({i}, {j})")
                    self.noteUpdateNeeded = False
                    self.correctCounter -= 1
                    self.incorrectCounter += 1

                elif reply == qt.QMessageBox.Yes:
                    # Get word IDs
                    ids = []
                    for word in [word1, word2]:
                        c.execute(f"SELECT wordID from words WHERE word = '{word}'")
                        i = c.fetchone()
                        if i:
                            # If word is already in table
                            i = i[0]
                        else:
                            c.execute("SELECT wordID from words ORDER BY wordID DESC")
                            i = c.fetchone()
                            if i:
                                # If word is not in table
                                i = i[0] + 1
                            else:
                                # If not words are in table
                                i = 1
                            c.execute(f"INSERT INTO words (wordID, word) VALUES ({i}, '{word}')")
                        ids.append(i)

                    # Save word pair into table
                    i, j = ids
                    c.execute(f"INSERT INTO synonyms (word1, word2) VALUES ({i}, {j})")
                self.correctCounter += 1
                self.incorrectCounter -= 1

        conn.commit()
        conn.close()
        conn2.commit()
        conn2.close()

        self.showNextNote()

    def resetValues(self):
        """ Resets values """
        self.missingWords = []
        self.prevWord = []
        self.blankWords = []

        self.currentNote = None
        self.currentMissingWord = None
        self.answerText = None
        self.noteUpdateNeeded = None
        self.numOfSec = None

        self.isImage = False
        self.activateKeyPress = False
        self.breakThread = False
        self.allowNextNote = False

        self.readThread = ReadThread()

        self.factThread = FactThread()  # Create thread
        self.factThread.change_value.connect(self.setAnswerText)  # Connect thread to function

        self.defThread = DefinitionThread()  # Create thread
        self.defThread.change_value.connect(self.updateTimer)  # Connect thread to function

    def finishStudying(self):
        """ Shows summary """
        if self.noteUpdateNeeded is not None:
            self.updateAns(self.noteUpdateNeeded)

        self.back = False
        self.w = showSummary.Window(self.superClass, self.courseName, self.color, self.factCorrect, self.defCorrect,
                                    self.formCorrect, self.processCorrect, self.diagramCorrect, self.tableCorrect,
                                    len(self.noteList), time() - self.timeStarted, self.correctCounter,
                                    self.incorrectCounter, self.scorePerTopic)
        self.w.show()
        self.close()

    def setAnswerText(self, val):
        """ Run by thread """
        v = self.answerEdit.verticalScrollBar().value()
        self.answerEdit.clear()
        self.answerEdit.append(val)  # Set text to text edit
        self.answerEdit.verticalScrollBar().setValue(v)

    def updateAns(self, correct):
        """ Run when user correctly answered note """
        note = self.currentNote
        noteID, noCorrect, noPractised = note["noteID"], note["correctCount"], note["practiceCount"]

        try:
            score = note["correctCount"] / note["practiceCount"]
        except ZeroDivisionError:
            score = 1.0

        noPractised += 1
        twoPartQuestions = ["Formula", "Process"]
        answeredFirstPart = self.calcFormulaList + self.fillProcessList
        if correct and ((note["type"] not in twoPartQuestions) or
                        (note["type"] in twoPartQuestions and note in answeredFirstPart)):
            noCorrect += 1
            self.correctCounter += 1
            note["count"] += 1
            if note["count"] < 2 and note["correctCount"] < 10 and score < 0.7:
                # Relearn note
                if len(self.noteList) < 5:
                    self.noteList.append(note)
                else:
                    self.noteList.insert(4, note)
            else:
                self.correctCounter += 1
                self.notesCompleted += 1
                self.totalNotesCompleted += 1
                self.scorePerTopic[note["topicName"]] += 1
                if note["type"] == "Fact":
                    self.factCorrect += 1
                elif note["type"] == "Definition":
                    self.defCorrect += 1
                elif note["type"] == "Formula":
                    self.formCorrect += 1
                elif note["type"] == "Process":
                    self.processCorrect += 1
                elif note["type"] == "Diagram":
                    self.diagramCorrect += 1
                elif note["type"] == "Table":
                    self.tableCorrect += 1
        else:
            if note not in self.calcFormulaList and note["type"] == "Formula":
                self.calcFormulaList.append(note)
                noPractised -= 1

            if note not in self.fillProcessList and note["type"] == "Process":
                self.fillProcessList.append(note)
                noPractised -= 1

            note["count"] = 0

            if len(self.noteList) < 2:
                self.noteList.append(note)
            else:
                self.noteList.insert(1, note)

        try:
            score = round(noCorrect / noPractised, 2)
        except ZeroDivisionError:
            score = 1.0

        # Update database
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"UPDATE notes SET correctCount = {noCorrect}, practiceCount = {noPractised}, \
                            userScore = {score} WHERE noteID = {noteID}")
        conn.commit()
        conn.close()

        self.noteUpdateNeeded = None

    def keyPressEvent(self, e):
        """ Runs when user presses key """
        if self.activateKeyPress:
            note = self.currentNote
            i = self.missingWords[0]["index"]
            ans = self.missingWords[0]["word"].lower()
            correct = True

            if not self.prevWord:
                self.prevWord = [self.answerText[i]]

            try:
                j = self.answerText[i].index("_")
            except ValueError:
                j = len(self.answerText[i])

            # Return what key is pressed
            try:
                char = chr(e.key())
                if char.isalpha():
                    char = char.lower()

                self.answerText[i] = self.answerText[i][:j] + char + self.answerText[i][j + 1:]
                self.prevWord.append(self.answerText[i])

            except Exception:
                if e == "return" or e.key() == Qt.Key_Return:
                    correct = False
                    enteredAnswer = self.answerText[i].replace("_", "").replace("'", "`")
                    # Check if entered word is similar
                    for word in [ans] + self.missingWords[0]["validWords"]:
                        if similar(enteredAnswer, word):
                            self.answerText[i] = word
                            correct = True
                            break

                    if not correct:
                        # Incorrect
                        uAns = ans.replace("`", "'")
                        self.answerText[i] = self.answerText[i].replace("_", "") + "❌" + f" ({uAns})"
                        self.incorrectCounter += 1
                        correct = False

                elif e.key() == Qt.Key_Backspace and len(self.prevWord) > 1:
                    del self.prevWord[-1]
                    self.answerText[i] = self.prevWord[-1]

            enteredAnswer = self.answerText[i].replace("_", "").replace("'", "`").lower()
            if self.currentNote["type"] == "Formula":
                # Check if answer is numerically correct
                try:
                    if roundTo3Sf(float(enteredAnswer)) == roundTo3Sf(float(ans)):
                        enteredAnswer = ans
                except Exception:
                    pass

            if enteredAnswer == ans or enteredAnswer in self.missingWords[0]["validWords"] or not correct or \
                    enteredAnswer.replace("`", "") == ans.replace("`", ""):
                # Word has been filled in
                correctAnswer = self.missingWords[0]
                if "❌" in enteredAnswer:
                    k = enteredAnswer.index("❌")
                    enteredAnswer = enteredAnswer[:k]
                else:
                    self.correctCounter += 1

                if enteredAnswer and correctAnswer["word"].lower() != enteredAnswer and \
                        correctAnswer["word"].lower() != enteredAnswer + "s":
                    self.blankWords.append((correctAnswer["word"].lower(), enteredAnswer))
                self.prevWord = []

                # Correct displayed word
                if correct:
                    self.answerText[i] = ans.replace("`", "'")

                self.missingWords.pop(0)
                if self.missingWords:
                    # Next word
                    self.currentMissingWord = self.missingWords[0]
                else:
                    # All words have been filled in
                    self.answerEdit.setText(" ".join(self.answerText))
                    self.activateKeyPress = False
                    self.allowNextNote = True

                    # Update database
                    fullCorrect = "❌" not in "".join(self.answerText)
                    self.noteUpdateNeeded = fullCorrect

                    # Clear button layout
                    for i in reversed(range(self.buttonLayout.count())):
                        self.buttonLayout.itemAt(i).widget().setParent(None)

                    # Add buttons
                    proceedBtn = qt.QPushButton(self, text=" Next Note ")
                    proceedBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
                    proceedBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                             "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
                    proceedBtn.setMaximumWidth(300)
                    proceedBtn.clicked.connect(self.showNextNote)
                    self.buttonLayout.addWidget(proceedBtn)

                    if self.blankWords:
                        objectBtn = qt.QPushButton(self, text=" Incorrect Marking ")
                        objectBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
                        objectBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                                "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
                        objectBtn.setMaximumWidth(300)
                        objectBtn.clicked.connect(self.updateWordDatabase)
                        self.buttonLayout.addWidget(objectBtn)

                    editBtn = qt.QPushButton(self, text=" Edit Note ")
                    editBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
                    editBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                          "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
                    editBtn.setMaximumWidth(300)
                    editBtn.setIcon(QIcon("images/edit white.png"))
                    editBtn.clicked.connect(self.editCurrentNote)
                    self.buttonLayout.addWidget(editBtn)

                    # Add respective buttons
                    if fullCorrect:
                        self.ding.play()
                        self.questionEdit.setText(self.questionEdit.toPlainText() + " ✅")
                        self.questionEdit.setAlignment(Qt.AlignCenter)

        elif self.allowNextNote and e.key() == Qt.Key_Return:
            self.showNextNote()

    def editCurrentNote(self):
        """ Edits current note to remove mistakes"""
        if self.textbookPath[0]:
            self.w = createNotes.Window(self, self.courseName, self.color, self.textbookPath,
                                        sendToNote=self.currentNote["noteID"], closeFunction=self.saveAndProceed)
        else:
            self.w = createNotesNoPDF.Window(self, self.courseName, self.color, self.textbookPath,
                                             sendToNote=self.currentNote["noteID"], closeFunction=self.saveAndProceed)
        self.w.show()
        self.hide()

    def saveAndProceed(self):
        """ Runs when the user is finished editing the current note """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()

        # Update current note
        c.execute("SELECT type, question, answer, qImageNo, correctCount, practiceCount, starred, subtopicName, "
                  "topicName, noteID FROM notes n JOIN subtopics s ON n.subtopicID = s.subtopicID JOIN topics t ON "
                  f"s.topicID = t.topicID WHERE noteID = {self.currentNote['noteID']}")

        note = c.fetchone()
        self.currentNote = {"type": note[0], "question": note[1], "answer": note[2], "qImageNo": note[3],
                            "correctCount": note[4], "practiceCount": note[5], "starred": bool(note[6]),
                            "subtopicName": note[7], "topicName": note[8], "noteID": note[9],
                            "count": self.currentNote["count"]}

        # Update values on other notes
        for i, n in enumerate(self.noteList):
            c.execute("SELECT type, question, answer, qImageNo, correctCount, practiceCount, starred, subtopicName, "
                      "topicName, noteID FROM notes n JOIN subtopics s ON n.subtopicID = s.subtopicID JOIN topics t ON "
                      f"s.topicID = t.topicID WHERE noteID = {n['noteID']}")

            note = c.fetchone()
            n = {"type": note[0], "question": note[1], "answer": note[2], "qImageNo": note[3],
                 "correctCount": note[4], "practiceCount": note[5], "starred": bool(note[6]),
                 "subtopicName": note[7], "topicName": note[8], "noteID": note[9], "count": n["count"]}
            self.noteList[i] = n

        conn.close()

    def findBoldWords(self):
        """ Reads the question to find the best words to fill in """
        note = self.currentNote
        quest, ans, noteCorrect = note["question"], note["answer"], note["correctCount"]

        try:
            score = note["correctCount"] / note["practiceCount"]
        except ZeroDivisionError:
            score = 1.0

        # Load filter words
        with open("text/fillerWords.json") as f:
            FILLER_WORDS = json.load(f)

        # Separate punctuation
        for symbol in PUNCTUATION:
            ans = ans.replace(symbol, f" {symbol} ")

        # Find key words
        ans = ans.replace("<br>", " <br> ")
        ans = ans.split()
        newAns = []
        boldList = []
        keyList = []

        for i, word in enumerate(ans):
            tempWord = word.replace("<br>", " ").lower()
            if len(tempWord) > 3 and tempWord not in quest and tempWord not in FILLER_WORDS and tempWord[0] != "*":
                word = "*" + word + "*"
                boldList.append(i)
            else:
                if tempWord[0] == "*":
                    keyList.append(i)
                word = word
            newAns.append(word)

        random.shuffle(boldList)
        boldList = keyList + boldList

        if len(boldList) == 0:
            boldList = list(range(len(ans)))

        # Calculate how many words to remove
        num = (noteCorrect + 3) * score
        num = int(num) + (num % 1 > 0)  # Round up to nearest int

        if num > 6:
            num = 6
        elif num < 1:
            num = 1

        if note["type"] == "Process":
            num = int(num * 1.5)
            if num > 9:
                num = 9

        # Calculate which words to remove
        selectedWords = []
        for i in range(num):
            if not selectedWords:
                # If empty then choose a random word
                selectedWords.append(boldList.pop(0))
            else:
                # Decide which is the best word to add
                wordAdded = False
                for word in boldList:
                    if (word - 1) not in selectedWords and (word + 1) not in selectedWords and len(selectedWords) < num:
                        # Add not neighbouring word
                        selectedWords.append(word)
                        boldList.remove(word)
                        wordAdded = True
                        break

                    if not wordAdded and len(selectedWords) < num:
                        # Add any word
                        selectedWords.append(word)
                        boldList.remove(word)

        # Clean up words
        for i in boldList:
            newAns[i] = newAns[i].replace("*", "")

        # Remove chosen words
        selectedWords = sorted(selectedWords)
        for i in selectedWords:
            word = newAns[i].replace("<br>", "").replace("*", "")
            word = word.replace("'", "`")
            newAns[i] = "_" * len(word)

            # Check database for synonyms
            validWordList = []
            conn = sqlite3.connect("text/words.db")
            c = conn.cursor()
            c.execute(f"SELECT wordID FROM words WHERE word = '{word}'")
            j = c.fetchone()
            if j:
                j = j[0]
                c.execute(f"SELECT w.word FROM synonyms s JOIN words w ON s.word2 = w.wordID WHERE s.word1 = {j}")
                validWordList = [word[0] for word in c.fetchall()]

            conn.close()
            self.missingWords.append({"word": word, "index": i, "validWords": validWordList})

        # Make words bold
        for i, word in enumerate(newAns):
            if word[0] == "*":
                newAns[i] = f"<b>{word[1:-1]}</b>"

        self.currentMissingWord = self.missingWords[0]

        for i in range(len(self.missingWords)):
            if self.missingWords[i]["word"][-1] == "s":
                self.missingWords[i]["validWords"].append(self.missingWords[i]["word"][:-1])
        self.activateKeyPress = True

        return newAns

    def passNote(self):
        """ Show note answers """
        for _ in range(len(self.missingWords)):
            self.keyPressEvent("return")

    def overruleMarking(self):
        """ Changes correct value to opposite """
        self.noteUpdateNeeded = not self.noteUpdateNeeded
        self.showNextNote()

    def checkDefinitionAnswer(self):
        """ Checks text written to see whether it matches the answer """
        inputAns = self.answerEdit.toPlainText()
        ans = self.currentNote["answer"]

        if inputAns and inputAns[-1] in (" ", "."):
            if self.areTextsSimilar(inputAns, ans):
                # Entered word is correct
                self.revealDefinition(correct=True)

    def revealDefinition(self, correct=False):
        """ Shows definition answer """
        self.answerEdit.textChanged.disconnect()
        ans = self.answerEdit.toPlainText()
        self.answerEdit.setReadOnly(True)
        self.insertDefinition()
        self.noteUpdateNeeded = correct

        if correct:
            self.ding.play()
            self.questionEdit.setText(self.questionEdit.toPlainText() + " ✅")
        else:
            self.questionEdit.setText(self.questionEdit.toPlainText() + " ❌")
        self.questionEdit.setAlignment(Qt.AlignCenter)

        for i in reversed(range(self.buttonLayout.count())):
            self.buttonLayout.itemAt(i).widget().setParent(None)

        # Add buttons
        proceedBtn = qt.QPushButton(self, text=" Next Note ")
        proceedBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
        proceedBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                 "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        proceedBtn.setMaximumWidth(300)
        proceedBtn.clicked.connect(self.showNextNote)
        self.buttonLayout.addWidget(proceedBtn)

        # Bind return key
        self.addAction(self.ReturnAction)

        if ans:
            objectBtn = qt.QPushButton(self, text=" Incorrect Marking ")
            objectBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
            objectBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                    "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
            objectBtn.setMaximumWidth(300)
            objectBtn.clicked.connect(self.overruleMarking)
            self.buttonLayout.addWidget(objectBtn)

        editBtn = qt.QPushButton(self, text=" Edit Note ")
        editBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
        editBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                              "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        editBtn.setMaximumWidth(300)
        editBtn.setIcon(QIcon("images/edit white.png"))
        editBtn.clicked.connect(self.editCurrentNote)
        self.buttonLayout.addWidget(editBtn)

    def updateTimer(self, val):
        """ Updates label with time remaining """
        for i in reversed(range(self.buttonLayout.count())):
            self.buttonLayout.itemAt(i).widget().setText(f"Remember the Answer ({val})")

        if val == 0:
            self.flashFinished()

    def flashFinished(self):
        """ Allow user to answer """
        self.answerEdit.clear()
        self.answerEdit.setReadOnly(False)
        self.answerEdit.setAlignment(Qt.AlignLeft)
        self.answerEdit.setFocus()
        self.answerEdit.textChanged.connect(self.checkDefinitionAnswer)

        for i in reversed(range(self.buttonLayout.count())):
            self.buttonLayout.itemAt(i).widget().setParent(None)

        # Add pass button
        btn = qt.QPushButton(self, text=" Pass ")
        btn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
        btn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                          "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        btn.setMaximumWidth(300)
        btn.clicked.connect(self.revealDefinition)
        self.buttonLayout.addWidget(btn)

    def insertDefinition(self):
        """ Inserts definition into answer edit """
        note = self.currentNote
        ans = note["answer"].split()

        # Make words bold
        for i, word in enumerate(ans):
            indexes = [j for j, ltr in enumerate(word) if ltr == "*"]
            if indexes:
                ans[i] = f"<b>{word[indexes[0] + 1:indexes[-1]]}</b>"

        self.answerEdit.clear()
        self.answerEdit.append(" ".join(ans))

    def definitionFlash(self):
        """ Decide how long to reveal answer for """
        note = self.currentNote

        try:
            score = note["correctCount"] / note["practiceCount"]
        except ZeroDivisionError:
            score = 1.0

        # Calculate definition duration
        lengthMultiplier = (len(note["answer"]) // 10) / 10
        tNum = int(5 - note["correctCount"] * score) * lengthMultiplier
        tNum = int(tNum) + (tNum % 1 > 0)  # Round up to nearest int
        if tNum > 0 and lengthMultiplier < 1:
            lengthMultiplier = 1
        num = int(5 - note["correctCount"] * score) * lengthMultiplier
        num = int(num) + (num % 1 > 0)  # Round up to nearest int

        # If there is any time
        if num > 0:
            self.insertDefinition()

            # Add timer label
            label = qt.QLabel(self)
            font = QFont("Neue Haas Grotesk Text Pro", 20)
            font.setBold(True)
            label.setFont(font)
            label.setAlignment(Qt.AlignHCenter)
            self.buttonLayout.addWidget(label)

            self.numOfSec = num
            self.defThread.start()

        else:
            self.numOfSec = None
            self.flashFinished()

    def showNextNote(self):
        """ Loads the next note into the widgets """
        self.back = True
        self.diagramLabel.setText("")
        self.stepListWidget.setParent(None)
        self.tableWidget.setParent(None)
        self.answerEdit.hide()
        self.removeAction(self.ReturnAction)

        if self.noteUpdateNeeded is not None:
            self.updateAns(self.noteUpdateNeeded)

        if not self.noteList:
            # All notes have been studied
            self.finishStudying()

        elif self.notesCompleted % self.SWAP_NOTES == 0 and self.notesCompleted > 0:
            # Show current scores
            self.noteUpdateNeeded = None
            self.notesCompleted = -1

            # Send user to learn window
            self.back = False
            self.w = showScore.Window(self, self.courseName, self.color, self.showNextNote,
                                      self.totalNotesCompleted, len(self.noteList), time() - self.timeStarted,
                                      self.correctCounter, self.incorrectCounter, self.finishStudying)
            self.w.show()
            self.close()

        else:
            # Show next note
            self.resetValues()
            self.currentNote = self.noteList.pop(0)
            note = self.currentNote

            # Fill in labels
            self.topicLabel.setText(note["topicName"])
            self.subtopicLabel.setText(note["subtopicName"])
            self.answerEdit.setReadOnly(True)
            self.answerEdit.setAlignment(Qt.AlignCenter)

            # Clear button layout
            for i in reversed(range(self.buttonLayout.count())):
                self.buttonLayout.itemAt(i).widget().setParent(None)

            # Add diagram
            if note["qImageNo"] == 0:
                self.isImage = False
                self.diagramLabel.clear()
                self.diagramLabel.adjustSize()
            else:
                self.isImage = True
                self.reshapeImage()
                self.resizeEvent(None)

            # Change widgets depending on type of note
            if note["type"] == "Fact":
                # Add buttons
                self.answerEdit.show()
                btn = qt.QPushButton(self, text=" Pass ")
                btn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
                btn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                  "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
                btn.setMaximumWidth(300)
                btn.clicked.connect(self.passNote)
                self.buttonLayout.addWidget(btn)

                self.answerText = self.findBoldWords()
                self.factThread.start()

            elif note["type"] == "Definition":
                self.answerEdit.show()
                self.definitionFlash()

            elif note["type"] == "Formula":
                self.answerEdit.show()
                # Determine type of formula question
                try:
                    score = note["correctCount"] / note["practiceCount"]
                except ZeroDivisionError:
                    score = 1.0

                if (note["correctCount"] < 2 or (note["correctCount"] >= 2 and score <= 0.5)) and \
                        note not in self.calcFormulaList:
                    # Enter formula question
                    btn = qt.QPushButton(self, text=" Pass ")
                    btn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
                    btn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                      "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
                    btn.setMaximumWidth(300)
                    btn.clicked.connect(self.passNote)
                    self.buttonLayout.addWidget(btn)

                    self.currentNote["question"], self.answerText = self.findBlankFormVariables()
                    self.factThread.start()
                else:
                    # Calculation question
                    self.calcFormulaList.append(self.currentNote)
                    btn = qt.QPushButton(self, text=" Pass ")
                    btn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
                    btn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                      "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
                    btn.setMaximumWidth(300)
                    btn.clicked.connect(self.passNote)
                    self.buttonLayout.addWidget(btn)

                    self.currentNote["question"], self.answerText = self.generateMathQuestion()
                    self.factThread.start()

            elif note["type"] == "Process":
                self.answerEdit.show()
                # Determine type of formula question
                try:
                    score = note["correctCount"] / note["practiceCount"]
                except ZeroDivisionError:
                    score = 1.0

                if (note["correctCount"] < 2 or (note["correctCount"] >= 2 and score <= 0.5)) and \
                        note not in self.fillProcessList:
                    # Drag process question
                    self.diagramLabel.setText("Drag in the right order")
                    font = QFont("MS Sans Serif", 14)
                    font.setItalic(True)
                    self.diagramLabel.setFont(font)
                    self.stepListWidget.setAcceptDrops(True)  # Enable dropping files
                    self.stepListWidget.setDragEnabled(True)  # Enable dragging files
                    self.noteBox.addWidget(self.stepListWidget)
                    self.correctStepOrder = self.getCorrectStepOrder()
                    randomSteps = list(self.correctStepOrder)
                    while randomSteps == list(self.correctStepOrder):
                        random.shuffle(randomSteps)

                    for i, step in enumerate(randomSteps, start=1):
                        self.stepListWidget.addItem(f"{i}. {step}")
                    self.stepListWidget.setCurrentRow(0)

                    btn = qt.QPushButton(self, text=" Pass ")
                    btn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
                    btn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                      "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
                    btn.setMaximumWidth(300)
                    btn.clicked.connect(self.revealProcessOrder)
                    self.buttonLayout.addWidget(btn)
                else:
                    # Fill in the blank question
                    self.fillProcessList.append(self.currentNote)
                    btn = qt.QPushButton(self, text=" Pass ")
                    btn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
                    btn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                      "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
                    btn.setMaximumWidth(300)
                    btn.clicked.connect(self.passNote)
                    self.buttonLayout.addWidget(btn)

                    self.currentNote["answer"] = "<br><br>".join([f"{i}. {step}" for i, step in
                                                                  enumerate(self.getCorrectStepOrder(), start=1)])

                    self.answerText = self.findBoldWords()
                    self.factThread.start()

            elif note["type"] == "Diagram":
                # Add buttons
                btn = qt.QPushButton(self, text=" Start Drawing ")
                btn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
                btn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                  "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
                btn.setMaximumWidth(300)
                btn.clicked.connect(self.startDrawing)
                self.buttonLayout.addWidget(btn)

            elif note["type"] == "Table":
                self.diagramLabel.setText("Fill in the table")
                font = QFont("MS Sans Serif", 14)
                font.setItalic(True)
                self.diagramLabel.setFont(font)
                self.tableWidget.itemChanged.connect(self.tableChanged)
                self.openTable(False)  # Draws table

                btn = qt.QPushButton(self, text=" Pass ")
                btn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
                btn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                  "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
                btn.setMaximumWidth(300)
                btn.clicked.connect(self.revealTableAnswer)
                self.buttonLayout.addWidget(btn)

            self.questionEdit.setText(title(note["question"]))
            self.questionEdit.setAlignment(Qt.AlignCenter)
            if self.readQuestion:
                self.readThread.start()

    def tableHasCorrectAnswers(self):
        """ Returns whether user has entered correct values in table """
        answers = [False for word in self.missingWords]
        missingPositions = [word["pos"] for word in self.missingWords]
        for i in range(self.tableWidget.rowCount()):
            for j in range(self.tableWidget.columnCount()):
                if (i, j) in missingPositions:
                    # Check if user entered correct word
                    entered = self.tableWidget.item(i, j).text().strip().lower()
                    correctAns = self.missingWords[missingPositions.index((i, j))]["text"].lower()

                    # Clean powers
                    powers = re.findall(r"\^\-?\d*", entered)
                    for power in powers:
                        newPower = "".join([POWER_SYMBOL[i] for i in power[1:]])
                        entered = entered.replace(power, newPower)

                    # Check if answer is numerically correct
                    try:
                        if roundTo3Sf(float(entered)) == roundTo3Sf(float(correctAns)):
                            entered = correctAns
                    except Exception:
                        pass

                    answers[missingPositions.index((i, j))] = entered == correctAns

        return False not in answers

    def revealTableAnswer(self):
        """ Shows table answer """
        self.tableWidget.itemChanged.disconnect()
        self.activateTableThread = False
        correct = self.tableHasCorrectAnswers()
        self.noteUpdateNeeded = correct
        self.diagramLabel.setText("")

        if correct:
            self.ding.play()
            self.questionEdit.setText(self.questionEdit.toPlainText() + " ✅")
        else:
            self.tableWidget.setParent(None)
            self.openTable(True)
            self.questionEdit.setText(self.questionEdit.toPlainText() + " ❌")
        self.questionEdit.setAlignment(Qt.AlignCenter)

        for i in reversed(range(self.buttonLayout.count())):
            self.buttonLayout.itemAt(i).widget().setParent(None)

        # Add buttons
        proceedBtn = qt.QPushButton(self, text=" Next Note ")
        proceedBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
        proceedBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                 "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        proceedBtn.setMaximumWidth(300)
        proceedBtn.clicked.connect(self.showNextNote)
        self.buttonLayout.addWidget(proceedBtn)

        # Bind return key
        self.addAction(self.ReturnAction)

        if not correct:
            objectBtn = qt.QPushButton(self, text=" Incorrect Marking ")
            objectBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
            objectBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                    "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
            objectBtn.setMaximumWidth(300)
            objectBtn.clicked.connect(self.overruleMarking)
            self.buttonLayout.addWidget(objectBtn)

        editBtn = qt.QPushButton(self, text=" Edit Note ")
        editBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
        editBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                              "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        editBtn.setMaximumWidth(300)
        editBtn.setIcon(QIcon("images/edit white.png"))
        editBtn.clicked.connect(self.editCurrentNote)
        self.buttonLayout.addWidget(editBtn)

    def openTable(self, displayAnswer):
        """ Opens a new window with a table """
        # Get table elements
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"SELECT rowNo, colNo, textVal, userFill FROM tableElements t JOIN notes n ON t.tableID = n.tableID "
                  f"WHERE noteID = {self.currentNote['noteID']} ORDER BY rowNo, colNo")
        values = c.fetchall()
        noRows, noCols = values[-1][0] + 1, values[-1][1] + 1

        tableValues = [[{"text": "", "userFill": False} for _ in range(noCols)] for _ in range(noRows)]
        fillCells = []
        for cell in values:
            i, j = cell[0], cell[1]
            tableValues[i][j]["text"] = cell[2].replace("`", "'")
            tableValues[i][j]["userFill"] = cell[3]
            fillCells.append((i, j))
        conn.commit()
        conn.close()

        if not displayAnswer:
            # Work out number of elements to fill
            note = self.currentNote
            try:
                score = note["correctCount"] / note["practiceCount"]
            except ZeroDivisionError:
                score = 1.0

            noFill = (note["correctCount"] + 3) * score
            noFill = int(noFill) + (noFill % 1 > 0)  # Round up to nearest int

            if noFill > 6:
                noFill = 6
            elif noFill < 1:
                noFill = 1

            fillCells = [cell for cell in fillCells if tableValues[cell[0]][cell[1]]["userFill"]]
            random.shuffle(fillCells)

            if noFill > len(fillCells):
                noFill = len(fillCells)
            fillCells = sorted(fillCells[:noFill])
        else:
            fillCells = []

        # Adds table
        self.tableWidget.setRowCount(len(tableValues))
        self.tableWidget.setColumnCount(len(tableValues[0]))
        self.tableWidget.setVerticalHeaderLabels([""] + [str(i + 1) for i in range(len(tableValues[1:]))])
        self.tableWidget.setHorizontalHeaderLabels([chr(65 + i) for i in range(26)])

        # Add top headings
        for i, name in enumerate(tableValues[0]):
            item = qt.QTableWidgetItem(name["text"])
            item.setFont(self.boldFont)
            item.setFlags(Qt.ItemIsEnabled)
            self.tableWidget.setItem(0, i, item)

        # Add data
        for row, item in enumerate(tableValues[1:], start=1):
            for column, element in enumerate(item):
                if (row, column) in fillCells:
                    item = qt.QTableWidgetItem()
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
                    self.missingWords.append({"text": element["text"], "pos": (row, column)})
                else:
                    item = qt.QTableWidgetItem(element["text"])
                    item.setFlags(Qt.ItemIsEnabled)

                self.tableWidget.setItem(row, column, item)

        # Work out if table is one-way or two-way
        firstColumn = [row[0]["userFill"] for row in tableValues]
        if True not in firstColumn:
            # Add side headings
            for i, name in enumerate([row[0] for row in tableValues]):
                item = qt.QTableWidgetItem(name["text"])
                item.setFont(self.boldFont)
                item.setFlags(Qt.ItemIsEnabled)
                self.tableWidget.setItem(i, 0, item)

        self.noteBox.addWidget(self.tableWidget)
        self.activateTableThread = not displayAnswer

    def startDrawing(self):
        """ Opens drawing widget """
        note = self.currentNote
        imagePath = "images/temp/foo.png"

        img = Image.open(f"data/{self.courseName}/images/{note['qImageNo']}.png")
        img.save(imagePath)

        with open("text/currentSettings.json") as f:
            data = json.load(f)

        if os.path.exists(data["editorPath"][0]) and data["editorPath"][1]:
            # Open external application
            cwd = os.getcwd()
            os.chdir(os.path.join(os.getcwd(), "images/temp/").replace("\\", "/"))
            p = subprocess.Popen([data["editorPath"][0], os.path.basename(imagePath)])
            os.chdir(cwd)
            self.hide()

            # Reopen application
            p.wait()
            self.show()
            self.drawingComplete()

        else:
            # Open paint application
            self.w = paint.Window(self, imagePath, None, self.drawingComplete)
            self.w.show()
            self.hide()

    def addDiagramLayout(self):
        """ Adds diagram layout """
        vbox = qt.QVBoxLayout()
        drawnImageLabel = qt.QLabel(self)
        drawnImageLabel.setText("Your Diagram")
        drawnImageLabel.setFont(QFont("Neue Haas Grotesk Text Pro", 14))
        drawnImageLabel.setStyleSheet("font-weight: bold")
        drawnImageLabel.setAlignment(Qt.AlignCenter)
        vbox.addWidget(drawnImageLabel)
        vbox.addWidget(self.drawnImage)
        self.diagramLayout.addLayout(vbox)

        vbox = qt.QVBoxLayout()
        correctImageLabel = qt.QLabel(self)
        correctImageLabel.setText("Correct Diagram")
        correctImageLabel.setFont(QFont("Neue Haas Grotesk Text Pro", 14))
        correctImageLabel.setStyleSheet("font-weight: bold")
        correctImageLabel.setAlignment(Qt.AlignCenter)
        vbox.addWidget(correctImageLabel)
        vbox.addWidget(self.correctImage)
        self.diagramLayout.addLayout(vbox)

        self.noteBox.addLayout(self.diagramLayout)

    def drawingComplete(self, *args):
        """ Runs when user finishes drawing diagram """
        note = self.currentNote
        self.isImage = "Diagram"

        # Clear layout
        self.diagramLabel.clear()
        for i in reversed(range(self.buttonLayout.count())):
            self.buttonLayout.itemAt(i).widget().setParent(None)

        # Get correct answer
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"SELECT aImageNo FROM notes WHERE noteID = {note['noteID']}")
        aImageNo = c.fetchone()[0]

        conn.close()

        # Compare two images
        self.addDiagramLayout()

        pixmap = QPixmap(f"images/temp/foo.png")  # Drawn diagram
        self.drawnImage.setPixmap(pixmap)
        self.drawnImage.adjustSize()

        pixmap = QPixmap(f"data/{self.courseName}/images/{aImageNo}.png")  # Correct diagram
        self.correctImage.setPixmap(pixmap)
        self.correctImage.adjustSize()

        # Add buttons
        correctBtn = qt.QPushButton(self, text=" Answer Correct ✅ ")
        correctBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
        correctBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                 "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        correctBtn.setMaximumWidth(300)
        correctBtn.clicked.connect(lambda: self.setCorrect(True))
        self.buttonLayout.addWidget(correctBtn)

        incorrectBtn = qt.QPushButton(self, text=" Answer Incorrect ❌ ")
        incorrectBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
        incorrectBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                   "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        incorrectBtn.setMaximumWidth(300)
        incorrectBtn.clicked.connect(lambda: self.setCorrect(False))
        self.buttonLayout.addWidget(incorrectBtn)

        editBtn = qt.QPushButton(self, text=" Edit Note ")
        editBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
        editBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                              "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        editBtn.setMaximumWidth(300)
        editBtn.setIcon(QIcon("images/edit white.png"))
        editBtn.clicked.connect(self.editCurrentNote)
        self.buttonLayout.addWidget(editBtn)

    def setCorrect(self, correct):
        """ Sets whether question was correct or incorrect """
        if correct:
            self.ding.play()

        self.noteUpdateNeeded = correct
        deleteItemsOfLayout(self.diagramLayout)
        self.showNextNote()

    def revealProcessOrder(self, correct=False):
        """ Shows definition answer """
        self.stepListWidget.setAcceptDrops(False)
        self.stepListWidget.setDragEnabled(False)
        self.noteUpdateNeeded = correct
        self.diagramLabel.setText("")

        # Display correct order
        self.stepListWidget.setParent(None)
        self.answerEdit.setText("<br><br>".join([f"{i}. {step}" for i, step in
                                                 enumerate(self.correctStepOrder, start=1)]))

        if correct:
            self.ding.play()
            self.questionEdit.setText(self.questionEdit.toPlainText() + " ✅")
        else:
            self.questionEdit.setText(self.questionEdit.toPlainText() + " ❌")
        self.questionEdit.setAlignment(Qt.AlignCenter)

        for i in reversed(range(self.buttonLayout.count())):
            self.buttonLayout.itemAt(i).widget().setParent(None)

        # Add buttons
        proceedBtn = qt.QPushButton(self, text=" Next Note ")
        proceedBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
        proceedBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                                 "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        proceedBtn.setMaximumWidth(300)
        proceedBtn.clicked.connect(self.showNextNote)
        self.buttonLayout.addWidget(proceedBtn)

        # Bind return key
        self.addAction(self.ReturnAction)

        editBtn = qt.QPushButton(self, text=" Edit Note ")
        editBtn.setFont(QFont("Neue Haas Grotesk Text Pro", 16))
        editBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                              "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        editBtn.setStyleSheet("QPushButton {background-color: #0285c2;border-radius: 10px;color: "
                              "#F6F7FB;}QPushButton:hover {background-color: rgb(2, 106, 154);}")
        editBtn.setMaximumWidth(300)
        editBtn.setIcon(QIcon("images/edit white.png"))
        editBtn.clicked.connect(self.editCurrentNote)
        self.buttonLayout.addWidget(editBtn)

    def showProcessStep(self):
        """ Display currently selected process """
        items = [self.stepListWidget.item(i).text() for i in range(self.stepListWidget.count())]
        i = self.stepListWidget.currentRow()
        step = items[i]

        no = re.findall(r"\d+\. |\d+\) ", step)
        for n in no:
            if step[:len(n)] == n:
                step = step[len(n):]

        self.answerEdit.setText(step)

    def stepListModified(self):
        """ Deletes previous element when dragged """
        items = [self.stepListWidget.item(i).text() for i in range(self.stepListWidget.count())]

        # Clean steps
        for i, step in enumerate(items):
            no = re.findall(r"\d+\. |\d+\) ", step)
            for n in no:
                if step[:len(n)] == n:
                    step = step[len(n):]
            items[i] = step

        i = self.stepListWidget.currentRow()
        moved = items[i]

        # Remove Duplicate
        if items.count(moved) > 1:
            del items[i]
            self.stepListWidget.clear()
            for i, step in enumerate(items, start=1):
                self.stepListWidget.addItem(f"{i}. {step}")
            self.stepListWidget.setCurrentRow(items.index(moved))

        if items == list(self.correctStepOrder):
            self.revealProcessOrder(correct=True)

    def getCorrectStepOrder(self):
        """ Returns the steps in a process """
        # Connect to database
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"SELECT step FROM processes p JOIN notes n ON p.processID = n.processID WHERE noteID = \
        {self.currentNote['noteID']} ORDER BY stepNo")
        steps = tuple([step[0] for step in c.fetchall()])
        conn.commit()
        conn.close()
        return steps

    def generateMathQuestion(self):
        """ Generates formula question """
        # Connect to database
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"SELECT name, symbol, unit, min, max, step FROM formulas f JOIN notes n ON \
                        f.formulaID = n.formulaID WHERE noteID = {self.currentNote['noteID']}")
        formulaVariables = [{"name": term[0], "symbol": term[1], "unit": term[2], "min": term[3], "max": term[4],
                             "step": term[5]} for term in c.fetchall()]
        conn.commit()
        conn.close()

        # Determine which variable to make the subject
        validVariables = [var for var in formulaVariables if var["step"] != 0]
        if len(validVariables) == 0:
            validVariables = formulaVariables
        random.shuffle(validVariables)
        subject = validVariables.pop()

        # Make subject the subject
        formula = self.currentNote["answer"].replace("^", "**")
        i = formula.index("=")
        lhs, rhs = formula[:i], formula[i + 1:]
        sympy.var(", ".join([var["symbol"] for var in formulaVariables]))
        equation = sympy.Eq(eval(lhs), eval(rhs))
        try:
            lhs = subject["symbol"]
            rhs = str(sympy.solve(equation, eval(subject["symbol"]))[-1])
        except Exception:
            # Calculate too hard to manipulate
            variableNames = [var["symbol"] for var in formulaVariables]
            if lhs in variableNames:
                # Left hand side already the subject
                subject = [var for var in formulaVariables if var["symbol"] == lhs]
                rhs = formula[i + 1]

            elif rhs in variableNames:
                # Right hand side already the subject
                subject = [var for var in formulaVariables if var["symbol"] == rhs]
                lhs = rhs
                rhs = formula[:i]

            else:
                # Too hard to manipulate
                text = f"Equation {formula} too hard to make {subject['symbol']} the subject. Type 'enter' " \
                       "to skip. _____ ".split()
                self.missingWords = [
                    {"word": "enter", "index": text.index("_____"), "validWords": []}]
                self.currentMissingWord = self.missingWords[0]
                self.activateKeyPress = True
                return "Error", text

        # Work out values for variables
        newAns = []
        varNeedDefining = [var for var in formulaVariables if var["symbol"] != lhs]
        for var in varNeedDefining:
            value = random.choice(list(drange(var['min'], var['max'], var['step'])))
            exec(f"{var['symbol']}={value}")

            # Clean powers
            unit = var["unit"]
            powers = re.findall(r"\^\-?\d*", unit)
            for power in powers:
                newPower = "".join([POWER_SYMBOL[i] for i in power[1:]])
                unit = unit.replace(power, newPower)
            newAns.extend([var["name"].title(), "=", str(value), unit, "<br>"])

        # Generate answer text
        try:
            answerVal = eval(rhs)
        except Exception:
            return self.generateMathQuestion()

        answer = roundTo3Sf(answerVal)
        sfNeeded = False
        if answerVal != answer and len(str(answer).replace("-", "")) >= 3:
            sfNeeded = True

        if len(str(answer)) >= 5:
            # Convert to standard form
            answer = format(answer, '.2E').lower()
            sfNeeded = True

        unit = subject["unit"]
        powers = re.findall(r"\^\-?\d*", unit)
        for power in powers:
            newPower = "".join([POWER_SYMBOL[i] for i in power[1:]])
            unit = unit.replace(power, newPower)
        newAns.extend(["➔", subject["name"].title(), "=", "_" * len(str(answer)), unit])
        if sfNeeded:
            newAns.append("(3sf)")

        self.missingWords = [{"word": str(answer), "index": newAns.index("_" * len(str(answer))), "validWords": []}]
        self.currentMissingWord = self.missingWords[0]
        self.activateKeyPress = True

        return "Work out " + subject["name"].title(), newAns

    def findBlankFormVariables(self):
        """ Finds the non-subject variables in a formula """
        # Connect to database
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute(f"SELECT name, symbol, unit, min, max, step FROM formulas f JOIN notes n ON \
                f.formulaID = n.formulaID WHERE noteID = {self.currentNote['noteID']}")
        formulaVariables = [{"name": term[0], "symbol": term[1], "unit": term[2], "min": term[3], "max": term[4],
                             "step": term[5]} for term in c.fetchall()]
        conn.commit()
        conn.close()

        # Convert to list
        text = self.currentNote["answer"]
        terms = sorted([var["symbol"] for var in formulaVariables], key=len)[::-1]
        for term in terms:
            text = text.replace(term, " " + term + " ")
        newAns = text.split()

        # Remove * symbol
        for _ in range(newAns.count("*")):
            newAns.remove("*")

        # Clean powers
        for i, word in enumerate(newAns):
            if word[0] == "^":
                # Replace indices with smaller numbers
                indices = ""
                for t in word[1:]:
                    if t in list(POWER_SYMBOL.keys()):
                        indices += POWER_SYMBOL[t]
                    else:
                        indices += t
                newAns[i] = indices

        sep = newAns.index("=")
        lhs, rhs = newAns[:sep], newAns[sep + 1:]

        if len(lhs) == 1:
            # Left hand side only consists of one term
            selectedWords = [term for term in rhs if term in terms]

            question = "Complete the Formula for " + \
                       [term for term in formulaVariables if term["symbol"] == lhs[0]][0]["name"].title()
        elif len(rhs) == 1:
            # Right hand side only consists of one term
            selectedWords = [term for term in lhs if term in terms]
            question = "Complete the Formula for " + \
                       [term for term in formulaVariables if term["symbol"] == rhs[0]][0]["name"].title()
        else:
            # Equation
            selectedWords = [term for term in (lhs + rhs)[1:] if term in terms]
            question = "Complete the Equation"

        # Replace variables with underscores
        for term in selectedWords:
            i = newAns.index(term)
            newAns[i] = "_" * len(term)
            self.missingWords.append({"word": term, "index": i, "validWords": []})

        self.currentMissingWord = self.missingWords[0]
        self.activateKeyPress = True
        return question, newAns

    def resizeEvent(self, event):
        """ Run when window gets resized """
        # Resize image
        if self.isImage is True:
            note = self.currentNote
            pixmap = QPixmap(f"images/temp/foo.png")
            w, h = pixmap.width(), pixmap.height()

            if note["type"] == "Diagram":
                newHeight = self.height() // 2
            else:
                newHeight = self.height() // 3

            try:
                scale = newHeight / h
                pixmap = pixmap.scaled(int(w * scale), int(h * scale), Qt.KeepAspectRatio)
                self.diagramLabel.setPixmap(pixmap)
                self.diagramLabel.adjustSize()
            except ZeroDivisionError:
                pass

        elif self.isImage == "Diagram":
            pass

    def reshapeImage(self):
        """ Reshapes image to best fit """
        note = self.currentNote
        imgPath = f"data/{self.courseName}/images/{note['qImageNo']}.png"
        img = Image.open(imgPath)
        WIDTH, HEIGHT = 720, 542
        if img.width == WIDTH and img.height == HEIGHT:
            # Standard image
            t = 20

            # Find coordinates of main image
            n, s, w, e = getCentralCoordinates(img, t)
            img = img.crop((w, n, e, s))

        elif img.width > WIDTH or img.height > HEIGHT:
            scale = min([WIDTH / img.width, HEIGHT / img.height])
            img = img.resize((int(img.width * scale), int(img.height * scale)))

        img.save(f"images/temp/foo.png")

    def loadNotes(self):
        """ Select Notes that match the criteria """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()

        if len(self.subtopics) == 1:
            # If only one subtopic is selected
            c.execute(f"SELECT subtopicID, subtopicName FROM subtopics")
            result = c.fetchall()
            for record in result:
                if record[1] == self.subtopics[0]:
                    condition = f"WHERE n.subtopicID = {record[0]}"
                    break

        else:
            # If more than one subtopic is selected
            c.execute(f"SELECT subtopicID FROM subtopics WHERE subtopicName IN {tuple(self.subtopics)}")
            subtopicIDs = tuple([i[0] for i in c.fetchall()])
            condition = f"WHERE n.subtopicID IN {subtopicIDs}"

        c.execute(f"SELECT type, question, answer, qImageNo, correctCount, practiceCount, starred, subtopicName, "
                  f"topicName, noteID FROM notes n JOIN subtopics s ON n.subtopicID = s.subtopicID JOIN topics t ON "
                  f"s.topicID = t.topicID {condition} ORDER BY userScore "
                  f"ASC, practiceCount DESC, noteID ASC")

        self.noteList = [{"type": note[0], "question": note[1], "answer": note[2], "qImageNo": note[3],
                          "correctCount": note[4], "practiceCount": note[5], "starred": bool(note[6]),
                          "subtopicName": note[7], "topicName": note[8], "noteID": note[9],
                          "count": 0} for note in c.fetchall()]
        conn.close()

        # Replace '`'
        for i, note in enumerate(self.noteList):
            self.noteList[i]["answer"] = self.noteList[i]["answer"].replace("`", "'")

        # Filter notes
        if not self.focusWeak:
            random.shuffle(self.noteList)

        if self.starred:
            newNotes = []
            for note in self.noteList:
                if note["starred"]:
                    newNotes.append(note)
            self.noteList = newNotes

        if len(self.noteList) > self.MAX_NOTES:
            reply = qt.QMessageBox.question(self, f"Do you want to review all {len(self.noteList)} notes?",
                                            "This exceeds the number of notes per session, which is currently set to " +
                                            f"{self.MAX_NOTES}. \n\nSelect 'No' to only review your weakest " +
                                            f"{self.MAX_NOTES} notes.\n\nThe maximum number of notes can be changed " +
                                            "in settings.", qt.QMessageBox.Yes, qt.QMessageBox.No)

            if qt.QMessageBox.No:
                # Calculate which MAX_NOTES notes to take from note sample
                noteTopics = [note["topicName"] for note in self.noteList]
                frequency = collections.Counter(noteTopics)
                newNoteList = []
                for topic in frequency:
                    noTopics = round((frequency[topic] / len(self.noteList)) * self.MAX_NOTES)

                    for _ in range(noTopics):
                        newNoteList.append(self.noteList[noteTopics.index(topic)])
                        noteTopics[noteTopics.index(topic)] = None

                self.noteList = newNoteList

        topicList = set([note["topicName"] for note in self.noteList])

        for topic in topicList:
            self.scorePerTopic[str(topic)] = 0

    def closeEvent(self, event):
        """ Run when window gets closed """
        if self.back:
            files = [f"images/temp/{file}" for file in os.listdir("images/temp")]
            for file in files:
                os.remove(file)
            self.breakThread = True
            self.superClass.show()

    def updateMenuBar(self):
        """ Updates menu bar with course title """
        # Load widgets
        courseNameLabel = self.findChild(qt.QLabel, "courseNameLabel")
        menuBar = self.findChild(qt.QWidget, "menuBar")

        menuBar.setStyleSheet(f"background-color:{self.color}")
        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        courseNameLabel.setText(self.courseName + " - Learn Notes")
        courseNameLabel.setStyleSheet(f"color:{fontColor}")
