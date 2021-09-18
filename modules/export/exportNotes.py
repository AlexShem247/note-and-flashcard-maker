import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QPen, QBrush
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QCategoryAxis
from PyQt5 import uic
import os
import sys
import docx
import webbrowser
import sqlite3
import json
import shutil
from distutils.dir_util import copy_tree
import subprocess
import zipfile


class Doc:
    def __init__(self):
        self.doc = docx.Document()
        self.paragraphNo = 0

        sections = self.doc.sections
        for section in sections:
            section.top_margin = docx.shared.Cm(1.27)
            section.bottom_margin = docx.shared.Cm(1.27)
            section.left_margin = docx.shared.Cm(1.27)
            section.right_margin = docx.shared.Cm(1.27)

        # Create styles
        obj_styles = self.doc.styles

        # Document Title
        obj_charstyle = obj_styles.add_style("0", docx.enum.style.WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.bold, obj_font.italic, obj_font.underline = True, False, True
        obj_font.name, obj_font.size = "Arial Black", docx.shared.Pt(36)

        # Heading
        obj_charstyle = obj_styles.add_style("1", docx.enum.style.WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.bold, obj_font.italic, obj_font.underline = True, False, True
        obj_font.name, obj_font.size = "Arial", docx.shared.Pt(24)

        # Subtitle
        obj_charstyle = obj_styles.add_style("2", docx.enum.style.WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.bold, obj_font.italic, obj_font.underline = False, True, False
        obj_font.name, obj_font.size = "Arial", docx.shared.Pt(18)

        # Fact Question
        obj_charstyle = obj_styles.add_style("3", docx.enum.style.WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.bold, obj_font.italic, obj_font.underline = True, True, False
        obj_font.name, obj_font.size = "Arial", docx.shared.Pt(12)
        obj_font.color.rgb = docx.shared.RGBColor.from_string("4F81BD")

        # Definition Question
        obj_charstyle = obj_styles.add_style("4", docx.enum.style.WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.bold, obj_font.italic, obj_font.underline = True, True, False
        obj_font.name, obj_font.size = "Arial", docx.shared.Pt(12)
        obj_font.color.rgb = docx.shared.RGBColor.from_string("8064A2")

        # Text
        obj_charstyle = obj_styles.add_style("5", docx.enum.style.WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.bold, obj_font.italic, obj_font.underline = False, False, False
        obj_font.name, obj_font.size = "Arial", docx.shared.Pt(12)

        # Bold Text
        obj_charstyle = obj_styles.add_style("6", docx.enum.style.WD_STYLE_TYPE.CHARACTER)
        obj_font = obj_charstyle.font
        obj_font.bold, obj_font.italic, obj_font.underline = True, False, False
        obj_font.name, obj_font.size = "Arial", docx.shared.Pt(12)

    def addTitle(self, text):
        """Adds paragraph to document"""
        paragraph = self.doc.add_paragraph("")
        paragraph.add_run(text, style="0")

    def addHeading(self, text):
        """Adds paragraph to document"""
        paragraph = self.doc.add_paragraph("")
        paragraph.add_run("", style="1")
        paragraph = self.doc.add_paragraph("")
        paragraph.add_run(text, style="1")

    def addSubheading(self, text):
        """Adds paragraph to document"""
        paragraph = self.doc.add_paragraph("")
        paragraph.add_run(text, style="2")

    def addFact(self, questionText, answerText):
        """Adds paragraph to document"""
        paragraph = self.doc.add_paragraph("")
        paragraph.add_run(questionText + ": ", style="3")
        for i, text in enumerate(answerText):
            for word in text.split():

                if word[0] == "*":
                    _style = "6"
                    text = text[1:-1]
                else:
                    _style = "5"

                paragraph.add_run(word + " ", style=_style)

            if i < len(answerText) - 1:
                paragraph = self.doc.add_paragraph("")

    def addDef(self, questionText, answerText):
        """Adds paragraph to document"""
        paragraph = self.doc.add_paragraph("")
        paragraph.add_run(questionText + ": ", style="4")
        for i, text in enumerate(answerText):
            for word in text.split():

                if word[0] == "*":
                    _style = "6"
                    word = word[1:-1]
                else:
                    _style = "5"

                paragraph.add_run(word + " ", style=_style)

            if i < len(answerText) - 1:
                paragraph = self.doc.add_paragraph("")

    def save(self, filename):
        """Exports document"""
        self.doc.save(filename)


class Window(qt.QMainWindow):

    def __init__(self, superClass, course, color):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/exportNotes.ui", self)
        self.superClass = superClass
        self.courseName = course
        self.color = color
        self.databasePath = "data/" + course + "/courseData.db"
        self.updateTitleColor()
        self.show()

        # Get widgets
        importBtn = self.findChild(qt.QPushButton, "importBtn")
        wordBtn = self.findChild(qt.QPushButton, "wordBtn")
        dataBtn = self.findChild(qt.QPushButton, "dataBtn")

        # Add Icons
        importBtn.setIcon(QIcon("images/import.png"))
        importBtn.setIconSize(QSize(50, 50))
        wordBtn.setIcon(QIcon("images/doc.png"))
        wordBtn.setIconSize(QSize(50, 50))
        dataBtn.setIcon(QIcon("images/zip.png"))
        dataBtn.setIconSize(QSize(50, 50))

        # Bind widgets
        importBtn.clicked.connect(self.showImportOptions)
        wordBtn.clicked.connect(self.convertToDoc)
        dataBtn.clicked.connect(self.exportNotesToZip)

        # Check for notes
        conn = sqlite3.connect(self.databasePath)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        notes = c.fetchall()
        conn.commit()
        conn.close()

        # Update buttons
        wordBtn.setEnabled(bool(notes))
        dataBtn.setEnabled(bool(notes))


    def importNotes(self, fName, merge):
        """ Imports notes """
        unzipPath = os.path.dirname(fName) + "/unzip"
        dataFilepath = f"data/{self.courseName}"

        # Delete folder if exists
        if os.path.exists(unzipPath) and os.path.isdir(unzipPath):
            shutil.rmtree(unzipPath)

        # Unzip folder
        with zipfile.ZipFile(fName, "r") as zip_ref:
            zip_ref.extractall(unzipPath)

        if "images" in os.listdir(unzipPath) and "courseData.db" in os.listdir(unzipPath):
            # Correctly formatted zip
            if not merge:
                # Delete current files and replace with new files
                os.remove(f"{dataFilepath}/courseData.db")
                shutil.rmtree(f"{dataFilepath}/images")

                # Modify database file
                conn = sqlite3.connect(f"{unzipPath}/courseData.db")
                c = conn.cursor()
                c.execute("UPDATE notes SET practiceCount = 0, correctCount = 0, userScore = 0, starred = 0")
                conn.commit()
                conn.close()

                # Move files
                shutil.move(f"{unzipPath}/courseData.db", f"{dataFilepath}/courseData.db")
                shutil.move(f"{unzipPath}/images", f"{dataFilepath}")

            else:
                # Get number of current database images
                conn = sqlite3.connect(self.databasePath)
                c = conn.cursor()
                c.execute("SELECT qImageNo FROM notes WHERE qImageNo > 0 ORDER BY qImageNo DESC")
                imageNo = c.fetchone()[0]
                c.execute("SELECT topicID FROM topics ORDER BY topicID DESC")
                topicNo = c.fetchone()[0]
                c.execute("SELECT subtopicID FROM subtopics ORDER BY subtopicID DESC")
                subtopicsNo = c.fetchone()[0]
                c.execute("SELECT noteID FROM notes ORDER BY noteID DESC")
                notesNo = c.fetchone()[0]
                conn.close()

                # Get number of new images
                conn = sqlite3.connect(f"{unzipPath}/courseData.db")
                c = conn.cursor()
                c.execute("SELECT qImageNo FROM notes WHERE qImageNo > 0 ORDER BY qImageNo DESC")
                newImageNo = c.fetchone()

                if imageNo and newImageNo:
                    # Increment images in database
                    c.execute(f"UPDATE notes SET qImageNo = qImageNo + {imageNo} WHERE qImageNo > 0")
                    c.execute(f"UPDATE topics SET topicID = topicID + {topicNo}")
                    c.execute(f"UPDATE subtopics SET topicID = topicID + {topicNo}")
                    c.execute(f"UPDATE subtopics SET subtopicID = subtopicID + {subtopicsNo}")
                    c.execute(f"UPDATE notes SET subtopicID = subtopicID + {subtopicsNo}")
                    c.execute(f"UPDATE notes SET noteID = noteID + {notesNo}")
                    conn.commit()

                    # Increment image in folder
                    n = len(os.listdir(f"{unzipPath}/images"))
                    for i in reversed(range(1, n + 1)):
                        os.rename(f"{unzipPath}/images/{i}.png", f"{unzipPath}/images/{i+imageNo}.png")

                    # Merge notes
                    for file in os.listdir(f"{unzipPath}/images"):
                        shutil.move(f"{unzipPath}/images/{file}", f"{dataFilepath}/images/{file}")

                    # Merge databases
                    c.execute("SELECT * FROM topics")
                    topicTable = c.fetchall()
                    c.execute("SELECT * FROM subtopics")
                    subtopicTable = c.fetchall()
                    c.execute("SELECT noteID, type, question, answer, qImageNo, subtopicID FROM notes")
                    noteTable = c.fetchall()

                    conn = sqlite3.connect(self.databasePath)
                    c = conn.cursor()

                    for topic in topicTable:
                        a, b = topic
                        c.execute(f"INSERT INTO topics (topicID, topicName) VALUES ({a}, '{b}')")

                    for subtopic in subtopicTable:
                        a, b, d = subtopic
                        c.execute(f"INSERT INTO subtopics (subtopicID, subtopicName, topicID) VALUES ({a}, '{b}', {d})")

                    for note in noteTable:
                        i, type_, question, answer, questImgNo, j = note
                        c.execute(f"INSERT INTO notes (noteID, type, question, answer, qImageNo, subTopicID, \
                        practiceCount, correctCount, userScore, starred) VALUES ({i}, '{type_}', '{question}', \
                        '{answer}', {questImgNo}, {j}, 0, 0, 0, 0)")

                    conn.commit()

                conn.close()
                os.remove(fName)

            qt.QMessageBox.information(self, "Success", "Files have been Successfully Imported", qt.QMessageBox.Ok)

        else:
            # Incorrect file uploaded
            qt.QMessageBox.critical(self, "Error", "Incorrectly formatted file", qt.QMessageBox.Ok)

        shutil.rmtree(unzipPath)


    def showImportOptions(self):
        """ Allows user to import notes """
        with open("text/currentSettings.json") as f:
            data = json.load(f)

        fName, _ = qt.QFileDialog.getOpenFileName(self, "Select Notes Zip", data["textbookPath"], "Zip files (*.zip)")

        if fName:
            # Ask whether they want to replace notes or merge notes
            reply = qt.QMessageBox.question(self, "Import Options",
                                            "Would you like to Merge new Notes with existing notes",
                                            qt.QMessageBox.Yes | qt.QMessageBox.No | qt.QMessageBox.Cancel)

            if reply == qt.QMessageBox.Yes:
                # Merge notes
                self.importNotes(fName, merge=True)

            elif reply == qt.QMessageBox.No:
                check = qt.QMessageBox.warning(self, "Are you sure?", "All existing Notes will be lost",
                                               qt.QMessageBox.Yes | qt.QMessageBox.Cancel)

                if check == qt.QMessageBox.Yes:
                    # Delete notes and replace with new ones
                    self.importNotes(fName, merge=False)

    def exportNotesToZip(self):
        """ Sends notes folder to zip """
        with open("text/currentSettings.json") as f:
            data = json.load(f)

        filename = str(qt.QFileDialog.getExistingDirectory(self, "Select where to save Notes", data["textbookPath"]))

        # Duplicate folder
        directoryName = f"images/temp/{self.courseName}"
        copy_tree(f"data/{self.courseName}", f"images/temp/{self.courseName}")
        os.remove(f"images/temp/{self.courseName}/courseInfo.json")

        # Save zip
        zipName = f"{filename}/{self.courseName}"
        shutil.make_archive(zipName, "zip", directoryName)
        shutil.rmtree(directoryName)

        qt.QMessageBox.information(self, "Export Successful", f"{self.courseName}.zip saved in {filename}",
                                   qt.QMessageBox.Ok)

        webbrowser.open(zipName + ".zip")


    def convertToDoc(self):
        """ Inserts values from database into document """
        with open("text/currentSettings.json") as f:
            data = json.load(f)

        filename, _ = qt.QFileDialog.getSaveFileName(self, "Select where to save Document", data["textbookPath"],
                                                     "Word Document (*.docx);;Word Document (*.doc)")

        if filename:
            doc = Doc()  # Create doc object
            doc.addTitle(f"{self.courseName} Notes")
            conn = sqlite3.connect(self.databasePath)
            c = conn.cursor()

            c.execute("SELECT topicID, topicName FROM topics ORDER BY topicID")
            topics = c.fetchall()

            for topic in topics:
                doc.addHeading(topic[1])
                c.execute(f"SELECT subtopicID, subtopicName FROM subtopics WHERE topicID = {topic[0]} "
                          "ORDER BY subtopicID")
                subtopics = c.fetchall()

                for subtopic in subtopics:
                    doc.addSubheading(subtopic[1])
                    c.execute(f"SELECT type, question, answer FROM notes WHERE subtopicID = {subtopic[0]} "
                              "ORDER BY noteID")
                    notes = c.fetchall()

                    for note in notes:
                        answer = note[2]

                        # Split up string
                        answerList = []
                        indexList = [0]

                        for i, char in enumerate(answer):
                            if char == "<" and answer[i:i + 8] == "<br><br>":
                                indexList.append(i)
                        indexList.append(len(answer)-1)

                        for i, num in enumerate(indexList[:-1]):
                            answerText = answer[indexList[i]:indexList[i+1]].replace("<br>", "")
                            answerList.append(answerText)

                        if note[0] == "Fact":
                            # Add fact
                            doc.addFact(note[1], answerList)

                        elif note[0] == "Definition":
                            doc.addDef(note[1], answerList)


            # Save Document
            doc.save(filename)
            webbrowser.open(filename)
            conn.close()



    def closeEvent(self, event):
        """ Run when window gets closed """
        self.superClass.show()

    def updateTitleColor(self):
        """ Updates title with course colour """
        titleLabel = self.findChild(qt.QLabel, "titleLabel")

        fontColor = self.color.lstrip("#")
        lv = len(fontColor)
        r, g, b = tuple(int(fontColor[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        if (r * 0.299 + g * 0.587 + b * 0.114) > 186:
            fontColor = "#000000"
        else:
            fontColor = "#FFFFFF"

        titleLabel.setStyleSheet(f"background-color:{self.color}; color:{fontColor}")
