from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import Qt, QDateTime
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor, QFont

from .csv_utils import types
from .compat import message_log_levels, get_field

SELECTED_COL_POS = 0
SELECTED_COL_ID = "select"

"""Indicates how many columns were added into the model before the table_headers
from the standard CSV files."""

class TrackingModel(QStandardItemModel):

    """Brushes used for the table's cells' background"""
    BRUSH_VALID_ROW = QBrush(QColor(Qt.white))
    BRUSH_BIANGULATED_ROW = QBrush(QColor(Qt.green).lighter(100))
    BRUSH_INVALID_ROW = QBrush(QColor(Qt.red).lighter(165))

    SORT_ROLE = Qt.UserRole + 1
    ID_ROLE = Qt.UserRole + 2

    def __init__(self, parent):
        super(TrackingModel, self).__init__(parent)
        self.biangulation_detector = BiangulationDetector(self)
        self.setSortRole(self.SORT_ROLE)
        self.setDateTimeFormat("yyyy-MM-dd hh:mm:ss")

    def clear(self):
        super(TrackingModel, self).clear()
        self.biangulation_detector.clear()

    def id(self, row):
        return self.item(row, 0).data(self.ID_ROLE)

    def setId(self, row, id):
        self.item(row, 0).setData(id, self.ID_ROLE)

    def setDateTimeFormat(self, datetime_format):
        self.datetime_format = datetime_format
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        if headers != []:
            date_index = headers.index('datetime')
            update_color = False
            for row in range(self.rowCount()):
                if self.item(row, date_index).parse():
                    update_color = True
                    self.biangulation_detector.update_biangulation(row)
            if update_color:
                self.update_color()

    def dateTimeFormat(self):
        return self.datetime_format

    def valid(self, row):
        for col in range(self.columnCount()):
            if not self.item(row, col).valid():
                return False
        return True

    def validPosition(self, row):
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        lat_index = headers.index('lat')
        lon_index = headers.index('lon')
        return self.item(row, lat_index).valid() and \
            self.item(row, lon_index).valid()

    def validAzimuth(self, row):
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        azi_index = headers.index('azi')
        return self.item(row, azi_index).valid()

    def validDatetime(self, row):
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        date_index = headers.index('datetime')
        return self.item(row, date_index).valid()

    def biangulated(self, row):
        return self.biangulation_detector.biangulated(row)

    def selected(self, row):
        return self.item(row, SELECTED_COL_POS).checkState() == Qt.Checked

    def set_brush_row(self, row, brush):
        for col in range(self.columnCount()):
            current_item = self.item(row, col)
            # Find the appropriate color
            # This test is there to avoid turning a invalid cell into a
            # valid cell
            if current_item.valid():
                current_item.setBackground(brush)

    def update_color(self):
        """Update the color of current row and possibly other impacted rows"""
        for row in range(self.rowCount()):
            if not self.valid(row):
                self.set_brush_row(row, self.BRUSH_INVALID_ROW)
            elif self.biangulated(row):
                self.set_brush_row(row, self.BRUSH_BIANGULATED_ROW)
            else:
                self.set_brush_row(row, self.BRUSH_VALID_ROW)

    def update(self, item):
        # Update validity in case of a successful parsing (which was
        # not already parsed)
        if item.parse():
            if not self.valid(item.row()):
                self.set_brush_row(item.row(), self.BRUSH_INVALID_ROW)
            elif self.biangulated(item.row()):
                self.set_brush_row(item.row(), self.BRUSH_BIANGULATED_ROW)
            else:
                self.set_brush_row(item.row(), self.BRUSH_VALID_ROW)
        # Update biangulation and table color
        header = self.headerData(item.column(), Qt.Horizontal)
        if item.valid() and (header == 'id' or header == 'datetime'):
            self.biangulation_detector.update_biangulation(item.row())
            self.update_color()

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
                row.insert(SELECTED_COL_POS, SELECTED_COL_ID)
                self.setHorizontalHeaderLabels(row)
                is_first_row = False
            else:
                items = []
                checkbox = TrackingItem("")
                checkbox.setCheckable(True)
                checkbox.setCheckState(Qt.Checked)
                items.append(checkbox)
                for field in row:
                    content = get_field(field)
                    item = TrackingItem(content)
                    items.append(item)
                self.appendRow(items)
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                self.item(row, col).parse()
            # should start at 1 because layer ids start at 1
            # XXX let Qgis returns these ids
            self.setId(row, row + 1)
            self.biangulation_detector.update_biangulation(row)
        self.update_color()

    def get_row(self, row):
        result = {}
        for col in range(self.columnCount()):
            header = self.headerData(col, Qt.Horizontal)
            result[header] = self.item(row, col).data(Qt.EditRole)
        result['id_observation'] = self.id(row)
        return result

    def get_all(self):
        """Returns all the detailed rows, in id_observation order

        Return
        ------
        result : list
            The array of rows using the get_row format
        """
        nb_rows = self.rowCount()
        result = [None] * nb_rows
        for row in range(self.rowCount()):
            row_info = self.get_row(row)
            #XXX - 1 is a fragile operation
            result_index = self.id(row) - 1
            result[result_index] = row_info
        return result

    def to_array_select(self):
        """Creates an array of arrays from the content

        Return
        ------
        array : list
            The array containing all the data of the table/model
        """
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        array = [headers[1:]]
        for row in range(self.rowCount()):
            if self.selected(row):
                line = []
                for col in range(1, self.columnCount()):
                    line.append(self.item(row, col).text())
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
        item_font = self.font()
        item_font.setBold(False)
        self.setFont(item_font)

    def setInvalid(self):
        self.setBackground(self.BRUSH_INVALID_CELL)
        item_font = self.font()
        item_font.setBold(True)
        self.setFont(item_font)

    def valid(self):
        return self.background() != self.BRUSH_INVALID_CELL

    def parse(self):
        """Return true when an invalid cell becomes valid"""
        if self.isCheckable():
            return False
        # Change the current type if not the correct one
        header = self.model().headerData(self.column(), Qt.Horizontal)
        parse_function = types[header]
        data = self.data(Qt.EditRole)
        if isinstance(data, parse_function):
            return False
        try:
            if parse_function != QDateTime:
                content = parse_function(data)
            else:
                content = QDateTime.fromString(data,
                                               self.model().dateTimeFormat())
                if content == QDateTime():
                    raise
            self.setData(content, Qt.EditRole)
            self.setData(content, TrackingModel.SORT_ROLE)
            self.setValid()
            return True
        except:
            QgsMessageLog.logMessage('Error reading column %s at line %d.' %
                                     (header, self.row()), 'Radiotrack',
                                     level=message_log_levels['Warning'])
            if self.valid():
                if parse_function == float:
                    self.setData(float('inf'), TrackingModel.SORT_ROLE)
                self.setInvalid()
            return False

class BiangulationDetector:

    def __init__(self, model):
        self.rows_for_date = {}
        self.model = model

    def clear(self):
        self.rows_for_date = {}

    def update_biangulation(self, row):
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        id_sp_index = headers.index('id')
        date_index = headers.index('datetime')
        row_id = self.model.id(row)
        row_id_sp = self.model.item(row, id_sp_index).data(Qt.EditRole)
        row_date = self.model.item(row, date_index).data(Qt.EditRole)

        # Remove previous values
        for id in self.rows_for_date:
            for _, row_ids in self.rows_for_date[id].items():
                row_ids.discard(row_id)

        # Create the set if it doesn't exist
        if row_id_sp not in self.rows_for_date:
            self.rows_for_date[row_id_sp] = {}
        if row_date not in self.rows_for_date[row_id_sp]:
            self.rows_for_date[row_id_sp][row_date] = set()
        # Register the row into the dates map
        self.rows_for_date[row_id_sp][row_date].add(row_id)

    def biangulated(self, row):
        headers = [self.model.headerData(col, Qt.Horizontal)
                   for col in range(self.model.columnCount())]
        id_sp_index = headers.index('id')
        date_index = headers.index('datetime')
        row_id_sp = self.model.item(row, id_sp_index).data(Qt.EditRole)
        row_date = self.model.item(row, date_index).data(Qt.EditRole)
        return len(self.rows_for_date[row_id_sp][row_date]) >= 2
