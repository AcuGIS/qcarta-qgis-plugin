# TabbedConsole.py
import os
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QStackedWidget, QWidget, QListWidgetItem
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon

# Use your existing dialogs (pure Python)
from .ConfigDialog import ConfigDialog
from .CreateDialog import CreateDialog
from .UploadDialog import UploadDialog
from .PublishDialog import PublishDialog

class QCartaConsole(QDialog):
    """
    Single tabbed window that embeds your existing dialogs:
      - Configure Access
      - Create Store
      - Update Store
      - Publish Map
    """
    def __init__(self, config, parent=None, save_callback=None):
        super().__init__(parent)
        self.config = config
        self.save_callback = save_callback
        self.setWindowTitle("QCarta Console")
        self.resize(900, 650)

        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left side: List widget acting as tabs
        self.tab_list = QListWidget()
        self.tab_list.setMaximumWidth(150)
        self.tab_list.setMinimumWidth(150)
        self.tab_list.setStyleSheet("""
            QListWidget {
                background-color: #5D5D5D;
                border: none;
                outline: none;
		color: white;
            }
            QListWidget::item {
                padding: 12px 8px;
                border-bottom: none;
            }
            QListWidget::item:selected {
                background-color: #36454F;
                color: yellow;
            }
            QListWidget::item:hover {
                background-color: #36454F;
		color: white;
            }
        """)
        
        # Right side: Stacked widget for content
        self.content_stack = QStackedWidget()
        
        # Add to main layout
        main_layout.addWidget(self.tab_list)
        main_layout.addWidget(self.content_stack, 1)  # stretch factor 1
        
        # Create tab items and dialogs
        self.dialogs = {}
        
        # Validate and clean up selected server
        selected_server = config.get('_selected_server')
        if selected_server and selected_server not in config:
            # Selected server no longer exists, clear it
            config['_selected_server'] = None
            if self.save_callback:
                self.save_callback(config)
        
        self.setup_tabs(config)
        
        # Connect selection change
        self.tab_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        
        # Connect to config dialog's server selection change
        if "Configure" in self.dialogs:
            self.dialogs["Configure"].selected_server_dropdown.currentTextChanged.connect(self.update_other_tabs)

    def setup_tabs(self, config):
        """Setup the tab list and dialogs"""
        # Get the plugin directory for icons
        plugin_dir = os.path.dirname(__file__)
        icon_dir = os.path.join(plugin_dir, 'icons')
        
        tab_items = [
            ("Configure", ConfigDialog, "configure.png"),
            ("Create Store", CreateDialog, "create.png"), 
            ("Publish", PublishDialog, "publish.png"),
            ("Update Store", UploadDialog, "update.png"),		
        ]
        
        for i, (title, dialog_cls, icon_name) in enumerate(tab_items):
            # Create icon
            icon_path = os.path.join(icon_dir, icon_name)
            icon = QIcon(icon_path)
            
            # Add to list widget with icon
            item = QListWidgetItem(icon, title)
            self.tab_list.addItem(item)
            
            # Create dialog
            if title == "Configure":
                dlg = dialog_cls(config, self.save_callback)
            elif title == "Create Store":
                # Pass selected server and parent console to CreateDialog
                selected_server = config.get('_selected_server')
                dlg = dialog_cls(config, selected_server, self)
            else:
                # Pass selected server to other dialogs
                selected_server = config.get('_selected_server')
                dlg = dialog_cls(config, selected_server)
            dlg.setWindowFlags(Qt.Widget)
            # Neutralize accept/reject so inner dialogs don't close the whole console
            dlg.accept = lambda *a, **k: None
            dlg.reject = lambda *a, **k: None
            
            # Create container widget
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(dlg)
            layout.addStretch()  # Push content to top
            
            # Add to stacked widget
            self.content_stack.addWidget(container)
            self.dialogs[title] = dlg
        
        # Select first tab
        self.tab_list.setCurrentRow(0)
    
    def update_other_tabs(self, selected_server):
        """Update other tabs when server selection changes in Configure tab"""
        # Update the config with the new selected server
        self.config['_selected_server'] = selected_server
        
        # Update other dialogs
        for title, dialog in self.dialogs.items():
            if title != "Configure":
                # Update the server label in other dialogs
                if hasattr(dialog, 'server_label'):
                    if selected_server and selected_server in self.config:
                        dialog.server_label.setText(f"Server: {selected_server}")
                        dialog.server_label.setStyleSheet("font-weight: bold; color: #2E8B57;")
                    else:
                        dialog.server_label.setText("Server: No server selected")
                        dialog.server_label.setStyleSheet("font-weight: bold; color: #DC143C;")
                
                # Update the selected server in the dialog
                if hasattr(dialog, 'selected_server'):
                    dialog.selected_server = selected_server
                
                # Trigger server change updates for dialogs that need it
                if hasattr(dialog, 'onServerChanged'):
                    dialog.onServerChanged()
    
    def refresh_store_lists(self):
        """Refresh store lists in all dialogs that have them"""
        for title, dialog in self.dialogs.items():
            if hasattr(dialog, 'updateStores'):
                dialog.updateStores()
