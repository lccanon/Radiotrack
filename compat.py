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
from qgis.core import QgsGeometry
from qgis.core import QgsMessageLog
from qgis.gui import QgsMessageBar

# Python version (2 to 3)

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

def write_csv(csv_file_name, array):
    try:
        if PY2:
            with open(csv_file_name, 'w') as output_file:
                for row in array:
                    for cell in row:
                        if cell.find(',') != -1:
                            cell = '"' + cell + '"'
                    line = (u','.join(row) + u'\n').encode("utf-8")
                    output_file.write(line)
        else:
            with io.open(csv_file_name, 'w', newline='') as output_file:
                writer = csv.writer(output_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

                writer.writerows(array)

        return True
    except:
        return False


def get_field(field):
    if PY2:
        return field.decode(sys.getfilesystemencoding())
    else:
        return field

# QGis and Qt versions (2 to 3 and 4 to 5)

def get_filename_qdialog(qdialog_return):
    if QGis.QGIS_VERSION_INT >= 30000:
        # Qt 5
        return qdialog_return[0]
    else:
        # Qt 4
        return qdialog_return

if hasattr(core, "QGis"):
    from qgis.core import QGis
else:
    from qgis.core import Qgis as QGis

if QGis.QGIS_VERSION_INT >= 30000:
    from qgis.PyQt.QtWidgets import QAction, QDockWidget, QShortcut, QItemEditorFactory, QStyledItemDelegate, QDoubleSpinBox, QCheckBox, QDateTimeEdit
    from qgis.core import QgsProject
    from qgis.core import QgsPointXY

    buildGeomPoint = lambda x, y: QgsGeometry.fromPointXY(QgsPointXY(x, y))

    message_log_levels = {
        "Info": QGis.Info,
        "Warning": QGis.Warning,
        "Critical": QGis.Critical,
    }
    message_bar_levels = message_log_levels
else:
    from qgis.PyQt.QtGui import QAction, QDockWidget, QShortcut, QItemEditorFactory, QStyledItemDelegate, QDoubleSpinBox, QCheckBox, QDateTimeEdit
    from qgis.core import QgsMapLayerRegistry as QgsProject
    from qgis.core import QgsPoint

    buildGeomPoint = lambda x, y: QgsGeometry.fromPoint(QgsPoint(x, y))

    message_log_levels = {
        "Info": QgsMessageLog.INFO,
        "Warning": QgsMessageLog.WARNING,
        "Critical": QgsMessageLog.CRITICAL,
    }
    message_bar_levels = {
        "Info": QgsMessageBar.INFO,
        "Warning": QgsMessageBar.WARNING,
        "Critical": QgsMessageBar.CRITICAL,
    }
