from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QPushButton, QTextBrowser, QProgressBar, QFileDialog, QLabel, QHBoxLayout, QLineEdit, QStackedWidget
from PySide6.QtGui import Qt, QFont, QCloseEvent
from PySide6.QtCore import Signal, Slot
from .TransactionHandlers import TransactionSender, TransactionReceiver
from humanize import naturalsize
from .utils import get_download_path, QElidedLabel
from ..vars import STYLES_PATH
from pathlib import Path

class TransactionHeading(QWidget):
    """
    Affiche l'identifiant de la transaction.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._heading = QLabel(alignment=Qt.AlignmentFlag.AlignHCenter, textInteractionFlags=Qt.TextInteractionFlag.TextSelectableByMouse)
        self._heading.setObjectName("heading")
        self._layout.addWidget(self._heading)
        self.setLayout(self._layout)

    def set_heading(self, transaction_id: str):
        """
        Ajoute l'identifiant.
        """
        self._heading.setText(transaction_id)

class TransactionFeed(QWidget):
    """
    Fil de la transaction.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._feed_box = QGroupBox("Feed:")
        self._feed_box_layout = QVBoxLayout()

        self._feed = QTextBrowser() # le fil est un QTextBrowser qui supporte le HTML
        self._feed_box_layout.addWidget(self._feed)
        self._feed_box.setLayout(self._feed_box_layout)
        self._layout.addWidget(self._feed_box)
        self.setLayout(self._layout)

    def append(self, text: str):
        self._feed.append(f"<div><span style='color: lightgray; font-style: italic;'>{text}</span></div>")

    def clear(self):
        self._feed.clear()

class TransactionFile(QWidget):
    """
    Widget qui contient des informations sur le fichier cible (nom + taille).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()
        self._filename = None
        self._filesize = None

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._box = QGroupBox("File:")
        self._box_layout = QVBoxLayout()

        self._filename_label = QElidedLabel("", alignment=Qt.AlignmentFlag.AlignHCenter) # affiche le nom du fichier
        self._filesize_label = QLabel("", alignment=Qt.AlignmentFlag.AlignHCenter) # affiche la taille

        self._box_layout.addWidget(self._filename_label)
        self._box_layout.addWidget(self._filesize_label)
        self._box_layout.addStretch(2)

        self._box.setLayout(self._box_layout)
        self._layout.addWidget(self._box)
        self.setLayout(self._layout)

    def set_file_infos(self, filename: str, filesize: int):
        """
        Ajoute les informations sur le fichier lorsqu'elles sont reçues.
        """
        self._filename = filename
        self._filesize = filesize
        
        self._filename_label.setText(f"Filename: {self._filename}")
        self._filesize_label.setText(f"Size: {naturalsize(self._filesize, binary=True)}")

    def clear(self):
        self._filename = None
        self._filesize = None
        self._filename_label.setText("")
        self._filesize_label.setText("")

class TransactionClose(QWidget):
    """
    Widget affiché lorsqu'un pair a annulé la transaction prématurément.
    """
    closed = Signal() # ferme le widget

    def __init__(self, is_sender: bool, parent=None):
        super().__init__(parent)
        self._is_sender = is_sender
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._box = QGroupBox("Close:")
        self._box_layout = QVBoxLayout()

        label_text = "Receiver has left the transaction." if self._is_sender else "Sender has left the transaction."
        self._label = QLabel(label_text, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._close_button = QPushButton("Close")
        self._close_button.setObjectName("cancel")
        self._close_button.clicked.connect(lambda: self.closed.emit())

        self._box_layout.addWidget(self._label)
        self._box_layout.addWidget(self._close_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box.setLayout(self._box_layout)
        self._layout.addWidget(self._box)
        
        self.setLayout(self._layout)

class TransactionProgress(QWidget):
    """
    Contient la barre de progression affichée lorsque la transaction est lancée par l'émetteur.
    """
    closed = Signal() # lorsque le client appuie sur "Close" qui apparaît une fois la transaction terminée
    cancelled = Signal() # transaction abandonnée
    uploaded = Signal() # uploadé
    finished = Signal() # téléchargé

    def __init__(self, is_sender: bool, parent=None):
        super().__init__(parent)
        self._filesize = None
        self._value = 0
        self._is_sender = is_sender
        self._is_pending = True # True avant que le premier octet de fichier soit envoyé ou reçu
        self._finished = False
        self._uploaded = False
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._box = QGroupBox("Progression:")
        self._box_layout = QVBoxLayout()

        self._status_label = QLabel(self.status_text(), alignment=Qt.AlignmentFlag.AlignHCenter)

        self._close_button = QPushButton("Close")
        self._close_button.setObjectName("cancel")
        self._close_button.clicked.connect(lambda: self.closed.emit())
        self._close_button.hide() # caché au début, apparaît quand la transaction est terminée

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setObjectName("cancel")
        self._cancel_button.clicked.connect(lambda: self.cancelled.emit())

        self._bar = QProgressBar(alignment=Qt.AlignmentFlag.AlignHCenter)
        self._bar.setMinimum(0)
        self._bar.setTextVisible(True)
        self._bar.hide() # cachée au début, apparaît quand la transaction commence

        self._box_layout.addWidget(self._status_label)
        self._box_layout.addWidget(self._bar)
        self._box_layout.addWidget(self._cancel_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addWidget(self._close_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box.setLayout(self._box_layout)

        self._layout.addWidget(self._box)
        self.setLayout(self._layout)

    def set_filesize(self, filesize: int):
        self._filesize = filesize
        self._bar.setMaximum(self._filesize)

    def status_text(self):
        """
        Renvoie le texte qui doit être affiché le temps que la transaction soit lancée.
        """
        if self._is_sender:
            return "Starting transaction..."
        else:
            return "Waiting for the sender to start transaction..."

    def update_value(self, n: int):
        """
        Met à jour la QProgressBar.
        """
        if self._is_pending: # on change le statut
            self._bar.show()
            self._cancel_button.hide() # plus de retour en arrière
            self._status_label.setText("Transaction in progress...")
            self._is_pending = False

        self._value += n
        self._bar.setValue(self._value)

        if self._value == self._filesize: # fichier totalement téléversé ou téléchargé
            if self._is_sender:
                self._uploaded = True
                self.uploaded.emit()
            else:
                self._finished = True
                self.finished.emit()

    @Slot()
    def on_upload(self):
        self._status_label.setText("Receiver is downloading the file...")
        self._uploaded = True

    @Slot()
    def on_finish(self):
        self._status_label.setText("Transaction finished! You can close the interface.")
        self._close_button.show()
        self._finished = True

    def is_finished(self):
        return self._finished
    
    def is_uploaded(self):
        return self._uploaded

    def show_close_button(self):
        self._close_button.show()

    def clear(self):
        self._bar.hide()
        self._is_pending = True
        self._value = 0
        self._bar.setValue(0)
        self._status_label.setText(self.status_text())
        self._close_button.hide()
        self._cancel_button.show()

class TransactionSenderActions(QWidget):
    """
    Panel qui contient les différentes actions que pourra effectuer l'émetteur.
    Affiche en plus des informations sur la procédure.
    """
    cancelled = Signal() # transaction abandonnée par le client
    started = Signal() # la transaction commence (nécessite que le récepteur l'ait acceptée)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._box = QGroupBox("Actions:")
        self._box_layout = QVBoxLayout()

        self._communicate_id_label = QLabel("Share the transaction ID to the receiver:", alignment=Qt.AlignmentFlag.AlignHCenter)
        self._more_actions = QLabel("You will be able to start the transaction once the receiver accepts it.", alignment=Qt.AlignmentFlag.AlignHCenter)

        self._id_label = QLabel(alignment=Qt.AlignmentFlag.AlignHCenter, textInteractionFlags=Qt.TextInteractionFlag.TextSelectableByMouse) # contient ID de la transaction
        bold_font = QFont()
        bold_font.setBold(True)
        bold_font.setPointSize(12)
        self._id_label.setFont(bold_font)

        self._start_button = QPushButton("Start")
        self._start_button.setObjectName("submit")
        self._start_button.hide()
        self._start_button.clicked.connect(lambda: self.started.emit())

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setObjectName("cancel")
        self._cancel_button.clicked.connect(lambda: self.cancelled.emit())

        self._box_layout.addWidget(self._communicate_id_label)
        self._box_layout.addWidget(self._id_label)
        self._box_layout.addWidget(self._more_actions)
        self._box_layout.addSpacing(50)
        self._box_layout.addWidget(self._start_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addWidget(self._cancel_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._box.setLayout(self._box_layout)
        self._layout.addWidget(self._box)
        self.setLayout(self._layout)

    def set_transaction_id(self, transaction_id: str):
        self._id_label.setText(transaction_id)

    def show_start_button(self):
        self._box_layout.insertSpacing(3, -20)
        self._start_button.show()

    def hide_start_button(self):
        self._start_button.hide()

    def clear(self):
        self._id_label.setText("")
        self.hide_start_button()

class TransactionReceiverActions(QWidget):
    """
    Panel qui contient les différentes actions que pourra effectuer le récepteur.
    Affiche en plus des informations sur la procédure.
    """
    accepted = Signal(str) # émis quand le récepteur accepte de recevoir la transaction
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()
        self._filename = None
        self._destination = None

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._box = QGroupBox("Actions:")
        self._box_layout = QVBoxLayout()

        self._input_label = QLabel("Set the file destination path:", alignment=Qt.AlignmentFlag.AlignHCenter)
        self._input_layout = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setReadOnly(True) # en readonly car sera modifié par le bouton Browse

        self._browse_button = QPushButton("Browse...")
        self._browse_button.setObjectName("browse")
        self._browse_button.setDisabled(True) # sera cliquable une fois que les informations sur la transaction auront été reçues
        self._input_layout.addWidget(self._input)
        self._input_layout.addWidget(self._browse_button)

        self._browse_button.clicked.connect(self.browse)

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setObjectName("cancel")
        self._cancel_button.clicked.connect(lambda: self.cancelled.emit())

        self._accept_button = QPushButton("Accept")
        self._accept_button.setObjectName("submit")
        self._accept_button.hide() # visible une fois que le chemin d'enregistrement a été choisi
        self._accept_button.clicked.connect(lambda: self.accepted.emit(self._input.text()))

        self._box_layout.addWidget(self._input_label)
        self._box_layout.addLayout(self._input_layout)
        self._box_layout.addSpacing(50)
        self._box_layout.addWidget(self._accept_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_layout.addWidget(self._cancel_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._box.setLayout(self._box_layout)
        self._layout.addWidget(self._box)
        self.setLayout(self._layout)

    def set_filename(self, filename: str):
        self._filename = filename
        self._browse_button.setDisabled(False) # le bouton devient cliquable

    def browse(self):
        """
        Choisir la destination du fichier.
        """
        self._destination, _ = QFileDialog.getSaveFileName(dir=f"{get_download_path()/self._filename}")
        if self._destination != "":
            self._input.setText(self._destination)
            self._box_layout.insertSpacing(2, -20)
            self._accept_button.show()

    def clear(self):
        self._accept_button.hide()
        self._input.setText("")
        self._browse_button.setDisabled(True)

class TransactionSenderPage(QWidget):
    """
    La page d'envoi de fichier.
    """
    closed = Signal() # lorsque la transaction est quittée

    def __init__(self, parent=None):
        super().__init__(parent)
        self._transaction_id = None
        self._filepath = None # chemin du fichier à envoyer
        self._connection = None
        self.init_UI()

    def invoke(self, transaction_id: str, filepath: str):
        """
        Crée la connexion au serveur, affiche les informations sur la transaction.
        """
        self._transaction_id = transaction_id
        self._filepath = filepath
        self._actions.set_transaction_id(transaction_id)

        self._feed.append("Establishing connection...")

        self._connection = TransactionSender(transaction_id, filepath) # ajout des slots
        self._connection.text_received.connect(self._feed.append)
        self._connection.infos_received.connect(self.set_file_infos)
        self._connection.transaction_accepted.connect(self._actions.show_start_button)
        self._connection.transaction_progressed.connect(self.update_progress)
        self._connection.transaction_uploaded.connect(self._progress.on_upload)
        self._connection.transaction_finished.connect(self._progress.on_finish)
        self._connection.peer_left.connect(self.on_peer_close)

        self._connection.offer()
        self._heading.set_heading(transaction_id)

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._top_layout = QHBoxLayout()
        self._stacked_widget = QStackedWidget()

        self._heading = TransactionHeading()
        self._feed = TransactionFeed()
        self._file = TransactionFile()
        self._actions = TransactionSenderActions()
        self._progress = TransactionProgress(True)
        self._close = TransactionClose(True)

        self._actions.started.connect(self.start)
        self._actions.cancelled.connect(self.clear)
        self._progress.closed.connect(self.clear)
        self._close.closed.connect(self.clear)

        self._stacked_widget.addWidget(self._actions)
        self._stacked_widget.addWidget(self._progress)
        self._stacked_widget.addWidget(self._close)

        self._stacked_widget.setCurrentIndex(0)

        self._top_layout.addWidget(self._feed)
        self._top_layout.addWidget(self._file, 2)

        self._layout.addWidget(self._heading)
        self._layout.addLayout(self._top_layout)
        self._layout.addWidget(self._stacked_widget)
        self.setLayout(self._layout)

        self.setStyleSheet(Path(f"{STYLES_PATH}/transaction_page.qss").read_text())

    @Slot()
    def start(self):
        """
        La transaction commence : le stream du fichier débute.
        """
        self._stacked_widget.setCurrentIndex(1)
        self._connection.start()

    def connection(self):
        return self._connection
    
    @Slot(int)
    def update_progress(self, n: int):
        """
        Mettre à jour la barre de progression.
        """
        self._progress.update_value(n)

    @Slot(str, int)
    def set_file_infos(self, filename: str, filesize: int):
        """
        Afficher les informations du fichier dans TransactionFile.
        """
        self._file.set_file_infos(filename, filesize)
        self._progress.set_filesize(filesize)

    def clear(self):
        """
        Arrêt de la transaction.
        """
        self.closed.emit()
        self._stacked_widget.setCurrentIndex(0)
        self._file.clear()
        self._actions.clear()
        self._feed.clear()
        self._progress.clear()
        self._connection.close()

    def on_transaction_finish(self):
        self._progress.show_close_button()

    def resizeEvent(self, event):
        """TransactionFile ne doit pas occuper plus de la moitié de la largeur de la fenêtre."""
        self._file.setMaximumWidth(self.width() // 2)
        super().resizeEvent(event)

    def closeEvent(self, event: QCloseEvent):
        """
        On ferme le socket en cas de fermeture de fenêtre.
        """
        self._connection.close()
        event.accept()

    @Slot()
    def on_peer_close(self):
        if not self._progress.is_finished(): # si prématuré
            self._stacked_widget.setCurrentIndex(2)

class TransactionReceiverPage(QWidget):
    closed = Signal() # lorsque la transaction est quittée

    def __init__(self, parent=None):
        super().__init__(parent)
        self._transaction_id = None
        self._filepath = None # chemin d'écriture du fichier reçu
        self._connection = None
        self.init_UI()

    @Slot(str, int)
    def set_file_infos(self, filename: str, filesize: int):
        """
        Afficher les informations du fichier dans TransactionFile.
        """
        self._file.set_file_infos(filename, filesize)
        self._actions.set_filename(filename)
        self._progress.set_filesize(filesize)

    def invoke(self, transaction_id: str):
        """
        Crée une connexion au serveur, affiche les informations sur la transaction.
        """
        self._transaction_id = transaction_id

        self._feed.append("Establishing connection...")

        self._connection = TransactionReceiver(transaction_id) # ajout des slots
        self._connection.open()
        self._connection.text_received.connect(self._feed.append)
        self._connection.infos_received.connect(self.set_file_infos)
        self._connection.transaction_progressed.connect(self.update_progress)
        self._connection.transaction_finished.connect(self._progress.on_finish)
        self._progress.finished.connect(self._connection.finish)
        self._connection.transaction_uploaded.connect(self._progress.on_upload)
        self._connection.peer_left.connect(self.on_peer_close)

        self._heading.set_heading(transaction_id)

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._top_layout = QHBoxLayout()

        self._stacked_widget = QStackedWidget()

        self._heading = TransactionHeading()
        self._feed = TransactionFeed()
        self._file = TransactionFile()
        self._actions = TransactionReceiverActions()
        self._progress = TransactionProgress(False)
        self._close = TransactionClose(False)

        self._actions.accepted.connect(self.accept_transaction)
        self._actions.cancelled.connect(self.clear)
        self._progress.cancelled.connect(self.clear)
        self._progress.closed.connect(self.clear)
        self._close.closed.connect(self.clear)

        self._stacked_widget.addWidget(self._actions)
        self._stacked_widget.addWidget(self._progress)
        self._stacked_widget.addWidget(self._close)

        self._stacked_widget.setCurrentIndex(0)

        self._top_layout.addWidget(self._feed)
        self._top_layout.addWidget(self._file, 2)

        self._layout.addWidget(self._heading)
        self._layout.addLayout(self._top_layout)
        self._layout.addWidget(self._stacked_widget)
        self.setLayout(self._layout)

        self.setStyleSheet(Path(f"{STYLES_PATH}/transaction_page.qss").read_text())

    def connection(self):
        return self._connection
    
    @Slot(str)
    def accept_transaction(self, filepath: str):
        """
        Le client a accepté la transaction : le stream peut débuter.
        """
        self._connection.set_filepath(filepath)
        self._connection.accept()
        self._stacked_widget.setCurrentIndex(1)

    @Slot(int)
    def update_progress(self, n: int):
        """
        Mettre à jour la barre de progression.
        """
        self._progress.update_value(n)
    
    @Slot()
    def on_peer_close(self):
        if not self._progress.is_finished(): # si prématuré
            self._stacked_widget.setCurrentIndex(2)

    @Slot()
    def clear(self):
        """
        Arrêt de la transaction.
        """
        self.closed.emit()
        self._stacked_widget.setCurrentIndex(0)
        self._file.clear()
        self._actions.clear()
        self._feed.clear()
        self._progress.clear()
        self._connection.close()

    def closeEvent(self, event: QCloseEvent):
        """
        On ferme le socket en cas de fermeture de fenêtre.
        """
        self._connection.close()
        event.accept()