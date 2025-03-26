from PySide6.QtWebSockets import QWebSocket
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, QFileInfo, QThread, QByteArray
from ..vars import SERVER_DOMAIN, UNAUTHORIZED, NOT_FOUND
from humanize import naturalsize
import json

"""
Fonctionnement des transactions :
- Une transaction désigne l'envoi du fichier d'un pair à un autre
- Le pair émetteur génère un identifiant et crée une transaction côté serveur en ouvrant un socket à transaction/:transaction_id
- Le pair récepteur doit être en possession de l'identifiant de la transaction pour pouvoir s'y connecter.
Pour s'y connecter il ouvre aussi un socket à transaction/:transaction_id
- Diverses informations sont échangées (informations sur le fichier, acceptation de la transaction, début, etc.) à travers cette connexion
- Lorsque l'émetteur et le récepteur sont prêts, ils se connectent à transaction/:transaction_id/bin. C'est ici que l'émetteur
envoie le stream au récepteur.
"""

class Sender(QThread):
    """
    Une classe qui hérite de QThread et qui envoie un stream d'octets au serveur (transaction/:transaction_id/bin).
    Utilisation de QThread pour ne pas bloquer le GUI.
    """
    progress = Signal(int) # émis lorsqu'un nouveau chunk a été envoyé, prend en argument la taille du chunk
    finished = Signal() # émis lorsque l'upload est terminé

    def __init__(self, transaction_id: str, filepath: str, parent=None):
        super().__init__(parent)
        self._filepath = filepath
        self._url = f"{SERVER_DOMAIN}/transaction/{transaction_id}/bin?sender=true"

    def send_file(self):
        self._s = QWebSocket()
        def on_open():
            with open(self._filepath, "rb") as file:
                while True:
                    chunk = file.read(2048)
                    if not chunk: # fin de la lecture
                        break
                    self._s.sendBinaryMessage(chunk)
                    self.progress.emit(len(chunk))

                self._s.close()
                self.finished.emit()

        def on_error(error):
            print(self._s.errorString())

        self._s.open(self._url)
        self._s.connected.connect(on_open)
        self._s.errorOccurred.connect(on_error)

    def run(self):
        self.send_file()

class Receiver(QWidget):
    """
    Classe qui écoute le stream de l'émetteur (transaction/:transaction_id/bin) et l'écrit dans le fichier spécifié.
    """
    progress = Signal(int) # émis lorsqu'un nouveau chunk a été reçu, prend en argument la taille du chunk

    def __init__(self, transaction_id: str, filepath: str, parent=None):
        super().__init__(parent)
        self._filepath = filepath
        self._s = QWebSocket()

        with open(filepath, "w"): # fichier vierge
            pass

        self._url = f"{SERVER_DOMAIN}/transaction/{transaction_id}/bin?sender=false"
        self._s.binaryMessageReceived.connect(self.on_received)
        self._s.open(self._url)

    def on_received(self, data: QByteArray):
        chunk = data.data()
        with open(self._filepath, "ab") as file: # écriture
            file.write(chunk)
        self.progress.emit(len(chunk))

    def close(self):
        self._s.close()

class Transaction(QWidget):
    """
    Classe parente qui permet des opérations qui seront réutilisées par TransactionSender et TransactionReceiver.
    """
    text_received = Signal(str) # émis lorsque un nouvel événement a eu lieu
    infos_received = Signal(str, int) # émis lorsque les informations concernant le fichier ont été partagées
    connection_refused = Signal(int) # émis lorsque erreur
    transaction_accepted = Signal() # émis lorsque le receveur accepte la transaction
    transaction_progressed = Signal(int) # émis lorsqu'un chunk a été reçu ou envoyé
    transaction_finished = Signal() # émis lorsque la transaction est terminé
    transaction_uploaded = Signal() # émis lorsque le receveur a uploadé le fichier
    peer_left = Signal()

    def __init__(self, transaction_id: str, parent=None):
        super().__init__(parent)
        self._transaction_id = transaction_id
        self._socket = QWebSocket()
        self._socket.errorOccurred.connect(self.on_error)
        self._url = f"{SERVER_DOMAIN}/transaction/{self._transaction_id}"
        self._socket.textMessageReceived.connect(self.handle_incoming_message)

    def on_error(self, error):
        error_str = self._socket.errorString()
        print(error_str)

        if str(NOT_FOUND) in error_str:
            self.connection_refused.emit(NOT_FOUND)
        elif "WWW-Authenticate" in error_str:
            self.connection_refused.emit(UNAUTHORIZED)

    def handle_incoming_message(self, message):
        """
        Traite les événements reçus et émet le texte qui sera affiché dans le fil.
        """
        data = json.loads(message)
        match data["type"]:
            case "TRANSACTION_INFOS_RECEIVED":
                _str = "Transaction infos have been updated on server."
                self.infos_received.emit(data["body"]["filename"], data["body"]["filesize"])
            case "TRANSACTION_INFOS":
                _str = f"Transaction infos received from server: file is {data['body']['filename']} ({naturalsize(data['body']['filesize'], binary=True)})"
                self.infos_received.emit(data["body"]["filename"], data["body"]["filesize"])
            case "TRANSACTION_JOIN":
                _str = "Receiver has joined the transaction."
            case "TRANSACTION_ACCEPT" | "TRANSACTION_ACCEPT_RECEIVED":
                self.transaction_accepted.emit()
                _str = "Receiver has accepted the transaction."
            case "TRANSACTION_START" | "TRANSACTION_START_RECEIVED":
                _str = "Sender has started the transaction."
            case "TRANSACTION_END" | "TRANSACTION_END_RECEIVED":
                _str = "Transaction is finished."
                self.transaction_finished.emit()
            case "TRANSACTION_UPLOAD" | "TRANSACTION_UPLOAD_RECEIVED":
                _str = "Receiver starts downloading the file."
                self.transaction_uploaded.emit()
            case "LEAVE":
                _str = "The remote party closed the transaction."
                self.peer_left.emit()

        self.text_received.emit(_str)

    def open(self):
        self._socket.open(self._url)

    def close(self):
        self._socket.close()

class TransactionSender(Transaction):
    """
    Classe utilisée pour envoyer un fichier via une transaction.
    """
    def __init__(self, transaction_id: str, filepath: str):
        super().__init__(transaction_id)
        self._filepath = filepath # chemin du fichier
        self._filename = filepath.split("/")[-1]
        self._filesize = QFileInfo(filepath).size() # taille du fichier
        self._url += "?sender=true"

    def offer(self):
        """
        Envoie une offre de transaction (la transaction est créée côté serveur) puis envoie les infos du fichier.
        """
        self.open()
        def send_transaction_infos():
            message = { "type": "TRANSACTION_INFOS", "body": { "filename": self._filename, "filesize": self._filesize }}
            self._socket.sendTextMessage(json.dumps(message))

        self._socket.connected.connect(send_transaction_infos)

    def start(self):
        """
        Lance l'envoi du fichier en démarrant un QThread.
        """
        message = { "type": "TRANSACTION_START", "body": None }
        self._socket.sendTextMessage(json.dumps(message))
        sender = Sender(self._transaction_id, self._filepath, self) # QThread
        sender.progress.connect(lambda n: self.transaction_progressed.emit(n))
        # quand l'upload est fini
        sender.finished.connect(lambda: self._socket.sendTextMessage(json.dumps({ "type": "TRANSACTION_UPLOAD", "body": None })))
        sender.run()

class TransactionReceiver(Transaction):
    """
    Classe utilisée pour recevoir un fichier via une transaction.
    """
    def __init__(self, transaction_id: str):
        super().__init__(transaction_id)
        self._filename = None # nom du fichier
        self._filesize = None # taille
        self._filepath = None # lieu d'enregistrement
        self._receiver = None # Receiver

        self._url += "?sender=false"
        self.infos_received.connect(self.set_file)
        self._transaction_id = transaction_id

    def set_file(self, filename: str, filesize: int):
        """
        Ajoute les informations sur le fichier à la classe en tant qu'attributs.
        """
        self._filename = filename
        self._filesize = filesize

    def set_filepath(self, filepath: str):
        """
        Ajoute le chemin d'enregistrement du fichier.
        """
        self._filepath = filepath

    def accept(self):
        """
        Le client accepte la transaction, signifiant que le transfert peut commencer.
        """
        message = { "type": "TRANSACTION_ACCEPT", "body": None }
        self._socket.sendTextMessage(json.dumps(message))
        self._receiver = Receiver(self._transaction_id, self._filepath)
        self._receiver.progress.connect(lambda n: self.transaction_progressed.emit(n))

    def finish(self):
        """
        Le client a reçu l'entièreté du fichier.
        """
        message = { "type": "TRANSACTION_END", "body": None }
        self._socket.sendTextMessage(json.dumps(message))
        self._receiver.close()