from qgis.PyQt.QtCore import Qt, QVariant, QDateTime, QRect
from qgis.PyQt.QtWidgets import QHeaderView, QStyle, QStyleOptionButton
from qgis.PyQt.QtWidgets import  QItemEditorFactory, QStyledItemDelegate, QDoubleSpinBox, QDateTimeEdit

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