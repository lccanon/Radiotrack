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

import os, csv, sys
from qgis.PyQt import QtCore, QtGui, uic
from qgis.core import QgsMessageLog
from qgis.utils import iface
from qgis.gui import QgsMessageBar
import qgis

from qgis.PyQt.QtGui import QBrush, QColor, QFont, QKeySequence
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant
from qgis.PyQt.QtWidgets import QWidget, QFileDialog

from .compat import QShortcut

from .algorithmNewPoint import dst

from .compat import get_field, QDoubleSpinBox
from .compat import QDockWidget, QTableView, QItemEditorFactory, QStyledItemDelegate, message_log_levels, message_bar_levels

from .manageDocumentation import importDoc

from .csv_utils import table_info, select_csv_file, load_csv_to_array, save_array_to_csv, select_save_file
from .layer_utils import create_layers, update_layers, clear_layers
from .TrackingModel import TrackingModel


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Radiotrack_dockwidget_base.ui'))

COORD_PRECISION = 6 # precision up to 10 cm
COORD_MIN = -180 # longitude starts at -180°
COORD_MAX = 180 # longitude ends at 180°


class ItemEditorFactory(QItemEditorFactory):
    def __init__(self):
        super(QItemEditorFactory, self).__init__()


    def createEditor(self, userType, parent):
        if userType == QVariant.Double:
            doubleSpinBox = QDoubleSpinBox(parent)
            doubleSpinBox.setDecimals(COORD_PRECISION)
            doubleSpinBox.setRange(COORD_MIN, COORD_MAX)
            doubleSpinBox.setSingleStep(0.0001)
            return doubleSpinBox
        else:
            return super().createEditor(userType, parent)


class RadiotrackDockWidget(QDockWidget, FORM_CLASS):

    """Variables membre"""
    w = QWidget()

    """Brushes used for the table's cells' background"""
    BRUSH_VALID_ROW = QBrush(QColor(Qt.white))
    BRUSH_INVALID_CELL = QBrush(QColor(Qt.red).lighter(125))
    BRUSH_INVALID_ROW = QBrush(QColor(Qt.red).lighter(165))

    closingPlugin = pyqtSignal()

    layer_suffix = ''

    model = None

    def __init__(self, parent=None):
        """Constructor."""
        super(RadiotrackDockWidget, self).__init__(parent)
        self.setupUi(self)
        """Used statements"""
        """Plugin actions"""
        """Clear old layers"""
        clear_layers()
        """Import the documentation"""
        importDoc(self.documentationText)
        """Navigation in QTableWidget shortcut"""
        QShortcut(QKeySequence("Ctrl+PgDown"), self).activated.connect(self.navigateRightTab)
        QShortcut(QKeySequence("Ctrl+PgUp"), self).activated.connect(self.navigateLeftTab)
        """Import and export csv project actions"""
        self.importButton.clicked.connect(self.import_file)
        self.currentProjectText.clear()
        self.importButton.setShortcut("Ctrl+Alt+I")
        """Save actions"""
        self.saveAsButton.clicked.connect(self.save_as)
        self.saveAsButton.setShortcut("Ctrl+Alt+S")
        """Empty the table and the model, and forget the CSV file"""
        self.clearButton.clicked.connect(self.clear)
        self.clearButton.setShortcut("Ctrl+Alt+C")
        """Table actions"""
        styledItemDelegate = QStyledItemDelegate()
        styledItemDelegate.setItemEditorFactory(ItemEditorFactory())
        self.tableView.setItemDelegate(styledItemDelegate)

    def navigateRightTab(self):
        currentIndex=(self.tabWidget.currentIndex()-1)%self.tabWidget.count()
        self.tabWidget.setCurrentIndex(currentIndex)

    def navigateLeftTab(self):
        currentIndex=(self.tabWidget.currentIndex()+1)%self.tabWidget.count()
        self.tabWidget.setCurrentIndex(currentIndex)

    def closeEvent(self, event):
        """Clean Plugin close"""
        self.closingPlugin.emit()
        event.accept()

    def refresh(self, item):
        """Handle table edits

        Parameters
        ----------
        item
            The changed item of the table
        """
        # Disable auto refresh because we may change cells' colors
        self.model.itemChanged.disconnect()

        self.update_row(item.row())

        # Enable auto refresh again
        self.model.itemChanged.connect(self.refresh)
        QgsMessageLog.logMessage('Project refreshed', 'Radiotrack', level=message_log_levels["Info"])

    def clear(self):
        clear_layers()
        if self.model:
            self.model.clear()
        self.currentProjectText.setText('')
        QgsMessageLog.logMessage('Cleared layers and table', 'Radiotrack', level=message_log_levels["Info"])

    def update_row(self, row):
        """Reads the data from the changed row to update the colors in the
        table and the features in the map layers
        """
        # Restore the "valid" style for the row
        for col in range(self.model.columnCount()):
            current_item = self.model.item(row, col)
            current_item.setBackground(self.BRUSH_VALID_ROW)
            current_font = current_item.font()
            current_font.setBold(False)
            current_item.setFont(current_font)

        # Read the line's fields
        row_info = self.model.get_row(row)

        erroneous_columns = row_info['erroneous_columns']
        if erroneous_columns:
            self.create_red_row(row, erroneous_columns)

        update_layers(row_info)

    def create_red_row(self, row, erroneous_columns):
        """Color a row in red

        Parameters
        ----------
        row : integer
            The number of the row to color
        erroneous_columns : list
            The columns where the errors are
        """

        for col in range(self.model.columnCount()):
            current_item = self.model.item(row, col)
            item_color = current_item.background()
            item_font = current_item.font()
            # Find the appropriate color
            # This test is there to avoid turning a red cell into a pink one or
            # applying the red color twice
            if item_color != self.BRUSH_INVALID_CELL:
                if col in erroneous_columns:
                    item_color = self.BRUSH_INVALID_CELL
                    item_font.setBold(True)
                else:
                    item_color = self.BRUSH_INVALID_ROW
                    item_font.setBold(False)
                current_item.setBackground(item_color)
                current_item.setFont(item_font)

    def colorize(self, rows):
        """Color the rows that have errors

        Parameters
        ----------
        erroneous_rows : list
            The list of errors
        """
        for row in rows:
            erroneous_columns = row['erroneous_columns']
            if erroneous_columns:
                self.create_red_row(row['data']['ID_OBSERVATION']-1, erroneous_columns)


    def import_file(self):
        """Import a file: displays a dialog to select the file and load it
        """
        filename = select_csv_file()
        if filename:
            csv_array = load_csv_to_array(filename)
            if csv_array == []:
                QgsMessageLog.logMessage('Unable to load the file: wrong format', 'Radiotrack', level=message_log_levels['Warning'])
                iface.messageBar().pushWarning('Warning Radiotrack', 'Unable to load the file: wrong format.')
                self.currentProjectText.clear()
            else:
                self.layer_suffix = ' ' + os.path.splitext(os.path.basename(filename))[0] + '__radiotrack__'
                self.clear()
                self.currentProjectText.setText(filename)
                self.load_array_in_model(csv_array)
                self.create_table()
                processed_model = self.model.get_all()
                create_layers(processed_model, self.layer_suffix)
                self.colorize(processed_model)
                self.model.itemChanged.connect(self.refresh)
        else:
            QgsMessageLog.logMessage('Error initializing point layer', 'Radiotrack', level=message_log_levels["Critical"])
            iface.messageBar().pushInfo(u'Radiotrack: ', u'No project imported')


    def create_table(self):
        """Configure the table and assign the model to it
        """
        self.tableView.setModel(self.model)
        self.tableView.setColumnHidden(0,True)
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()
        QgsMessageLog.logMessage('Table successfully created', 'Radiotrack', level=message_log_levels["Info"])

    def save_as(self):
        """Display a dialog to ask where to save, and save the current content of the table in the selected file
        """
        filename = select_save_file()
        if filename != '':
            try:
                array = self.model.to_array()
            except:
                QgsMessageLog.logMessage('Unable serialize the table.', 'Radiotrack', level=message_log_levels["Critical"])
                iface.messageBar().pushWarning('Warning Radiotrack', 'Unable serialize the table.')
            else:
                if save_array_to_csv(array, filename):
                    self.currentProjectText.setText(filename)
                    iface.messageBar().pushInfo(u'Radiotrack: ', u'CSV file saved!')


    def load_array_in_model(self, array):
        """Load an array in the model/table

        Parameters
        ----------
        array : list of list of str
            The array containing the data to be displayed. The first line must be the headers of the table
        """
        self.model = TrackingModel(self)
        is_first_row = True
        for row in array:
            if is_first_row:
                self.model.setHorizontalHeaderLabels(row)
                is_first_row = False
            else:
                items = []
                for field in row:
                    item = QtGui.QStandardItem()
                    content = get_field(field)
                    try:
                        content = int(content)
                    except ValueError:
                        try:
                            content = float(content)
                        except ValueError:
                            pass
                    item.setData(content, Qt.EditRole)
                    items.append(item)

                self.model.appendRow(items)

