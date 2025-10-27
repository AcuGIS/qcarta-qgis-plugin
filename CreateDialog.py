import os
import requests
from qgis.PyQt.QtWidgets import QVBoxLayout, QMessageBox, QLineEdit, QDialog, QVBoxLayout, QLabel, QFormLayout, QComboBox, QComboBox, QHBoxLayout, QProgressBar, QTextEdit, QDialog, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject
from .util import app_http_login

class CreateDialog(QDialog):
    def __init__(self, config, selected_server=None, parent_console=None):
        super().__init__()
    
        self.config = config
        self.selected_server = selected_server
        self.parent_console = parent_console
        self.setWindowTitle("Create QCarta store from Project Directory")
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(3, 3, 4, 4)
        self.layout.setSpacing(4)
        self.access_groups = {}
    
        logo_path = os.path.join(os.path.dirname(__file__), 'logo.png')
        if os.path.exists(logo_path):
            logo_label = QLabel()
            logo_label.setPixmap(QIcon(logo_path).pixmap(120, 40))
            logo_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            logo_label.setContentsMargins(6, 6, 0, 0)
            self.layout.addWidget(logo_label)

        branding_label = QLabel(
            "<b style='font-size:14pt;'>Create Store</b><br>"
            "<span style='font-size:10pt;'>Create a QGIS Store</span>"
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

        self.store_name = QLineEdit()
        
        form_layout.addRow(self.server_label)
        form_layout.addRow("Store:", self.store_name)
    
        self.layout.addLayout(form_layout)
    
        self.access_groups_dropdown = QListWidget()
        self.access_groups_dropdown.setSelectionMode(QListWidget.MultiSelection)    


        form_layout.addRow("Access Groups:", self.access_groups_dropdown)

        button_box = QHBoxLayout()
        create_btn = QPushButton("Create")
        cancel_btn = QPushButton("Cancel")
        button_box.addWidget(create_btn)
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
        
        create_btn.clicked.connect(self.create_store)
        cancel_btn.clicked.connect(self.reject)
        
        self.s = requests.Session()
        self.onServerChanged()


    def onServerChanged(self):
        if not self.selected_server or self.selected_server not in self.config:
            self.access_groups_dropdown.clear()
            return
            
        server_info = self.config.get(self.selected_server, {})
        if not server_info or not isinstance(server_info, dict):
            self.access_groups_dropdown.clear()
            return
        
        proto = 'https' if server_info.get('port', 443) == 443 else 'http'
        
        try:
            if not app_http_login(self.s, proto, server_info['host'], server_info['username'], server_info['password']):
                QMessageBox.warning(None, "Login error", "Failed to login to with " + server_info['username'] + ' to ' + server_info['host'])
        except Exception as e:
            QMessageBox.warning(None, "HTTP error", "Failed on login: " + str(e))
            return

        self.updateAccessGroups()

    def updateAccessGroups(self):
        if not self.selected_server or self.selected_server not in self.config:
            self.access_groups_dropdown.clear()
            return
            
        server_info = self.config.get(self.selected_server, {})
        if not server_info or not isinstance(server_info, dict):
            self.access_groups_dropdown.clear()
            return

        self.access_groups_dropdown.blockSignals(True)
        self.access_groups_dropdown.clear()
        
        for g in self.get_access_groups(server_info):
            self.access_groups[g['name']] = g['id']
            self.access_groups_dropdown.addItem(QListWidgetItem(g['name']))
        self.access_groups_dropdown.blockSignals(False)
    
    def get_access_groups(self, server_info):
        rv = {}
        
        proto = 'https' if server_info['port'] == 443 else 'http'
        try:
            response = self.s.post(proto + '://' + server_info['host'] + '/admin/action/access_group.php', data={'action':'list'}, timeout=(10, 30))
            if response.status_code == 200:
                response = response.json()
                if response['success']:
                    rv = response['access_groups']
                else:
                    QMessageBox.warning(None, "QCarta Error", response['message'])
        except Exception as e:
            QMessageBox.critical(None, "HTTP Error", f"An error occurred: {e}")

        return rv

    def read_in_chunks(self, file_object, chunk_size=65536):
        while True:
            data = file_object.read(chunk_size)
            if not data:
                break
            yield data

    def create_store(self):
        server_name = self.selected_server
        store_name = self.store_name.text()

        if not server_name or not store_name:
            QMessageBox.warning(self, "Missing Info", "Please select a server in the Configure tab and enter a store name.")
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
        
        # convert access group names to ids
        map_access_groups = []
        for g in self.access_groups_dropdown.selectedItems():
            map_access_groups.append(self.access_groups[g.text()])
        
        if not map_access_groups:
            QMessageBox.warning(self, "Missing Info", "Please select layer access groups.")
            return

        proto = 'https' if server_info['port'] == 443 else 'http'

        project_dir = os.path.dirname(project_path)
        
        qgs_list = []
        file_list = []
        try:
            for root, _, files in os.walk(project_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, project_dir)
                    
                    if file.endswith('.qgs'):
                        qgs_list.append(file)
                        with open(local_path, 'rb') as f:
                            offset = 0                            
                            post_values={'action':'upload_bytes', 'source': os.path.basename(local_path)}

                            for chunk in self.read_in_chunks(f):                                
                                post_values['start'] = offset
                                post_values['bytes'] = chunk
                                response = self.s.post(proto + '://' + server_info['host'] + '/admin/action/upload.php', data=post_values, timeout=(10,30));
                                if response.status_code != 200:
                                    raise Exception("Chunk upload failed")
                                offset = offset + len(chunk)
                    else:
                        file_list.append((local_path,relative_path));
        except Exception as e:
            QMessageBox.critical(None, "QGS Upload Failed", f"An error occurred: {e}")
            return
        
        # upload .qgs files, so we can create store
        post_values = {'action':'save', 'name': store_name, 'group_id[]': map_access_groups, 'source[]':qgs_list}
        
        response = self.s.post(proto + '://' + server_info['host'] + '/admin/action/qgs.php', data=post_values, timeout=(10,30))
        if response.status_code != 200:
            response = response.json();
            QMessageBox.warning(None, "Create error", "Failed to create store: " + response['message'])
            return

        # now upload all other files
        try:            
            # show progress bar and output
            self.progress_bar.setMaximum(len(file_list))
            self.progress_bar.setVisible(True)
            self.log_output.setVisible(True)

            try:
                response = self.s.get(proto + '://' + server_info['host'] + '/rest/store/' + store_name, timeout=(10, 30))
            except Exception as e:
                QMessageBox.warning(None, "HTTP error", "Failed to request store info: " + str(e))
                return

            if response.status_code != 200:
                response = response.json();
                QMessageBox.warning(None, "REST error", "Failed to get store info: " + response['message'])
                return
            
            store_info = response.json()['store'];

            chunk_size = store_info['post_max_size'] - 1000
            store_created = True
            
            for i, (local_path,relative_path) in enumerate(file_list):
                self.progress_bar.setValue(i + 1)
                try:
                    with open(local_path, 'rb') as f:
                        offset = 0
                        
                        post_values={'action':'upload_bytes', 'source': os.path.basename(local_path)}
                        
                        for chunk in self.read_in_chunks(f):                                
                            post_values['start'] = offset
                            post_values['bytes'] = chunk
                            response = self.s.post(proto + '://' + server_info['host'] + '/admin/action/upload.php', data=post_values, timeout=(10, 30));
                            if response.status_code != 200:
                                raise Exception("Chunk upload failed")
                            offset = offset + len(chunk)
                    
                    post_values={'id':store_info['id'], 'action':'update_file', 'relative_path': relative_path, 'mtime': os.path.getmtime(local_path)}
                    response = self.s.post(proto + '://' + server_info['host'] + '/admin/action/qgs.php', data=post_values, timeout=(10, 30));
                    if response.status_code != 200:
                        raise Exception("Store update failed")

                    self.log_output.append(f"✔ Uploaded: {relative_path}")

                except Exception as e:
                    store_created = False
                    self.log_output.append(f"✖ Failed to upload {relative_path}: {e}")
            if store_created:
                QMessageBox.information(self, "Create Complete", "Store created successfully.")
                # Refresh store lists in other tabs
                if self.parent_console:
                    self.parent_console.refresh_store_lists()
            else:
                QMessageBox.critical(self, "Create Incomplete", "Store created failed.")

            self.accept()
        except Exception as e:
            QMessageBox.critical(None, "Upload Failed", f"An error occurred: {e}")
