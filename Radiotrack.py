# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Radiotrack
                                 A QGIS plugin
 This plugin allows to process data from a csv file
                              -------------------
        begin                : 2018-11-10
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Wetzel Anthony, Bello Fernando, Moyikoulou Chris-Féri
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import Qgis as QGis

# Initialize Qt resources from file resources.py
from . import resources

# Import the code for the DockWidget
from .radiotrack_dockwidget import RadiotrackDockWidget
import os.path

class radiotrack:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.pluginDir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        localePath = os.path.join(
            self.pluginDir,
            'i18n',
            'Radiotrack_{}.qm'.format(locale))
        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)
            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
        self.dlg = RadiotrackDockWidget()
        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Radiotrack')
        # Create the dockwidget (after translation) and keep reference
        self.dockwidget = RadiotrackDockWidget()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """

        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Radiotrack', message)

    def addAction(
        self,
        iconPath,
        text,
        callback,
        enabledFlag = True,
        addToMenu = True,
        addToToolbar = True,
        statusTip = None,
        whatsThis = None,
        parent = None):
        """Add a toolbar icon to the toolbar.

        :param iconPath: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type iconPath: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabledFlag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabledFlag: bool

        :param addToMenu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type addToMenu: bool

        :param addToToolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type addToToolbar: bool

        :param statusTip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type statusTip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whatsThis: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(iconPath)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabledFlag)

        if statusTip is not None:
            action.setStatusTip(statusTip)
        if whatsThis is not None:
            action.setWhatsThis(whatsThis)
        if addToToolbar:
            self.iface.addToolBarIcon(action)
        if addToMenu:
            self.iface.addPluginToMenu(
                self.menu,
                action)
        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        iconPath = ':/plugins/Radiotrack/icon.png'
        actionOpen = self.addAction(
            iconPath,
            text = self.tr(u'Open/close Radiotrack'),
            callback = self.run,
            parent = self.iface.mainWindow())
        # Configure shortcut (use configured one if any)
        DEFAULT = 'Ctrl+Alt+B'
        settings = QSettings()
        settings.beginGroup('shortcuts')
        shortcut = settings.value(actionOpen.text())
        if shortcut is None:
            shortcut = DEFAULT
        self.iface.registerMainWindowAction(actionOpen, shortcut)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)


    #--------------------------------------------------------------------------
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Radiotrack'),
                action)
            self.iface.removeToolBarIcon(action)
            self.iface.unregisterMainWindowAction(action)
        self.dockwidget.clear()

    #--------------------------------------------------------------------------
    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.dockwidget.isVisible():
            # show the dockwidget
            self.dockwidget.show()
        else:
            self.dockwidget.close()
