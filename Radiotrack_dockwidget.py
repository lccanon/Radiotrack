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
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant, QDateTime
from qgis.PyQt.QtWidgets import QWidget, QFileDialog

from .compat import QShortcut

from .algorithmNewPoint import dst

from .compat import get_field, QDoubleSpinBox
from .compat import QDockWidget, QTableView, QItemEditorFactory, QStyledItemDelegate, message_log_levels, message_bar_levels

from .manageDocumentation import importDoc

from .csv_utils import labels, types, select_csv_file, load_csv_to_array, save_array_to_csv, select_save_file
from .layer_utils import create_layers, clear_layers, add_line_and_point, set_filter, set_segment_length
from .TrackingModel import TrackingModel


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Radiotrack_dockwidget_base.ui'))

SELECTED_COL_ID = "select"

COORD_PREC = 6 # precision up to 10 cm
COORD_MIN = -180 # longitude starts at -180°
COORD_MAX = 180 # longitude ends at 180°
COORD_STEP = 0.0001 # 10 meters step


class CoordItemDelegate(QStyledItemDelegate):
    def __init__(self):
        super(QStyledItemDelegate, self).__init__()

    def displayText(self, value, locale):
        if isinstance(value, float):
            return locale.toString(value, 'f', COORD_PREC)
        else:
            return super(CoordItemDelegate, self).displayText(value, locale)

class CoordItemEditorFactory(QItemEditorFactory):
    def __init__(self):
        super(QItemEditorFactory, self).__init__()

    def createEditor(self, userType, parent):
        if userType == QVariant.Double:
            doubleSpinBox = QDoubleSpinBox(parent)
            doubleSpinBox.setDecimals(COORD_PREC)
            doubleSpinBox.setRange(COORD_MIN, COORD_MAX)
            doubleSpinBox.setSingleStep(COORD_STEP)
            return doubleSpinBox
        else:
            return super(CoordItemEditorFactory, self).createEditor(userType, parent)


class RadiotrackDockWidget(QDockWidget, FORM_CLASS):

    """Variables membre"""

    """Brushes used for the table's cells' background"""
    BRUSH_VALID_ROW = QBrush(QColor(Qt.white))
    BRUSH_BIANGULATED = QBrush(QColor(Qt.green).lighter(100))
    BRUSH_INVALID_CELL = QBrush(QColor(Qt.red).lighter(125))
    BRUSH_INVALID_ROW = QBrush(QColor(Qt.red).lighter(165))

    closingPlugin = pyqtSignal()

    layer_suffix = ''

    def __init__(self, parent=None):
        """Constructor."""
        super(RadiotrackDockWidget, self).__init__(parent)
        self.setupUi(self)
        """Import the documentation"""
        importDoc(self.documentationText)
        """Model initialization"""
        self.model = TrackingModel(self)
        self.model.itemChanged.connect(self.refresh)
        self.tableView.setModel(self.model)
        """Navigation in QTableWidget shortcut"""
        QShortcut(QKeySequence("Ctrl+PgDown"), self).activated.connect(self.navigateRightTab)
        QShortcut(QKeySequence("Ctrl+PgUp"), self).activated.connect(self.navigateLeftTab)
        """Import and export csv project actions"""
        self.importButton.clicked.connect(self.import_file)
        self.importButton.setShortcut("Ctrl+Alt+I")
        """Save actions"""
        self.saveAsButton.clicked.connect(self.save_as)
        self.saveAsButton.setShortcut("Ctrl+Alt+X")
        """Empty the table and the model, and forget the CSV file"""
        self.clearButton.clicked.connect(self.clear)
        self.clearButton.setShortcut("Ctrl+Alt+C")
        """Filter actions"""
        self.nameFilter.addItem("All")
        self.idFilter.addItem("All")
        self.resetFilterButton.clicked.connect(self.unfilter)
        self.nameFilter.currentTextChanged.connect(self.filter)
        self.idFilter.currentTextChanged.connect(self.filter)
        self.dateTimeStart.dateTimeChanged.connect(self.filter)
        self.dateTimeEnd.dateTimeChanged.connect(self.filter)
        """Link DateTimeEdit"""
        self.dateTimeStart.setSyncDateTime(self.dateTimeEnd)
        """Date format selection"""
        self.dateComboBox.addItem("yyyy-MM-dd hh:mm:ss")
        self.dateComboBox.addItem("dd/MM/yyyy hh:mm:ss")
        self.dateComboBox.addItem("MM/dd/yyyy hh:mm:ss")
        self.dateComboBox.addItem("hh:mm:ss MM/dd/yyyy")
        self.dateComboBox.addItem("hh:mm:ss dd/MM/yyyy")
        self.dateComboBox.currentTextChanged.connect(self.setDateFormat)
        self.dateComboBox.currentTextChanged.connect(self.dateTimeStart.setDisplayFormat)
        self.dateComboBox.currentTextChanged.connect(self.dateTimeEnd.setDisplayFormat)
        self.dateComboBox.setCurrentIndex(1) # required to init self.dateFormat
        """Set segment length"""
        self.segmentLength.valueChanged.connect(set_segment_length)

    def navigateRightTab(self):
        currentIndex=(self.tabWidget.currentIndex()+1)%self.tabWidget.count()
        self.tabWidget.setCurrentIndex(currentIndex)

    def navigateLeftTab(self):
        currentIndex=(self.tabWidget.currentIndex()-1)%self.tabWidget.count()
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
        if item.isCheckable():
            return

        # Disable auto refresh because we may change cells' colors
        self.model.itemChanged.disconnect()

        # Change the current type if not the correct one
        header = self.model.headerData(item.column(), Qt.Horizontal)
        parse_function = types[header]
        data = item.data(Qt.EditRole)
        if not isinstance(data, parse_function):
            try:
                content = parse_function(data)
                item.setData(content, Qt.EditRole)
            except:
                pass

        # Update biangulation color
        if header == 'id' or header == 'date':
            self.model.update_biangulation(item)
            self.update_row(item.row())
            processed_model = self.model.get_all()
            self.color_table(processed_model)

        # Enable auto refresh again
        self.model.itemChanged.connect(self.refresh)
        QgsMessageLog.logMessage('Project refreshed', 'Radiotrack', level=message_log_levels["Info"])

    def clear(self):
        clear_layers()
        self.model.clear()
        self.currentProjectText.clear()
        self.idFilter.currentTextChanged.disconnect()
        self.idFilter.setCurrentIndex(0)
        self.idFilter.currentTextChanged.connect(self.filter)
        for i in range(1, self.idFilter.count()):
            self.idFilter.removeItem(1)
        self.nameFilter.currentTextChanged.disconnect()
        self.nameFilter.setCurrentIndex(0)
        self.nameFilter.currentTextChanged.connect(self.filter)
        for i in range(1, self.nameFilter.count()):
            self.nameFilter.removeItem(1)
        QgsMessageLog.logMessage('Cleared layers and table', 'Radiotrack', level=message_log_levels["Info"])

    def update_row(self, row):
        """Reads the data from the changed row to update the colors in the
        table and the features in the map layers
        """
        # Restore the "valid" style for the row
        #XXX redundant code
        for col in range(self.model.columnCount()):
            current_item = self.model.item(row, col)
            current_item.setBackground(self.BRUSH_VALID_ROW)
            if not current_item.isCheckable():
                current_font = current_item.font()
                current_font.setBold(False)
                current_item.setFont(current_font)

        # Read the line's fields
        row_info = self.model.get_row(row)

        #XXX -1 is a fragile operation
        row_index = row_info['data']['id_observation']-1
        erroneous_columns = row_info['erroneous_columns']
        if erroneous_columns:
            self.create_red_row(row, erroneous_columns)
        elif row_info['biangulated']:
            self.color_biangulated_row(row_index)

        add_line_and_point([row_info])

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

    def color_biangulated_row(self, row):
        for col in range(self.model.columnCount()):
            current_item = self.model.item(row, col)
            item_font = current_item.font()
            item_font.setBold(False)
            current_item.setBackground(self.BRUSH_BIANGULATED)
            current_item.setFont(item_font)

    def color_table(self, rows):
        """Color the rows that have errors

        Parameters
        ----------
        erroneous_rows : list
            The list of errors
        """
        for row in rows:
            # Restore the "valid" style for the row
            #XXX -1 is a fragile operation
            #XXX redundant code
            row_index = row['data']['id_observation']-1
            for col in range(self.model.columnCount()):
                current_item = self.model.item(row_index, col)
                current_item.setBackground(self.BRUSH_VALID_ROW)
                if not current_item.isCheckable():
                    current_font = current_item.font()
                    current_font.setBold(False)
                    current_item.setFont(current_font)

            erroneous_columns = row['erroneous_columns']
            if erroneous_columns:
                self.create_red_row(row_index, erroneous_columns)
            elif row['biangulated']:
                self.color_biangulated_row(row_index)

    def import_file(self):
        """Import a file: displays a dialog to select the file and load it
        """
        filename = select_csv_file()
        if filename is None:
            return
        csv_array = load_csv_to_array(filename)
        if csv_array is None:
            return

        self.clear()
        self.layer_suffix = ' ' + os.path.splitext(os.path.basename(filename))[0] + '__radiotrack__'
        self.currentProjectText.setText(filename)
        self.model.itemChanged.disconnect()
        self.load_array_in_model(csv_array)
        processed_model = self.model.get_all()
        self.color_table(processed_model)
        self.model.itemChanged.connect(self.refresh)
        create_layers(processed_model, self.layer_suffix)
        self.adjust_table()

        ids = set()
        names = set()
        smallest_date = None
        biggest_date = None
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        col_id = headers.index('id')
        col_name = headers.index('name')
        col_date = headers.index('date')
        for row in range(self.model.rowCount()):
            ids.add(self.model.item(row, col_id).text())
            names.add(self.model.item(row, col_name).text())
            str_date = self.model.item(row, col_date).text()
            date = QDateTime.fromString(str_date, self.dateFormat)

            if (smallest_date is None or smallest_date > date) and \
               date != QDateTime():
                smallest_date = date
            if biggest_date is None or biggest_date < date:
                biggest_date = date

        for id in sorted(ids):
            self.idFilter.addItem(id)
        for name in sorted(names):
            self.nameFilter.addItem(name)
        if smallest_date is not None:
            self.dateTimeStart.setDateTime(smallest_date)
        if biggest_date is not None:
            self.dateTimeEnd.setDateTime(biggest_date)

    def adjust_table(self):
        """Configure the table and assign the model to it
        """
        self.tableView.setModel(self.model)
        self.tableView.setColumnHidden(1, True)
        self.setItemDelegate()
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()
        QgsMessageLog.logMessage('Table successfully created', 'Radiotrack', level=message_log_levels["Info"])


    def setItemDelegate(self):
        """Table actions"""
        itemDelegate = CoordItemDelegate()
        itemDelegate.setItemEditorFactory(CoordItemEditorFactory())
        for col in range(self.model.columnCount()):
            header = self.model.headerData(col, Qt.Horizontal)
            if header == labels['X'] or header == labels['Y']:
                self.tableView.setItemDelegateForColumn(col, itemDelegate)


    def save_as(self):
        """Display a dialog to ask where to save, and save the current content of the table in the selected file
        """
        filename = select_save_file()
        if filename != '':
            try:
                array = self.model.to_array_select()
            except:
                QgsMessageLog.logMessage('Unable serialize the table.', 'Radiotrack', level=message_log_levels["Critical"])
                iface.messageBar().pushWarning('Warning Radiotrack', 'Unable serialize the table.')
            else:
                if save_array_to_csv(array, filename):
                    self.currentProjectText.setText(filename)
                    iface.messageBar().pushInfo(u'Radiotrack: ', u'CSV file saved.')

    def convert_field(self, field):
        content = get_field(field)
        try:
            content = int(content)
        except ValueError:
            try:
                content = float(content)
            except ValueError:
                pass
        return content

    def load_array_in_model(self, array):
        """Load an array in the model/table

        Parameters
        ----------
        array : list of list of str
            The array containing the data to be displayed. The first line must be the headers of the table
        """
        is_first_row = True
        for row in array:
            if is_first_row:
                row.insert(0, SELECTED_COL_ID)
                self.model.setHorizontalHeaderLabels(row)
                is_first_row = False
            else:
                items = []
                checkbox = QtGui.QStandardItem()
                checkbox.setCheckable(True)
                checkbox.setCheckState(Qt.Checked)
                items.append(checkbox)
                for field in row:
                    item = QtGui.QStandardItem()
                    content = self.convert_field(field)
                    item.setData(content, Qt.EditRole)
                    items.append(item)
                self.model.appendRow(items)

    def filter(self):
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        col_id_obs = headers.index('id_observation')
        col_id = headers.index('id')
        col_name = headers.index('name')
        col_date = headers.index('date')
        rows_add = []
        rows_del = []
        for row in range(self.model.rowCount()):
            str_date = self.model.item(row, col_date).text()
            date = QDateTime.fromString(str_date, self.dateFormat)
            id = self.idFilter.currentText()
            name = self.nameFilter.currentText()
            if (id == "All" or self.model.item(row, col_id).text() == id) and \
               (name == "All" or self.model.item(row, col_name).text() == name) and \
               (date == QDateTime() or
                (date >= self.dateTimeStart.dateTime() and
                 date <= self.dateTimeEnd.dateTime())):
                if self.tableView.isRowHidden(row):
                    rows_add.append(self.model.item(row, col_id_obs)
                                    .data(Qt.EditRole))
                    self.tableView.setRowHidden(row, False)
            else:
                if not self.tableView.isRowHidden(row):
                    rows_del.append(self.model.item(row, col_id_obs)
                                    .data(Qt.EditRole))
                    self.tableView.setRowHidden(row, True)
        set_filter(rows_add, False)
        set_filter(rows_del, True)

    def unfilter(self):
        self.idFilter.setCurrentIndex(0)
        self.nameFilter.setCurrentIndex(0)
        # XXX redundant code
        smallest_date = None
        biggest_date = None
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        col_date = headers.index('date')
        for row in range(self.model.rowCount()):
            str_date = self.model.item(row, col_date).text()
            date = QDateTime.fromString(str_date, self.dateFormat)

            if (smallest_date is None or smallest_date > date) and \
               date != QDateTime():
                smallest_date = date
            if biggest_date is None or biggest_date < date:
                biggest_date = date

        if smallest_date is not None:
            self.dateTimeStart.setDateTime(smallest_date)
        if biggest_date is not None:
            self.dateTimeEnd.setDateTime(biggest_date)

    # unused and broken method
    def hide_all(self):
        if self.model:
            for row in range(self.model.rowCount()):
                for col in range(self.model.columnCount()):
                    self.tableView.setRowHidden(row, True);
                    remove_line_and_point(self.model.get_row(row))

    def setDateFormat(self, dateFormat):
        self.dateFormat = dateFormat
