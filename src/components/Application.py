from PySide6.QtWidgets import QWidget, QStackedWidget, QVBoxLayout
from PySide6.QtCore import Slot
from .HomePage import HomeMenu
from .RoomPage import RoomPage
from .TransactionPage import TransactionSenderPage, TransactionReceiverPage
from ..vars import CONFLICT, NOT_FOUND, UNAUTHORIZED, STYLES_PATH
from uuid import uuid4
from .utils import QErrorDialog
from pathlib import Path

class Application(QWidget):
    """
    Widget principal qui relie les différentes pages entre elles avec à un QStackedWidget.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_UI()

    def init_UI(self):
        self.setWindowTitle("NSI Client")

        self._stacked_widgets = QStackedWidget(self)
        self._home_page = HomeMenu(self) # menu principal
        self._room_page = RoomPage(self) # page du salon
        self._transaction_send_page = TransactionSenderPage(self) # page de l'envoi de fichier
        self._transaction_receive_page = TransactionReceiverPage(self) # page de la réception de fichier

        self._stacked_widgets.addWidget(self._home_page)
        self._stacked_widgets.addWidget(self._room_page)
        self._stacked_widgets.addWidget(self._transaction_send_page)
        self._stacked_widgets.addWidget(self._transaction_receive_page)
        self._stacked_widgets.setCurrentIndex(0)

        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self._stacked_widgets)
        self.setLayout(self._layout)

        self._room_page.left.connect(self.leave_room)
        self._transaction_receive_page.closed.connect(self.on_transaction_closed)
        self._transaction_send_page.closed.connect(self.on_transaction_closed)
        self._home_page.room_form_submitted.connect(self.join_room)
        self._home_page.send_form_submitted.connect(self.join_send_page)
        self._home_page.receive_form_submitted.connect(self.join_receive_page)

        self.setStyleSheet(Path(f"{STYLES_PATH}/global.qss").read_text())

    @Slot(int)
    def room_connection_refused(self, code: int):
        """
        Slot appelé quand une connexion à un salon est refusé (se produit quand alias déjà utilisé dans le salon)
        """
        if code == CONFLICT:
            self._stacked_widgets.setCurrentIndex(0)
            dialog = QErrorDialog(f"Username {self._room_page.connection().alias()} is already in use in room {self._room_page.connection().room_id()}")
            dialog.exec()

    @Slot(int)
    def transaction_connection_refused(self, code: int):
        """
        Slot appelé quand une connexion à une transaction est refusée (se produit quand la transaction n'a pas été créée
        ou quand elle comporte déjà un émetteur et un récepteur).
        """
        if code == NOT_FOUND:
            self._stacked_widgets.currentWidget().clear()
            self._stacked_widgets.setCurrentIndex(0)
            dialog = QErrorDialog(f"No receiver has instantiated this transaction.")
            dialog.exec()
        
        elif code == UNAUTHORIZED:
            self._stacked_widgets.currentWidget().clear()
            self._stacked_widgets.setCurrentIndex(0)
            dialog = QErrorDialog(f"Transaction is already full.")
            dialog.exec()

    @Slot(str, str)
    def join_room(self, room_id: str, alias: str):
        """
        Rejoint le salon renseigné par l'utilisateur dans le formulaire RoomForm.
        """
        self._room_page.invoke(room_id, alias)
        self._room_page.connection().connection_refused.connect(self.room_connection_refused)
        self._stacked_widgets.setCurrentIndex(1)

    @Slot()
    def leave_room(self):
        """
        Revenir au menu principal lorsque le salon est quitté.
        """
        self._stacked_widgets.setCurrentIndex(0)
        self._home_page.back_to_menu()

    @Slot(str)
    def join_send_page(self, filepath: str):
        """
        Rejoint la page de transaction (côté émetteur) avec un UUID généré côté client.
        """
        transaction_id = str(uuid4())
        self._transaction_send_page.invoke(transaction_id, filepath)
        self._stacked_widgets.setCurrentIndex(2)
        self._transaction_send_page.connection().connection_refused.connect(self.transaction_connection_refused)

    @Slot(str)
    def join_receive_page(self, transaction_id: str):
        """
        Rejoint la page de transaction (côté receveur).
        """
        self._transaction_receive_page.invoke(transaction_id)
        self._stacked_widgets.setCurrentIndex(3)
        self._transaction_receive_page.connection().connection_refused.connect(self.transaction_connection_refused)

    @Slot()
    def on_transaction_closed(self):
        """
        Revenir au menu principal lorsque la transaction est terminée.
        """
        self._stacked_widgets.setCurrentIndex(0)
        self._home_page.back_to_menu()