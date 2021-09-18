import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QKeySequence
from PyQt5.QtCore import Qt
from PyQt5 import uic
import os
import sys
import sqlite3
import json
from PIL import Image
import numpy

import editTopics
import editSubtopics
import paint
import textbookSnipper


class CreateWindow(qt.QMainWindow):

    def initWidgets(self):
        """ Main Window """
        self.diagramPath = None
        self.noteID = None
        self.creatingNewNote = True

        # Get widgets
        self.topicCombo = self.findChild(qt.QComboBox, "topicCombo")
        self.subtopicCombo = self.findChild(qt.QComboBox, "subtopicCombo")
        self.factBtn = self.findChild(qt.QPushButton, "factBtn")
        self.definitionBtn = self.findChild(qt.QPushButton, "definitionBtn")
        self.answerEdit = self.findChild(qt.QPlainTextEdit, "answerEdit")
        self.questionEdit = self.findChild(qt.QLineEdit, "questionEdit")
        self.createNoteBtn = self.findChild(qt.QPushButton, "createNoteBtn")
        self.questDiagramBtn = self.findChild(qt.QPushButton, "questDiagramBtn")
        self.prevNoteBtn = self.findChild(qt.QToolButton, "prevNoteBtn")
        self.nextNoteBtn = self.findChild(qt.QToolButton, "nextNoteBtn")
        self.noteNoLabel = self.findChild(qt.QLabel, "noteNoLabel")
        self.delBtn = self.findChild(qt.QPushButton, "delBtn")
        self.delBtn.setIcon(QIcon("images/trash.png"))

        # Add shortcuts
        qt.QShortcut(QKeySequence("Ctrl+B"), self.answerEdit).activated.connect(self.highlightWord)

        # Bind buttons
        self.subtopicCombo.currentTextChanged.connect(self.validateQuestion)
        self.questionEdit.textChanged.connect(self.validateQuestion)
        self.answerEdit.textChanged.connect(self.validateQuestion)
        self.createNoteBtn.clicked.connect(self.createNote)
        self.questDiagramBtn.clicked.connect(self.addQuestPic)
        self.nextNoteBtn.clicked.connect(lambda: self.nextNote(1))
        self.prevNoteBtn.clicked.connect(lambda: self.nextNote(-1))
        self.delBtn.clicked.connect(self.deleteNote)
        self.buttons = [self.factBtn, self.definitionBtn]

        for button in self.buttons:
            button.setCheckable(True)
            button.clicked.connect(self.changeNoteType)

        self.factBtn.setChecked(True)
        self.noteType = self.factBtn

        # Fill in combo boxes
        self.getCourseData()
        self.fillComboBoxes()
        self.updateDiagramBtn()
        self.updateNoteNav()

    def deleteNote(self):
        """ Allows user to delete their existing note """
        reply = qt.QMessageBox.warning(self, "Are you Sure?", "This action cannot be undone",
                                       qt.QMessageBox.Yes, qt.QMessageBox.No)
        if reply == qt.QMessageBox.Yes:
            conn = sqlite3.connect(self.databasePath)
            c = conn.cursor()

            c.execute(f"SELECT qImageNo FROM notes WHERE noteID = {self.noteID}")
            no = c.fetchone()[0]
            if no != 0:
                os.remove(f"data/{self.courseName}/images/{no}.png")

            c.execute(f"DELETE FROM notes WHERE noteID = {self.noteID}")
            c.execute(f"SELECT noteID FROM notes WHERE noteID>{self.noteID}")
            noteIDs = [i[0] for i in c.fetchall()]
            for i in noteIDs:
                c.execute(f"UPDATE notes SET noteID = {i-1} WHERE noteID = {i}")
            conn.commit()
            conn.close()
            self.nextNote(0)

    def updateNoteNav(self):
        """ Update label and navigate buttons based on existing notes """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        if c.fetchall():
            c.execute("SELECT noteID FROM notes ORDER BY noteID")
            noteList = [i[0] for i in c.fetchall()]
        else:
            noteList = []

        conn.commit()
        conn.close()

        if not self.noteID:
            if self.sendToNote:
                self.noteID = self.sendToNote
                self.nextNote(0)
            else:
                self.noteID = len(noteList) + 1

        if noteList:
            # There are existing notes
            self.prevNoteBtn.setEnabled(self.noteID != noteList[0])  # Update if first note
            self.nextNoteBtn.setEnabled(self.noteID <= noteList[-1])  # Update if last note
            self.noteNoLabel.setText(f"{self.noteID}/{len(noteList)}")

    def nextNote(self, i):
        """ Loads the next load in the database """
        proceed = True
        question = self.questionEdit.text().strip()
        answer = self.answerEdit.toPlainText().strip()

        if self.creatingNewNote and (self.diagramPath or question or answer):
            reply = qt.QMessageBox.warning(self, "Note is Not Saved", "Your work will be lost",
                                           qt.QMessageBox.Ok, qt.QMessageBox.Cancel)
            if reply == qt.QMessageBox.Cancel:
                proceed = False

        if proceed:
            self.noteID += i
            try:
                conn = sqlite3.connect(self.databasePath)
                c = conn.cursor()
                c.execute(f"SELECT type, question, answer, qImageNo, subtopicID FROM notes \
                WHERE noteID = {self.noteID}")
                record = c.fetchone()
                c.execute(f"SELECT subtopicName, topicID FROM subtopics WHERE subtopicID = {record[4]}")
                results = c.fetchone()
                subtopicName = results[0]
                c.execute(f"SELECT topicName FROM topics WHERE topicID = {results[1]}")
                topicName = c.fetchone()[0]
                conn.close()
            except TypeError:
                # New note
                self.questionEdit.clear()
                self.answerEdit.clear()
                self.diagramPath = None
                self.creatingNewNote = True
                self.createNoteBtn.setText("Create Note")
                self.delBtn.setEnabled(False)
            else:
                # Set values
                self.creatingNewNote = False
                self.questionEdit.setText(record[1])
                self.answerEdit.clear()
                self.answerEdit.insertPlainText(record[2])

                imageNo = record[3]
                if imageNo != 0:
                    img = Image.open("data/" + self.courseName + "/images" + f"/{imageNo}.png")
                    self.diagramPath = "images/temp/foo.png"
                    img.save(self.diagramPath)
                else:
                    self.diagramPath = None

                for button in self.buttons:
                    if button.text() == record[0]:
                        self.noteType.setChecked(False)
                        self.noteType = button
                        self.noteType.setChecked(True)

                self.topicCombo.setCurrentText(topicName)
                self.subtopicCombo.setCurrentText(subtopicName)
                self.createNoteBtn.setText("Save Note")
                self.delBtn.setEnabled(True)
                self.makeWordsBold()

            # Update navigation buttons
            self.updateDiagramBtn()
            self.updateNoteNav()

    def updateDiagramBtn(self):
        """ Changes text depending on whether an image is saved """
        if self.diagramPath:
            self.questDiagramBtn.setText("Modify Question Diagram")
        else:
            self.questDiagramBtn.setText("Add Question Diagram")

    def addQuestPic(self):
        """ Opens window for adding a picture to the question """
        if self.diagramPath:
            # Open paint application
            self.w = paint.Window(self, "images/temp/foo.png", self.paintOptionSelected)
            self.w.show()
            self.hide()
        else:
            # Show options
            msg = qt.QMessageBox()
            msg.setWindowTitle("Select where to import Picture from")
            msg.setText("Click Open to upload your a picture from your files")
            msg.setIcon(qt.QMessageBox.Question)
            msg.setDefaultButton(qt.QMessageBox.Cancel)
            msg.buttonClicked.connect(self.popUp_quest)

            if self.textbookPath[0]:
                # Textbook added
                msg.setInformativeText("Click Ok to take a Snippet from the Textbook")
                msg.setStandardButtons(qt.QMessageBox.Open | qt.QMessageBox.Ok | qt.QMessageBox.Cancel)
            else:
                # Textbook not added
                msg.setStandardButtons(qt.QMessageBox.Open | qt.QMessageBox.Cancel)

            x = msg.exec_()

    def popUp_quest(self, i):
        if i.text() == "OK":
            # Navigate to PDF screenshot window
            self.takeTextbookSnip()
        elif i.text() == "Open":
            # Navigate to file dialog
            self.uploadQuestFile()

    def paintOptionSelected(self, option):
        """ Runs when paint window is closed """
        if option == "save":
            # Save image
            self.diagramPath = "images/temp/foo.png"
        elif option == "delete":
            # Delete image
            self.diagramPath = None

        self.updateDiagramBtn()

    def takeTextbookSnip(self):
        """ Opens window to take snippet from current textbook page """
        path = "images/temp/snip.png"
        img = Image.open(self.tempPath)
        img.save(path)
        self.w = textbookSnipper.Window(self, path, self.uploadQuestFile)
        self.w.show()
        self.hide()

    def uploadQuestFile(self, fName=None):
        """ Opens file dialog to select picture """
        with open("text/currentSettings.json") as f:
            data = json.load(f)

        if not fName:
            fName, _ = qt.QFileDialog.getOpenFileName(self, "Select Picture", data["picturePath"],
                                                      "Image files (*.png *.jpg *.jpeg *.gif *.bmp)")
        if fName:
            # Create image
            img = Image.open(fName)
            pix = numpy.array(img)
            border = [[], [], []]

            # North border
            for pixel in pix[0]:
                for i in range(3):
                    border[i].append(pixel[i])

            # South border
            for pixel in pix[-1]:
                for i in range(3):
                    border[i].append(pixel[i])

            # West and East border
            for j in range(img.height):
                for i in range(3):
                    border[i].append(pix[j][0][i])
                    border[i].append(pix[j][-1][i])

            average = tuple([max(set(color), key=color.count) for color in border])

            # Create new image
            w, h, t = 720, 640, 25
            image = Image.new("RGB", (w, h), "#%02x%02x%02x" % average)

            # Generate size of picture
            x = int((w - img.width) / 2)
            y = int((h - img.height) / 2)

            if x < t or y < t:
                # Picture too big
                if x <= y:
                    # Width is biggest
                    scale = (w - 2*t)/img.width
                else:
                    # Height is biggest
                    scale = (w - 2*t) / img.height

                # New values
                width = int(img.width*scale)
                height = int(img.height*scale)
                x = int((w - width) / 2)
                y = int((h - height) / 2)

                if x <= y:
                    x = int(t / 2)
                else:
                    y = int(t / 2)

                img = img.resize((width, height))
            elif (img.width/w) < 0.5 and (img.height/h) < 0.5:
                # If image is too small, then make it bigger
                img = img.resize((img.width*2, img.height*2))
                x = int((w - img.width) / 2)
                y = int((h - img.height) / 2)

            image.paste(img, (x, y, x + img.width, y + img.height))
            image.save("images/temp/foo.png")

            # Open paint application
            self.w = paint.Window(self, "images/temp/foo.png", self.paintOptionSelected)
            self.w.show()
            self.hide()

    def highlightWord(self):
        """ Highlights word """
        cursor = self.answerEdit.textCursor()
        word = cursor.selectedText().strip()
        if word:
            # If words are selected
            cursor.removeSelectedText()
            newText = ""
            for singleWord in word.split():
                if "*" in [singleWord[0], singleWord[-1]]:
                    # If word selected is already bold
                    if singleWord[0] == "*":
                        singleWord = singleWord[1:]
                    if singleWord[-1] == "*":
                        singleWord = singleWord[:-1]
                    newWord = singleWord
                else:
                    # If text selected is not bold
                    newWord = "*" + singleWord + "*"
                newText += newWord + " "

            self.answerEdit.insertPlainText(newText)
            self.makeWordsBold()

    def makeWordsBold(self):
        """ Makes words surrounded by '*' to be bold """
        newText = ""
        cursor = self.answerEdit.textCursor()
        i = cursor.position()
        for word in self.answerEdit.toPlainText().split():
            if word[0] == "*" and word[-1] == "*":
                # Word is bold
                newText += f"<b>{word}</b> "
            else:
                # Regular word
                newText += f"{word} "
        self.answerEdit.clear()
        self.answerEdit.appendHtml("<html>" + newText + "<html>")
        cursor.setPosition(i)
        self.answerEdit.setTextCursor(cursor)


    def changeNoteType(self):
        """ Changes the stylesheet of selected button """
        if self.noteType == self.sender():
            self.noteType.setChecked(True)
        else:
            self.noteType.setChecked(False)
            self.noteType = self.sender()


    def getCourseData(self):
        """ Gets course data from database """
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT topicName FROM topics")
        self.topicList = [topic[0] for topic in c.fetchall()]
        if not self.topicList:
            self.topicList = [""]
        conn.close()

    def getSubtopicData(self):
        """ Gets the list of subtopics for the current topic """
        topic = self.topicCombo.currentText()
        if topic:
            conn = sqlite3.connect(self.databasePath)
            c = conn.cursor()
            c.execute(f"SELECT topicID FROM topics WHERE topicName = '{topic}'")
            j = c.fetchone()[0]

            # Check whether subtopics table has been created
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subtopics'")
            if c.fetchall():
                c.execute(f"SELECT subtopicName FROM subtopics WHERE topicID = '{j}'")
                self.subtopicList = [subTopic[0] for subTopic in c.fetchall()]
                if not self.subtopicList:
                    self.subtopicList = [""]
            else:
                c.execute("CREATE TABLE subtopics (subtopicID integer, subtopicName text, topicID integer, \
                FOREIGN KEY(topicID) REFERENCES topics(topicID))")
                conn.commit()
                self.subtopicList = [""]
            conn.close()
        else:
            self.subtopicList = [""]

        # Add subtopics to combo box
        self.subtopicCombo.clear()
        for subtopics in self.subtopicList:
            self.subtopicCombo.addItem(subtopics)
        self.subtopicCombo.addItem("Manage Subtopics")

        self.subtopicCombo.currentTextChanged.connect(self.manageSubtopics)
        if self.subtopicList:
            self.prevSubtopic = self.subtopicList[0]
        else:
            self.prevSubtopic = None

    def fillComboBoxes(self):
        """ Inserts data into combo box """
        self.getCourseData()

        # Manage topics
        self.topicCombo.clear()
        for topic in self.topicList:
            self.topicCombo.addItem(topic)
        self.topicCombo.addItem("Manage Topics")

        self.topicCombo.currentTextChanged.connect(self.manageTopics)
        self.prevTopic = self.topicList[0]

        # Manage subtopics
        self.getSubtopicData()

    def manageTopics(self):
        """ Navigates user to edit topic window """
        if self.topicCombo.currentText() == "Manage Topics":
            self.w = editTopics.Window(self, self.databasePath, self.fillComboBoxes)
            self.w.show()
            self.hide()

            if self.prevTopic:
                self.topicCombo.setCurrentText(self.prevTopic)
            else:
                self.topicCombo.setCurrentText(self.topicList[0])
        else:
            self.prevTopic = self.topicCombo.currentText()
            self.getSubtopicData()

    def manageSubtopics(self):
        """ Navigates user to edit subtopic window """
        if self.subtopicCombo.currentText() == "Manage Subtopics":
            self.w = editSubtopics.Window(self, self.databasePath, self.getSubtopicData)
            self.w.show()
            self.hide()

            if self.prevSubtopic:
                self.subtopicCombo.setCurrentText(self.prevSubtopic)
            else:
                self.subtopicCombo.setCurrentText(self.subtopicList[0])
        else:
            self.prevSubtopic = self.subtopicCombo.currentText()

    def validateQuestion(self):
        """ Checks whether question is valid """
        subtopicName = self.subtopicCombo.currentText().strip()
        question = self.questionEdit.text().strip()
        answer = self.answerEdit.toPlainText().strip()
        self.createNoteBtn.setEnabled(bool(subtopicName) and bool(question) and bool(answer))

    def getQuestImgPath(self):
        """ Move foo.png to image data folder """
        if self.diagramPath:
            folder = "data/" + self.courseName + "/images"
            images = sorted([int(os.path.splitext(file)[0]) for file in os.listdir(folder)])

            if images:
                imageNo = images[-1] + 1
            else:
                imageNo = 1

            img = Image.open("images/temp/foo.png")
            img.save(folder + f"/{imageNo}.png")

            return imageNo
        else:
            return 0

    def createNote(self):
        """ Adds note to database """
        # Get data
        subtopicName = self.subtopicCombo.currentText().strip()
        question = self.questionEdit.text().strip()
        answer = self.answerEdit.toPlainText().strip()
        type_ = self.noteType.text()
        questImgNo = self.getQuestImgPath()

        # Modify data
        question = question.replace("'", "`")
        question = question.replace('"', "``")
        answer = answer.replace("'", "`")
        answer = answer.replace('"', "``")
        answer = answer.replace("\n", "<br>")

        # Connect to database
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS notes (noteID integer, type text, question text, answer text, \
        qImageNo integer, ansImagePath text, processID integer, tableID integer, formulaID integer, \
        subTopicID integer, practiceCount integer, correctCount integer, userScore real, starred integer, \
        FOREIGN KEY(subTopicID) REFERENCES subtopics(subTopicID))")
        conn.commit()

        # Get data from database
        c.execute(f"SELECT noteID FROM notes ORDER BY noteID DESC")
        values = [value[0] for value in c.fetchall()]
        if values:
            i = values[0] + 1
        else:
            i = 1

        c.execute(f"SELECT subtopicID FROM subtopics WHERE subtopicName = '{subtopicName}'")
        j = c.fetchone()[0]

        # Append note to database
        if self.noteID in values:
            c.execute(f"DELETE FROM notes WHERE noteID = {self.noteID}")
            i = self.noteID

        c.execute(f"INSERT INTO notes (noteID, type, question, answer, qImageNo, subTopicID, practiceCount, \
                    correctCount, userScore, starred) VALUES ({i}, '{type_}', '{question}', '{answer}', {questImgNo}, \
                    {j}, 0, 0, 0, 0)")
        conn.commit()
        conn.close()

        # Update screen
        self.questionEdit.clear()
        self.answerEdit.clear()
        self.diagramPath = None
        self.nextNote(1)
