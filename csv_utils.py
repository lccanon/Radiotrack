import os, csv, io
from qgis.core import QgsMessageLog
from qgis.utils import iface

from qgis.PyQt.QtCore import QDateTime
from qgis.PyQt.QtWidgets import QFileDialog

labels = {'ID': 'id', 'X': 'lon', 'Y': 'lat', 'AZIMUT': 'azi'}

types = {
    'datetime': QDateTime,
    'lat': float,
    'lon': float,
    'azi': float,
}

tableHeaders = ['id', 'datetime', 'lat', 'lon', 'azi']

def writeCsv(csvFileName, array):
    try:
        with io.open(csvFileName, 'w', newline = '') as outpulFile:
            writer = csv.writer(outpulFile, delimiter = ',', quotechar = '"', quoting = csv.QUOTE_MINIMAL)

            writer.writerows(array)

        return True
    except:
        return False

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

def validateHeaders(headers):
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
        for index, header in enumerate(tableHeaders):
            if header != headers[index]:
                errors.append('Field ' + headers[index] + ' should be ' + header)
    except:
        errors.append('Missing header field(s)')

    if len(errors) > 0:
        iface.messageBar().pushCritical('Error Radiotrack', 'Header structure error. Check the log.')
        for err in errors:
            QgsMessageLog.logMessage(err, 'Radiotrack', level = QGis.Critical)

    return len(errors) == 0

def loadCsvToArray(filename):
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
                if not validateHeaders(row):
                    return None
            csvArray.append(row)
    # In case of empty file
    if isFirstLine:
        QgsMessageLog.logMessage('Unable to load the file: empty file', 'Radiotrack', level = QGis.Critical)
        iface.messageBar().pushCritical('Warning Radiotrack', 'Unable to load the file: empty file.')
        return None
    return csvArray

def saveArrayToCsv(array, csvFileName):
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
    if not writeCsv(csvFileName, array):
        if os.path.exists(csvFileName):
            os.remove(csvFileName)

            QgsMessageLog.logMessage('Unable to write the csv file', 'Radiotrack', level = QGis.Critical)
            iface.messageBar().pushCritical('Error Radiotrack', 'Unable to write the csv file.')
        return False
    else:
        return True

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
