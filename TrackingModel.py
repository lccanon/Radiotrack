from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QStandardItemModel

from .csv_utils import types
from .compat import message_log_levels

"""Indicates how many columns were added into the model before the table_headers
from the standard CSV files."""

class TrackingModel(QStandardItemModel):
    def __init__(self, parent):
        self.rows_for_date = {}
        super(TrackingModel, self).__init__(parent)

    def clear(self):
        self.rows_for_date = {}
        super(TrackingModel, self).clear()

    def appendRow(self, items):
        # Extract id and date from the new row
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        id_index = headers.index('id_observation')
        id_sp_index = headers.index('id')
        date_index = headers.index('date')
        row_id = items[id_index].data(Qt.EditRole)
        row_id_sp = items[id_sp_index].data(Qt.EditRole)
        row_date = items[date_index].data(Qt.EditRole)

        # Create the set if it doesn't exist
        if row_id_sp not in self.rows_for_date:
            self.rows_for_date[row_id_sp] = {}
        if row_date not in self.rows_for_date[row_id_sp]:
            self.rows_for_date[row_id_sp][row_date] = set()
        # Register the row into the dates map
        self.rows_for_date[row_id_sp][row_date].add(row_id)
        # Effectively add the row to the model
        super(TrackingModel, self).appendRow(items)

    def update_biangulation(self, item):
        header = self.headerData(item.column(), Qt.Horizontal)
        if header != 'id' and header != 'date':
            return

        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        id_index = headers.index('id_observation')
        id_sp_index = headers.index('id')
        date_index = headers.index('date')
        row = item.row()
        row_id = self.item(row, id_index).data(Qt.EditRole)
        row_id_sp = self.item(row, id_sp_index).data(Qt.EditRole)
        row_date = self.item(row, date_index).data(Qt.EditRole)

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

    def get_row(self, row_index):
        result = {'data': {}, 'erroneous_columns': set(), 'biangulated': False}
        headers = [self.headerData(col, Qt.Horizontal)
                   for col in range(self.columnCount())]
        id_sp_index = headers.index('id')
        row_id_sp = self.item(row_index, id_sp_index).data(Qt.EditRole)
        for col in range(self.columnCount()):
            header = self.headerData(col, Qt.Horizontal)
            result['data'][header] = self.item(row_index, col).data(Qt.EditRole)
            parse_function = types[header]
            try:
                item_text = self.item(row_index, col).text()
                parse_function(item_text)
            except:
                result['erroneous_columns'].add(col)
                QgsMessageLog.logMessage('Error reading column %s at line %d.' % (header, row_index + 1), 'Radiotrack', level=message_log_levels['Warning'])
            else:
                if header == 'date':
                    if row_id_sp in self.rows_for_date and \
                       item_text in self.rows_for_date[row_id_sp] and \
                       len(self.rows_for_date[row_id_sp][item_text]) >= 2:
                        result['biangulated'] = True
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
        for n_row in range(self.rowCount()):
            row_info = self.get_row(n_row)
            #XXX - 1 is a fragile operation
            result_index = row_info['data']['id_observation'] - 1
            result[result_index] = row_info
        return result

    # unused method (replaced by to_array_select)
    def to_array(self):
        """Creates an array of arrays from the content

        Return
        ------
        array : list
            The array containing all the data of the table/model
        """
        headers = [self.headerData(col, Qt.Horizontal) for col in range(self.columnCount())]
        array = [headers[:]]

        for row in range(self.rowCount()):
            line = []
            for column in range(self.columnCount()):
                line.append(self.item(row, column).text())
            array.append(line)

        return array

    def to_array_select(self):
        """Creates an array of arrays from the content

        Return
        ------
        array : list
            The array containing all the data of the table/model
        """
        headers = [self.headerData(col, Qt.Horizontal) for col in range(self.columnCount())]
        array = [headers[1:]]
        select = False
        for row in range(self.rowCount()):
            line = []
            for column in range(self.columnCount()):
                current = self.item(row, column)
                if current.isCheckable():
                    if current.checkState() == Qt.Checked:
                        select = True
                    else:
                        select = False
                else:
                    line.append(self.item(row, column).text())
            if select:
                array.append(line)

        return array
