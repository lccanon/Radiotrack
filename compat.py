# -*- coding: utf-8 -*-
"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os, csv, io
import sys
from qgis import core
from qgis.core import QgsMessageLog
from qgis.gui import QgsMessageBar

# Python version (2 to 3)

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

def writeCsv(csvFileName, array):
    try:
        if PY2:
            with open(csvFileName, 'w') as outpulFile:
                for row in array:
                    for cell in row:
                        if cell.find(',') != -1:
                            cell = '"' + cell + '"'
                    line = (u','.join(row) + u'\n').encode('utf-8')
                    outpulFile.write(line)
        else:
            with io.open(csvFileName, 'w', newline = '') as outpulFile:
                writer = csv.writer(outpulFile, delimiter = ',', quotechar = '"', quoting = csv.QUOTE_MINIMAL)

                writer.writerows(array)

        return True
    except:
        return False


def getField(field):
    if PY2:
        return field.decode(sys.getfilesystemencoding())
    else:
        return field

# QGis and Qt versions (2 to 3 and 4 to 5)

def getFilenameQdialog(qdialogReturn):
    if QGis.QGIS_VERSION_INT >= 30000:
        # Qt 5
        return qdialogReturn[0]
    else:
        # Qt 4
        return qdialogReturn

if hasattr(core, 'QGis'):
    from qgis.core import QGis
else:
    from qgis.core import Qgis as QGis

if QGis.QGIS_VERSION_INT >= 30000:
    from qgis.PyQt.QtWidgets import QAction, QDockWidget, QShortcut, QItemEditorFactory, QStyledItemDelegate, QDoubleSpinBox, QCheckBox, QDateTimeEdit

    messageLogLevels = {
        'Info': QGis.Info,
        'Warning': QGis.Warning,
        'Critical': QGis.Critical,
    }
    messageBarLevels = messageLogLevels
else:
    from qgis.PyQt.QtGui import QAction, QDockWidget, QShortcut, QItemEditorFactory, QStyledItemDelegate, QDoubleSpinBox, QCheckBox, QDateTimeEdit

    messageLogLevels = {
        'Info': QgsMessageLog.INFO,
        'Warning': QgsMessageLog.WARNING,
        'Critical': QgsMessageLog.CRITICAL,
    }
    messageBarLevels = {
        'Info': QgsMessageBar.INFO,
        'Warning': QgsMessageBar.WARNING,
        'Critical': QgsMessageBar.CRITICAL,
    }
