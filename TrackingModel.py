from qgis.core import QgsMessageLog
from qgis.PyQt.QtGui import QStandardItemModel

from .csv_utils import table_info, table_headers, columns_count
from .compat import message_log_levels

class TrackingModel(QStandardItemModel):

    # shows GPS points up to 6 decimals (but breaks itemDelegate)
    #def data(self, index, role):
    #    result = super().data(index, role)
    #    if result != None and isinstance(result, float):
    #        return "{0:.6f}".format(result)
    #    return result

    def get_row(self, row_index):
        result = {'data': {}, 'erroneous_columns': set(), 'can_draw_point': True, 'can_draw_line': True}
        for column_name, column_infos in table_info.items():
            column_index = column_infos['index']
            parse_function = column_infos['type']
            try:
                result['data'][column_name] = parse_function(self.item(row_index, column_index).text())
            except:
                result['erroneous_columns'].add(column_index)
                QgsMessageLog.logMessage('Error reading column %s at line %d.' % (column_infos['header'], row_index + 1), 'Radiotrack', level=message_log_levels['Warning'])
                if column_infos['used_for_points']:
                    result['can_draw_point'] = False
                if column_infos['used_for_lines']:
                    result['can_draw_line'] = False

        return result

    def get_all(self):
        """Returns all the detailed rows, in ID_OBSERVATION order

        Return
        ------
        result : list
            The array of rows using the get_row format
        """
        nb_rows = self.rowCount()
        result = [None] * nb_rows
        for n_row in range(self.rowCount()):
            row_info = self.get_row(n_row)
            result_index = row_info['data']['ID_OBSERVATION'] - 1
            result[result_index] = row_info
        return result

    def to_array(self):
        """Creates an array of arrays from the content

        Return
        ------
        array : list
            The array containing all the data of the table/model
        """
        array = [table_headers[:]]

        for row in range(self.rowCount()):
            line = []
            for column in range(columns_count):
                line.append(self.item(row, column).text())
            array.append(line)

        return array
