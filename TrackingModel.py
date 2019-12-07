from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QStandardItemModel

from .csv_utils import types
from .compat import message_log_levels

class TrackingModel(QStandardItemModel):

    def get_row(self, row_index):
        result = {'data': {}, 'erroneous_columns': set()}
        for col in range(self.columnCount()):
            header = self.headerData(col, Qt.Horizontal)
            result['data'][header] = self.item(row_index, col).data(Qt.EditRole)
            parse_function = types[header]
            try:
                parse_function(self.item(row_index, col).text())
            except:
                result['erroneous_columns'].add(col)
                QgsMessageLog.logMessage('Error reading column %s at line %d.' % (header, row_index + 1), 'Radiotrack', level=message_log_levels['Warning'])
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
            result_index = row_info['data']['id_observation'] - 1
            result[result_index] = row_info
        return result

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
