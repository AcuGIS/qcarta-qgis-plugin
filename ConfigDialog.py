import os
import requests
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QPushButton, QVBoxLayout, QLabel, QListWidget, QFormLayout, QLineEdit, QLineEdit, QLineEdit, QLineEdit, QLineEdit, QLabel, QHBoxLayout
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt, QTimer

class ConfigDialog(QDialog):
    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("Configure QCarta Access")
        self.config = config
        self.layout = QVBoxLayout()

        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), 'logo.png')
        if os.path.exists(logo_path):
            logo_label.setPixmap(QIcon(logo_path).pixmap(120, 40))
        branding_label = QLabel("<b style='font-size:14pt;'>QCarta Servers</b><br><span style='font-size:10pt;'>Secure QCarta Deployment Tool</span>")
        branding_label.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(logo_label)
        self.layout.addWidget(branding_label)

        self.list_widget = QListWidget()
        self.list_widget.addItems(sorted(config.keys()))
        self.layout.addWidget(self.list_widget)

        self.form_layout = QFormLayout()
        self.server_name = QLineEdit()
        self.host = QLineEdit()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.port = QLineEdit()

        self.form_layout.addRow("Server Name:", self.server_name)
        self.form_layout.addRow("Host:", self.host)
        self.form_layout.addRow("Username:", self.username)
        self.form_layout.addRow("Password:", self.password)
        self.form_layout.addRow("Port (default 443):", self.port)
        self.layout.addLayout(self.form_layout)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: green;")
        self.layout.addWidget(self.status_label)

        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.delete_button = QPushButton("Delete")
        self.add_button = QPushButton("Add New")
        self.test_button = QPushButton("Test Connection")
        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addWidget(self.test_button)

        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)

        self.list_widget.currentItemChanged.connect(self.load_selected)
        self.save_button.clicked.connect(self.save_entry)
        self.delete_button.clicked.connect(self.delete_entry)
        self.add_button.clicked.connect(self.clear_form)
        self.test_button.clicked.connect(self.test_connection)

    def load_selected(self):
        if self.list_widget.count() == 0:
            return
        name = self.list_widget.currentItem().text()
        entry = self.config.get(name, {})
        self.server_name.setText(name)
        self.host.setText(entry.get('host', ''))
        self.username.setText(entry.get('username', ''))
        self.password.setText(entry.get('password', ''))
        self.port.setText(str(entry.get('port', '443')))

    def save_entry(self):
        name = self.server_name.text().strip()
        if not name:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText("✖ Server name is required.")
            QTimer.singleShot(4000, lambda: self.status_label.clear())
            return
        self.config[name] = {
            'host': self.host.text().strip(),
            'username': self.username.text().strip(),
            'password': self.password.text().strip(),
            'port': int(self.port.text().strip()) if self.port.text().strip().isdigit() else 443
        }
        if name not in [self.list_widget.item(i).text() for i in range(self.list_widget.count())]:
            self.list_widget.addItem(name)
        self.status_label.setStyleSheet("color: green;")
        self.status_label.setText(f"✔ Server '{name}' saved.")
        QTimer.singleShot(4000, lambda: self.status_label.clear())

    def delete_entry(self):
        name = self.server_name.text().strip()
        if name in self.config:
            confirm = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete server '{name}'?", QMessageBox.Yes | QMessageBox.No)
            if confirm != QMessageBox.Yes:
                return
            del self.config[name]

            self.list_widget.blockSignals(True)

            items = self.list_widget.findItems(name, Qt.MatchExactly)
            for item in items:
                itm = self.list_widget.takeItem(self.list_widget.row(item))
                del itm
            self.list_widget.blockSignals(False)
            
            self.clear_form()
            self.status_label.setStyleSheet("color: green;")
            self.status_label.setText(f"✔ Server '{name}' deleted.")
            QTimer.singleShot(4000, lambda: self.status_label.clear())

    def clear_form(self):
        self.server_name.clear()
        self.host.clear()
        self.username.clear()
        self.password.clear()
        self.port.clear()

    def test_connection(self):
        self.status_label.clear()
        host = self.host.text().strip()
        username = self.username.text().strip()
        password = self.password.text().strip()
        port = int(self.port.text().strip()) if self.port.text().strip().isdigit() else 443
        
        proto = 'https' if port == 443 else 'http'
        try:
            response = requests.get(proto + '://' + host + '/rest/stores', auth=(username, password), timeout=(10, 30))
            if response.status_code == 200:
                response = response.json()
                
                if response['success']:
                    self.status_label.setStyleSheet("color: green;")
                    self.status_label.setText("✔ Connection successful!")
                    QTimer.singleShot(4000, lambda: self.status_label.clear())
                else:
                    self.status_label.setStyleSheet("color: red;")
                    self.status_label.setText(f"✖ Login failed: {response['message']}")
                    QTimer.singleShot(5000, lambda: self.status_label.clear())
        except Exception as e:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText(f"✖ Connection failed: {str(e)}")
            QTimer.singleShot(5000, lambda: self.status_label.clear())
