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
from qgis import core
from qgis.core import QgsGeometry
from qgis.core import QgsMessageLog
from qgis.gui import QgsMessageBar

if hasattr(core, "QGis"):
    from qgis.core import QGis
else:
    from qgis.core import Qgis as QGis

if QGis.QGIS_VERSION_INT >= 30000:
    from qgis.PyQt.QtWidgets import QAction, QDockWidget, QTableView,QShortcut
    from qgis.PyQt.QtGui import QKeySequence
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
    from qgis.PyQt.QtGui import QAction, QDockWidget, QTableView,QKeySequence,QShortcut
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

#def getCanvasDestinationCrs(iface):
#    if QGis.QGIS_VERSION_INT >= 30000:
#        return iface.mapCanvas().mapSettings().destinationCrs()
#    else:
#        return iface.mapCanvas().mapRenderer().destinationCrs()
