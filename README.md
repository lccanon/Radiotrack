# Radiotrack (v0.4)

Welcome to the Radiotrack's documentation. See also the QGIS
[plugin page](http://plugins.qgis.org/plugins/Radiotrack/).

## Feature Summary

- Import and export CSV files
- Create map layers showing the measures
- Indicate errors in the data
- Automatic map updates when changing the data
- Alerts given with QGIS' message bar
- Detailed information is logged into QGIS' standard window

## Purpose

This plugin was developed to help viewing and correcting manual
telemetric data. The first users were measuring signals from a bat
with a radioemitter at night. With the direction and the strength of
the signal, they could guess where the bat is.

The data is stored in CSV files and consists of latitude-longitude
coordinates, an azimuth and the strength of the signal. When filling
those files, the users can do mistakes, thus making the data unusable.
When importing a CSV file, the plugin indicates which data is
erroneous and enables the user to correct it.

## Main features

The plugin has a graphical user interface that is brought up by either
using the Ctrl+Alt+B keyboard shortcut, or by using QGIS' "Extensions"
menu, selecting "Radiotrack", and "Open/close Radiotrack", or clicking
the black bat icon if available. This interface is described later on
this page.

After importing a file, two map layers are created: one drawing dots
where measures were taken, and one drawing lines indicating in which
direction the measured signal comes from. The length of the line
depends on the strength of the signal. A weaker signal means a further
radioemitter, thus a longer line. If the data contains errors, some
dots or lines won't be drawn until the errors are corrected.

The table can be edited to correct the errors. Once everything is
fine, you can export the result as a CSV file.

## Plugin Layout

The following image shows the plugin on its main tab with numbers
marking the useful parts.

![Plugin layout](Documentation/images/main.png)

The plugin has different tabs, indicated by (1). This documentation is
in the "Documentation" tab. The main tab was selected for the
screenshot.

After clicking the "Import" button, in the buttons area (3), and
selecting a valid CSV file, the table (2) will show the file's data. A
pink row contains errors. It means that one or more cells contain data
that can't be used as is. Such cells are red. You can select a cell
and type to input valid data. When hitting the Enter key or leaving
the cell, its content will be checked. If it is valid, the red goes
away, and the pink too if the line no longer contains errors. Also,
the map will be updated. This is actually true for each cell: putting
erroneous data will turn the cells red and remove the associated
content on the map.

The button "Export" will let you export your edited data to as a CSV
file.

The button "Clear" will empty the table and remove the two layers, as
if you didn't even use the plugin yet.

The "Project" field is used to remind you which file you imported.
However, if you edit the table, their data will no longer match, so
don't forget to save your data when you're done.

## Shortcuts

| Shortcut         | Effect                |
| ---------------- |-----------------------|
| Ctrl + Alt + B   | Open/Close the plugin |
| Ctrl + Alt + I   | Import a new file     |
| Ctrl + Alt + X   | Export selected items |
| F2               | Edit cell             |
| Ctrl + Alt + C   | Clear the loaded data |
| Ctrl + Page Down | Go to the next tab    |
| Ctrl + Page Up   | Go to previous tab    |

## CSV files format

The plugin works with CSV files. Usually, any spreadsheet software can
export its spreadsheets to this format.

The first line of the spreadsheet must be a header. Instead of
containing data, its cells hold the name of the columns' data. The
plugin requires the following header (and columns), in that order:

- id_observation: a number representing the row. The first row of data
  (right below the header) must have the number 1, the next one 2, and
  so on. A spreadsheet editor like Excel will help you easily fill
  this column.
- id: a number identifying the radioemitter that was measured. It
  makes more sense to use different files for different radioemitters,
  so a file always contains the same value.
- name: the name of that radioemitter.
- date: time when the signal was measured. Example: 23/01/2018
  03:48:00.
- lat: latitude (North) of the antenna when measuring.
- lon: longitude (East) of the antenna when measuring.
- azi: angle in [0, 360[ indicating where the signal came from.
- filter: filter level in [0, 10]. A greater value means that if the
  signal was measured, its emitter was closer.
- power: strength of the signal in [0, 10]. A greater sum with
  niveau_filtre will produce a shorter line on the map layer, thus
  indicating a closer emitter.
- comment: any comment you want to associate with the data.

## Authors

- Bello Fernando
- Boisson Romain
- Cabodi Alexis
- [Canon Louis-Claude](http://lccanon.free.fr/)
- Jeannin Emile
- Moyikoulou Chris-Féri
- Wetzel Anthony
