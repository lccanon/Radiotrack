# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RadiotrackDockWidget
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

import io
import os

from qgis.PyQt import QtCore, QtGui, uic, QtWidgets

def importDoc(qTextDoc):
    qTextDoc.setOpenLinks(True)
    qTextDoc.setOpenExternalLinks(True)
    docFile = './Documentation/README.html'
    qTextDoc.clear()
    THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
    my_file = os.path.join(THIS_FOLDER, docFile)
    qTextDoc.setSource(QtCore.QUrl.fromLocalFile(my_file))
