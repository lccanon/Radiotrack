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
from qgis.PyQt import uic
from qgis.core import QgsMessageLog
from qgis.utils import iface
from qgis.gui import QgsMessageBar
import qgis

from qgis.PyQt.QtGui import QKeySequence
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant, QDateTime
from qgis.PyQt.QtWidgets import QWidget, QFileDialog

from .compat import QShortcut

from .algorithmNewPoint import dst

from .compat import QDoubleSpinBox
from .compat import QDockWidget, QTableView, QItemEditorFactory, QStyledItemDelegate, message_log_levels, message_bar_levels

from .manageDocumentation import importDoc

from .csv_utils import labels, select_csv_file, load_csv_to_array, save_array_to_csv, select_save_file
from .layer_utils import create_layers, clear_layers, add_line_and_point, set_filter, set_segment_length, set_EPSG4326, set_project_CRS
from .TrackingModel import TrackingModel


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Radiotrack_dockwidget_base.ui'))


class DateCoordItemDelegate(QStyledItemDelegate):

    COORD_PREC = 6 # precision up to 10 cm
    COORD_MIN = -180 # longitude starts at -180°
    COORD_MAX = 180 # longitude ends at 180°
    COORD_STEP = 0.0001 # 10 meters step

    def __init__(self, model):
        super(QStyledItemDelegate, self).__init__()
        self.model = model

    def displayText(self, value, locale):
        if isinstance(value, float):
            return locale.toString(value, 'f', self.COORD_PREC)
        elif isinstance(value, QDateTime):
            return value.toString(self.model.dateTimeFormat())
        else:
            return super(DateCoordItemDelegate, self).displayText(value, locale)

class DateCoordItemEditorFactory(QItemEditorFactory):
    def __init__(self):
        super(QItemEditorFactory, self).__init__()

    def createEditor(self, userType, parent):
        if userType == QVariant.Double:
            doubleSpinBox = QDoubleSpinBox(parent)
            doubleSpinBox.setDecimals(DateCoordItemDelegate.COORD_PREC)
            doubleSpinBox.setRange(DateCoordItemDelegate.COORD_MIN,
                                   DateCoordItemDelegate.COORD_MAX)
            doubleSpinBox.setSingleStep(DateCoordItemDelegate.COORD_STEP)
            return doubleSpinBox
        else:
            return super(DateCoordItemEditorFactory,
                         self).createEditor(userType, parent)


class RadiotrackDockWidget(QDockWidget, FORM_CLASS):

    """Variables membre"""

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
        self.idFilter.addItem("All")
        self.resetFilterButton.clicked.connect(self.reset_filter)
        self.idFilter.currentTextChanged.connect(self.filter)
        self.dateTimeStart.dateTimeChanged.connect(self.filter)
        self.dateTimeEnd.dateTimeChanged.connect(self.filter)
        self.position.stateChanged.connect(self.filter)
        self.azimuth.stateChanged.connect(self.filter)
        self.datetime.stateChanged.connect(self.filter)
        self.biangulation.stateChanged.connect(self.filter)
        self.selected.stateChanged.connect(self.filter)
        self.tableView.horizontalHeader().sortIndicatorChanged.connect(self.filter)
        """Link DateTimeEdit"""
        self.dateTimeStart.setSyncDateTime(self.dateTimeEnd)
        """Date format selection"""
        self.dateComboBox.addItem("yyyy-MM-dd hh:mm:ss")
        self.dateComboBox.addItem("d/M/yyyy hh:mm:ss")
        self.dateComboBox.addItem("M/d/yyyy hh:mm:ss")
        self.dateComboBox.addItem("hh:mm:ss d/M/yyyy")
        self.dateComboBox.addItem("hh:mm:ss M/d/yyyy")
        self.dateComboBox.currentTextChanged.connect(self.setDateTimeFormat)
        self.dateComboBox.currentTextChanged.connect(self.dateTimeStart.setDisplayFormat)
        self.dateComboBox.currentTextChanged.connect(self.dateTimeEnd.setDisplayFormat)
        # Date format may change biggest and largest known datetimes
        self.dateComboBox.currentTextChanged.connect(self.reset_filter)
        self.dateComboBox.setCurrentIndex(0)
        """Set segment length"""
        self.segmentLength.valueChanged.connect(set_segment_length)
        """Set CRS"""
        self.epsg4326.clicked.connect(set_EPSG4326)
        self.projectCrs.clicked.connect(set_project_CRS)
        self.demoButton.clicked.connect(self.import_demo)

    def navigateRightTab(self):
        currentIndex=(self.tabWidget.currentIndex()+1)%self.tabWidget.count()
        self.tabWidget.setCurrentIndex(currentIndex)

    def navigateLeftTab(self):
        currentIndex=(self.tabWidget.currentIndex()-1)%self.tabWidget.count()
        self.tabWidget.setCurrentIndex(currentIndex)

    def import_demo(self, checked):
        THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
        my_file = os.path.join(THIS_FOLDER, "./Documentation/example.csv")
        self.import_file(checked, filename = my_file)

    def refresh(self, item):
        """Handle table edits

        Parameters
        ----------
        item
            The changed item of the table
        """
        if item.isCheckable():
            self.filter()
            return

        # Disable auto refresh because we may change cells' colors
        self.model.itemChanged.disconnect()

        # Reparse data
        self.model.update(item)
        # Add geometry if required
        row_info = self.model.get_row(item.row())
        add_line_and_point([row_info])

        # Enable auto refresh again
        self.model.itemChanged.connect(self.refresh)
        QgsMessageLog.logMessage('Project refreshed', 'Radiotrack', level=message_log_levels["Info"])

        # Update filter id list
        # XXX abstract this code in a function (until filter) and
        # merge with similar code in reset_filter
        # XXX reinit only if id has been touched
        ids = set()
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        if headers == []:
            return
        col_id = headers.index('id')
        for row in range(self.model.rowCount()):
            ids.add(self.model.item(row, col_id).text())

        filter_index = 0
        filter_id = self.idFilter.currentText()
        self.idFilter.currentTextChanged.disconnect()
        self.idFilter.setCurrentIndex(0)
        for i in range(1, self.idFilter.count()):
            self.idFilter.removeItem(1)
        index = 0
        for id in sorted(ids):
            index += 1
            if filter_id == id:
                filter_index = index
            self.idFilter.addItem(id)
        self.idFilter.setCurrentIndex(filter_index)
        self.idFilter.currentTextChanged.connect(self.filter)

        # XXX update the filter on the date (keep a boolean stating
        # whether the datetime filter was set, and if not reinit it
        # with the new value if datetime has been touched)

        # Re-apply filter
        self.filter()

    def setDateTimeFormat(self, datetime_format):
        self.model.itemChanged.disconnect()
        self.model.setDateTimeFormat(datetime_format)
        self.model.itemChanged.connect(self.refresh)

    def clear(self):
        clear_layers()
        self.model.clear()
        self.currentProjectText.clear()
        # Clear filter tab view
        self.clear_filter()
        QgsMessageLog.logMessage('Cleared layers and table', 'Radiotrack', level=message_log_levels["Info"])

    def import_file(self, checked, filename = None):
        """Import a file: displays a dialog to select the file and load it
        """
        if filename is None:
            filename = select_csv_file()
            if filename is None:
                return
        # Clear only when new file is selected
        self.clear()
        # Load model
        csv_array = load_csv_to_array(filename)
        if csv_array is None:
            return
        self.model.itemChanged.disconnect()
        self.model.load_array_in_model(csv_array)
        self.model.itemChanged.connect(self.refresh)
        # Update main and filter tab views
        self.currentProjectText.setText(filename)
        self.update_view()
        self.reset_filter()
        # Update canvas
        self.layer_suffix = ' ' + os.path.splitext(os.path.basename(filename))[0] + '__radiotrack__'
        create_layers(self.model.get_all(), self.layer_suffix)

    def update_view(self):
        """Configure the table view and actions
        """
        itemDelegate = DateCoordItemDelegate(self.model)
        itemDelegate.setItemEditorFactory(DateCoordItemEditorFactory())
        for col in range(self.model.columnCount()):
            header = self.model.headerData(col, Qt.Horizontal)
            if header == labels['X'] or header == labels['Y'] or \
               header == 'datetime':
                self.tableView.setItemDelegateForColumn(col, itemDelegate)
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()
        QgsMessageLog.logMessage('Table successfully created', 'Radiotrack', level=message_log_levels["Info"])

    def save_as(self):
        """Display a dialog to ask where to save, and save the current content of the table in the selected file
        """
        filename = select_save_file()
        if filename != '':
            try:
                array = self.model.to_array_select()
            except:
                QgsMessageLog.logMessage('Unable to serialize the table.', 'Radiotrack', level=message_log_levels["Critical"])
                iface.messageBar().pushWarning('Warning Radiotrack', 'Unable to serialize the table.')
            else:
                if save_array_to_csv(array, filename):
                    self.currentProjectText.setText(filename)
                    iface.messageBar().pushInfo(u'Radiotrack: ', u'CSV file saved.')

    def filter(self):
        if self.model.rowCount() == 0:
            return

        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        col_id = headers.index('id')
        col_date = headers.index('datetime')
        rows_add = []
        rows_del = []
        for row in range(self.model.rowCount()):
            date = self.model.item(row, col_date).data(Qt.EditRole)
            filter_id = self.idFilter.currentText()
            if (filter_id == "All" or self.model.item(row, col_id).text() == filter_id) and \
               (isinstance(date, str) or
                (date >= self.dateTimeStart.dateTime() and
                 date <= self.dateTimeEnd.dateTime())) and \
                 (not self.position.isChecked() or
                  self.model.validPosition(row)) and \
                  (not self.azimuth.isChecked() or
                   self.model.validAzimuth(row)) and \
                   (not self.datetime.isChecked() or
                    self.model.validDatetime(row)) and \
                    (not self.biangulation.isChecked() or
                     self.model.biangulated(row)) and \
                     (not self.selected.isChecked() or self.model.selected(row)):
                if self.tableView.isRowHidden(row):
                    rows_add.append(self.model.id(row))
                    self.tableView.setRowHidden(row, False)
            else:
                if not self.tableView.isRowHidden(row):
                    rows_del.append(self.model.id(row))
                    self.tableView.setRowHidden(row, True)
        set_filter(rows_add, False)
        set_filter(rows_del, True)
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()

    def reset_filter(self):
        ids = set()
        smallest_date = None
        biggest_date = None
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        if headers == []:
            return
        col_id = headers.index('id')
        col_date = headers.index('datetime')
        for row in range(self.model.rowCount()):
            ids.add(self.model.item(row, col_id).text())
            date = self.model.item(row, col_date).data(Qt.EditRole)

            if not isinstance(date, str) and (smallest_date is None or
                                              smallest_date > date):
                smallest_date = date
            if not isinstance(date, str) and (biggest_date is None or
                                              biggest_date < date):
                biggest_date = date

        self.idFilter.setCurrentIndex(0)
        self.clear_filter()
        for filter_id in sorted(ids):
            self.idFilter.addItem(filter_id)

        if smallest_date is not None:
            self.dateTimeStart.setDateTime(smallest_date)
        if biggest_date is not None:
            self.dateTimeEnd.setDateTime(biggest_date)
        self.position.setChecked(False)
        self.azimuth.setChecked(False)
        self.datetime.setChecked(False)
        self.biangulation.setChecked(False)
        self.selected.setChecked(False)

    def clear_filter(self):
        self.idFilter.currentTextChanged.disconnect()
        self.idFilter.setCurrentIndex(0)
        self.idFilter.currentTextChanged.connect(self.filter)
        for i in range(1, self.idFilter.count()):
            self.idFilter.removeItem(1)
