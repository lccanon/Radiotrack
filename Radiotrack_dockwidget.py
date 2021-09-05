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

from qgis.PyQt.QtGui import QKeySequence, QPalette, QColor
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant, QDateTime, QRect
from qgis.PyQt.QtWidgets import QWidget, QFileDialog, QHeaderView, QStyle, QStyleOptionButton

from .compat import QShortcut

from .compat import QDoubleSpinBox, QDateTimeEdit
from .compat import QDockWidget, QItemEditorFactory, QStyledItemDelegate, message_log_levels, message_bar_levels

from .manageDocumentation import importDoc

from .csv_utils import select_csv_file, load_csv_to_array, save_array_to_csv, select_save_file
from .QgsController import QgsController
from .TrackingModel import TrackingModel


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Radiotrack_dockwidget_base.ui'))


class DateCoordItemDelegate(QStyledItemDelegate):

    COORD_PREC = 6 # precision up to 10 cm
    COORD_MIN = -180 # longitude starts at -180°
    COORD_MAX = 180 # longitude ends at 180°
    COORD_STEP = 0.0001 # 10 meters step

    def __init__(self, model):
        super(DateCoordItemDelegate, self).__init__()
        self.model = model

    def displayText(self, value, locale):
        if isinstance(value, float):
            return locale.toString(value, 'f', self.COORD_PREC)
        elif isinstance(value, QDateTime):
            return value.toString(self.model.dateTimeFormat())
        else:
            return super(DateCoordItemDelegate, self).displayText(value, locale)

class DateCoordItemEditorFactory(QItemEditorFactory):
    def __init__(self, model):
        super(DateCoordItemEditorFactory, self).__init__()
        self.model = model

    def createEditor(self, userType, parent):
        if userType == QVariant.Double:
            doubleSpinBox = QDoubleSpinBox(parent)
            doubleSpinBox.setDecimals(DateCoordItemDelegate.COORD_PREC)
            doubleSpinBox.setRange(DateCoordItemDelegate.COORD_MIN,
                                   DateCoordItemDelegate.COORD_MAX)
            doubleSpinBox.setSingleStep(DateCoordItemDelegate.COORD_STEP)
            return doubleSpinBox
        elif userType == QVariant.DateTime:
            datetimeedit = QDateTimeEdit(parent)
            datetimeedit.setDisplayFormat(self.model.dateTimeFormat())
            return datetimeedit
        else:
            return super(DateCoordItemEditorFactory,
                         self).createEditor(userType, parent)


class CheckBoxHeader(QHeaderView):
    def __init__(self, orientation, parent, dock):
        super(CheckBoxHeader, self).__init__(orientation, parent)
        self.isOn = True
        self.dock = dock

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        super(CheckBoxHeader, self).paintSection(painter, rect, logicalIndex)
        painter.restore()
        if logicalIndex == 0:
            option = QStyleOptionButton()
            option.rect = QRect(3, 3, 14, 14)
            if self.isOn:
                option.state = QStyle.State_On
            else:
                option.state = QStyle.State_Off
            self.style().drawPrimitive(QStyle.PE_IndicatorCheckBox, option, painter)

    def mousePressEvent(self, event):
        pos = event.x()
        logicalIndex = self.logicalIndexAt(pos)
        if logicalIndex == 0:
            tableView = self.parent()
            n = tableView.model().rowCount()
            visible_rows = [i for i in range(n) if not tableView.isRowHidden(i)]
            if self.isOn:
                state = Qt.Unchecked
            else:
                state = Qt.Checked
            tableView.model().itemChanged.disconnect()
            for row in visible_rows:
                tableView.model().setSelected(row, state)
            tableView.model().itemChanged.connect(self.dock.refresh)
            self.dock.filter()
            self.isOn = not self.isOn
        self.update()
        super(CheckBoxHeader, self).mousePressEvent(event)


class RadiotrackDockWidget(QDockWidget, FORM_CLASS):

    """Variables membres"""

    def __init__(self, parent=None):
        """Constructor."""
        super(RadiotrackDockWidget, self).__init__(parent)
        self.setupUi(self)
        #iface.dock = self # for debug only
        """Import the documentation"""
        importDoc(self.documentationText)
        """Model initialization"""
        self.model = TrackingModel(self)
        self.qgs = QgsController()
        self.model.itemChanged.connect(self.refresh)
        self.tableView.setModel(self.model)
        self.tableView.setSortingEnabled(True)
        checkboxHeader = CheckBoxHeader(Qt.Horizontal, self.tableView, self)
        checkboxHeader.setSectionsClickable(True)
        checkboxHeader.setHighlightSections(True)
        checkboxHeader.setMinimumSectionSize(0)
        self.tableView.setHorizontalHeader(checkboxHeader)
        """Navigation in QTableWidget shortcut"""
        QShortcut(QKeySequence("Ctrl+PgDown"), self).activated.connect(self.navigateRightTab)
        QShortcut(QKeySequence("Ctrl+PgUp"), self).activated.connect(self.navigateLeftTab)
        """Import and export csv project actions"""
        self.importButton.clicked.connect(self.importFile)
        self.importButton.setShortcut("Ctrl+Alt+I")
        """Save actions"""
        self.saveAsButton.clicked.connect(self.save_as)
        self.saveAsButton.setShortcut("Ctrl+Alt+X")
        """Empty the table and the model, and forget the CSV file"""
        self.clearButton.clicked.connect(self.clear)
        self.clearButton.setShortcut("Ctrl+Alt+C")
        """Filter actions"""
        self.idFilter.addItem("All")
        self.idFilter.currentTextChanged.connect(self.filter_update)
        self.dateTimeStart.dateTimeChanged.connect(self.filter)
        self.dateTimeEnd.dateTimeChanged.connect(self.filter)
        self.dateTimeFixedInterval.clicked.connect(self.link_datetime_edit)
        self.dateTimeAdjust.clicked.connect(self.adjust_datetime_filter)
        self.position.stateChanged.connect(self.filter)
        self.azimuth.stateChanged.connect(self.filter)
        self.datetime.stateChanged.connect(self.filter)
        self.triangulation.stateChanged.connect(self.filter)
        """Decoration for triangulation"""
        self.triangulation.setAutoFillBackground(True)
        palette = self.triangulation.palette()
        palette.setBrush(QPalette.Button, self.model.BRUSH_TRIANGULATED_ROW)
        self.triangulation.setPalette(palette)
        self.selected.stateChanged.connect(self.filter)
        self.resetFilterButton.clicked.connect(self.reset_filter)
        self.tableView.horizontalHeader().sortIndicatorChanged.connect(self.filter)
        # Put all values to default ones (in particular for the date)
        self.reset_filter()
        """Date format selection"""
        self.dateComboBox.currentTextChanged.connect(self.dateTimeStart.setDisplayFormat)
        self.dateComboBox.currentTextChanged.connect(self.dateTimeEnd.setDisplayFormat)
        self.dateComboBox.currentTextChanged.connect(self.setDateTimeFormat)
        self.dateComboBox.addItem("yyyy-MM-dd hh:mm:ss")
        self.dateComboBox.addItem("d/M/yyyy hh:mm:ss")
        self.dateComboBox.addItem("M/d/yyyy hh:mm:ss")
        self.dateComboBox.addItem("hh:mm:ss d/M/yyyy")
        self.dateComboBox.addItem("hh:mm:ss M/d/yyyy")
        """Set segment length"""
        self.segmentLength.valueChanged.connect(self.qgs.setSegmentLength)
        """Set CRS"""
        self.epsg4326.clicked.connect(self.qgs.setEPSG4326)
        self.projectCrs.clicked.connect(self.qgs.setProjectCRS)
        """Intersection computation"""
        self.intersectionVisible.clicked.connect(self.qgs.toggleIntersectionsVisible)
        self.intersectionUpdate.clicked.connect(self.intersectTriangulation)
        self.demoButton.clicked.connect(self.importDemo)

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
        # Enable auto refresh again
        self.model.itemChanged.connect(self.refresh)

        # Add geometry if required
        header = self.model.headerData(item.column(), Qt.Horizontal)
        if header == 'lon' or header == 'lat' or header == 'azi':
            row_info = self.model.get_row(item.row())
            self.qgs.updateRowLinePoint(row_info)
        elif header == 'id':
            row_info = self.model.get_row(item.row())
            self.qgs.setId([row_info])

        # Re-apply filter and update filter id list
        if header == 'id':
            self.filter_update()
        else:
            self.filter()

        QgsMessageLog.logMessage('Project refreshed', 'Radiotrack',
                                 level = message_log_levels["Info"])

    def navigateRightTab(self):
        tb = self.tabWidget
        currentIndex = (tb.currentIndex() + 1) % tb.count()
        self.tabWidget.setCurrentIndex(currentIndex)

    def navigateLeftTab(self):
        tb = self.tabWidget
        currentIndex = (tb.currentIndex() - 1) % tb.count()
        self.tabWidget.setCurrentIndex(currentIndex)

    def importFile(self, checked, filename = None):
        """Import a file: displays a dialog to select the file and load it

        It is important to keep the checked argument, even if not
        used, for disambiguation with the filename.
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
        # Update canvas and create colors (must be done before
        # initializing the filters)
        layerSuffix = ' ' + os.path.splitext(os.path.basename(filename))[0] + '__radiotrack__'
        self.qgs.setLayerSuffix(layerSuffix)
        triangs = self.model.triangulations()
        self.qgs.createLayers(self.model.get_all(), triangs)
        # Update main and filter tab views
        self.currentProjectText.setText(filename)
        self.update_view()
        self.reset_filter()
        # Initial population of ids with available ones in data
        self.filter_update()

    def update_view(self):
        """Configure the table view and actions

        Requires the colors of the individuals.
        """
        itemDelegate = DateCoordItemDelegate(self.model)
        itemDelegate.setItemEditorFactory(DateCoordItemEditorFactory(self.model))
        for col in range(self.model.columnCount()):
            header = self.model.headerData(col, Qt.Horizontal)
            if header == 'datetime' or header == 'lon' or header == 'lat':
                self.tableView.setItemDelegateForColumn(col, itemDelegate)
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()
        QgsMessageLog.logMessage('Table successfully created', 'Radiotrack',
                                 level = message_log_levels["Info"])

    def save_as(self):
        """Save selected rows

        Display a dialog to ask where to save, and save the current
        content of the table in the selected file.
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

    def clear(self):
        self.qgs.clearLayers()
        self.model.clear()
        self.currentProjectText.clear()
        # Clear filter tab view
        self.clear_filter()
        QgsMessageLog.logMessage('Cleared layers and table', 'Radiotrack', level=message_log_levels["Info"])

    def filter(self):
        #XXX remove check eventually
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
            if (filter_id == "All" or
                self.model.item(row, col_id).text() == filter_id) and \
                (isinstance(date, str) or
                 (date >= self.dateTimeStart.dateTime() and
                  date <= self.dateTimeEnd.dateTime())) and \
                  (not self.position.isChecked() or
                   self.model.validPosition(row)) and \
                   (not self.azimuth.isChecked() or
                    self.model.validAzimuth(row)) and \
                    (not self.datetime.isChecked() or
                     self.model.validDatetime(row)) and \
                     (not self.triangulation.isChecked() or
                      self.model.triangulated(row)) and \
                      (not self.selected.isChecked() or self.model.selected(row)):
                if self.tableView.isRowHidden(row):
                    rows_add.append(self.model.id(row))
                    self.tableView.setRowHidden(row, False)
            else:
                if not self.tableView.isRowHidden(row):
                    rows_del.append(self.model.id(row))
                    self.tableView.setRowHidden(row, True)
        self.qgs.setFilter(rows_add, False)
        self.qgs.setFilter(rows_del, True)
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()

    def update_ids(self):
        #XXX remove check eventually
        if self.model.rowCount() == 0:
            return
        # Remove orphan ids if not selected
        # Find id column
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        col_id = headers.index('id')
        # Get ids in data
        ids = set()
        for row in range(self.model.rowCount()):
            ids.add(self.model.item(row, col_id).text())
        # Add current filtered ids even if absent from data
        curr_index = self.idFilter.currentIndex()
        if curr_index != 0:
            filter_id = self.idFilter.currentText()
            ids.add(filter_id)
            self.idFilter.currentTextChanged.disconnect()
        # Replace all combo boxes
        self.clear_filter()
        ids = sorted(ids)
        self.idFilter.addItems(ids)
        # Set color for each item in the ids combo box
        colors = self.qgs.getIdColors()
        for i in range(1, self.idFilter.count()):
            id = self.idFilter.itemText(i)
            self.idFilter.setItemData(i, colors[id], Qt.BackgroundColorRole)
        palette = self.idFilter.palette()
        if curr_index == 0:
            palette.setColor(QPalette.Button, QColor(Qt.white))
        else:
            palette.setColor(QPalette.Button, colors[filter_id])
            # Put combo index back to initial value
            self.idFilter.setCurrentIndex(ids.index(filter_id) + 1)
            self.idFilter.currentTextChanged.connect(self.filter_update)
        self.idFilter.setPalette(palette)

    def clear_filter(self):
        self.idFilter.setCurrentIndex(0)
        for i in range(1, self.idFilter.count()):
            self.idFilter.removeItem(1)

    # Filter values and update list of ids
    def filter_update(self):
        self.filter()
        self.update_ids()

    def reset_filter(self):
        self.idFilter.setCurrentIndex(0)
        self.dateTimeStart.setDateTime(self.dateTimeStart.minimumDateTime())
        self.dateTimeEnd.setDateTime(QDateTime.currentDateTime())
        self.position.setChecked(False)
        self.azimuth.setChecked(False)
        self.datetime.setChecked(False)
        self.triangulation.setChecked(False)
        self.selected.setChecked(False)

    def link_datetime_edit(self):
        """Link DateTimeEdit"""
        if self.dateTimeFixedInterval.isChecked():
            self.dateTimeStart.setSyncDateTime(self.dateTimeEnd)
            self.dateTimeEnd.setSyncDateTime(self.dateTimeStart)
        else:
            self.dateTimeStart.setSyncDateTime(None)
            self.dateTimeEnd.setSyncDateTime(None)

    def adjust_datetime_filter(self):
        #XXX remove check eventually
        if self.model.rowCount() == 0:
            return
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        col_date = headers.index('datetime')
        smallest_date = None
        biggest_date = None
        for row in range(self.model.rowCount()):
            date = self.model.item(row, col_date).data(Qt.EditRole)
            if isinstance(date, QDateTime) and (smallest_date is None or
                                              smallest_date > date):
                smallest_date = date
            if isinstance(date, QDateTime) and (biggest_date is None or
                                              biggest_date < date):
                biggest_date = date
        if smallest_date is not None:
            self.dateTimeStart.setDateTime(smallest_date)
        if biggest_date is not None:
            self.dateTimeEnd.setDateTime(biggest_date)

    def setDateTimeFormat(self, datetime_format):
        self.model.itemChanged.disconnect()
        self.model.setDateTimeFormat(datetime_format)
        self.model.itemChanged.connect(self.refresh)

    def intersectTriangulation(self):
        """Get triangulated row ids as pairs of indices"""
        triangs = self.model.triangulations()
        self.qgs.updateIntersections(triangs)

    def importDemo(self, checked):
        THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
        my_file = os.path.join(THIS_FOLDER, "./Documentation/example.csv")
        """checked is passed on because of argument ambiguity"""
        self.importFile(checked, filename = my_file)
