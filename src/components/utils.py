from PySide6.QtWidgets import QTextEdit, QLineEdit, QWidget, QDialog, QLabel, QSizePolicy, QVBoxLayout, QDialogButtonBox, QStyle, QStyleOptionFrame
from PySide6.QtCore import Slot, Qt, QSize
from PySide6.QtGui import QPainter
import os
from pathlib import Path

class QLimitedLineEdit(QLineEdit):
    """
    Un QLineEdit mais sa taille (nombre de caractères) est limité au paramètre max_length du constructeur.
    """
    def __init__(self, max_length: int, parent: QWidget = None):
        super().__init__(parent)
        self.max_length = max_length
        self.textChanged.connect(self.on_change)

    @Slot()
    def on_change(self):
        text = self.text()
        if len(text) > self.max_length:
            self.setText(text[:-1]) # nouveau caractère pas pris en compte si limite dépassée

class QErrorDialog(QDialog):
    """
    Affiche une nouvelle fenêtre avec le message d'erreur passé en constructeur.
    """
    def __init__(self, error_msg: str, parent: QWidget = None):
        super().__init__(parent)
        self._error_msg = error_msg
        self.init_UI()

    def init_UI(self):
        self._dialog = QDialog()
        self.setWindowTitle("Chat Client Error")
        self._layout = QVBoxLayout()
        self._message = QLabel(self._error_msg)
        self._button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok) # Bouton OK
        self._layout.addWidget(self._message)
        self._layout.addWidget(self._button_box)

        self.setLayout(self._layout)
        self._button_box.accepted.connect(self.close)

def get_download_path() -> Path:
    """Renvoie le dossier par défaut des téléchargements sur Windows et Linux."""
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return Path(location)
    else:
        return Path(os.path.join(os.path.expanduser('~'), 'downloads'))
    
class QElidedLabel(QLabel):
    """
    Un QLabel mais le texte est élidé s'il dépasse la largeur fixée (trouvée sur StackOverflow).
    """
    _elideMode = Qt.TextElideMode.ElideMiddle

    def sizePolicy(self):
        # s'étend avec le widget parent
        return QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def elideMode(self):
        return self._elideMode

    def setElideMode(self, mode):
        if self._elideMode != mode and mode != Qt.TextElideMode.ElideNone:
            self._elideMode = mode
            self.updateGeometry()

    def minimumSizeHint(self):
        return self.sizeHint()

    def sizeHint(self):
        hint = self.fontMetrics().boundingRect(self.text()).size() # QSize avec la taille du texte pour la police de caractère utilisée
        margins = self.contentsMargins()
        l, t, r, b = margins.left(), margins.top(), margins.right(), margins.bottom()
        margin = self.margin() * 2
        return QSize(
            min(100, hint.width()) + l + r + margin, 
            min(self.fontMetrics().height(), hint.height()) + t + b + margin
        )

    def paintEvent(self, event):
        qp = QPainter(self)
        opt = QStyleOptionFrame()

        self.initStyleOption(opt)
        self.style().drawControl(QStyle.ControlElement.CE_ShapedFrame, opt, qp, self)

        margins = self.contentsMargins()
        l, t, r, b = margins.left(), margins.top(), margins.right(), margins.bottom()
        margin = self.margin()
        m = self.fontMetrics().horizontalAdvance('x') / 2 - margin
        r = self.contentsRect().adjusted(
            margin + m,  margin, -(margin + m), -margin)
        qp.drawText(r, self.alignment(), 
            self.fontMetrics().elidedText(
                self.text(), self.elideMode(), r.width()))
        