import os, csv, io
from qgis.core import QgsMessageLog
from qgis.utils import iface

from qgis.PyQt.QtWidgets import QFileDialog

from .compat import message_log_levels, message_bar_levels, get_filename_qdialog, write_csv

labels = {"Y": "lat", "X": "lon", "AZIMUT": "azi"}

types = {
    "select": str,
    "id_observation": int,
    "id": int,
    "name": str,
    "date": str,
    "lat": float,
    "lon": float,
    "azi": float,
    "filter": float,
    "power": float,
    "comment": str
}

table_headers = ["id_observation", "id", "name", "date", "lat", "lon", "azi", "filter", "power", "comment"]

def select_csv_file():
    """Displays a dialog allowing the user to select a file

    Returns
    -------
    file_path : str
        The path of the selected csv file. Empty if an error occurred, or if nothing was selected
    """
    dialog = QFileDialog()
    dialog.setNameFilter("Text files (*.csv)")
    if dialog.exec_():
        filenames = dialog.selectedFiles()
        QgsMessageLog.logMessage('File successfully selected', 'Radiotrack', level=message_log_levels["Info"])
        return filenames[0]
    else:
        QgsMessageLog.logMessage('No file selected', 'Radiotrack', level=message_log_levels["Info"])
        return None

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
        for index, header in enumerate(table_headers):
            if header != headers[index]:
                errors.append('Field ' + headers[index] + ' should be ' + header)
    except:
        errors.append('Missing header field(s)')

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
                    return None
            csv_array.append(row)
    # In case of empty file
    if is_first_line:
        QgsMessageLog.logMessage('Unable to load the file: empty file', 'Radiotrack', level=message_log_levels['Critical'])
        iface.messageBar().pushCritical('Warning Radiotrack', 'Unable to load the file: empty file.')
        return None
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
