import PyQt5.QtWidgets as qt
from PyQt5.QtGui import QIcon
from PyQt5 import uic
import decimal


def drange(x, y, jump):
    x = decimal.Decimal(str(x))
    y += jump / 2
    while x < y:
        yield float(x)
        x += decimal.Decimal(str(jump))


class Window(qt.QMainWindow):
    back = True

    def __init__(self, superClass, terms, checkTerms):
        """ Main Window """
        super(Window, self).__init__()
        uic.loadUi("gui/editFormula.ui", self)
        self.setWindowIcon(QIcon("images/logo.png"))
        self.superClass = superClass
        self.terms = terms
        self.currentTerm = terms[0]
        self.checkTerms = checkTerms

        # Get widgets
        self.termListWidget = self.findChild(qt.QListWidget, "termListWidget")
        self.nameEdit = self.findChild(qt.QLineEdit, "nameEdit")
        self.symbolEdit = self.findChild(qt.QLineEdit, "symbolEdit")
        self.unitEdit = self.findChild(qt.QLineEdit, "unitEdit")
        self.minEdit = self.findChild(qt.QLineEdit, "minEdit")
        self.maxEdit = self.findChild(qt.QLineEdit, "maxEdit")
        self.stepEdit = self.findChild(qt.QLineEdit, "stepEdit")
        self.updateBtn = self.findChild(qt.QPushButton, "updateBtn")
        self.backBtn = self.findChild(qt.QPushButton, "backBtn")

        # Bind widgets
        self.termListWidget.clicked.connect(self.changeTerm)
        self.backBtn.clicked.connect(self.close)
        self.updateBtn.clicked.connect(lambda: self.updateTerm(True))

        # Insert terms into List Widget
        for term in terms:
            self.termListWidget.addItem(term["symbol"])

        # Fill line edits with values
        self.fillEdits()

    def updateTerm(self, showError=True):
        """ Updates term in dictionary """
        term = self.validateTerm(showError=showError)
        if term:
            # Valid - Update term
            i = self.terms.index(self.currentTerm)
            self.currentTerm = term
            self.terms[i] = self.currentTerm
            i = (i + 1) % len(self.terms)
            self.termListWidget.setCurrentRow(i)
            self.currentTerm = self.terms[i]
            self.fillEdits()

    def validateTerm(self, showError=True):
        """ Validate whether the inputs for the term is valid """
        name = self.nameEdit.text().strip()
        symbol = self.symbolEdit.text().strip()
        unit = self.unitEdit.text().strip()

        min_ = self.minEdit.text().strip()
        max_ = self.maxEdit.text().strip()
        step = self.stepEdit.text().strip()

        # Validate inputs
        if "" in [name, symbol, unit, min_, max_, step]:
            # Field empty
            if showError:
                error = qt.QMessageBox.critical(self, "Error - Missing fields",
                                                "Please ensure that all fields are filled in", qt.QMessageBox.Ok)
            return False

        elif not min_.replace(".", "").isnumeric() or not max_.replace(".", "").isnumeric() or\
                not step.replace(".", "").isnumeric() or len(list(drange(float(min_), float(max_), float(step)))) == 0:
            # Invalid min, max, step values
            if showError:
                error = qt.QMessageBox.critical(self, "Error - Invalid Input",
                                                "Invalid Min, Max or Step Value", qt.QMessageBox.Ok)
            return False

        else:
            return {"name": name, "symbol": symbol, "unit": unit, "min": float(min_), "max": float(max_),
                    "step": float(step)}

    def changeTerm(self):
        """ Insert a new term """
        self.updateTerm(showError=False)
        self.currentTerm = [t for t in self.terms if t["symbol"] == self.termListWidget.currentItem().text()][0]
        self.fillEdits()

    def fillEdits(self):
        """ Fills edits using current term values """
        self.nameEdit.setText(self.currentTerm["name"])
        self.symbolEdit.setText(self.currentTerm["symbol"])
        self.unitEdit.setText(self.currentTerm["unit"])

        if (float(self.currentTerm["min"])).is_integer():
            self.minEdit.setText(str(int(self.currentTerm["min"])))
        else:
            self.minEdit.setText(str(self.currentTerm["min"]))

        if (float(self.currentTerm["max"])).is_integer():
            self.maxEdit.setText(str(int(self.currentTerm["max"])))
        else:
            self.maxEdit.setText(str(self.currentTerm["max"]))

        if (float(self.currentTerm["step"])).is_integer():
            self.stepEdit.setText(str(int(self.currentTerm["step"])))
        else:
            self.stepEdit.setText(str(self.currentTerm["step"]))

    def closeEvent(self, event):
        """ Run when window gets closed """
        self.updateTerm(showError=False)
        self.superClass.show()
        self.checkTerms(self.terms)
