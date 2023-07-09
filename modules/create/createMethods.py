import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QKeySequence
import os
import sqlite3
import json
from PIL import Image
import numpy
from math import *
import string
import re
from random import randint
from keyword import kwlist
import subprocess
from table2ascii import table2ascii, PresetStyle

import modules.create.editTopics as editTopics
import modules.create.editSubtopics as editSubtopics
import modules.create.paint as paint
import modules.create.textbookSnipper as textbookSnipper
import modules.create.editFormula as editFormula
import modules.create.editTable as editTable


def validEquation(text):
    """ Returns whether passed in text is a valid equation """
    #  Return variable names in string
    variableText = text
    for index, char in enumerate(text):
        if char.lower() not in list(string.ascii_lowercase) + list(string.digits) + ["_"]:
            variableText = variableText[:index] + " " + variableText[index + 1:]
    variables = [var for var in variableText.split() if not var.isnumeric() and not var[0].isnumeric() and
                 var not in kwlist]
    variables = list(dict.fromkeys(variables))

    # Check whether variable is actually already used as a constant
    for var in variables:
        try:
            eval(var)
        except Exception:
            pass
        else:
            variables.remove(var)

    # Check whether variable is actually a mathematical function
    for var in variables:
        try:
            eval(f"{var}({randint(1, 999999)})")
        except Exception:
            pass
        else:
            variables.remove(var)

    # Validate whether equation is valid
    if text.count("=") == 1 and len(variables) > 1:
        # Give variables a temporary value
        for var in variables:
            exec(f"{var}={randint(1, 999999)}")

        # Split equation
        sep = text.index("=")
        lhs, rhs = text[:sep], text[sep + 1:]

        # Try to evaluate equation
        try:
            eval(lhs)
            eval(rhs)
        except Exception:
            return False
        else:
            # Format variables
            return [{"name": var, "symbol": var, "unit": "units", "min": 1, "max": 100, "step": 1} for var in variables]
    else:
        return False


class CreateWindow(qt.QMainWindow):

    def initWidgets(self):
        """ Main Window """
        self.diagramPath = None
        self.ansDiagramPath = None
        self.noteID = None
        self.creatingNewNote = True
        self.formulaVariables = []
        self.processSteps = []
        self.tableValues = []
        self.formatted = False
        self.type = None

        # Get widgets
        self.topicCombo = self.findChild(qt.QComboBox, "topicCombo")
        self.subtopicCombo = self.findChild(qt.QComboBox, "subtopicCombo")
        self.factBtn = self.findChild(qt.QPushButton, "factBtn")
        self.definitionBtn = self.findChild(qt.QPushButton, "definitionBtn")
        self.formulaBtn = self.findChild(qt.QPushButton, "formulaBtn")
        self.processBtn = self.findChild(qt.QPushButton, "processBtn")
        self.diagramBtn = self.findChild(qt.QPushButton, "diagramBtn")
        self.tableBtn = self.findChild(qt.QPushButton, "tableBtn")
        self.answerEdit = self.findChild(qt.QPlainTextEdit, "answerEdit")
        self.questionEdit = self.findChild(qt.QLineEdit, "questionEdit")
        self.createNoteBtn = self.findChild(qt.QPushButton, "createNoteBtn")
        self.questDiagramBtn = self.findChild(qt.QPushButton, "questDiagramBtn")
        self.prevNoteBtn = self.findChild(qt.QToolButton, "prevNoteBtn")
        self.nextNoteBtn = self.findChild(qt.QToolButton, "nextNoteBtn")
        self.noteNoBox = self.findChild(qt.QSpinBox, "noteNoBox")
        self.noteNoLabel = self.findChild(qt.QLabel, "noteNoLabel")
        self.questLabel = self.findChild(qt.QLabel, "questLabel")
        self.answerLabel = self.findChild(qt.QLabel, "answerLabel")
        self.infoLabel = self.findChild(qt.QLabel, "infoLabel")
        self.buttonLayout = self.findChild(qt.QHBoxLayout, "buttonLayout")
        self.delBtn = self.findChild(qt.QPushButton, "delBtn")
        self.delBtn.setIcon(QIcon("images/trash.png"))
        self.starBtn = self.findChild(qt.QPushButton, "starBtn")
        self.starBtn.setIcon(QIcon("images/star.png"))

        # Create widgets
        self.formatBtn = qt.QPushButton(self)
        self.formatBtn.setText("Format")
        self.formatBtn.setFont(QFont("MS Shell Dlg 2", 10))
        self.formatBtn.setStyleSheet("QPushButton {background-color: #00cac3;border-radius: 10px;color: "
                                     "#F6F7FB;}QPushButton:hover {background-color: rgb(0, 173, 164);}")
        self.formatBtn.setParent(None)

        self.answerDiaBtn = qt.QPushButton(self)
        self.answerDiaBtn.setText("Add Correct Answer Diagram")
        self.answerDiaBtn.setFont(QFont("MS Shell Dlg 2", 10))
        self.answerDiaBtn.setStyleSheet("QPushButton {background-color: #00cac3;border-radius: 10px;color: "
                                        "#F6F7FB;}QPushButton:hover {background-color: rgb(0, 173, 164);}")
        self.answerDiaBtn.setParent(None)

        # Create font
        self.normalFont = QFont("MS Shell Dlg 2")
        self.normalFont.setPointSize(12)
        self.monospaceFont = QFont("Consolas")
        self.monospaceFont.setPointSize(12)

        # Add shortcuts
        qt.QShortcut(QKeySequence("Ctrl+B"), self.answerEdit).activated.connect(self.highlightWord)

        # Bind buttons
        self.subtopicCombo.currentTextChanged.connect(lambda: self.validateQuestion("subtopic"))
        self.questionEdit.textChanged.connect(lambda: self.validateQuestion("question"))
        self.answerEdit.textChanged.connect(lambda: self.validateQuestion("answer"))
        self.createNoteBtn.clicked.connect(self.createNote)
        self.questDiagramBtn.clicked.connect(lambda: self.addQuestPic("initial"))
        self.formatBtn.clicked.connect(self.formatProcess)
        self.answerDiaBtn.clicked.connect(lambda: self.addQuestPic("answer"))
        self.nextNoteBtn.clicked.connect(lambda: self.nextNote(1))
        self.prevNoteBtn.clicked.connect(lambda: self.nextNote(-1))
        self.delBtn.clicked.connect(self.deleteNote)
        self.starBtn.clicked.connect(self.starNote)
        self.noteNoBox.valueChanged.connect(self.spinboxUpdate)
        self.buttons = [self.factBtn, self.definitionBtn, self.formulaBtn, self.processBtn, self.diagramBtn, self.tableBtn]

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

    def spinboxUpdate(self):
        """ Runs when spinbox is updated """
        self.nextNote(self.noteNoBox.value() - self.noteID)

    def starNote(self):
        """ Changes note from unstarred to starred or vice versa """
        self.starBtn.setChecked(self.starBtn.isChecked())

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

            c.execute(f"SELECT aImageNo FROM notes WHERE noteID = {self.noteID}")
            no = c.fetchone()[0]
            if no != 0:
                os.remove(f"data/{self.courseName}/images/{no}.png")

            # If note is a formula
            c.execute(f"SELECT formulaID FROM notes WHERE noteID = {self.noteID}")
            formID = c.fetchone()
            if formID:
                c.execute(f"DELETE FROM formulas WHERE formulaID = {formID[0]}")

            # If note is a process
            c.execute(f"SELECT processID FROM notes WHERE noteID = {self.noteID}")
            processID = c.fetchone()
            if processID:
                c.execute(f"DELETE FROM processes WHERE processID = {processID[0]}")

            c.execute(f"DELETE FROM notes WHERE noteID = {self.noteID}")
            c.execute(f"SELECT noteID FROM notes WHERE noteID>{self.noteID}")
            noteIDs = [i[0] for i in c.fetchall()]
            for i in noteIDs:
                c.execute(f"UPDATE notes SET noteID = {i - 1} WHERE noteID = {i}")
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
            self.noteNoBox.setMinimum(1)
            self.noteNoBox.setMaximum(len(noteList) + 1)
            self.noteNoBox.setValue(self.noteID)
            self.noteNoLabel.setText(f"/{len(noteList)}")

    def nextNote(self, i):
        """ Loads the next load in the database """
        proceed = True
        question = self.questionEdit.text().strip()
        answer = self.answerEdit.toPlainText().strip()
        formatProcessNeeded = False

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
                c.execute(f"SELECT type, question, answer, qImageNo, subtopicID, starred, aImageNo FROM notes \
                WHERE noteID = {self.noteID}")
                record = c.fetchone()
                c.execute(f"SELECT subtopicName, topicID FROM subtopics WHERE subtopicID = {record[4]}")
                results = c.fetchone()
                subtopicName = results[0]
                c.execute(f"SELECT topicName FROM topics WHERE topicID = {results[1]}")
                topicName = c.fetchone()[0]
            except TypeError:
                # New note
                self.questionEdit.clear()
                self.answerEdit.clear()
                self.diagramPath = None
                self.ansDiagramPath = None
                self.tableValues = []
                self.creatingNewNote = True
                self.createNoteBtn.setText("Create Note")
                self.delBtn.setEnabled(False)
                self.starBtn.setChecked(False)
            else:
                # Set values
                self.creatingNewNote = False
                self.questionEdit.setText(record[1])
                self.answerEdit.clear()
                self.answerEdit.insertPlainText(record[2].replace("`", "'"))

                if record[0] == "Process":
                    # Import process steps
                    c.execute(f"SELECT processID FROM notes WHERE noteID = {self.noteID}")
                    processID = c.fetchone()[0]
                    c.execute(f"SELECT step FROM processes WHERE processID = {processID} ORDER BY stepNo")
                    self.answerEdit.appendHtml("<br>".join([step[0] for step in c.fetchall()]))
                    formatProcessNeeded = True
                conn.close()

                imageNo = record[3]
                if imageNo != 0:
                    img = Image.open("data/" + self.courseName + "/images" + f"/{imageNo}.png")
                    self.diagramPath = "images/temp/foo.png"
                    img.save(self.diagramPath)
                    img.save("images/temp/foo2.png")
                else:
                    self.diagramPath = None

                imageNo = record[6]
                if imageNo != 0:
                    img = Image.open("data/" + self.courseName + "/images" + f"/{imageNo}.png")
                    self.ansDiagramPath = "images/temp/foo2.png"
                    img.save(self.ansDiagramPath)
                else:
                    self.ansDiagramPath = None

                for button in self.buttons:
                    if button.text() == record[0]:
                        self.noteType.setChecked(False)
                        self.noteType = button
                        self.noteType.setChecked(True)

                self.topicCombo.setCurrentText(topicName)
                self.subtopicCombo.setCurrentText(subtopicName)
                self.createNoteBtn.setText("Save Note")
                self.delBtn.setEnabled(True)
                self.starBtn.setChecked(record[5])
                self.makeWordsBold()

            # Update navigation buttons
            self.updateDiagramBtn()
            self.updateNoteNav()
            self.changeNoteType(focus=False)
            if formatProcessNeeded:
                self.formatProcess()

    def updateDiagramBtn(self):
        """ Changes text depending on whether an image is saved """
        if self.noteType == self.diagramBtn:
            text = "Initial"
        else:
            text = "Question"

        if self.diagramPath:
            self.questDiagramBtn.setText(f"Modify {text} Diagram")
            self.answerDiaBtn.setEnabled(True)
        else:
            self.questDiagramBtn.setText(f"Add {text} Diagram")

        if self.ansDiagramPath:
            self.answerDiaBtn.setText("Modify Answer Diagram")
        else:
            self.answerDiaBtn.setText("Add Answer Diagram")

    def addQuestPic(self, path):
        """ Opens window for adding a picture to the question """
        if (path == "initial" and self.diagramPath and self.diagramPath != "blank") or \
                (path == "answer" and self.ansDiagramPath):
            with open("text/currentSettings.json") as f:
                data = json.load(f)

                if path == "answer":
                    imagePath = "images/temp/foo2.png"
                else:
                    imagePath = "images/temp/foo.png"

            if (os.path.exists(data["editorPath"][0]) or data["editorPath"][0] == "mspaint") and data["editorPath"][1]:
                # Open external application
                cwd = os.getcwd()
                os.chdir(os.path.join(os.getcwd(), "images/temp/").replace("\\", "/"))
                p = subprocess.Popen([data["editorPath"][0], os.path.basename(imagePath)])
                os.chdir(cwd)
                self.hide()

                # Reopen application
                p.wait()
                # Open messagebox
                msg = qt.QMessageBox()
                msg.setWindowTitle("Use drawing?")
                msg.setText("Would you like you use your drawing?")
                msg.setIcon(qt.QMessageBox.Question)
                msg.buttonClicked.connect(self.drawingFate)
                msg.addButton("Save", qt.QMessageBox.YesRole)
                msg.addButton("Delete", qt.QMessageBox.NoRole)
                self.type = path
                x = msg.exec_()

            else:
                # Open paint application
                self.w = paint.Window(self, imagePath, path, self.paintOptionSelected)
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

            if self.noteType == self.diagramBtn:
                # Diagram question
                if self.textbookPath[0]:
                    # Textbook added
                    if path == "initial":
                        msg.setInformativeText("Click 'Snip' to take a Snippet from the Textbook\n\n" +
                                               "Click 'Blank' to start note with a blank canvas")
                        msg.addButton("Snip", qt.QMessageBox.YesRole)
                        msg.addButton("Open", qt.QMessageBox.NoRole)
                        msg.addButton("Blank", qt.QMessageBox.ActionRole)
                        msg.addButton("Cancel", qt.QMessageBox.RejectRole)
                    else:
                        if self.diagramPath == "blank":
                            # Textbook and no initial diagram
                            msg.setInformativeText("Click 'Snip' to take a Snippet from the Textbook")
                            msg.addButton("Snip", qt.QMessageBox.YesRole)
                            msg.addButton("Open", qt.QMessageBox.NoRole)
                            msg.addButton("Cancel", qt.QMessageBox.RejectRole)
                        else:
                            # Textbook and initial diagram
                            msg.setInformativeText("Click 'Apply' to use Snippet from the Initial Diagram\n\n" +
                                                   "Click 'Snip' to take a Snippet from the Textbook")
                            msg.addButton("Apply", qt.QMessageBox.YesRole)
                            msg.addButton("Snip", qt.QMessageBox.NoRole)
                            msg.addButton("Open", qt.QMessageBox.ActionRole)
                            msg.addButton("Cancel", qt.QMessageBox.RejectRole)

                else:
                    if path == "initial":
                        # Textbook not added
                        msg.setInformativeText("Click 'Ignore' to start note with a blank canvas")
                        msg.addButton("Blank", qt.QMessageBox.YesRole)
                        msg.addButton("Open", qt.QMessageBox.NoRole)
                        msg.addButton("Cancel", qt.QMessageBox.RejectRole)
                    else:
                        if self.diagramPath == "blank":
                            # No textbook and no initial diagram
                            msg.setStandardButtons(qt.QMessageBox.Open | qt.QMessageBox.Cancel)
                        else:
                            # No textbook and initial diagram
                            msg.setInformativeText("Click 'Apply' to use Snippet from the Initial Diagram")
                            msg.addButton("Apply", qt.QMessageBox.YesRole)
                            msg.addButton("Open", qt.QMessageBox.ActionRole)
                            msg.addButton("Cancel", qt.QMessageBox.RejectRole)
            else:
                # Non-diagram question
                if self.textbookPath[0]:
                    # Textbook added
                    msg.setInformativeText("Click 'Snip' to take a Snippet from the Textbook")
                    msg.addButton("Snip", qt.QMessageBox.YesRole)
                    msg.addButton("Open", qt.QMessageBox.NoRole)
                    msg.addButton("Cancel", qt.QMessageBox.RejectRole)
                else:
                    # Textbook not added
                    msg.setStandardButtons(qt.QMessageBox.Open | qt.QMessageBox.Cancel)

            x = msg.exec_()

    def popUp_quest(self, i):
        if self.diagramPath:
            # Answer diagram
            _type = "answer"
        else:
            _type = "initial"

        # Initial diagram
        if i.text() == "Snip":
            # Navigate to PDF screenshot window
            self.takeTextbookSnip(_type)
        elif i.text() == "Apply":
            self.uploadQuestFile("answer", fName="images/temp/foo2.png")
        elif i.text() == "Open":
            # Navigate to file dialog
            self.uploadQuestFile(_type)
        elif i.text() == "Blank":
            # Use blank canvas
            self.diagramPath = "blank"
            self.paintOptionSelected("initial", self.diagramPath)

    def paintOptionSelected(self, _type, option):
        """ Runs when paint window is closed """
        if _type == "initial":
            if option == "save":
                # Save image
                self.diagramPath = "images/temp/foo.png"
            elif option == "delete":
                # Delete image
                self.diagramPath = None
        else:
            if option == "save":
                # Save image
                self.ansDiagramPath = "images/temp/foo2.png"
            elif option == "delete":
                # Delete image
                self.ansDiagramPath = None

        self.updateDiagramBtn()
        self.answerDiaBtn.setEnabled(self.diagramPath is not None or self.ansDiagramPath is not None)
        self.validateQuestion("diagram")

    def takeTextbookSnip(self, _type):
        """ Opens window to take snippet from current textbook page """
        path = "images/temp/snip.png"
        img = Image.open(self.tempPath)
        img.save(path)
        self.w = textbookSnipper.Window(self, path, self.uploadQuestFile, _type, self.noteType == self.diagramBtn)
        self.w.show()
        self.hide()

    def drawingFate(self, i):
        if i.text() == "Save":
            self.paintOptionSelected(self.type, "save")
        elif i.text() == "Delete":
            self.paintOptionSelected(self.type, "delete")
        self.show()

    def uploadQuestFile(self, _type, fName=None):
        """ Opens file dialog to select picture """
        with open("text/currentSettings.json") as f:
            data = json.load(f)

        if _type == "answer":
            imagePath = "images/temp/foo2.png"
        else:
            imagePath = "images/temp/foo.png"

        if not fName:
            fName, _ = qt.QFileDialog.getOpenFileName(self, "Select Picture", data["picturePath"],
                                                      "Image files (*.png *.jpg *.jpeg *.gif *.bmp)")
            upload = True
        else:
            upload = False

        if fName:
            # Create image
            img = Image.open(fName)
            if (os.path.exists(data["editorPath"][0]) or data["editorPath"][0] == "mspaint") and data["editorPath"][1]:
                if upload:
                    img.save(imagePath)
                else:
                    t = 20
                    image = Image.new("RGB", (img.width + 2 * t, img.height + 2 * t), "#ffffff")
                    image.paste(img, (t, t, t + img.width, t + img.height))
                    image.save(imagePath)

                # Open external application
                cwd = os.getcwd()
                os.chdir(os.path.join(os.getcwd(), "images/temp/").replace("\\", "/"))
                p = subprocess.Popen([data["editorPath"][0], os.path.basename(imagePath)])
                os.chdir(cwd)
                self.hide()

                # Reopen application
                p.wait()

                # Open messagebox
                msg = qt.QMessageBox()
                msg.setWindowTitle("Use drawing?")
                msg.setText("Would you like you use your drawing?")
                msg.setIcon(qt.QMessageBox.Question)
                msg.buttonClicked.connect(self.drawingFate)
                msg.addButton("Save", qt.QMessageBox.YesRole)
                msg.addButton("Delete", qt.QMessageBox.NoRole)
                self.type = _type
                x = msg.exec_()

            else:
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
                        scale = (w - 2 * t) / img.width
                    else:
                        # Height is biggest
                        scale = (w - 2 * t) / img.height

                    # New values
                    width = int(img.width * scale)
                    height = int(img.height * scale)
                    x = int((w - width) / 2)
                    y = int((h - height) / 2)

                    if x <= y:
                        x = int(t / 2)
                    else:
                        y = int(t / 2)

                    img = img.resize((width, height))
                elif (img.width / w) < 0.5 and (img.height / h) < 0.5:
                    # If image is too small, then make it bigger
                    img = img.resize((img.width * 2, img.height * 2))
                    x = int((w - img.width) / 2)
                    y = int((h - img.height) / 2)

                image.paste(img, (x, y, x + img.width, y + img.height))
                image.save(imagePath)

                # Open paint application
                self.w = paint.Window(self, imagePath, _type, self.paintOptionSelected)
                self.w.show()
                self.hide()

    def highlightWord(self):
        """ Highlights word """
        if self.noteType in [self.factBtn, self.definitionBtn, self.processBtn]:
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
        for line in self.answerEdit.toPlainText().split("\n"):
            for word in line.split():
                if word[0] == "*" and word[-1] == "*":
                    # Word is bold
                    newText += f"<b>{word}</b> "
                else:
                    # Regular word
                    newText += f"{word} "
            newText += "<br>"
        newText = newText[:-4]
        self.answerEdit.clear()
        self.answerEdit.appendHtml("<html>" + newText + "<html>")
        cursor.setPosition(i)
        self.answerEdit.setTextCursor(cursor)

    def changeNoteType(self, focus=True):
        """ Changes the stylesheet of selected button """
        if focus:
            if self.noteType == self.sender():
                self.noteType.setChecked(True)
            else:
                self.noteType.setChecked(False)
                self.noteType = self.sender()

        self.formatBtn.setParent(None)
        self.answerDiaBtn.setParent(None)
        self.answerLabel.setEnabled(True)
        self.answerEdit.setEnabled(True)
        self.answerEdit.setReadOnly(False)
        self.answerEdit.setFont(self.normalFont)
        self.answerEdit.setLineWrapMode(qt.QPlainTextEdit.WidgetWidth)

        # Change button depending on note type
        if self.noteType == self.formulaBtn:
            self.questDiagramBtn.setText("Define Formula Terms")
            self.questDiagramBtn.disconnect()
            self.questDiagramBtn.clicked.connect(self.addFormulaTerms)
            self.infoLabel.setText("Enter the Formula")
            self.questDiagramBtn.setEnabled(False)
            self.questLabel.setEnabled(False)
            self.questionEdit.setEnabled(False)
            self.answerLabel.setText("Formula:")

            if not focus:
                # Formula is being loaded
                conn = sqlite3.connect(self.databasePath)
                c = conn.cursor()

                # Get formula id
                c.execute(f"SELECT formulaID FROM notes WHERE noteID = {self.noteID}")
                formID = c.fetchone()
                if formID:
                    c.execute(f"SELECT name, symbol, unit, min, max, step FROM formulas WHERE formulaID = {formID[0]}")
                    self.formulaVariables = [{"name": term[0], "symbol": term[1], "unit": term[2], "min": term[3],
                                              "max": term[4], "step": term[5]} for term in c.fetchall()]
                conn.close()

            self.validateQuestion("type")

        elif self.noteType == self.tableBtn:
            self.questDiagramBtn.disconnect()
            self.questDiagramBtn.clicked.connect(self.modifyTable)
            self.validateQuestion("table")
            self.questDiagramBtn.setEnabled(True)
            self.answerEdit.clear()
            self.answerEdit.setReadOnly(True)
            self.answerEdit.setFont(self.monospaceFont)
            self.answerEdit.setLineWrapMode(qt.QPlainTextEdit.NoWrap)

            if not focus:
                # Table is being loaded
                conn = sqlite3.connect(self.databasePath)
                c = conn.cursor()

                # Get table id
                c.execute(f"SELECT tableID FROM notes WHERE noteID = {self.noteID}")
                tableID = c.fetchone()
                if tableID:
                    c.execute(f"SELECT rowNo, colNo, textVal, userFill FROM tableElements WHERE tableID = {tableID[0]} "
                              "ORDER BY rowNo, colNo")
                    values = c.fetchall()
                    noRows, noCols = values[-1][0] + 1, values[-1][1] + 1

                    self.tableValues = [[{"text": "", "userFill": False} for _ in range(noCols)] for _ in range(noRows)]
                    for cell in values:
                        i, j = cell[0], cell[1]
                        self.tableValues[i][j]["text"] = cell[2].replace("`", "'")
                        self.tableValues[i][j]["userFill"] = cell[3]

                conn.close()

            if self.tableValues:
                self.displayTable()

        else:
            self.updateDiagramBtn()
            self.questDiagramBtn.disconnect()
            self.questDiagramBtn.clicked.connect(lambda: self.addQuestPic("initial"))
            self.infoLabel.setText("Press CTRL+B to make Highlighted Text Bold")
            self.questDiagramBtn.setEnabled(True)
            self.questLabel.setEnabled(True)
            self.questionEdit.setEnabled(True)
            self.answerLabel.setText("Answer:")
            self.validateQuestion("type")

            # Add format button for processes
            if self.noteType == self.processBtn:
                self.questDiagramBtn.setParent(None)
                self.buttonLayout.addWidget(self.formatBtn)
                self.buttonLayout.addWidget(self.questDiagramBtn)

            elif self.noteType == self.diagramBtn:
                self.answerLabel.setEnabled(False)
                self.answerEdit.setEnabled(False)
                self.infoLabel.setText("Add a diagram to your note")
                self.buttonLayout.addWidget(self.answerDiaBtn)
                self.questDiagramBtn.setText("Add Initial Diagram")
                self.answerDiaBtn.setEnabled(False)
                self.updateDiagramBtn()

    def modifyTable(self):
        """ Opens table window """
        self.w = editTable.Window(self, self.tableValues, self.tableSubmitted)
        self.w.show()
        self.hide()

    def displayTable(self):
        """ Displays ASCII table """
        output = table2ascii(
            header=[cell["text"] for cell in self.tableValues[0]],
            body=[[cell["text"] for cell in row] for row in self.tableValues[1:]],
            style=PresetStyle.ascii_box
        ).split("\n")

        self.answerEdit.clear()
        self.answerEdit.setFont(self.monospaceFont)
        for line in output:
            self.answerEdit.appendPlainText(line)

    def tableSubmitted(self, values):
        """ Updates table """
        self.tableValues = values
        if self.tableValues:
            self.displayTable()
        self.validateQuestion("table")

    def formatProcess(self):
        """ Auto-formats answer into ordered process """
        self.processSteps = [line.strip() for line in self.answerEdit.toPlainText().split("\n") if line.strip() != ""]

        # Clean steps
        for i, step in enumerate(self.processSteps):
            no = re.findall(r"\d+\. |\d+\) ", step)
            for n in no:
                if step[:len(n)] == n:
                    step = step[len(n):]
            self.processSteps[i] = step

        self.answerEdit.clear()
        text = "<br>".join([f"{i}. {line}" for i, line in enumerate(self.processSteps, start=1)])
        self.answerEdit.appendHtml(text)
        self.formatted = True
        self.validateQuestion("format")

    def addFormulaTerms(self):
        """ Opens window to allow user to define formula terms """
        self.w = editFormula.Window(self, self.formulaVariables, self.validateFormula)
        self.w.show()
        self.hide()

    def validateFormula(self, terms):
        """ Checks whether the values for the formula has been filled in """
        self.formulaVariables = terms

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

    def validateQuestion(self, updated):
        """ Checks whether question is valid """
        subtopicName = self.subtopicCombo.currentText().strip()
        question = self.questionEdit.text().strip()
        answer = self.answerEdit.toPlainText().strip()
        if updated == "answer":
            self.formatted = False

        if self.noteType == self.formulaBtn:
            if answer == "":
                self.infoLabel.setText("Enter the Formula")
            else:
                # Calculate whether entered formula is valid
                valid = validEquation(answer)
                if valid:
                    self.infoLabel.setText("Valid Formula  ✅")
                    self.questDiagramBtn.setEnabled(True)
                    self.createNoteBtn.setEnabled(True)

                    # Use old variable data
                    oldSymbols = [s["symbol"] for s in self.formulaVariables]
                    for i, var in enumerate(valid):
                        if var["symbol"] in oldSymbols:
                            valid[i] = self.formulaVariables[oldSymbols.index(var["symbol"])]

                    self.formulaVariables = valid

                else:
                    self.infoLabel.setText("Invalid Formula ❌")
                    self.questDiagramBtn.setEnabled(False)
                    self.createNoteBtn.setEnabled(False)

        elif self.noteType == self.processBtn:
            self.formatBtn.setEnabled(answer != "")
            self.createNoteBtn.setEnabled(bool(subtopicName) and bool(question) and self.formatted)

        elif self.noteType == self.diagramBtn:
            self.createNoteBtn.setEnabled(bool(question) and self.diagramPath is not None and
                                          self.ansDiagramPath is not None)

        elif self.noteType == self.tableBtn:
            if not self.tableValues:
                self.infoLabel.setText("Click 'Define Table' to create table")
                self.questDiagramBtn.setText("Define Table")
            elif not bool(question):
                self.infoLabel.setText("Enter a question for the note")
                self.questDiagramBtn.setText("Edit Table")
            else:
                self.infoLabel.setText("Click 'Edit Table' to modify table")
                self.questDiagramBtn.setText("Edit Table")

            self.createNoteBtn.setEnabled(bool(question) and bool(self.tableValues))

        else:
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

            if self.diagramPath == "blank":
                # No image was created yet
                image = Image.open("images/temp/foo2.png")
                img = Image.new("RGB", (image.width, image.height), "#ffffff")
            else:
                img = Image.open("images/temp/foo.png")

            img.save(folder + f"/{imageNo}.png")

            return imageNo
        else:
            return 0

    def getAnsImgPath(self):
        """ Move foo2.png to image data folder """
        if self.ansDiagramPath:
            folder = "data/" + self.courseName + "/images"
            images = sorted([int(os.path.splitext(file)[0]) for file in os.listdir(folder)])

            if images:
                imageNo = images[-1] + 1
            else:
                imageNo = 1

            img = Image.open("images/temp/foo2.png")
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
        ansImgNo = self.getAnsImgPath()
        formID = 0
        processID = 0
        tableID = 0

        # Modify data
        question = question.replace("'", "`")
        question = question.replace('"', "``")
        answer = answer.replace("'", "`")
        answer = answer.replace('"', "``")
        answer = answer.replace("\n", "<br>")

        if type_ in ["Process", "Diagram", "Table"]:
            answer = ""

        # Connect to database
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS notes (noteID integer, type text, question text, answer text, \
        qImageNo integer, aImageNo integer, processID integer, tableID integer, formulaID integer, \
        subTopicID integer, practiceCount integer, correctCount integer, userScore real, starred integer, \
        FOREIGN KEY(subTopicID) REFERENCES subtopics(subTopicID))")

        c.execute("CREATE TABLE IF NOT EXISTS formulas (formulaID integer, name text, symbol text, unit text, \
        min real, max real, step real)")

        c.execute("CREATE TABLE IF NOT EXISTS processes (processID integer, stepNo integer, step text)")
        conn.commit()

        c.execute("CREATE TABLE IF NOT EXISTS tableElements (tableID integer, rowNo integer, ColNo integer, "
                  "textVal text, userFill integer)")
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
            if type_ == "Formula":
                # Delete old formula terms
                c.execute(f"SELECT formulaID FROM notes WHERE noteID = {self.noteID}")
                formID = c.fetchone()[0]
                try:
                    c.execute(f"DELETE FROM formulas WHERE formulaID = {formID}")
                except Exception:
                    conn.close()
                    conn = sqlite3.connect(self.databasePath)
                    c = conn.cursor()
                    c.execute(f"DELETE FROM formulas WHERE formulaID = {formID}")

            elif type_ == "Process":
                # Delete old process terms
                c.execute(f"SELECT processID FROM notes WHERE noteID = {self.noteID}")
                processID = c.fetchone()[0]
                try:
                    c.execute(f"DELETE FROM processes WHERE processID = {processID}")
                except Exception:
                    conn.close()
                    conn = sqlite3.connect(self.databasePath)
                    c = conn.cursor()
                    c.execute(f"DELETE FROM processes WHERE processID = {processID}")

            elif type_ == "Table":
                # Delete old table terms
                c.execute(f"SELECT tableID FROM notes WHERE noteID = {self.noteID}")
                tableID = c.fetchone()[0]
                try:
                    c.execute(f"DELETE FROM tableElements WHERE tableID = {tableID}")
                except Exception:
                    conn.close()
                    conn = sqlite3.connect(self.databasePath)
                    c = conn.cursor()
                    c.execute(f"DELETE FROM tableElements WHERE tableID = {tableID}")

            try:
                c.execute(f"DELETE FROM notes WHERE noteID = {self.noteID}")
                i = self.noteID
            except Exception:
                conn.close()
                conn = sqlite3.connect(self.databasePath)
                c = conn.cursor()
                c.execute(f"DELETE FROM notes WHERE noteID = {self.noteID}")
                i = self.noteID

        elif type_ == "Formula":
            # Work out the new form id
            c.execute(f"SELECT formulaID FROM formulas ORDER BY formulaID DESC")
            formID = c.fetchone()
            if formID:
                formID = formID[0] + 1
            else:
                formID = 1

        elif type_ == "Process":
            # Work out the new form id
            c.execute(f"SELECT processID FROM processes ORDER BY processID DESC")
            processID = c.fetchone()
            if processID:
                processID = processID[0] + 1
            else:
                processID = 1

        elif type_ == "Table":
            # Work out the new form id
            c.execute(f"SELECT tableID FROM tableElements ORDER BY tableID DESC")
            tableID = c.fetchone()
            if tableID:
                tableID = tableID[0] + 1
            else:
                tableID = 1

        c.execute(f"INSERT INTO notes (noteID, type, question, answer, qImageNo, aImageNo, formulaID, processID, \
        tableID, subTopicID, practiceCount, correctCount, userScore, starred) VALUES ({i}, '{type_}', '{question}', \
        '{answer}', {questImgNo}, {ansImgNo}, {formID}, {processID}, {tableID}, {j}, 0, 0, 0, \
        {self.starBtn.isChecked()})")

        # Insert new formula terms
        if type_ == "Formula":
            for term in self.formulaVariables:
                name, symbol, unit = term["name"], term["symbol"], term["unit"]
                min_, max_, step = term["min"], term["max"], term["step"]

                c.execute(f"INSERT INTO formulas (formulaID, name, symbol, unit, min, max, step) VALUES \
                ({formID}, '{name}', '{symbol}', '{unit}', {min_}, {max_}, {step})")

        elif type_ == "Process":
            for i, step in enumerate(self.processSteps, start=1):
                step = step.strip().replace("'", "`").replace('"', "`")
                c.execute(
                    f"INSERT INTO processes (processID, stepNo, step) VALUES ({processID}, {i}, '{step}')")

        elif type_ == "Table":
            for i in range(len(self.tableValues)):
                for j in range(len(self.tableValues[0])):
                    item = self.tableValues[i][j]
                    text = item["text"].strip().replace("'", "`").replace('"', "`")
                    userFill = int(item["userFill"])
                    c.execute(f"INSERT INTO tableElements (tableID, rowNo, ColNo, textVal, userFill) VALUES \
                    ({tableID}, {i}, {j}, '{text}', {userFill})")

        conn.commit()
        conn.close()

        # Update screen
        self.questionEdit.clear()
        self.answerEdit.clear()
        self.diagramPath = None
        self.ansDiagramPath = None
        self.tableValues = []
        self.nextNote(1)
