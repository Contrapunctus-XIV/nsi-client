from PySide6.QtWidgets import QWidget, QHBoxLayout, QTextEdit, QTextBrowser, QVBoxLayout, QLabel, QPushButton, QGroupBox
from PySide6.QtGui import QCloseEvent
from PySide6.QtCore import QEvent, Qt, QObject, Signal, Slot
from .Connection import Connection
from pathlib import Path
from ..vars import STYLES_PATH

class RoomFeed(QWidget):
    """
    Représente le fil des messages d'un salon.
    """
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._box = QGroupBox("Room feed:")
        self._box_layout = QVBoxLayout()

        self._feed_layout = QHBoxLayout()
        self._messages_feed = QTextBrowser() # le fil des messages est un QTextBrowser qui supporte le HTML

        self._messages_layout = QVBoxLayout()
        self._messages_feed_label = QLabel("Messages:", parent=self._box)
        self._messages_layout.addWidget(self._messages_feed_label)
        self._messages_layout.addWidget(self._messages_feed)

        self._peers_layout = QVBoxLayout()
        self._peers_feed_label = QLabel("Peers:", parent=self._box)
        self._peers_feed = QTextBrowser(self._box)  # le fil des pairs est un QTextBrowser qui supporte le HTML
        self._peers_layout.addWidget(self._peers_feed_label)
        self._peers_layout.addWidget(self._peers_feed)

        self._feed_layout.addLayout(self._messages_layout, 3)
        self._feed_layout.addLayout(self._peers_layout, 1)
        self._box_layout.addLayout(self._feed_layout)

        self._box.setLayout(self._box_layout)
        self._layout.addWidget(self._box)
        self.setLayout(self._layout)

    def clear_feed(self):
        self._messages_feed.clear()
        self._peers_feed.clear()
    
    def peers_feed(self):
        return self._peers_feed
    
    @Slot(str, str, bool)
    def append_to_messages_feed(self, alias: str, text: str, event: bool):
        """Ajout d'un message textuel au fil. Si event est à True, il s'agit d'un message signalant l'arrivée ou le départ d'un pair."""
        if event:
            formatted_message = f"<div><span style='color: gray; font-style: italic; padding-right: 50px;'>{text}</span></div>"
        else:
            with_br = text.replace('\n', '<br>')
            formatted_message = f"<div><span style='color: gray; font-style: italic; padding-right: 50px;'>{alias}: </span>{with_br}</div>"
        self._messages_feed.append(formatted_message)

    @Slot(list)
    def set_peers_feed(self, peers: list[str]):
        """Mise à jour des pairs."""
        self._peers_feed.clear()
        for peer in peers:
            self._peers_feed.append(f"<div><span style='color: gray; font-style: italic; padding-right: 50px;'>{peer}</span></div>")

class Interactions(QWidget):
    """Widget contenant les interactions du client dans le salon : envoyer un message et quitter le salon."""
    message_submitted = Signal(str) # émis pour envoyer un message
    leave_clicked = Signal() # émis pour quitter le salon

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self._layout = QVBoxLayout()
        self._box = QGroupBox("Interactions:", self)
        self._box_layout = QVBoxLayout()

        self._input = QTextEdit(self._box)
        self._input.setPlaceholderText("Enter a text message (Enter to send, Alt+Enter to add a linebreak):")
        self._leave_button = QPushButton("Leave", self._box)
        self._leave_button.setObjectName("cancel")
        self._leave_button.clicked.connect(lambda: self.leave_clicked.emit())

        self._box_layout.addWidget(self._input)
        self._box_layout.addWidget(self._leave_button, alignment=Qt.AlignmentFlag.AlignRight)
        self._box.setLayout(self._box_layout)

        self._input.installEventFilter(self)

        self._layout.addWidget(self._box)
        self.setLayout(self._layout)

    def eventFilter(self, obj: QObject, event: QEvent):
        """Pour capturer les événements émis dans l'input."""
        if event.type() == QEvent.KeyPress and obj is self._input and self._input.hasFocus():
            if event.key() == Qt.Key_Return: # si Entrée pressé, on envoie le message
                if event.keyCombination().keyboardModifiers() == Qt.KeyboardModifier.NoModifier:
                    text = self._input.toPlainText().strip()

                    if len(text) > 0:
                        self.message_submitted.emit(text)
                        self._input.clear()

                    return True

                elif event.keyCombination().keyboardModifiers() == Qt.KeyboardModifier.AltModifier:
                    # si Alt+Entrée, nouvelle ligne
                    self._input.insertPlainText("\n")

                    return True
            
        return super().eventFilter(obj, event)

    def leave_button(self):
        return self._leave_button

class RoomPage(QWidget):
    left = Signal() # signal émis pour signifier que le salon a été quitté

    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self._connection = None
        self.init_UI()

    def init_UI(self):
        self._heading = QLabel(alignment=Qt.AlignmentFlag.AlignHCenter, textInteractionFlags=Qt.TextInteractionFlag.TextSelectableByMouse)
        self._heading.setObjectName("heading")
        self._feed = RoomFeed(self)
        self._interactions = Interactions(self)

        self._layout = QVBoxLayout()
        self._bottom_layout = QHBoxLayout()
        self._bottom_layout.addWidget(self._interactions, 3)

        self._layout.addWidget(self._heading)
        self._layout.addWidget(self._feed, 2)
        self._layout.addLayout(self._bottom_layout, 1)
        self.setLayout(self._layout)

        self.setStyleSheet(Path(f"{STYLES_PATH}/room_page.qss").read_text())
        self.setLayout(self._layout)

    def closeEvent(self, event: QCloseEvent):
        """on ferme la connexion si la fenêtre est quittée"""
        self._connection.close()
        event.accept()
        
    @Slot()
    def leave_room(self):
        self._feed.clear_feed()
        self._feed.peers_feed().clear()

        self._connection.close()
        self.left.emit()

    def connection(self):
        return self._connection
    
    @Slot(str, str)
    def invoke(self, room_id: str, alias: str):
        """
        Crée la connexion et affiche les données relatives au salon que l'utilisateur rejoint.
        Appelé lorsque le formulaire pour rejoindre un salon est envoyé.
        """
        self._connection = Connection(room_id, alias) # instantiation de la connexion
        self._connection.open()

        self._heading.setText(room_id) # écriture de l'ID du salon

        self._interactions.leave_button().clicked.connect(self.leave_room) # connexions aux slots
        self._connection.update_peers.connect(self._feed.set_peers_feed)
        self._connection.text_received.connect(self._feed.append_to_messages_feed)
        self._interactions.message_submitted.connect(self._connection.send_text)
        self._interactions.leave_clicked.connect(self.leave_room)
