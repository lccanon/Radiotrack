import os, csv, io
from qgis.core import QgsMessageLog
from qgis.utils import iface

from qgis.PyQt.QtWidgets import QFileDialog

from .compat import message_log_levels, message_bar_levels, get_filename_qdialog, write_csv


table_info = {
    "ID_OBSERVATION": {"header": "id_observation", "type": int, "index": 0, "used_for_points": False, "used_for_lines": False},
    "ID_INDIVIDU": {"header": "id", "type": int, "index": 1, "used_for_points": False, "used_for_lines": False},
    "NOM_INDIVIDU": {"header": "nom", "type": str, "index": 2, "used_for_points": False, "used_for_lines": False},
    "DATE": {"header": "date", "type": str, "index": 3, "used_for_points": False, "used_for_lines": False},
    "Y": {"header": "lat", "type": float, "index": 4, "used_for_points": True, "used_for_lines": True},
    "X": {"header": "lon", "type": float, "index": 5, "used_for_points": True, "used_for_lines": True},
    "AZIMUT": {"header": "azimut", "type": float, "index": 6, "used_for_points": False, "used_for_lines": True},
    "NIVEAU_FILTRE": {"header": "filtre", "type": float, "index": 7, "used_for_points": False, "used_for_lines": True},
    "PUISSANCE_SIGNAL": {"header": "puissance", "type": float, "index": 8, "used_for_points": False, "used_for_lines": True},
    "COMMENTAIRE": {"header": "commentaire", "type": str, "index": 9, "used_for_points": False, "used_for_lines": False}
}

columns_count = len(table_info)

table_headers = [None] * columns_count
for column_name, column_infos in table_info.items():
    index = column_infos["index"]
    table_headers[index] = column_infos["header"]

def select_csv_file():
    """Displays a dialog allowing the user to select a file

    Returns
    -------
    file_path : str
        The path of the selected csv file. Empty if an error occurred, or if nothing was selected
    """
    try:
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setNameFilter("Text files (*.csv)")
        if dialog.exec_():
            filenames = dialog.selectedFiles()
            QgsMessageLog.logMessage('Project successfully imported', 'Radiotrack', level=message_log_levels["Info"])
            return filenames[0]
    except:
        QgsMessageLog.logMessage('Error importing file', 'Radiotrack', level=message_log_levels["Critical"])
        iface.messageBar().pushInfo(u'Radiotrack: ', u'Error importing file')
        return ''

def validate_headers(headers):
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
        for index, header in enumerate(headers):
            if header != table_headers[index]:
                errors.append(table_headers[index] + ' fatal error')
    except:
        errors.append('Fatal error validating header')
        QgsMessageLog.logMessage('Fatal error validating header', 'Radiotrack', level=message_log_levels["Critical"])

    if len(errors) > 0:
        iface.messageBar().pushCritical('Error Radiotrack', 'Header structure error. Check the log.')

        for err in errors:
            QgsMessageLog.logMessage(err, 'Radiotrack', level=message_log_levels["Critical"])

    return len(errors) == 0

def load_csv_to_array(filename):
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
    csv_array = []
    with open(filename, "rt") as fileInput:
        is_first_line = True
        for row in csv.reader(fileInput):
            if is_first_line:
                is_first_line = False
                # What we get here are the headers
                # We can check their validity first
                if not validate_headers(row):
                    return []

            csv_array.append(row)
    return csv_array

def save_array_to_csv(array, csv_file_name):
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
    csv_file_name : str
        The path of the csv file. The file will be created if it doesn't exist. If it exists, it will be replaced

    Return
    ------
    no_error : bool
        True if the writing succeed
    """
    if not write_csv(csv_file_name, array):
        if os.path.exists(csv_file_name):
            os.remove(csv_file_name)

            QgsMessageLog.logMessage('Unable to write the csv file', 'Radiotrack', level=message_log_levels["Critical"])
            iface.messageBar().pushCritical('Error Radiotrack', 'Unable to write the csv file.')
        return False
    else:
        return True

def select_save_file():
    """Display a selection dialog to choose the save file

    Return
    ------
    file_path : str
        The path of the selected file
    """
    try:
        filename = get_filename_qdialog(QFileDialog.getSaveFileName(None, "Select output file ", "", 'CSV files (*.csv)'))

        if filename != '':
            if os.path.splitext(filename)[-1].lower() != '.csv':
                filename = filename + '.csv'

        return filename
    except:
        iface.messageBar().pushCritical('Error Radiotrack', 'Unable to select a file.')
        return ''
