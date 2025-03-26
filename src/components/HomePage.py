from PySide6.QtWidgets import QWidget, QLineEdit, QApplication, QLabel, QPushButton, QVBoxLayout, QGroupBox, QStackedWidget, QFileDialog, QLineEdit
from PySide6.QtCore import Slot, QEvent, Qt, QObject, Signal, QFileInfo
from PySide6.QtGui import QFont
from random import randbytes
from pathlib import Path
from ..vars import STYLES_PATH, MAXIMUM_ALIAS_LENGTH
from .utils import QLimitedLineEdit, QErrorDialog, QElidedLabel
from humanize import naturalsize
import uuid

def is_valid_uuid(_str: str):
    """
    Renvoie True si le paramètre est un UUID v4 valide, False sinon.
    """
    try:
        uuid.UUID(_str, version=4)
        return True
    except ValueError:
        return False
    
class SendForm(QWidget):
    """
    Formulaire pour l'envoi d'un fichier.
    """
    cancelled = Signal() # émis si bouton "Back" cliqué
    submitted = Signal(str) # émis si bouton "Submit" cliqué

    def __init__(self, parent=None):
        self._filepath = "" # chemin du fichier à envoyer
        self._filesize = 0 # taille de ce fichier

        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._box = QGroupBox("Send a file:")

        self._stacked_widget = QStackedWidget() # un widget pour la sélection du fichier, un autre pour la confirmation de l'envoi

        self._box_layout = QVBoxLayout()
        
        self._file_button = QPushButton("Browse...") # bouton pour choisir le fichier
        self._submit_button = QPushButton("Submit")
        self._back_button = QPushButton("Back")
        self._second_back_button = QPushButton("Back")

        self._back_button.setObjectName("cancel")
        self._second_back_button.setObjectName("cancel")
        self._submit_button.setObjectName("submit")

        self._file_button.clicked.connect(self.browse)
        self._submit_button.clicked.connect(self.submit)
        self._back_button.clicked.connect(self.cancel)
        self._second_back_button.clicked.connect(self.cancel)

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self._filepath_label = QElidedLabel("", alignment=Qt.AlignmentFlag.AlignHCenter)
        self._filesize_label = QLabel("", alignment=Qt.AlignmentFlag.AlignHCenter)
        self._filepath_label.setFont(font)
        self._filesize_label.setFont(font)

        self._submit_widget = QWidget()
        self._submit_layout = QVBoxLayout()
        self._submit_layout.addWidget(self._filepath_label) # infos sur fichier
        self._submit_layout.addStretch(1)
        self._submit_layout.addWidget(self._filesize_label)
        self._submit_layout.addStretch(3)
        self._submit_layout.addWidget(self._submit_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._submit_layout.addWidget(self._second_back_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._submit_widget.setLayout(self._submit_layout)

        self._file_widget = QWidget()
        self._file_layout = QVBoxLayout()
        self._file_layout.addWidget(self._file_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._file_layout.addWidget(self._back_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._file_widget.setLayout(self._file_layout)

        self._stacked_widget.addWidget(self._file_widget)
        self._stacked_widget.addWidget(self._submit_widget)

        self._stacked_widget.setCurrentIndex(0)

        self._box_layout.addWidget(self._stacked_widget)
    
        self._box.setLayout(self._box_layout)
        self._layout.addWidget(self._box)
        self.setLayout(self._layout)

    @Slot()
    def browse(self):
        """
        Sélection d'un fichier à envoyer.
        """
        self._filepath, _ = QFileDialog.getOpenFileName()

        if len(self._filepath) > 0: # si un fichier a bien été sélectionné
            self._filesize = QFileInfo(self._filepath).size()
            self._filepath_label.setText(f"File: {self._filepath}")
            self._filesize_label.setText(f"Size: {naturalsize(self._filesize, binary=True)}") # mise à jour des labels
            self._stacked_widget.setCurrentIndex(1) # on passe à la confirmation

    @Slot()
    def cancel(self):
        self._stacked_widget.setCurrentIndex(0)
        self.cancelled.emit()

    @Slot()
    def submit(self):
        self.submitted.emit(self._filepath)
        self._filepath_label.setText("") # nettoyage
        self._filesize_label.setText("")
        self._stacked_widget.setCurrentIndex(0)

class ReceiveForm(QWidget):
    """Formulaire pour la réception d'un fichier."""
    cancelled = Signal() # émis si bouton "Back" cliqué
    submitted = Signal(str) # émis si bouton "Submit" cliqué

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._box = QGroupBox("Receive a file:")
        self._box_layout = QVBoxLayout()

        self._id_label = QLabel("Enter transaction id (provided by sender):")
        self._id_input = QLineEdit() # input pour l'ID de la transaction

        self._submit_button = QPushButton("Submit")
        self._submit_button.setObjectName("submit")
        self._back_button = QPushButton("Back")
        self._back_button.setObjectName("cancel")

        self._back_button.clicked.connect(self.cancel)
        self._submit_button.clicked.connect(self.submit)

        self._box_layout.addWidget(self._id_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addStretch()
        self._box_layout.addWidget(self._id_input)
        self._box_layout.addStretch()
        self._box_layout.addWidget(self._submit_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addWidget(self._back_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._box.setLayout(self._box_layout)
        self._layout.addWidget(self._box)
        self.setLayout(self._layout)

    def clear(self):
        self._id_input.clear()

    @Slot()
    def submit(self):
        transaction_id = self._id_input.text()
        
        if not is_valid_uuid(transaction_id):
            dialog = QErrorDialog("Provided transaction ID is not a valid UUID v4.")
            dialog.exec()
            return
        
        self.submitted.emit(transaction_id)
        self._id_input.clear()

    @Slot()
    def cancel(self):
        self.clear()
        self.cancelled.emit()

class RoomForm(QWidget):
    """Formulaire pour rejoindre un salon."""
    submitted = Signal(str, str) # émis quand bouton "Submit" cliqué
    cancelled = Signal() # émis quand bouton "Back" cliqué

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()
    
    def init_UI(self):
        self._layout = QVBoxLayout(self)
        self._head = HomeHead()
        self._box = QGroupBox("Join a room:", self)

        self._box_layout = QVBoxLayout(self._box)
        self._room_field = QLineEdit(self._box)
        self._alias_field = QLimitedLineEdit(MAXIMUM_ALIAS_LENGTH, self._box) # un QLineEdit limité en nombre de caractères
        self._randomize_button = QPushButton("Randomize", self._box) # bouton pour rendre l'ID du salon et le pseudo aléatoires
        self._randomize_button.setObjectName("randomize")
        self._submit_button = QPushButton("Join room", self._box)
        self._submit_button.setObjectName("submit")
        self._back_button = QPushButton("Back", self._box)
        self._back_button.setObjectName("cancel")

        self._box_layout.addWidget(QLabel("Room UUID:"))
        self._box_layout.addWidget(self._room_field)
        self._box_layout.addWidget(QLabel("Username (leave empty to randomize):"))
        self._box_layout.addWidget(self._alias_field)
        self._box_layout.addSpacing(20)
        self._box_layout.addWidget(self._randomize_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addWidget(self._submit_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addWidget(self._back_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._randomize_button.clicked.connect(self.randomize)
        self._submit_button.clicked.connect(self.submit_form)
        self._back_button.clicked.connect(self.back)

        self._box.setLayout(self._box_layout)
        self._layout.addWidget(self._box)
        self.setLayout(self._layout)

    @Slot()
    def randomize(self):
        room_id = str(uuid.uuid4()) # id aléatoire
        alias = randbytes(4).hex() # alias aléatoire

        self._room_field.setText(room_id)
        self._alias_field.setText(alias)

    def clear(self):
        self._room_field.clear()
        self._alias_field.clear()

    @Slot()
    def submit_form(self):
        room = self._room_field.text().strip()
        alias = self._alias_field.text().strip()

        if not is_valid_uuid(room):
            dialog = QErrorDialog("Provided room ID is not a valid UUID v4.")
            dialog.exec()
            return
        
        self.clear()
        self.submitted.emit(room, alias)

    @Slot()
    def back(self):
        self.clear()
        self.cancelled.emit()

    def eventFilter(self, obj: QObject, event: QEvent):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return: # formulaire envoyé si on appuie sur Entrée
                self.submit_form()

                return True

        return super().eventFilter(obj, event)

class HomeForm(QWidget):
    """
    Widget qui contient les boutons du menu principal
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout(self)
        self._box = QGroupBox("Create a connection:", self)

        self._box_layout = QVBoxLayout(self._box)
        self._room_button = QPushButton("Join a room")
        self._send_button = QPushButton("Send a file")
        self._receive_button = QPushButton("Receive a file")
        self._quit_button = QPushButton("Quit")

        self._room_button.setObjectName("submit")
        self._send_button.setObjectName("submit")
        self._receive_button.setObjectName("submit")
        self._quit_button.setObjectName("cancel")

        self._quit_button.clicked.connect(self.quit)

        spacing = 10
        self._box_layout.addStretch()
        self._box_layout.addWidget(self._room_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addSpacing(spacing)
        self._box_layout.addWidget(self._send_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addSpacing(spacing)
        self._box_layout.addWidget(self._receive_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addSpacing(spacing)
        self._box_layout.addWidget(self._quit_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addStretch()

        self._box.setLayout(self._box_layout)
        self._layout.addWidget(self._box)

        self.setLayout(self._layout)

    @Slot()
    def quit(self):
        QApplication.quit()

    def room_button(self):
        return self._room_button
    
    def file_send_button(self):
        return self._send_button
    
    def file_receive_button(self):
        return self._receive_button
    
    def resizeEvent(self, event):
        """pour ajouter les boutons à la largeur de la fenêtre"""
        new_width = self.width() // 2.4
        self._room_button.setFixedWidth(new_width)
        self._send_button.setFixedWidth(new_width)
        self._receive_button.setFixedWidth(new_width)
        self._quit_button.setFixedWidth(new_width)
        super().resizeEvent(event)

class HomeHead(QWidget):
    """
    Widget contenant l'en-tête du menu principal.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()
    
    def init_UI(self):
        self._layout = QVBoxLayout()
        self._heading = QLabel("NSI Client", parent=self, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._heading.setObjectName("heading")
        self._sub_heading = QLabel("A desktop client for Nameless & Secured Interactions", parent=self, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._sub_heading.setObjectName("sub_heading")
        self._author_heading = QLabel("Created by a NSI (Numérique et sciences informatiques) student", parent=self, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._author_heading.setObjectName("author_heading")

        self._layout.addWidget(self._heading)
        self._layout.addWidget(self._sub_heading)
        self._layout.addWidget(self._author_heading)
        self._layout.addSpacing(self.height() // 7)
        self.setLayout(self._layout)
    
class HomeMenu(QWidget):
    """
    Menu principal (et d'accueil) permettant de naviguer entre les type de connexion : salon, transaction entrante et transaction sortante
    """
    room_form_submitted = Signal(str, str) # lorsque l'utilisateur envoie le formulaire pour rejoindre un salon
    send_form_submitted = Signal(str) # idem pour envoyer un fichier
    receive_form_submitted = Signal(str) # idem pour recevoir un fichier

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._head = HomeHead()

        self._stacked_widgets = QStackedWidget()
        self._home_form = HomeForm()
        self._room_form = RoomForm()
        self._send_form = SendForm()
        self._receive_form = ReceiveForm()

        self._home_form.room_button().clicked.connect(self.switch_to_room_form)
        self._home_form.file_send_button().clicked.connect(self.switch_to_file_send_form)
        self._home_form.file_receive_button().clicked.connect(self.switch_to_file_receive_form)

        self._room_form.cancelled.connect(self.back_to_menu)
        self._room_form.submitted.connect(lambda room_id, alias: self.room_form_submitted.emit(room_id, alias))

        self._send_form.cancelled.connect(self.back_to_menu)
        self._send_form.submitted.connect(lambda filepath: self.send_form_submitted.emit(filepath))

        self._receive_form.cancelled.connect(self.back_to_menu)
        self._receive_form.submitted.connect(lambda transaction_id: self.receive_form_submitted.emit(transaction_id))

        self._stacked_widgets.addWidget(self._home_form)
        self._stacked_widgets.addWidget(self._room_form)
        self._stacked_widgets.addWidget(self._send_form)
        self._stacked_widgets.addWidget(self._receive_form)

        self._layout.addWidget(self._head, 8)
        self._layout.addWidget(self._stacked_widgets, 7)

        self.setStyleSheet(Path(f"{STYLES_PATH}/home_page.qss").read_text())

        self._stacked_widgets.setCurrentIndex(0)
        self.setLayout(self._layout)

    @Slot()
    def switch_to_room_form(self):
        self._stacked_widgets.setCurrentIndex(1)

    @Slot()
    def switch_to_file_send_form(self):
        self._stacked_widgets.setCurrentIndex(2)

    @Slot()
    def switch_to_file_receive_form(self):
        self._stacked_widgets.setCurrentIndex(3)
        
    @Slot()
    def back_to_menu(self):
        self._stacked_widgets.setCurrentIndex(0)