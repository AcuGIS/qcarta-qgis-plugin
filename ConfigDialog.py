import os
import requests
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QPushButton, QVBoxLayout, QLabel, QHBoxLayout, QComboBox
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt, QTimer
from .util import app_http_login
from .ServerConfigModal import ServerConfigModal

class ConfigDialog(QDialog):
    def __init__(self, config, save_callback=None):
        super().__init__()
        self.setWindowTitle("Configure QCarta Access")
        self.config = config
        self.save_callback = save_callback
        self.layout = QVBoxLayout()

        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), 'logo.png')
        if os.path.exists(logo_path):
            logo_label.setPixmap(QIcon(logo_path).pixmap(120, 40))
        branding_label = QLabel("<b style='font-size:14pt;'>QCarta Servers</b><br><span style='font-size:10pt;'>Add and Configure QCarta Servers</span>")
        branding_label.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(logo_label)
        self.layout.addWidget(branding_label)

        # Server selection section
        server_section_layout = QVBoxLayout()
        
        # Selected server dropdown
        self.selected_server_dropdown = QComboBox()
        # Filter out metadata keys like '_selected_server'
        server_names = [key for key in config.keys() if not key.startswith('_')]
        self.selected_server_dropdown.addItems(sorted(server_names))
        
        server_section_layout.addWidget(QLabel("Selected Server:"))
        server_section_layout.addWidget(self.selected_server_dropdown)
        
        # Add/Edit button
        self.add_edit_button = QPushButton("Edit Server")
        self.add_edit_button.clicked.connect(self.open_server_modal)
        server_section_layout.addWidget(self.add_edit_button)
        
        # Add New button (always visible)
        self.add_new_button = QPushButton("Add New Server")
        self.add_new_button.clicked.connect(self.add_new_server)
        server_section_layout.addWidget(self.add_new_button)
        
        self.layout.addLayout(server_section_layout)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: green;")
        self.layout.addWidget(self.status_label)

        # Button layout
        self.button_layout = QHBoxLayout()
        self.delete_button = QPushButton("Delete Server")
        self.delete_button.clicked.connect(self.delete_server)
        self.button_layout.addWidget(self.delete_button)

        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)

        self.selected_server_dropdown.currentTextChanged.connect(self.update_selected_server)
        
        # Set initial selection if there's only one server
        if self.selected_server_dropdown.count() == 1:
            self.selected_server_dropdown.setCurrentIndex(0)
            self.update_selected_server(self.selected_server_dropdown.currentText())
        elif self.selected_server_dropdown.count() == 0:
            self.add_edit_button.setEnabled(False)

    def open_server_modal(self):
        """Open the server configuration modal in edit mode"""
        selected_server = self.selected_server_dropdown.currentText()
        
        # Only open in edit mode if a server is selected
        if selected_server and selected_server in self.config:
            modal = ServerConfigModal(self.config, selected_server, self)
            
            if modal.exec_() == QDialog.Accepted:
                # Refresh the dropdown after modal closes
                self.refresh_server_dropdown()
                
                # Save config if callback is provided
                if self.save_callback:
                    self.save_callback(self.config)
        else:
            self.show_status("✖ Please select a server to edit.", "red")

    def add_new_server(self):
        """Open the server configuration modal in add mode"""
        modal = ServerConfigModal(self.config, None, self)
        
        if modal.exec_() == QDialog.Accepted:
            # Refresh the dropdown after modal closes
            self.refresh_server_dropdown()
            
            # Save config if callback is provided
            if self.save_callback:
                self.save_callback(self.config)

    def delete_server(self):
        """Delete the currently selected server"""
        selected_server = self.selected_server_dropdown.currentText()
        
        if not selected_server or selected_server not in self.config:
            self.show_status("✖ No server selected to delete.", "red")
            return
        
        confirm = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Are you sure you want to delete server '{selected_server}'?", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm != QMessageBox.Yes:
            return
        
        # Delete the server
        del self.config[selected_server]
        
        # Clear selected server if it was the deleted one
        if self.config.get('_selected_server') == selected_server:
            self.config['_selected_server'] = None
        
        # Refresh the dropdown
        self.refresh_server_dropdown()
        
        self.show_status(f"✔ Server '{selected_server}' deleted.", "green")

    def refresh_server_dropdown(self):
        """Refresh the server dropdown with current config"""

        self.selected_server_dropdown.clear()

        # Filter out metadata keys like '_selected_server'
        server_names = [key for key in self.config.keys() if not key.startswith('_')]
        self.selected_server_dropdown.addItems(sorted(server_names))
        
        # Update button text based on selection
        if self.selected_server_dropdown.count() > 0:
            self.add_edit_button.setEnabled(True)
            self.selected_server_dropdown.setCurrentIndex(0)
        else:
            self.add_edit_button.setEnabled(False)
        self.update_selected_server()

    def show_status(self, message, color):
        """Show status message with specified color"""
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setText(message)
        QTimer.singleShot(4000, lambda: self.status_label.clear())
    
    def update_selected_server(self, selected_server=None):
        """Update the selected server in the config"""
        if selected_server is None:
            selected_server = self.selected_server_dropdown.currentText()

        self.config['_selected_server'] = selected_server
        # Save config immediately after selection change
        if self.save_callback:
            self.save_callback(self.config)
