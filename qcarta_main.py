import os
import json
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

from .TabbedConsole import QCartaConsole

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".qcarta_uploader_config.json")

class AcugisQCartaPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.console_action = None

    def initGui(self):
        plugin_dir = os.path.dirname(__file__)
        icon_dir = os.path.join(plugin_dir, 'icons')
        console_icon_path = os.path.join(icon_dir, 'console.png')  # or icons/console.png

        self.console_action = QAction(QIcon(console_icon_path), "QCarta Console", self.iface.mainWindow())
        self.console_action.triggered.connect(self.open_console)

        # One toolbar button
        self.iface.addToolBarIcon(self.console_action)

        # Put it under the Web menu (Lizmap-style). Fallback to Plugins if needed.
        try:
            self.iface.addPluginToWebMenu("&QCarta", self.console_action)
        except Exception:
            self.iface.addPluginToMenu("&QCarta", self.console_action)

    def unload(self):
        if self.console_action:
            try:
                self.iface.removePluginWebMenu("&QCarta", self.console_action)
            except Exception:
                self.iface.removePluginMenu("&QCarta", self.console_action)
            self.iface.removeToolBarIcon(self.console_action)
            self.console_action = None

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_config(self, config):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except Exception:
            pass

    def open_console(self):
        config = self.load_config()
        dlg = QCartaConsole(config, parent=self.iface.mainWindow(), save_callback=self.save_config)
        dlg.exec_()

def classFactory(iface):
    return AcugisQCartaPlugin(iface)
