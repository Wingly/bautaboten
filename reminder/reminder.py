from datetime import datetime


class Reminder:
	hasReminded = False
	def __init__(self, sender, rawMessage):
		splitData = rawMessage.split(' ', 3)
		#0 will be the command
		#1 will be the date
		#2 will be the time
		dt = datetime.strptime(splitData[1] + " " + splitData[2], "%y-%m-%d %H:%M")
		self.remindString = sender +": " + splitData[3]
		self.remindDate = dt

	def checkReminder(self):
		now = datetime.now()
		if self.remindDate < now:
			self.hasReminded = True
			return self.remindString
		return "!wait"