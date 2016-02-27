import time
import bautenmessageHandler.bautenConf as botConf
import json
import urllib.request
import re
#from html import unescape as HTMLsanitizer
import math
import operator
class QuizModule:
	validGuesses = ["1" ,"2","3","4"]

	class Player:
		name =""
		hasGuessed = False
		points = 0
		def __init__(self, playerName):
			self.name = playerName
	class Question:
		q_id = -1
		q_category_id = -1
		q_text = ""
		q_options = {}
		q_correct_option = -1
		q_difficulty_level = -1
		finished = False
		answerDisplayed = False
		def __init__(self, questionJson):
			removeHtml = re.compile(r'<[^>]+>')
			question = json.loads(questionJson)
			self.q_id = question["id"]
			text = question["q_text"]
			newtext = text#HTMLsanitizer(text)
			self.q_text = removeHtml.sub('',newtext)
			for i in range(1,5):
				self.q_options[i] = removeHtml.sub('',question["q_options_" + str(i)])#HTMLsanitizer(removeHtml.sub('',question["q_options_" + str(i)]))
			self.q_correct_option = question["q_correct_option"]
			self.q_difficulty_level = question["q_difficulty_level"]

	def __init__(self, channel, socket):
		self.nextActionTime = 0
		self.scoreboard = {}
		self.socket = socket
		self.channel = channel
		self.currentQuestion = None
		self.currentQuestionNum = -1
		self.answerTime = 30.0
		self.__introMessage()
		self.lastTimePrompt = 0
		self.TotalNumberOfQuestions = 5
	def __getRandomQuestion(self):
		headers={
		    "X-Mashape-Key": botConf.apiKey,
		    "Accept": "application/json",
		    'User-Agent': 'Mozilla/5.0'
		  }
		res = urllib.request.Request("https://pareshchouhan-trivia-v1.p.mashape.com/v1/getRandomQuestion", None, headers)
		question = urllib.request.urlopen(res).read()
		return question.decode('utf-8')
	def __introMessage(self):
		line = "Hello and welcome to this quiz, with me " + botConf.nick + " as your host. The first question will be displayed in about 5 seconds"
		self.socket.send(self.composePrivMsg(self.channel, line))		
	def composePrivMsg(self,target, message):
		return bytes("PRIVMSG" +" " + target + " :" + message + botConf.stopsign, 'utf-8')

	def __dislayCurrentQuestion(self):
		line = "Question " + str(self.currentQuestionNum + 1) +": " + self.currentQuestion.q_text
		self.socket.send(self.composePrivMsg(self.channel, line))
		for i in range(1,5):
			line = str(i) +") " + self.currentQuestion.q_options[i]
			self.socket.send(self.composePrivMsg(self.channel, line))
		line = "You now have " + str(self.answerTime) +"s to answer (using !guess option(1/2/3/4))"
		self.socket.send(self.composePrivMsg(self.channel, line))

	def __displayAnswer(self):
		line = "The answer was, obviously, " + str(self.currentQuestion.q_correct_option)
		line += ". This question had a difficulty of " + str(self.currentQuestion.q_difficulty_level)
		self.socket.send(self.composePrivMsg(self.channel, line))

	def __displayWinner(self):
		if len(self.scoreboard) != 0:
			sortedScore = ""
			sortedList = sorted(self.scoreboard.values(), key=operator.attrgetter('points'), reverse=True)
			for player in sortedList:
				sortedScore += player.name + " " + str(player.points) +" "
			winner = sortedScore.split()[0]
			points = sortedScore.split()[1]
			line = "And the proud winner is " + winner +" with " + points + " points!"
			self.socket.send(self.composePrivMsg(self.channel, line))
			line = "Scoreboard: " + sortedScore
			self.socket.send(self.composePrivMsg(self.channel, line))
		line = "Thank you for playing!"
		self.socket.send(self.composePrivMsg(self.channel, line))
	def update(self):
		currTime = time.time()
		if currTime > self.nextActionTime:
			if self.currentQuestionNum == -1:
				self.currentQuestionNum = 0
				self.nextActionTime = time.time() + 5.0
				self.lastTimePrompt = 0
			elif self.currentQuestionNum != 0 and not self.currentQuestion.answerDisplayed:
				self.__displayAnswer()
				for player in self.scoreboard:
					self.scoreboard[player].hasGuessed = False
				self.nextActionTime = currTime + 20.0
				self.lastTimePrompt = 0
				self.currentQuestion.answerDisplayed = True
				self.socket.send(self.composePrivMsg(self.channel, str(self.nextActionTime - currTime) +"s until next question"))
			elif self.currentQuestionNum != self.TotalNumberOfQuestions:
				print ("Question "+ str(self.currentQuestionNum) )
				self.currentQuestion = self.Question(self.__getRandomQuestion())
				self.__dislayCurrentQuestion()
				self.currentQuestionNum += 1
				self.nextActionTime = time.time() + self.answerTime
				self.lastTimePrompt = 0

		elif int(self.nextActionTime - currTime) % 20 == 0 and int(self.nextActionTime - currTime) != self.lastTimePrompt:
			self.lastTimePrompt = int(self.nextActionTime - currTime)
			self.socket.send(self.composePrivMsg(self.channel, str(math.floor(self.nextActionTime - currTime)) +"s until next question"))

	def handleMessage(self, sender, message):
		message = message.lower()
		removeOperator = re.compile(r'[@\+%]')
		sender = removeOperator.sub('',sender)
		retMsg = ""
		if message.startswith("!"):
			if message.startswith("!guess"):
				if len(message.split()) > 1:
					guess = message.split()[1]
					if sender in self.scoreboard:
						if self.scoreboard[sender].hasGuessed == False:
							if guess in self.validGuesses:
								self.scoreboard[sender].hasGuessed = True
								if guess == str(self.currentQuestion.q_correct_option):
								#	print ("incrementing " + sender +"s score. Was " + str(self.scoreboard[sender].points))
									self.scoreboard[sender].points += 1
								#	print ("Score is now " + str(self.scoreboard[sender].points))
							else:
								retMsg = self.composePrivMsg(self.channel, "Invalid answer, valid answers are 1/2/3/4")
								self.socket.send(retMsg)
					else:
						print ("adding "+  sender + " to scoreboard")
						newPlayer = self.Player(sender)
						self.scoreboard[sender] = newPlayer
						if guess in self.validGuesses:
							self.scoreboard[sender].hasGuessed = True
							if guess == str(self.currentQuestion.q_correct_option):
							#	print (sender +" guessed right the first time score is now 1")
								self.scoreboard[sender].points = 1	
						else:
							retMsg = self.composePrivMsg(self.channel, "Invalid answer, valid answers are 1/2/3/4")
							self.socket.send(retMsg)
				else:
					retMsg = self.composePrivMsg(self.channel, "You need to choose an answer you silly goose, valid answers are 1/2/3/4")
					self.socket.send(retMsg)					
	def isFinished(self):
		if self.currentQuestionNum == self.TotalNumberOfQuestions and self.currentQuestion.answerDisplayed:
			print ("Finishing")
			self.__displayWinner()
			return True
		return False