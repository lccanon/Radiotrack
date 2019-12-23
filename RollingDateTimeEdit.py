from .compat import QDateTimeEdit

class RollingDateTimeEdit(QDateTimeEdit):
    def __init__(self, parent):
        super(QDateTimeEdit, self).__init__(parent)
        self.syncDateTime = None

    def setSyncDateTime(self, syncDateTime):
        self.syncDateTime = syncDateTime

    def stepBy(self, steps):
        section = self.currentSection()
        if self.syncDateTime is not None:
            diff = self.dateTime().msecsTo(self.syncDateTime.dateTime())
        if section == QDateTimeEdit.SecondSection:
            nextDate = self.dateTime().addSecs(steps)
        elif section == QDateTimeEdit.MinuteSection:
            nextDate = self.dateTime().addSecs(steps * 60)
        elif section == QDateTimeEdit.HourSection:
            nextDate = self.dateTime().addSecs(steps * 60 * 60)
        elif section == QDateTimeEdit.DaySection:
            nextDate = self.dateTime().addDays(steps)
        elif section == QDateTimeEdit.MonthSection:
            nextDate = self.dateTime().addMonths(steps)
        elif section == QDateTimeEdit.YearSection:
            nextDate = self.dateTime().addYears(steps)
        else:
            return
        self.setDateTime(nextDate)
        if self.syncDateTime is not None:
            self.syncDateTime.setDateTime(self.dateTime().addMSecs(diff))
