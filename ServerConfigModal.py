import os
import requests
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QPushButton, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QHBoxLayout
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt, QTimer
from .util import app_http_login

class ServerConfigModal(QDialog):
    def __init__(self, config, server_name=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.server_name = server_name
        self.is_edit_mode = server_name is not None
        
        # Set window properties
        self.setWindowTitle("Edit Server" if self.is_edit_mode else "Add New Server")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        # Create layout
        self.layout = QVBoxLayout()
        
        # Add title
        title_label = QLabel("Server Configuration")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title_label)
        
        # Create form layout
        self.form_layout = QFormLayout()
        
        # Form fields
        self.server_name_field = QLineEdit()
        self.host_field = QLineEdit()
        self.username_field = QLineEdit()
        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.Password)
        self.port_field = QLineEdit()
        self.port_field.setText("443")  # Default port
        
        # Add rows to form
        self.form_layout.addRow("Server Name:", self.server_name_field)
        self.form_layout.addRow("Host:", self.host_field)
        self.form_layout.addRow("Username:", self.username_field)
        self.form_layout.addRow("Password:", self.password_field)
        self.form_layout.addRow("Port (default 443):", self.port_field)
        
        self.layout.addLayout(self.form_layout)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: green;")
        self.layout.addWidget(self.status_label)
        
        # Button layout
        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.test_button = QPushButton("Test Connection")
        self.cancel_button = QPushButton("Cancel")
        
        self.button_layout.addWidget(self.test_button)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)
        
        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)
        
        # Connect signals
        self.save_button.clicked.connect(self.save_server)
        self.test_button.clicked.connect(self.test_connection)
        self.cancel_button.clicked.connect(self.reject)
        
        # Load existing server data if editing
        if self.is_edit_mode:
            self.load_server_data()
    
    def load_server_data(self):
        """Load existing server data into the form"""
        if self.server_name and self.server_name in self.config:
            server_info = self.config[self.server_name]
            self.server_name_field.setText(self.server_name)
            self.host_field.setText(server_info.get('host', ''))
            self.username_field.setText(server_info.get('username', ''))
            self.password_field.setText(server_info.get('password', ''))
            self.port_field.setText(str(server_info.get('port', '443')))
    
    def save_server(self):
        """Save the server configuration"""
        name = self.server_name_field.text().strip()
        if not name:
            self.show_status("✖ Server name is required.", "red")
            return
        
        # Check if we're renaming to an existing name (and it's not the same server)
        if name != self.server_name and name in self.config:
            self.show_status("✖ A server with this name already exists.", "red")
            return
        
        # Save the server configuration
        self.config[name] = {
            'host': self.host_field.text().strip(),
            'username': self.username_field.text().strip(),
            'password': self.password_field.text().strip(),
            'port': int(self.port_field.text().strip()) if self.port_field.text().strip().isdigit() else 443
        }
        
        # If we renamed the server, remove the old entry
        if self.is_edit_mode and self.server_name != name and self.server_name in self.config:
            del self.config[self.server_name]
        
        self.show_status(f"✔ Server '{name}' saved successfully.", "green")
        
        # Close the dialog after a short delay
        QTimer.singleShot(1500, self.accept)
    
    def test_connection(self):
        """Test the connection to the server"""
        self.status_label.clear()
        host = self.host_field.text().strip()
        username = self.username_field.text().strip()
        password = self.password_field.text().strip()
        port = int(self.port_field.text().strip()) if self.port_field.text().strip().isdigit() else 443
        
        if not host or not username or not password:
            self.show_status("✖ Please fill in all connection fields.", "red")
            return
        
        proto = 'https' if port == 443 else 'http'
        try:
            s = requests.Session()    
            if app_http_login(s, proto, host, username, password):
                self.show_status("✔ Connection successful!", "green")
            else:
                self.show_status("✖ Login failed.", "red")
        except Exception as e:
            self.show_status(f"✖ Connection failed: {str(e)}", "red")
    
    def show_status(self, message, color):
        """Show status message with specified color"""
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setText(message)
        QTimer.singleShot(4000, lambda: self.status_label.clear())
