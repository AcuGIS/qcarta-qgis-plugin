import os
import requests
from qgis.PyQt.QtWidgets import QVBoxLayout, QMessageBox, QDialog, QVBoxLayout, QLabel, QFormLayout, QComboBox, QComboBox, QHBoxLayout, QProgressBar, QTextEdit, QDialog, QVBoxLayout, QPushButton
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject
from .util import app_http_login

class UploadDialog(QDialog):
    def __init__(self, config, selected_server=None):
        super().__init__()
    
        self.config = config
        self.selected_server = selected_server
        self.setWindowTitle("Update QCarta store from Project Directory")
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(3, 3, 4, 4)
        self.layout.setSpacing(4)
    
        logo_path = os.path.join(os.path.dirname(__file__), 'logo.png')
        if os.path.exists(logo_path):
            logo_label = QLabel()
            logo_label.setPixmap(QIcon(logo_path).pixmap(120, 40))
            logo_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            logo_label.setContentsMargins(6, 6, 0, 0)
            self.layout.addWidget(logo_label)

        branding_label = QLabel(
            "<b style='font-size:14pt;'>Update Store</b><br>"
            "<span style='font-size:10pt;'>Update QGIS Project Store</span>"
        )
        branding_label.setAlignment(Qt.AlignCenter)
        branding_label.setContentsMargins(0, -10, 0, 0)
        self.layout.addWidget(branding_label)
    
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setVerticalSpacing(6)
        form_layout.setHorizontalSpacing(8)
        
        # Show selected server as label instead of dropdown
        if selected_server and selected_server in config:
            self.server_label = QLabel(f"Server: {selected_server}")
            self.server_label.setStyleSheet("font-weight: bold; color: #2E8B57;")
        else:
            self.server_label = QLabel("Server: No server selected")
            self.server_label.setStyleSheet("font-weight: bold; color: #DC143C;")
            
        self.store_dropdown = QComboBox()
        
        self.onServerChanged()
    
        form_layout.addRow(self.server_label)
        form_layout.addRow("Store:", self.store_dropdown)
    
        self.layout.addLayout(form_layout)
    
        button_box = QHBoxLayout()
        upload_btn = QPushButton("Upload")
        cancel_btn = QPushButton("Cancel")
        button_box.addWidget(upload_btn)
        button_box.addWidget(cancel_btn)
        self.layout.addLayout(button_box)
    
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(120)
        self.log_output.setVisible(False)
        self.layout.addWidget(self.log_output)
    
        self.setLayout(self.layout)
        
        upload_btn.clicked.connect(self.start_upload)
        cancel_btn.clicked.connect(self.reject)
    
    def onServerChanged(self):
        if not self.selected_server or self.selected_server not in self.config:
            self.store_dropdown.clear()
            return
            
        server_info = self.config.get(self.selected_server, {})
        if not server_info or not isinstance(server_info, dict):
            self.store_dropdown.clear()
            return
            
        stores = self.get_stores(server_info)
        stores = list(stores.keys())
        stores.sort()
        
        self.store_dropdown.blockSignals(True)
        self.store_dropdown.clear()
        self.store_dropdown.addItems(stores)
        self.store_dropdown.blockSignals(False)

    def read_in_chunks(self, file_object, chunk_size=65536):
        while True:
            data = file_object.read(chunk_size)
            if not data:
                break
            yield data

    def start_upload(self):
        server_name = self.selected_server
        store_name = self.store_dropdown.currentText()

        if not server_name or not store_name:
            QMessageBox.warning(self, "Missing Info", "Please select a server in the Configure tab and select a store.")
            return

        if server_name not in self.config:
            QMessageBox.warning(self, "Invalid Server", "Selected server is not configured.")
            return

        server_info = self.config[server_name]
        project_path = QgsProject.instance().fileName()
        if not project_path:
            QMessageBox.warning(None, "No Project", "Please save the QGIS project first.")
            return
        project_dir = os.path.dirname(project_path)
        
        proto = 'https' if server_info['port'] == 443 else 'http'

        s = requests.Session()
        try:
            if not app_http_login(s, proto, server_info['host'], server_info['username'], server_info['password']):
                QMessageBox.warning(None, "Login error", "Failed to login to with " + server_info['username'] + ' to ' + server_info['host'])
                return
            
            response = s.get(proto + '://' + server_info['host'] + '/rest/store/' + store_name, timeout=(10, 30))
            if response.status_code != 200:
                response = response.json();
                QMessageBox.warning(None, "Login error", "Failed to get store info: " + response['message'])
                return

        except Exception as e:
            QMessageBox.warning(None, "HTTP error", "Failed on login: " + str(e))
            return

        store_info = response.json()['store'];
        
        file_list = []
        for root, _, files in os.walk(project_dir):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, project_dir)
                
                try:
                    file_info = next(item for item in store_info['files'] if item["path"] == relative_path)
                except StopIteration:   # if file is missing on remote
                    file_info = {'path':relative_path, 'mtime':0}
                local_mtime = os.path.getmtime(local_path)

                if int(local_mtime) > file_info['mtime']:
                    file_list.append((local_path,relative_path));
        
        if len(file_list) == 0:
            QMessageBox.warning(None, "Upload info", "No new files to upload")
            return

        project_dir = os.path.dirname(project_path)
        try:
            self.progress_bar.setMaximum(len(file_list))
            self.progress_bar.setVisible(True)
            self.log_output.setVisible(True)
            
            store_updated = True
            chunk_size = store_info['post_max_size'] - 1000

            for i, (local_path,relative_path) in enumerate(file_list):
                self.progress_bar.setValue(i + 1)
                try:
                    with open(local_path, 'rb') as f:
                        offset = 0
                        
                        post_values={'action':'upload_bytes', 'source': os.path.basename(local_path)}
                        
                        for chunk in self.read_in_chunks(f):                                
                            post_values['start'] = offset
                            post_values['bytes'] = chunk
                            response = s.post(proto + '://' + server_info['host'] + '/admin/action/upload.php', data=post_values);
                            if response.status_code != 200:
                                raise Exception("Chunk upload failed")
                            offset = offset + len(chunk)
                    
                    post_values={'id':store_info['id'], 'action':'update_file', 'relative_path': relative_path, 'mtime': os.path.getmtime(local_path)}
                    response = s.post(proto + '://' + server_info['host'] + '/admin/action/qgs.php', data=post_values, timeout=(10, 30));
                    if response.status_code != 200:
                        raise Exception("Store update failed")

                    self.log_output.append(f"✔ Uploaded: {relative_path}")

                except Exception as e:
                    store_updated = False
                    self.log_output.append(f"✖ Failed to upload {relative_path}: {e}")
            
            if store_updated:
                QMessageBox.information(self, "Upload Complete", "Project directory uploaded successfully.")
            else:
                QMessageBox.critical(self, "Upload Incomplete", "Project directory wasn't uploaded successfully.")

            self.accept()
        except Exception as e:
            QMessageBox.critical(None, "Upload Failed", f"An error occurred: {e}")
        
    def get_stores(self, server_info):
        rv = {}
        
        if not server_info or not isinstance(server_info, dict):
            return rv
            
        proto = 'https' if server_info.get('port', 443) == 443 else 'http'
        try:
            response = requests.get(proto + '://' + server_info['host'] + '/rest/stores', auth=(server_info['username'], server_info['password']), timeout=(10, 30))
            if response.status_code == 200:
                response = response.json()
                for s in response['stores']['store']:
                    rv[s['name']] = s
        except Exception as e:
            QMessageBox.critical(None, "HTTP Error", f"An error occurred: {e}")

        return rv
