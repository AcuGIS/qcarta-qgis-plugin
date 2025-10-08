import os
import requests
from qgis.PyQt.QtWidgets import QVBoxLayout, QMessageBox, QLineEdit, QDialog, QVBoxLayout, QLabel, QFormLayout, QComboBox, QComboBox, QHBoxLayout, QProgressBar, QTextEdit, QDialog, QVBoxLayout, QPushButton, QCheckBox, QListWidget, QListWidgetItem, QSizePolicy
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject
from .util import app_http_login

class PublishDialog(QDialog):
    def __init__(self, config, selected_server=None):
        super().__init__()
    
        self.config = config
        self.selected_server = selected_server
        self.setWindowTitle("Create QCarta Layer")
        self.layout = QVBoxLayout()
    
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), 'logo.png')
        if os.path.exists(logo_path):
            logo_label.setPixmap(QIcon(logo_path).pixmap(120, 40))
        branding_label = QLabel("<b style='font-size:14pt;'>Publish Project</b><br><span style='font-size:10pt;'>Publish QCarta Project</span>")
        branding_label.setAlignment(Qt.AlignCenter)
    
        self.layout.addWidget(logo_label)
        self.layout.addWidget(branding_label)
    
        form_layout = QFormLayout()

        self.s = None
        self.stores = {}
        self.access_groups = {}
        self.basemaps = {}

        # Show selected server as label instead of dropdown
        if selected_server and selected_server in config:
            self.server_label = QLabel(f"Server: {selected_server}")
            self.server_label.setStyleSheet("font-weight: bold; color: #2E8B57;")
        else:
            self.server_label = QLabel("Server: No server selected")
            self.server_label.setStyleSheet("font-weight: bold; color: #DC143C;")
        
        self.store_dropdown = QComboBox()
        self.store_dropdown.currentIndexChanged.connect(self.updateLayers)
    
        self.layer_dropdown = QListWidget()
        self.layer_dropdown.setSelectionMode(QListWidget.ExtendedSelection)
        self.print_layout_dropdown = QComboBox()

        # optional: give inputs some minimum width so the dialog must grow
        self.store_dropdown.setMinimumWidth(250)

        self.layer_name = QLineEdit()
        self.layer_desc = QLineEdit()
        self.basemaps_dropdown = QComboBox()

        self.auto_generate_thumbnail = QCheckBox()

        self.option_public = QCheckBox('Public Access')
        self.option_cached = QCheckBox('Cached')
        self.option_customized = QCheckBox('Custom Styling')
        
        layer_options = QHBoxLayout()
        layer_options.addWidget(self.option_public)
        layer_options.addWidget(self.option_cached)
        layer_options.addWidget(self.option_customized)
        layer_options.addStretch()
        
        self.option_proxyfied = QCheckBox('Enabled')
        self.option_proxyfied.stateChanged.connect(self.onProxyfiedChanged)
        
        self.option_exposed = QCheckBox('Separate Layers')
        self.option_exposed.setEnabled(False)

        mapproxy_box = QHBoxLayout()
        mapproxy_box.addWidget(self.option_proxyfied)
        mapproxy_box.addWidget(self.option_exposed)
        mapproxy_box.addStretch()

        self.show_charts = QCheckBox('Charts tab')
        self.show_dt = QCheckBox('Data tables')
        self.show_query = QCheckBox('Query tab')
        self.show_fi_edit = QCheckBox('FeatureInfo Edit')

        show_box = QHBoxLayout()
        show_box.addWidget(self.show_charts)
        show_box.addWidget(self.show_query)
        show_box.addWidget(self.show_dt)
        show_box.addWidget(self.show_fi_edit)

        self.access_groups_dropdown = QListWidget()
        self.access_groups_dropdown.setSelectionMode(QListWidget.MultiSelection)
        
        # Don't call updateBasemaps() and updateAccessGroups() here - they'll be called in onServerChanged()

        form_layout.addRow(self.server_label)
        form_layout.addRow("Store:", self.store_dropdown)
        form_layout.addRow("Layer:", self.layer_dropdown)
        form_layout.addRow("Print Layout:", self.print_layout_dropdown)

        form_layout.addRow("Name:", self.layer_name)
        form_layout.addRow("Description:", self.layer_desc)
        form_layout.addRow("Basemap:", self.basemaps_dropdown)
        
        form_layout.addRow("Auto Thumbnail:", self.auto_generate_thumbnail)
        
        form_layout.addRow("Mapproxy:", mapproxy_box)
        form_layout.addRow("Layer options:", layer_options)        
        form_layout.addRow("Show options:", show_box)

        form_layout.addRow("Access Groups:", self.access_groups_dropdown)
    
        self.layout.addLayout(form_layout)
    
        button_box = QHBoxLayout()
        create_btn = QPushButton("Create")
        cancel_btn = QPushButton("Cancel")
        button_box.addWidget(create_btn)
        button_box.addWidget(cancel_btn)
        self.layout.addLayout(button_box)
            
        self.setLayout(self.layout)
    
        # make the dialog open bigger and allow growing
        self.setMinimumSize(560, 500)
        self.resize(560, 500)  # initial size
        self.setSizeGripEnabled(True)
    
        # let form fields expand
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    
        create_btn.clicked.connect(self.create_layer)
        cancel_btn.clicked.connect(self.reject)
        
        # Call onServerChanged after all widgets are created
        self.onServerChanged()
    
    def onServerChanged(self):
        if not self.selected_server or self.selected_server not in self.config:
            return
            
        server_info = self.config.get(self.selected_server, {})
        if not server_info or not isinstance(server_info, dict):
            return
            
        proto = 'https' if server_info.get('port', 443) == 443 else 'http'
        
        if self.s:
            self.s.close()
        self.s = requests.Session()
        
        try:
            if not app_http_login(self.s, proto, server_info['host'], server_info['username'], server_info['password']):
                QMessageBox.warning(None, "Login error", "Failed to login to with " + server_info['username'] + ' to ' + server_info['host'])
                self.s.close()
                self.s = None
                return
        except Exception as e:
            QMessageBox.warning(None, "HTTP error", "Failed on login: " + str(e))
            return

        self.updateStores()
        self.updateLayers()
        self.updateBasemaps()
        self.updateAccessGroups()
    
    def onProxyfiedChanged(self):
        self.option_exposed.setEnabled(self.option_proxyfied.isChecked())

    def updateStores(self):
        if not self.selected_server or self.selected_server not in self.config:
            return
            
        server_info = self.config.get(self.selected_server, {})
        if not server_info or not isinstance(server_info, dict):
            return
            
        stores = self.get_stores(server_info)
        stores.sort()
        
        self.store_dropdown.blockSignals(True)
        self.store_dropdown.clear()
        self.store_dropdown.addItems(stores)
        self.store_dropdown.blockSignals(False)
    
    def updateLayers(self):
        if not self.selected_server or self.selected_server not in self.config:
            return
            
        server_info = self.config.get(self.selected_server, {})
        if not server_info or not isinstance(server_info, dict):
            return
            
        store_name = self.store_dropdown.currentText()
        
        store_info = self.get_store_info(server_info,store_name)
        
        layers        = store_info['Layers'].split(',')
        print_layouts = store_info['Layouts'].split(',')
        
        self.layer_dropdown.blockSignals(True)
        self.layer_dropdown.clear()
        layers.sort()
        for l in layers:
            self.layer_dropdown.addItem(QListWidgetItem(l))
        self.layer_dropdown.blockSignals(False)
        
        self.print_layout_dropdown.blockSignals(True)
        self.print_layout_dropdown.clear()
        print_layouts.sort()
        self.print_layout_dropdown.addItems(print_layouts)
        self.print_layout_dropdown.blockSignals(False)
    
    def updateBasemaps(self):
        if not self.selected_server or self.selected_server not in self.config:
            return
            
        server_info = self.config.get(self.selected_server, {})
        if not server_info or not isinstance(server_info, dict):
            return

        self.basemaps_dropdown.blockSignals(True)
        self.basemaps_dropdown.clear()
        
        for g in self.get_basemaps(server_info):
            self.basemaps[g['name']] = g['id']
            self.basemaps_dropdown.addItem(g['name'])
        self.basemaps_dropdown.blockSignals(False)
    
    def updateAccessGroups(self):
        if not self.selected_server or self.selected_server not in self.config:
            return
            
        server_info = self.config.get(self.selected_server, {})
        if not server_info or not isinstance(server_info, dict):
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
    
    def get_basemaps(self, server_info):
        rv = {}
        
        proto = 'https' if server_info['port'] == 443 else 'http'
        try:
            response = self.s.post(proto + '://' + server_info['host'] + '/admin/action/basemap.php', data={'action':'list'}, timeout=(10, 30))
            if response.status_code == 200:
                response = response.json()
                if response['success']:
                    rv = response['basemaps']
                else:
                    QMessageBox.warning(None, "QCarta Error", response['message'])
        except Exception as e:
            QMessageBox.critical(None, "HTTP Error", f"An error occurred: {e}")

        return rv

    def get_stores(self, server_info):
        
        proto = 'https' if server_info['port'] == 443 else 'http'
        try:
            response = self.s.get(proto + '://' + server_info['host'] + '/rest/stores', timeout=(10, 30))
            if response.status_code == 200:
                response = response.json()
                for s in response['stores']['store']:
                    self.stores[s['name']] = s
        except Exception as e:
            QMessageBox.critical(None, "HTTP Error", f"An error occurred: {e}")

        return list(self.stores.keys())
    
    def get_store_info(self, server_info, store_name):
        rv = {}
        
        proto = 'https' if server_info['port'] == 443 else 'http'
        try:
            response = self.s.post(proto + '://' + server_info['host'] + '/admin/action/qgs.php', data={'action':'info', 'id': self.stores[store_name]['id']}, timeout=(10, 30))
            if response.status_code == 200:
                response = response.json()
                if response['success']:
                    rv = response['message']
                else:
                    QMessageBox.warning(None, "QCarta Error", response['message'])
        except Exception as e:
            QMessageBox.critical(None, "HTTP Error", f"An error occurred: {e}")

        return rv
            
    def create_layer(self):
        server_name = self.selected_server
        store_name = self.store_dropdown.currentText()

        layer_name = self.layer_name.text()
        layer_desc = self.layer_desc.text()

        # Get basemap ID safely
        basemap_text = self.basemaps_dropdown.currentText()
        if basemap_text and basemap_text in self.basemaps:
            basemap_id = self.basemaps[basemap_text]
        else:
            basemap_id = None

        print_layout = self.print_layout_dropdown.currentText()
        
        # convert access group names to ids
        map_access_groups = []
        for g in self.access_groups_dropdown.selectedItems():
            map_access_groups.append(self.access_groups[g.text()])
            
        # QListWidget preserves the order of clicks in MultiSelection, so we get selected items through indexes
        selectedIndexes = []
        for idx in self.layer_dropdown.selectedIndexes():
            selectedIndexes.append(idx.row())
        selectedIndexes.sort()

        qgis_layers = []
        for i in selectedIndexes:
            qgis_layers.append(self.layer_dropdown.item(i).text())

        if not server_name or not layer_name:
            QMessageBox.warning(self, "Missing Info", "Please select a server in the Configure tab and enter a layer name.")
            return
        
        if not map_access_groups:
            QMessageBox.warning(self, "Missing Info", "Please select layer access groups.")
            return

        server_info = self.config[server_name]
        proto = 'https' if server_info['port'] == 443 else 'http'
        
        try:
            post_data = {'action':'save', 'id': 0, 'store_id': self.stores[store_name]['id'], 'layers[]': qgis_layers, 'name':layer_name, 'description':layer_desc, 'print_layout': print_layout, 'group_id[]':map_access_groups}
            if basemap_id is not None:
                post_data['basemap_id'] = basemap_id
            if self.option_public.isChecked():
                post_data['public'] = 't'
            if self.option_cached.isChecked():
                post_data['cached'] = 't'
            if self.option_proxyfied.isChecked():
                post_data['proxyfied'] = 't'
            if self.option_customized.isChecked():
                post_data['customized'] = 't'
            if self.option_exposed.isChecked():
                post_data['exposed'] = 't'
            if self.auto_generate_thumbnail.isChecked():
                post_data['auto_thumbnail'] = 't'
            
            if self.show_charts.isChecked():
                post_data['show_charts'] = 't'
            if self.show_dt.isChecked():
                post_data['show_dt'] = 't'
            if self.show_query.isChecked():
                post_data['show_query'] = 't'
            if self.show_fi_edit.isChecked():
                post_data['show_fi_edit'] = 't'

            response = self.s.post(proto + '://' + server_info['host'] + '/admin/action/qgs_layer.php', data=post_data, timeout=(10, 30))
            if response.status_code != 200:
                QMessageBox.warning(None, "HTTP error", "HTTP code " + str(response.status_code))
                return

            response = response.json();
            if response['success']:
                layer_url = proto + '://' + server_info['host'] + '/layers/' + response['id'] + '/index.php';
                QMessageBox.information(None, "AcuGIS QCarta", 'Layer published. You can view it at <a href="' + layer_url +'">' + layer_url + '</a>')
            else:
                QMessageBox.warning(None, "QCarta error", response['message'])

        except Exception as e:
            QMessageBox.warning(None, "HTTP error", "HTTP code " + str(response.status_code))
            return

        self.accept()
