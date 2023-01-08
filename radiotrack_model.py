from qgis.core import QgsMessageLog
from qgis.core import Qgis as QGis
from qgis.PyQt.QtCore import Qt, QDateTime
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor, QFont

from .csv_utils import types

class TrackingModel(QStandardItemModel):

    """Brushes used for the table's cells' background"""
    BRUSH_VALID_ROW = QBrush(QColor(Qt.white))
    BRUSH_TRIANGULATED_ROW = QBrush(QColor(Qt.green).lighter(100))
    BRUSH_INVALID_ROW = QBrush(QColor(Qt.red).lighter(165))

    """Indicates specific column information/metadata"""
    selectedCol_POS = 0
    SORT_ROLE = Qt.UserRole + 1
    ID_ROLE = Qt.UserRole + 2
    colors = {}

    def __init__(self, parent):
        super(TrackingModel, self).__init__(parent)
        self.triangulationDetector = TriangulationDetector(self)
        self.setSortRole(self.SORT_ROLE)
        self.setDateTimeFormat('yyyy-MM-dd hh:mm:ss')

    def clear(self):
        super(TrackingModel, self).clear()
        self.triangulationDetector.clear()

    #XXX rename id into fid (Feature id)
    def id(self, row):
        return self.item(row, 0).data(self.ID_ROLE)

    def setId(self, row, rowId):
        self.item(row, 0).setData(rowId, self.ID_ROLE)

    def setDateTimeFormat(self, datetimeFormat):
        self.datetimeFormat = datetimeFormat
        #XXX remove check eventually
        if self.rowCount() == 0:
            return
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        dateIndex = headers.index('datetime')
        updateColor = False
        for row in range(self.rowCount()):
            if self.item(row, dateIndex).parse():
                updateColor = True
                self.triangulationDetector.updateTriangulation(row)
        if updateColor:
            self.updateColor(range(self.rowCount()))

    def dateTimeFormat(self):
        return self.datetimeFormat

    def valid(self, row):
        for col in range(self.columnCount()):
            if not self.item(row, col).valid():
                return False
        return True

    def validPosition(self, row):
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        latIndex = headers.index('lat')
        lonIndex = headers.index('lon')
        return self.item(row, latIndex).valid() and \
            self.item(row, lonIndex).valid()

    def validAzimuth(self, row):
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        aziIndex = headers.index('azi')
        return self.item(row, aziIndex).valid()

    def validDatetime(self, row):
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        dateIndex = headers.index('datetime')
        return self.item(row, dateIndex).valid()

    def triangulated(self, row):
        return self.triangulationDetector.triangulated(row)

    def triangulations(self):
        return self.triangulationDetector.triangulations()

    def selected(self, row):
        return self.item(row, self.selectedCol_POS).checkState() == Qt.Checked

    def setSelected(self, row, state):
        self.item(row, self.selectedCol_POS).setCheckState(state)

    def setIdColor(self,colors):       
        for row in range(self.rowCount()):
            currentItem = self.getId(row)
            currentItem.setBackground(colors[currentItem.text()])

    def setBrushRow(self, row, brush):
        for col in range(self.columnCount()):
            currentItem = self.item(row, col)
            # Find the appropriate color
            # This test is there to avoid turning a invalid cell into a valid cell
            # id set in setIdColor
            if (col != 1): 
                if currentItem.valid():
                    currentItem.setBackground(brush)

    def updateColor(self, rows):
        """Update the color of multiple rows"""
        for row in rows:
            if not self.valid(row):
                self.setBrushRow(row, self.BRUSH_INVALID_ROW)
            elif self.triangulated(row):
                self.setBrushRow(row, self.BRUSH_TRIANGULATED_ROW)
            else:
                self.setBrushRow(row, self.BRUSH_VALID_ROW)

    def update(self, item):
        # Test whether the parsing was successful (when it was not
        # already parsed)
        success = item.parse()
        # Update triangulation data (must be done before any call to
        # triangulated) and table color
        header = self.headerData(item.column(), Qt.Horizontal)
        if header == 'id' or (item.valid() and header == 'datetime'):
            self.triangulationDetector.updateTriangulation(item.row())
            # Update the color of current row and possibly other impacted rows
            self.updateColor(range(self.rowCount()))
        # Update validity color of local row in case of successful parsing
        elif success:
            self.updateColor([item.row()])

    def getIdCol(self):
        return 1

    def getDateCol(self):
        return 2

    def getLatCol(self):
        return 3

    def getLonCol(self):
        return 4

    def getAzimuthCol(self):
        return 5

    def getId(self,row):
        return self.item(row, self.getIdCol())

    def getDate(self,row):
        return self.item(row, self.getDateCol())

    def getLat(self,row):
        return self.item(row, self.getLatCol())

    def getLon(self,row):
        return self.item(row, self.getLonCol())

    def getAzimuth(self,row):
        return self.item(row, self.getAzimuthCol())

    def loadArrayInModel(self, array):
        """Load an array in the model/table

        Parameters
        ----------
        array : list of list of str
            The array containing the data to be displayed. The first line must be the headers of the table
        """
        isFirstRow = True
        for row in array:
            if isFirstRow:
                row.insert(self.selectedCol_POS, '')
                self.setHorizontalHeaderLabels(row)
                isFirstRow = False
            else:
                # XXX Necessarily insert selectedCol as first value
                items = []
                checkbox = TrackingItem('')
                checkbox.setCheckable(True)
                checkbox.setCheckState(Qt.Checked)
                items.append(checkbox)
                for field in row:
                    content = field
                    item = TrackingItem(content)
                    items.append(item)
                self.appendRow(items)
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                self.item(row, col).parse()
            # should start at 1 because layer ids start at 1
            # XXX let Qgis returns these ids
            self.setId(row, row + 1)
            self.triangulationDetector.updateTriangulation(row)
        self.updateColor(range(self.rowCount()))

    def getRow(self, row):
        result = {}
        for col in range(self.columnCount()):
            header = self.headerData(col, Qt.Horizontal)
            result[header] = self.item(row, col).data(Qt.EditRole)
        result['id_observation'] = self.id(row)
        return result

    def getAll(self):
        """Returns all the detailed rows, in id_observation order

        Return
        ------
        result : list
            The array of rows using the getRow format
        """
        nbRows = self.rowCount()
        result = [None] * nbRows
        for row in range(self.rowCount()):
            rowInfo = self.getRow(row)
            #XXX - 1 is a fragile operation
            resultIndex = self.id(row) - 1
            result[resultIndex] = rowInfo
        return result

    def toArraySelect(self):
        """Creates an array of arrays from the content

        Return
        ------
        array : list
            The array containing all the data of the table/model
        """
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        array = [headers[1:]]
        dateIndex = headers.index('datetime')
        for row in range(self.rowCount()):
            if self.selected(row):
                line = []
                for col in range(1, self.columnCount()):
                    item = self.item(row, col)
                    if col == dateIndex and item.valid():
                        data = item.data(Qt.EditRole)
                        line.append(str(data.toString(self.dateTimeFormat())))
                    else:
                        line.append(item.text())
                array.append(line)
        return array

class TrackingItem(QStandardItem):
    BRUSH_VALID_CELL = QBrush(QColor(Qt.white))
    BRUSH_INVALID_CELL = QBrush(QColor(Qt.red).lighter(125))

    def __init__(self, content):
        super(TrackingItem, self).__init__()
        self.setData(content, Qt.EditRole)
        self.setData(content, TrackingModel.SORT_ROLE)

    def setValid(self):
        self.setBackground(self.BRUSH_VALID_CELL)
        itemFont = self.font()
        itemFont.setBold(False)
        self.setFont(itemFont)

    def setInvalid(self):
        self.setBackground(self.BRUSH_INVALID_CELL)
        itemFont = self.font()
        itemFont.setBold(True)
        self.setFont(itemFont)

    def valid(self):
        return self.background() != self.BRUSH_INVALID_CELL

    def parse(self):
        """Return true when an invalid cell becomes valid"""
        if self.isCheckable():
            return False
        # Change the current type if not the correct one
        header = self.model().headerData(self.column(), Qt.Horizontal)
        parseFunction = types.get(header)
        if parseFunction == None:
            parseFunction = str
        data = self.data(Qt.EditRole)
        if isinstance(data, parseFunction):
            return False
        try:
            if parseFunction != QDateTime:
                content = parseFunction(data)
            else:
                content = QDateTime.fromString(data,
                                               self.model().dateTimeFormat())
                # Raise an exception when parsing a datetime fails
                if content == QDateTime():
                    raise
            self.setData(content, Qt.EditRole)
            self.setData(content, TrackingModel.SORT_ROLE)
            self.setValid()
            return True
        except:
            QgsMessageLog.logMessage('Error reading column %s at line %d.' %
                                     (header, self.row()), 'Radiotrack',
                                     level = QGis.Warning)
            if parseFunction == float:
                self.setData(float('inf'), TrackingModel.SORT_ROLE)
            self.setInvalid()
            return False

class TriangulationDetector:

    def __init__(self, model):
        self.rowsForDate = {}
        self.model = model

    def clear(self):
        self.rowsForDate = {}

    def updateTriangulation(self, row):
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        idSpIndex = headers.index('id')
        dateIndex = headers.index('datetime')
        rowId = self.model.id(row)
        rowIdSp = self.model.item(row, idSpIndex).text()
        rowDate = self.model.item(row, dateIndex).text()

        # Remove previous values
        for emitterId in self.rowsForDate:
            for _, rowIds in self.rowsForDate[emitterId].items():
                rowIds.discard(rowId)

        # Create the set if it doesn't exist
        if rowIdSp not in self.rowsForDate:
            self.rowsForDate[rowIdSp] = {}
        if rowDate not in self.rowsForDate[rowIdSp]:
            self.rowsForDate[rowIdSp][rowDate] = set()
        # Register the row into the dates map
        self.rowsForDate[rowIdSp][rowDate].add(rowId)

    def triangulated(self, row):
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        idSpIndex = headers.index('id')
        dateIndex = headers.index('datetime')
        rowIdSp = self.model.item(row, idSpIndex).text()
        rowDate = self.model.item(row, dateIndex).text()
        return len(self.rowsForDate[rowIdSp][rowDate]) >= 2

    def triangulations(self):
        triangs = {}
        for rowIdSp, idDict in self.rowsForDate.items():
            for _, idDateSet in idDict.items():
                for id1 in idDateSet:
                    for id2 in idDateSet:
                        if id1 < id2:
                            triangs[id1] = id2
        return triangs
