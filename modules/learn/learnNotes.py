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
from time import sleep, time
from PIL import Image
import string
from spellchecker import SpellChecker

sys.path.append("modules")

from modImage import getCentralCoordinates
import showScore
import showSummary

# Define constants
PUNCTUATION = ["!", "#", "$", "%", "&", "(", ")", "+", ",", "^", ".", "/", ":", ";", "=", "?", "@", "[", "\\", "]",
               "{", "|", "}", "~"]

window = None


def title(phrase):
    return " ".join([word.title() if len(word) > 3 else word for word in phrase.split()])


class DefinitionThread(QThread):
    """ Reveals Answer for few seconds thread """

    change_value = pyqtSignal(int)  # Create signal object

    def run(self):
        global window
        duration = window.numOfSec
        for i in reversed(range(duration)):
            self.change_value.emit(i+1)
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
    imageList = []
    missingWords = []
    blankWords = []
    prevWord = []

    currentNote = None
    currentMissingWord = None
    thread = None
    noteUpdateNeeded = None
    numOfSec = None
    answerText = [None]

    isImage = False
    activateKeyPress = False
    breakThread = False
    allowNextNote = False
    back = True

    def __init__(self, superClass, course, color, subtopics, starred, focusWeak):
        """ Main Window """
        global window
        super(Window, self).__init__()
        uic.loadUi("gui/learnNotes.ui", self)
        self.superClass = superClass
        self.courseName = course
        self.color = color
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
        self.scorePerTopic = {}

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
        start = self.loadNotes()

        if start:
            # Get widgets
            topicLabel = self.findChild(qt.QLabel, "topicLabel")
            subtopicLabel = self.findChild(qt.QLabel, "subtopicLabel")
            questionEdit = self.findChild(qt.QTextEdit, "questionEdit")
            diagramLabel = self.findChild(qt.QLabel, "diagramLabel")
            answerEdit = self.findChild(qt.QTextEdit, "answerEdit")
            buttonLayout = self.findChild(qt.QHBoxLayout, "buttonLayout")
            finishBtn = self.findChild(qt.QPushButton, "finishBtn")

            # Bind Buttons
            finishBtn.clicked.connect(self.finishStudying)

            self.showNextNote()

        else:
            self.close()

    def areTextsSimilar(self, inputAns, correctAns):
        """ Uses spell checker to check whether the texts are similar"""
        spell = SpellChecker()

        # Modify input text
        inputAns = inputAns.lower()
        inputAns = inputAns.translate(str.maketrans("", "", string.punctuation))
        inputAns = inputAns.split()

        # Modify answer text

        correctAns = correctAns.replace("<br>", " ").lower()
        correctAns = correctAns.translate(str.maketrans("", "", string.punctuation))
        correctAns = correctAns.split()

        # Check for spelling mistakes
        misspelled = spell.unknown(inputAns)
        typoCount = 0

        for word in misspelled:
            # Misspelled words
            i = inputAns.index(word)
            inputAns[i] = list(spell.candidates(word))

            typoCount += 1
            if typoCount > self.MAX_TYPOS:
                return False

        # Check texts
        if len(inputAns) == len(correctAns):
            for i, words in enumerate(inputAns):
                if type(words) == "str" and words != correctAns[i]:
                    raise False

                elif type(words) == "list":
                    wordFound = False

                    for word in words:
                        if word == correctAns[i]:
                            wordFound = True

                    if not wordFound:
                        raise False
        else:
            return False

        return True

    def updateWordDatabase(self):
        """ Adds synonyms to word database """
        # Connect to database
        conn = sqlite3.connect("text/words.db")
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS words (wordID int, word text)")
        c.execute("CREATE TABLE IF NOT EXISTS synonyms (word1 int, word2 int)")
        self.noteUpdateNeeded = True

        # Ask user for words
        for pair in self.blankWords:
            word1, word2 = pair
            word1 = word1.lower()

            reply = qt.QMessageBox.question(self, "Update Personal Database",
                                            f"Should the word '{word2}' be allowed to be used in place of '{word1}'?",
                                            qt.QMessageBox.Yes, qt.QMessageBox.No)

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
                        c.execute(f"SELECT wordID from words ORDER BY wordID DESC")
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
                                    len(self.noteList), time()-self.timeStarted, self.correctCounter,
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

        if correct:
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
        else:
            note["count"] = 0

            if len(self.noteList) < 2:
                self.noteList.append(note)
            else:
                self.noteList.insert(1, note)

        score = round(noCorrect / noPractised, 2)

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
                    self.answerText[i] = self.answerText[i].replace("_", "") + "❌" + f" ({ans})"
                    self.incorrectCounter += 1
                    correct = False

                elif e.key() == Qt.Key_Backspace and self.prevWord:
                    if self.prevWord[-1] == self.answerText[i]:
                        self.prevWord.remove(self.answerText[i])

                    if self.prevWord:
                        self.answerText[i] = self.prevWord.pop()

            enteredAnswer = self.answerText[i].replace("_", "")
            if enteredAnswer == ans or enteredAnswer in self.missingWords[0]["validWords"] or not correct:
                # Word has been filled in
                correctAnswer = self.missingWords.pop(0)
                if "❌" in enteredAnswer:
                    k = enteredAnswer.index("❌")
                    enteredAnswer = enteredAnswer[:k]
                else:
                    self.correctCounter += 1

                if enteredAnswer and correctAnswer["word"] != enteredAnswer:
                    self.blankWords.append((correctAnswer["word"], enteredAnswer))
                self.prevWord = []

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
                    proceedBtn.setFont(QFont("MS Shell Dlg 2", 16))
                    proceedBtn.setMaximumWidth(300)
                    proceedBtn.clicked.connect(self.showNextNote)
                    self.buttonLayout.addWidget(proceedBtn)

                    if self.blankWords:
                        objectBtn = qt.QPushButton(self, text=" Incorrect Marking ")
                        objectBtn.setFont(QFont("MS Shell Dlg 2", 16))
                        objectBtn.setMaximumWidth(300)
                        objectBtn.clicked.connect(self.updateWordDatabase)
                        self.buttonLayout.addWidget(objectBtn)

                    # Add respective buttons
                    if fullCorrect:
                        self.ding.play()

        elif self.allowNextNote and e.key() == Qt.Key_Return:
            self.showNextNote()

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

        # Calculate how many words to remove
        num = (noteCorrect + 2) * score
        num = int(num) + (num % 1 > 0)  # Round up to nearest int

        if num > 6:
            num = 6
        elif num < 1:
            num = 1

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

            self.missingWords.append({"word": word, "index": i, "validWords": validWordList})

        # Make words bold
        for i, word in enumerate(newAns):
            if word[0] == "*":
                newAns[i] = f"<b>{word[1:-1]}</b>"

        self.currentMissingWord = self.missingWords[0]
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

        if inputAns and inputAns[-1] == " ":
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
        proceedBtn.setFont(QFont("MS Shell Dlg 2", 16))
        proceedBtn.setMaximumWidth(300)
        proceedBtn.clicked.connect(self.showNextNote)
        self.buttonLayout.addWidget(proceedBtn)


        if ans:
            objectBtn = qt.QPushButton(self, text=" Incorrect Marking ")
            objectBtn.setFont(QFont("MS Shell Dlg 2", 16))
            objectBtn.setMaximumWidth(300)
            objectBtn.clicked.connect(self.overruleMarking)
            self.buttonLayout.addWidget(objectBtn)

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
        btn.setFont(QFont("MS Shell Dlg 2", 16))
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

        num = int(5 - note["correctCount"]*score)
        num = int(num) + (num % 1 > 0)  # Round up to nearest int

        if num > 0:
            self.insertDefinition()
            self.timeStarted += num

            # Add timer label
            label = qt.QLabel(self)
            font = QFont("MS Shell Dlg 2", 20)
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
                                      self.totalNotesCompleted, len(self.noteList), time()-self.timeStarted,
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
            self.questionEdit.setText(title(note["question"]))
            self.questionEdit.setAlignment(Qt.AlignCenter)
            self.answerEdit.setReadOnly(True)
            self.answerEdit.setAlignment(Qt.AlignCenter)

            # Clear button layout
            for i in reversed(range(self.buttonLayout.count())):
                self.buttonLayout.itemAt(i).widget().setParent(None)

            # Add diagram
            if note["qImageNo"] == 0:
                self.isImage = False
                self.diagramLabel.clear()
            else:
                self.isImage = True
                if note["qImageNo"] not in self.imageList:
                    self.reshapeImage()
                self.resizeEvent(None)

            # Change widgets depending on type of note
            if note["type"] == "Fact":
                # Add buttons
                btn = qt.QPushButton(self, text=" Pass ")
                btn.setFont(QFont("MS Shell Dlg 2", 16))
                btn.setMaximumWidth(300)
                btn.clicked.connect(self.passNote)
                self.buttonLayout.addWidget(btn)

                self.answerText = self.findBoldWords()
                self.factThread.start()

            elif note["type"] == "Definition":
                self.definitionFlash()

    def resizeEvent(self, event):
        """ Run when window gets resized """
        # Resize image
        if self.isImage:
            note = self.currentNote
            pixmap = QPixmap(f"images/temp/{note['qImageNo']}.png")
            h = self.height() // 2.5
            if h < pixmap.height():
                pixmap = pixmap.scaledToHeight(self.height() // 2.5)

            self.diagramLabel.setScaledContents(True)
            self.diagramLabel.setPixmap(pixmap)

    def reshapeImage(self):
        """ Reshapes image to best fit """
        note = self.currentNote
        imgPath = f"data/{self.courseName}/images/{note['qImageNo']}.png"
        img = Image.open(imgPath)
        t = 20

        # Find coordinates of main image
        n, s, w, e = getCentralCoordinates(img, t)
        img = img.crop((w, n, e, s))
        img.save(f"images/temp/{note['qImageNo']}.png")
        self.imageList.append(note['qImageNo'])

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

        # Filter notes
        if not self.focusWeak:
            random.shuffle(self.noteList)

        if self.starred:
            for note in self.noteList:
                if not note["starred"]:
                    self.noteList.remove(note)

        if len(self.noteList) > self.MAX_NOTES:
            self.noteList = self.noteList[:self.MAX_NOTES]

        if not self.noteList:
            error = qt.QMessageBox.critical(self, "Cannot Learn Notes",
                                            "There are no notes that match selected filters", qt.QMessageBox.Ok)
            return False
        else:

            topicList = set([note["topicName"] for note in self.noteList])

            for topic in topicList:
                self.scorePerTopic[str(topic)] = 0

            return True

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
