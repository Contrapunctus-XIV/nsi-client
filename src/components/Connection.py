from PySide6.QtWebSockets import QWebSocket
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal
from ..vars import SERVER_DOMAIN, CONFLICT
import json

class Connection(QWidget):
    """
    Widget qui permet de gérer la connexion à un salon.
    """
    connection_refused = Signal(int, name="connection_refused")
    update_peers = Signal(list, name="update_peers") # émis pour mettre à jour la liste des pairs
    text_received = Signal(str, str, bool, name="text_received") # émis pour ajouter un message au fil

    def __init__(self, room_id: str, alias: str = ""):
        super().__init__()

        self._socket = QWebSocket()
        self._socket.textMessageReceived.connect(self.handle_message)
        self._socket.errorOccurred.connect(self.on_connection_refused)
        
        self._room_id = room_id
        self._alias = alias
        self._url = f"{SERVER_DOMAIN}/room/{self._room_id}?alias={self._alias}" if len(self._alias) > 0 else f"{SERVER_DOMAIN}/room/{self._room_id}"

    def open(self):
        """Lance la connexion au salon."""
        self._socket.open(self._url)

    def handle_message(self, message):
        """
        Reçoit les messages diffusés dans le salon et les traite.
        """
        data = json.loads(message)
        
        self.update_peers.emit(data["peers"]) # mise à jour des pairs

        _str = ""
        is_event = True # True si pas un texte envoyé par un pair
        match data["type"]:
            case "WELCOME" | "JOIN":
                _str = f"{data['alias']} has joined the room." # nouvel arrivant
            case "MESSAGE" | "RECEIVED":
                _str = data["body"] # message d'un pair
                is_event = False
            case "LEAVE": 
                _str = f"{data['alias']} has left the room." # départ d'un pair

        self.text_received.emit(data["alias"], _str, is_event)

    def send_text(self, text: str):
        """
        Envoie un message au salon
        """
        message = json.dumps({ "type": "MESSAGE", "body": text })
        self._socket.sendTextMessage(message)

    def on_connection_refused(self, error):
        print(self._socket.errorString())
        if str(CONFLICT) in self._socket.errorString():
            self.connection_refused.emit(CONFLICT)

    def close(self):
        self._socket.close()

    def room_id(self):
        return self._room_id
    
    def alias(self):
        return self._alias

    def socket(self):
        return self._socket