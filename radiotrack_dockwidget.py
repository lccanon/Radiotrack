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

import os, csv, sys, io

from qgis.PyQt import uic, QtCore
from qgis.core import QgsMessageLog
from qgis.utils import iface
from qgis.gui import QgsMessageBar
import qgis
from qgis.core import Qgis as QGis

from qgis.PyQt.QtGui import QKeySequence, QPalette, QColor
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant, QDateTime, QRect
from qgis.PyQt.QtWidgets import QWidget, QFileDialog, QHeaderView, QStyle, QStyleOptionButton

from qgis.PyQt.QtWidgets import QDockWidget, QShortcut, QItemEditorFactory, QStyledItemDelegate, QDoubleSpinBox, QDateTimeEdit

from .radiotrack_qgs_controller import QgsController
from .radiotrack_model import TrackingModel

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'radiotrack_dockwidget_base.ui'))


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
            visibleRows = [i for i in range(n) if not tableView.isRowHidden(i)]
            if self.isOn:
                state = Qt.Unchecked
            else:
                state = Qt.Checked
            tableView.model().itemChanged.disconnect()
            for row in visibleRows:
                tableView.model().setSelected(row, state)
            tableView.model().itemChanged.connect(self.dock.refresh)
            self.dock.filter()
            self.isOn = not self.isOn
        self.update()
        super(CheckBoxHeader, self).mousePressEvent(event)


class RadiotrackDockWidget(QDockWidget, FORM_CLASS):
    """Variables membres"""
    tableHeaders = ['id', 'datetime', 'lat', 'lon', 'azi']

    def __init__(self, parent = None):
        """Constructor."""
        super(RadiotrackDockWidget, self).__init__(parent)
        self.setupUi(self)
        #iface.dock = self # for debug only
        """Import the documentation"""
        self.importDoc(self.documentationText)
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
        QShortcut(QKeySequence('Ctrl+PgDown'), self).activated.connect(self.navigateRightTab)
        QShortcut(QKeySequence('Ctrl+PgUp'), self).activated.connect(self.navigateLeftTab)
        """Import and export csv project actions"""
        self.importButton.clicked.connect(self.importFile)
        self.importButton.setShortcut('Ctrl+Alt+I')
        """Save actions"""
        self.saveAsButton.clicked.connect(self.saveAs)
        self.saveAsButton.setShortcut('Ctrl+Alt+X')
        """Empty the table and the model, and forget the CSV file"""
        self.clearButton.clicked.connect(self.clear)
        self.clearButton.setShortcut('Ctrl+Alt+C')
        """Filter actions"""
        self.idFilter.addItem('All')
        self.idFilter.currentTextChanged.connect(self.filterUpdate)
        self.dateTimeStart.dateTimeChanged.connect(self.filter)
        self.dateTimeEnd.dateTimeChanged.connect(self.filter)
        self.dateTimeFixedInterval.clicked.connect(self.linkDatetimeEdit)
        self.dateTimeAdjust.clicked.connect(self.adjustDatetimeFilter)
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
        self.resetFilterButton.clicked.connect(self.resetFilter)
        self.tableView.horizontalHeader().sortIndicatorChanged.connect(self.filter)
        # Put all values to default ones (in particular for the date)
        self.resetFilter()
        """Date format selection"""
        self.dateComboBox.currentTextChanged.connect(self.dateTimeStart.setDisplayFormat)
        self.dateComboBox.currentTextChanged.connect(self.dateTimeEnd.setDisplayFormat)
        self.dateComboBox.currentTextChanged.connect(self.setDateTimeFormat)
        self.dateComboBox.addItem('yyyy-MM-dd hh:mm:ss')
        self.dateComboBox.addItem('d/M/yyyy hh:mm:ss')
        self.dateComboBox.addItem('M/d/yyyy hh:mm:ss')
        self.dateComboBox.addItem('hh:mm:ss d/M/yyyy')
        self.dateComboBox.addItem('hh:mm:ss M/d/yyyy')
        """Set segment length"""
        self.segmentLength.valueChanged.connect(self.updateSegmentLength)
        """Set CRS"""
        self.epsg4326.clicked.connect(self.qgs.setEPSG4326)
        self.projectCrs.clicked.connect(self.qgs.setProjectCRS)
        """Intersection computation"""
        self.intersectionVisible.clicked.connect(self.qgs.toggleIntersectionsVisible)
        self.intersectionUpdate.clicked.connect(self.intersectTriangulation)
        self.demoButton.clicked.connect(self.importDemo)

        self.zoom.stateChanged.connect(self.zoomClick)

    def zoomClick(self):
        self.qgs.updateZoom(self.zoom.isChecked())

    def updateSegmentLength(self, length):
        self.qgs.setSegmentLength(length)
        rows = self.model.getAll()
        for row in rows:
            self.qgs.updateRowLinePoint(row)
        self.qgs.updateZoom(True)

        self.intersectTriangulation()

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
            rowInfo = self.model.getRow(item.row())
            self.qgs.updateRowLinePoint(rowInfo)
        elif header == 'id':
            rowInfo = self.model.getRow(item.row())
            self.qgs.setId([rowInfo])

        # Re-apply filter and update filter id list
        if header == 'id':
            self.filterUpdate()
        else:
            self.filter()

        # refresh color ID
        colors = self.qgs.getIdColors()
        self.model.setIdColor(colors)
        # Triangulation update
        if header == 'lon' or header == 'lat' or header == 'azi' or header == 'id' or header == 'datetime':
            self.intersectTriangulation()

        QgsMessageLog.logMessage('Project refreshed', 'Radiotrack',
                                 level = QGis.Info)

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
            filename = self.selectCsvFile()
            if filename is None:
                return
        # Clear only when new file is selected
        self.clear()
        # Load model
        csvArray = self.loadCsvToArray(filename)
        if csvArray is None:
            return
        self.model.itemChanged.disconnect()
        self.model.loadArrayInModel(csvArray)
        self.model.itemChanged.connect(self.refresh)
        # Update canvas and create colors (must be done before
        # initializing the filters)
        layerSuffix = ' ' + os.path.splitext(os.path.basename(filename))[0] + '__radiotrack__'
        self.qgs.setLayerSuffix(layerSuffix)
        triangs = self.model.triangulations()
        self.qgs.createLayers(self.model.getAll(), triangs)
        # Update main and filter tab views
        self.currentProjectText.setText(filename)
        self.updateView()
        self.resetFilter()
        # Initial population of ids with available ones in data
        self.filterUpdate()
        # Color the id in the tableview
        colors = self.qgs.getIdColors()
        self.model.setIdColor(colors)

    def updateView(self):
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
                                 level = QGis.Info)

    def saveAs(self):
        """Save selected rows

        Display a dialog to ask where to save, and save the current
        content of the table in the selected file.
        """
        filename = self.selectSaveFile()
        if filename != '':
            try:
                array = self.model.toArraySelect()
            except:
                QgsMessageLog.logMessage('Unable to serialize the table.', 'Radiotrack', level=QGis.Critical)
                iface.messageBar().pushWarning('Warning Radiotrack', 'Unable to serialize the table.')
            else:
                if self.saveArrayToCsv(array, filename):
                    self.currentProjectText.setText(filename)
                    iface.messageBar().pushInfo(u'Radiotrack: ', u'CSV file saved.')

    def clear(self):
        self.qgs.clearLayers()
        self.model.clear()
        self.currentProjectText.clear()
        # Clear filter tab view
        self.clearFilter()
        QgsMessageLog.logMessage('Cleared layers and table', 'Radiotrack', level = QGis.Info)

    def filter(self):
        #XXX remove check eventually
        if self.model.rowCount() == 0:
            return
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        colId = headers.index('id')
        colDate = headers.index('datetime')
        rowsAdd = []
        rowsDel = []

        for row in range(self.model.rowCount()):
            date = self.model.item(row, colDate).data(Qt.EditRole)
            filterId = self.idFilter.currentText()
            if (filterId == 'All' or
                self.model.item(row, colId).text() == filterId) and \
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
                    rowsAdd.append(self.model.id(row))
                    self.tableView.setRowHidden(row, False)

            else:
                if not self.tableView.isRowHidden(row):
                    rowsDel.append(self.model.id(row))
                    self.tableView.setRowHidden(row, True)

        self.qgs.setFilter(rowsAdd, False)
        self.qgs.setFilter(rowsDel, True)
        self.qgs.updateZoom(self.zoom.isChecked())
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()

    def updateIds(self):
        #XXX remove check eventually
        if self.model.rowCount() == 0:
            return
        # Remove orphan ids if not selected
        # Find id column
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        colId = headers.index('id')
        # Get ids in data
        ids = set()
        for row in range(self.model.rowCount()):
            ids.add(self.model.item(row, colId).text())
        # Add current filtered ids even if absent from data
        currIndex = self.idFilter.currentIndex()
        if currIndex != 0:
            filterId = self.idFilter.currentText()
            ids.add(filterId)
            self.idFilter.currentTextChanged.disconnect()
        # Replace all combo boxes
        self.clearFilter()
        ids = sorted(ids)
        self.idFilter.addItems(ids)
        # Set color for each item in the ids combo box
        colors = self.qgs.getIdColors()
        for i in range(1, self.idFilter.count()):
            id = self.idFilter.itemText(i)
            self.idFilter.setItemData(i, colors[id], Qt.BackgroundColorRole)
        palette = self.idFilter.palette()
        if currIndex == 0:
            palette.setColor(QPalette.Button, QColor(Qt.white))
        else:
            palette.setColor(QPalette.Button, colors[filterId])
            # Put combo index back to initial value
            self.idFilter.setCurrentIndex(ids.index(filterId) + 1)
            self.idFilter.currentTextChanged.connect(self.filterUpdate)
        self.idFilter.setPalette(palette)

    def clearFilter(self):
        self.idFilter.setCurrentIndex(0)
        for i in range(1, self.idFilter.count()):
            self.idFilter.removeItem(1)

    # Filter values and update list of ids
    def filterUpdate(self):
        self.filter()
        self.updateIds()

    def resetFilter(self):
        self.idFilter.setCurrentIndex(0)
        self.dateTimeStart.setDateTime(self.dateTimeStart.minimumDateTime())
        self.dateTimeEnd.setDateTime(QDateTime.currentDateTime())
        self.position.setChecked(False)
        self.azimuth.setChecked(False)
        self.datetime.setChecked(False)
        self.triangulation.setChecked(False)
        self.selected.setChecked(False)

    def linkDatetimeEdit(self):
        """Link DateTimeEdit"""
        if self.dateTimeFixedInterval.isChecked():
            self.dateTimeStart.setSyncDateTime(self.dateTimeEnd)
            self.dateTimeEnd.setSyncDateTime(self.dateTimeStart)
        else:
            self.dateTimeStart.setSyncDateTime(None)
            self.dateTimeEnd.setSyncDateTime(None)

    def adjustDatetimeFilter(self):
        #XXX remove check eventually
        if self.model.rowCount() == 0:
            return
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        colDate = headers.index('datetime')
        smallestDate = None
        biggestDate = None
        for row in range(self.model.rowCount()):
            date = self.model.item(row, colDate).data(Qt.EditRole)
            if isinstance(date, QDateTime) and (smallestDate is None or
                                              smallestDate > date):
                smallestDate = date
            if isinstance(date, QDateTime) and (biggestDate is None or
                                              biggestDate < date):
                biggestDate = date
        if smallestDate is not None:
            self.dateTimeStart.setDateTime(smallestDate)
        if biggestDate is not None:
            self.dateTimeEnd.setDateTime(biggestDate)

    def setDateTimeFormat(self, datetimeFormat):
        self.model.itemChanged.disconnect()
        self.model.setDateTimeFormat(datetimeFormat)
        self.model.itemChanged.connect(self.refresh)

    def intersectTriangulation(self):
        """Get triangulated row ids as pairs of indices"""
        triangs = self.model.triangulations()
        self.qgs.updateIntersections(triangs)
        self.qgs.updateIntersectionsLines(triangs)

    def importDemo(self, checked):
        THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
        myFile = os.path.join(THIS_FOLDER, './Documentation/example.csv')
        """checked is passed on because of argument ambiguity"""
        self.importFile(checked, filename = myFile)

    def writeCsv(csvFileName, array):
        try:
            with io.open(csvFileName, 'w', newline = '') as outputFile:
                writer = csv.writer(outputFile, delimiter = ',', quotechar = '"', quoting = csv.QUOTE_MINIMAL)

                writer.writerows(array)

            return True
        except:
            return False

    def saveArrayToCsv(self, array, csvFileName):
        """Save an array into a csv file.

        The array must have the header (name of the columns) in the first row.
        Each row of the array will be written on a line of the csv file.
        Each string will be separated by ','
        If necessary, a string will be escaped by '"'

        Note: each string in the array must be a string and not a byte array 'string' and not b'string'

        Parameters
        ----------
        array : list of list of str
            The array to save in a csv file
        csvFileName : str
            The path of the csv file. The file will be created if it doesn't exist. If it exists, it will be replaced

        Return
        ------
        no_error : bool
            True if the writing succeed
        """
        if not self.writeCsv(csvFileName, array):
            if os.path.exists(csvFileName):
                os.remove(csvFileName)

                QgsMessageLog.logMessage('Unable to write the csv file', 'Radiotrack', level = QGis.Critical)
                iface.messageBar().pushCritical('Error Radiotrack', 'Unable to write the csv file.')
            return False
        else:
            return True

    def loadCsvToArray(self,filename):
        """Load the content of the given csv file into an array

        The resulting array will contain each line of the csv file
        A line of the csv file is an array of strings

        Parameters
        ----------
        filename : str
            Path of the csv file to read

        Return
        ------
        array : list of list of str
            The array with all the csv file inside
        """
        csvArray = []
        with open(filename, 'rt') as fileInput:
            isFirstLine = True
            for row in csv.reader(fileInput):
                if isFirstLine:
                    isFirstLine = False
                    # What we get here are the headers
                    # We can check their validity first
                    if not self.validateHeaders(row):
                        return None
                csvArray.append(row)
        # In case of empty file
        if isFirstLine:
            QgsMessageLog.logMessage('Unable to load the file: empty file', 'Radiotrack', level = QGis.Critical)
            iface.messageBar().pushCritical('Warning Radiotrack', 'Unable to load the file: empty file.')
            return None
        return csvArray

    def validateHeaders(self,headers):
        """Validate the headers. Returns True if the headers are valid

        Parameters
        ----------
        headers : list of str
            First line of the csv file. Each column name must be in this array

        Returns
        -------
        no_error : bool
            True if the headers are validated, False if there is an error
        """

        errors = []
        try:
            for index, header in enumerate(self.tableHeaders):
                if header != headers[index]:
                    errors.append('Field ' + headers[index] + ' should be ' + header)
        except:
            errors.append('Missing header field(s)')

        if len(errors) > 0:
            iface.messageBar().pushCritical('Error Radiotrack', 'Header structure error. Check the log.')
            for err in errors:
                QgsMessageLog.logMessage(err, 'Radiotrack', level = QGis.Critical)

        return len(errors) == 0

    def selectSaveFile():
        """Display a selection dialog to choose the save file

        Return
        ------
        file_path : str
            The path of the selected file
        """
        try:
            filename = QFileDialog.getSaveFileName(None, 'Select output file ', '', 'CSV files (*.csv)')[0]

            if filename != '':
                if os.path.splitext(filename)[-1].lower() != '.csv':
                    filename = filename + '.csv'

            return filename
        except:
            iface.messageBar().pushCritical('Error Radiotrack', 'Unable to select a file.')
            return ''

    def selectCsvFile():
        """Displays a dialog allowing the user to select a file

        Returns
        -------
        file_path : str
            The path of the selected csv file. Empty if an error occurred, or if nothing was selected
        """
        dialog = QFileDialog()
        dialog.setNameFilter('Text files (*.csv)')
        if dialog.exec_():
            filenames = dialog.selectedFiles()
            QgsMessageLog.logMessage('File successfully selected', 'Radiotrack', level = QGis.Info)
            return filenames[0]
        else:
            QgsMessageLog.logMessage('No file selected', 'Radiotrack', level = QGis.Info)
            return None

    def importDoc(self, qTextDoc):
        qTextDoc.setOpenLinks(True)
        qTextDoc.setOpenExternalLinks(True)
        docFile = './Documentation/README.html'
        qTextDoc.clear()
        THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
        myFile = os.path.join(THIS_FOLDER, docFile)
        qTextDoc.setSource(QtCore.QUrl.fromLocalFile(myFile))
