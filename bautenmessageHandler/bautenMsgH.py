import socket
import urllib
import urllib.request
from urllib.error import URLError, HTTPError
from urllib.parse import quote, urlparse
import bautenmessageHandler.bautenConf as botConf
import reminder.reminder as reminderModule
from random import randint
import json
import re
import sys
import time
import os
import lxml.html
# -*-coding: utf-8 -*-

################################### Knowledge holder #############
class KnowledgeHolder:

	def __init__(self):
		self.knowledgeContainer = {}
		self.__readKnowledge()
	def __saveKnowledge(self, key):
		saveFile = open('savedData/knowledge.data', 'a')
		saveFile.write(key + ":" + self.knowledgeContainer[key] + "\n")
		saveFile.close()
	def __readKnowledge(self):
		loadFile = open('savedData/knowledge.data')
		for line in loadFile:
			data = line.split(':', 1)
			self.knowledgeContainer[data[0]] = data[1]
		loadFile.close()
	def learnKnowledge(self, key, knowledge):
		if len(knowledge) > 100:
			return "I can't remember that much  : ("
		if key in self.knowledgeContainer:
			return "I already knows what " +key + " is"
		self.knowledgeContainer[key] = " ".join(str(word) for word in knowledge)
		self.__saveKnowledge(key)
		return "Thank you for teaching me that!"
	def getKnowledge(self, key):
		if key not in self.knowledgeContainer:
			return "I don't know what that is : ("
		return self.knowledgeContainer[key] 
#################################### rockpaperScissor ###########
class RPSGame:
	rules = {}
	initTime = 0
	playTime = 60
	halfTimeWarningIssued = False 
	validOptions = ["rock" , "paper", "scissor",  "p",  "r",  "s"]
	class Player:
		name = "n/a"
		choice = ""
		def __init__(self, name):
			self.name = name
		def getName(self):
			return self.name
	def __init__(self, player1, player2, originChannel):
		self.player1 = self.Player(player1)
		self.player2 = self.Player(player2)
		if player1 == botConf.nick:
			self.player1.choice = self.aiChoice()
		elif player2 == botConf.nick:
			self.player2.choice = self.aiChoice()
		self.initTime = time.time()
		self.originChannel = originChannel
		self.rules['rockscissor'] = 0
		self.rules['rockpaper'] = 1
		self.rules['rockrock'] = 2
		self.rules['paperrock'] =  0
		self.rules['paperscissor'] = 1
		self.rules['paperpaper'] =  2 
		self.rules['scissorpaper']=  0 
		self.rules['scissorrock']=  1 
		self.rules['scissorscissor'] =2 
	def aiChoice(self):
		return self.validOptions[randint(0,2)]
	def isPlaying(self, person):
		if person == self.player1.name or person == self.player2.name:
			return True
		return False
	def makeChoice(self, player, choice):
		if choice == "r":
			choice = "rock"
		elif choice == "p":
			choice = "paper"
		elif choice == "s":
			choice = "scissor"
		if self.player1.name == player:
			self.player1.choice = choice
		elif self.player2.name == player:
			self.player2.choice = choice		 

	def __calculateWinner(self):
		print ("CalculateWinner")
		winCode = self.rules[self.player1.choice + self.player2.choice]
		if winCode == 0:
			return self.player1.name +" Won over "+ self.player2.name +"! With " + self.player1.choice +" vs "+ self.player2.choice 
		if winCode == 1:
			return self.player2.name +" Won over "+ self.player1.name +"! With " + self.player2.choice +" vs "+ self.player1.choice 
		else:
			return "And it's a tie between "+ self.player1.name +" and " + self.player2.name +"! Both chose " + self.player1.choice
	def checkStatus(self):
		done = 0
		if self.player1.choice != "" and self.player2.choice != "":
			return self.__calculateWinner()
		return "Waiting for last player"		
#################################### WIKI CLASS ###################################################
class wikiHandler:
	lang = ""
	url_search = 'http://%s.wikipedia.org/w/api.php?action=query&list=search&srsearch=%s&sroffset=%d&srlimit=%d&format=json'

	def __init__(self, lang):
		self.lang = lang
	def __rawGet(self, url):
		headers = {'User-Agent': 'Mozilla/5.0' }
		request = urllib.request.Request(url, None, headers)
		#request.add_header('User-Agent', 'Mozilla/5.0')
		res = ""
		try:
			res = urllib.request.urlopen(request)
		except HTTPError as e:
			print ("http error")
		except URLError as e:
			print ("url error")
		return res.read()
	def getWikiData(self, searchWord):
		print ("searching for: " + searchWord)
		offset = 0
		limit = 1
		url = self.url_search % (self.lang, quote(searchWord), offset,limit)
		
		content = self.__rawGet(url).decode('utf-8')				
		try:
			jData = json.loads(content)
			searchRes =  jData["query"]["search"][0]
			removeHtml = re.compile(r'<[^>]+>')
			rawsnippet = searchRes['snippet']
			return removeHtml.sub('', rawsnippet).replace("&quot" , " ")
		except Exception as e:
			print (e)
			return "Nothing found : ("
##################################### Main Messagehandler ##########################################
class MsgHandler:

	def __init__(self, socket):
		self.socket = socket
		self.rpsGameList = []
		self.wikicd = 0
		self.rpsScore = {}
		self.rpsLosses = {}
		self.rpsTies = {}
		self.loc = self.__countCode()
		self.botrpsCD = 60
		self.lastBotMatch = 0
		self.knowledgeHolder = KnowledgeHolder()
		self.reminders = []
	def getNames(self, channel):
			removeOperator = re.compile(r'[@\+%]')
			self.socket.send(bytes("NAMES " + channel + botConf.stopsign, 'utf-8'))
			rawNames = self.socket.recv(2040).decode('utf-8')
			rawNames = rawNames.split(':')[2]
			rawNames = removeOperator.sub('',rawNames)
			names = rawNames.split()
			return names
	def composePrivMsg(self,target, message):
		return bytes("PRIVMSG" +" " + target + " :" + message + botConf.stopsign, 'utf-8')
	def handleMessage(self, sender, message, channel):
		removeOperator = re.compile(r'[@\+%]')
		sender = removeOperator.sub('',sender)
		retMsg = ""
		if re.match(r"^![aA-zZ]", message) != None:
			print (" Command used: " + sender + message)
			if message.startswith("!wiki"):
				if self.wikicd > time.time():
					return
				splitted = message.split(' ', 2)
				test = botConf.wikiLandcodes
				if len(splitted) >= 3:				
					if splitted[1] in botConf.wikiLandcodes:
						wiki = wikiHandler(splitted[1])
						searchString = splitted[2]
					else:
						wiki = wikiHandler("en")
						searchString = splitted[1] + " "+ splitted[2]				
				elif len(splitted) == 2:
					wiki = wikiHandler("en")
					searchString = splitted[1]
				else:
					retMsg = self.composePrivMsg(channel, "You didn't tell me what to search for : (")
					self.socket.send(retMsg)
					return					
								
				retMsg = self.composePrivMsg(channel, wiki.getWikiData(searchString))
				self.socket.send(retMsg)
				self.wikicd = time.time() + 5
			elif message.startswith("!rockpaperscissors") or message.startswith("!rps"):
				if len(self.rpsGameList) != 0:
					retMsg = self.composePrivMsg(channel, "Someone is already playing! Wait for your turn")
					self.socket.send(retMsg)
					return
				if message.find(botConf.nick) != -1:
					if time.time() <  (self.lastBotMatch + self.botrpsCD):
						retMsg = self.composePrivMsg(channel, "I'm sorry, I'm too busy to play myself right now, play against a friend instead!")
						self.socket.send(retMsg)
						return
					else:
						self.lastBotMatch = time.time()					
				data = message.split()
				if len(data) > 3 or len(data) < 3:
					retMsg = self.composePrivMsg(channel, "bad parameters, should be !rockpaperscissors(!rps) fighter1 fighter2")
					self.socket.send(retMsg)
					return
				if data[1] == data[2]:
					retMsg = self.composePrivMsg(channel, "You can't play against yourself you silly goose you")
					self.socket.send(retMsg)
					return					
				names = self.getNames(channel)
				if data[1] in names and data[2] in names:
					newGame = RPSGame(data[1], data[2], channel)
					self.rpsGameList.append(newGame)
					retMsg = self.composePrivMsg(data[1], "You are now playing rps! Type "+ botConf.nick +" !play rock/paper/scissor to make your choice!")
					self.socket.send(retMsg)
					retMsg = self.composePrivMsg(data[2], "You are now playing rps! Type /msg "+ botConf.nick +" !play rock/paper/scissor to make your choice!")
					self.socket.send(retMsg)
					return
				else:
					retMsg = self.composePrivMsg(channel, "Both fighters must be in this channel")
					self.socket.send(retMsg)
					return
			elif message.startswith("!play"):
				choice = message.split()[1].lower()
				if len(self.rpsGameList) == 0:
					retMsg = self.composePrivMsg(sender, "No game in progress")
					self.socket.send(retMsg)
					return
				if self.rpsGameList[0].isPlaying(sender) == False:
					retMsg = self.composePrivMsg(sender, "Your not playing in the current game")
					self.socket.send(retMsg)
					return
				if choice not in self.rpsGameList[0].validOptions:
					retMsg = self.composePrivMsg(sender, "Choice must be rock(r), paper(p) or scissor(s)")
					self.socket.send(retMsg)
					return
				self.rpsGameList[0].makeChoice(sender, choice)
				retMsg = self.composePrivMsg(sender, "Okay!")
				self.socket.send(retMsg)
				gameStatus = self.rpsGameList[0].checkStatus()
				retMsg = self.composePrivMsg(self.rpsGameList[0].originChannel, gameStatus)
				self.socket.send(retMsg)
				if gameStatus != "Waiting for last player":
					self.rpsGameList.pop(0)
					winner = gameStatus.split()[0]
					if winner != "And":
						loser = gameStatus.split()[3]
						if winner in self.rpsScore:
							self.rpsScore[winner] = int(self.rpsScore[winner]) + 1
						else:
							self.rpsScore[winner] = 1
						if loser in self.rpsLosses:
							self.rpsLosses[loser[:-1]] = int(self.rpsLosses[loser[:-1]]) + 1
						else:
							self.rpsLosses[loser[:-1]] = 1
					else:
						ties = gameStatus.split()
						if ties[5] in self.rpsTies:
							self.rpsTies[ties[5]] = int(self.rpsTies[ties[5]]) + 1	
						else:
							self.rpsTies[ties[5]] = 1	
						if ties[7] in self.rpsTies:
							self.rpsTies[ties[7]] = int(self.rpsTies[ties[7]]) + 1	
						else:
							self.rpsTies[ties[7]] = 1	
				return
			elif message.startswith("!wins"):
				wins = ""
				if len(self.rpsScore) > 0:
					for person in self.rpsScore:
						wins += person +" " + str(self.rpsScore[person]) +" "
				else:
					wins = "Scoreboard is empty"
				retMsg = self.composePrivMsg(channel, wins)
				self.socket.send(retMsg)
				return
			elif message.startswith("!ties"):
				ties = ""
				if len(self.rpsTies) > 0:
					for person in self.rpsTies:
						ties += person +" " + str(self.rpsTies[person]) +" "
				else:
					ties = "Scoreboard(Tieboard?) is empty"
				retMsg = self.composePrivMsg(channel, ties)
				self.socket.send(retMsg)
				return
			elif message.startswith("!losses"):
				losses = ""
				if len(self.rpsLosses) > 0:
					for person in self.rpsLosses:
						losses += person +" " + str(self.rpsLosses[person]) +" "
				else:
					losses = "Scoreboard(Loseboard?) is empty"
				retMsg = self.composePrivMsg(channel, losses)
				self.socket.send(retMsg)
				return
			elif message.startswith("!about"):
				retMsg = self.composePrivMsg(channel, "Version: ~#500. Written in python with around(+-50 because i can't count properly :( ) " + str(self.loc) + " lines of code")
				self.socket.send(retMsg)
				return
			elif message.startswith("!rovare"):
				if len(message.split()) > 1: 
					consonants = ["q", "w", "r", "t", "p", "s", "d", "f", "g", "h", "j",
									 "k", "l", "z", "x", "c", "v","b" , "n" , "m"]
					preRovared = message.split(' ', 1)[1]
					preRovared = preRovared[0] + preRovared[1:].lower()
					afterRovared = ""
					for char in preRovared:
						if char.lower() in consonants:
							afterRovared += char + "o" + char.lower()
						else:
							afterRovared += char
					retMsg = self.composePrivMsg(channel, afterRovared)
					self.socket.send(retMsg)
				else:
					retMsg = self.composePrivMsg(channel, "You didn't tell me what to rövarify : (")
					self.socket.send(retMsg)
				return
			elif message.startswith("!derovare"):
				if len(message.split()) > 1: 
					consonants = ["q", "w", "r", "t", "p", "s", "d", "f", "g", "h", "j",
									 "k", "l", "z", "x", "c", "v","b" , "n" , "m"]
					rovared = message.split(' ', 1)[1]
					deRovared = ""
					index = 0
					while index < len(rovared):
						char = rovared[index]						
						if char in consonants:
							deRovared += char
							index += 3
						else:
							deRovared += char
							index += 1
						print (str(index) +" "+char)
					retMsg = self.composePrivMsg(channel, deRovared)
					self.socket.send(retMsg)
				else:
					retMsg = self.composePrivMsg(channel, "You didn't tell me what to derövarify : (")
					self.socket.send(retMsg)		
			elif message.startswith("!learn"):
				data = message.split()
				if len(data) < 3:
					retMsg = self.composePrivMsg(channel, sender + ": You need to provide a key and value for me to remember")
					self.socket.send(retMsg)
					return
				response = self.knowledgeHolder.learnKnowledge(data[1], data[2:])
				retMsg = self.composePrivMsg(channel, sender + ": " + response)
				self.socket.send(retMsg)
			elif message.startswith("!whatis"):
				data = message.split()
				if len(data) != 2:
					retMsg = self.composePrivMsg(channel, sender + ": Please provide the _single_ word key for what you wish me to remember")
					self.socket.send(retMsg)
					return
				response = self.knowledgeHolder.getKnowledge(data[1])
				retMsg = self.composePrivMsg(channel, sender + ": " + response)
				self.socket.send(retMsg)	
			elif message.startswith("!remindme"):
				try:
					rm = reminderModule.Reminder(sender, message)
					self.reminders.append(rm)

					retMsg = self.composePrivMsg(channel, "Okay will do! ")
					self.socket.send(retMsg)
					return
				except Exception as e:
					retMsg = self.composePrivMsg(channel, "Bad formatting " + str(e))
					self.socket.send(retMsg)
					return

			elif len(message) > 1:
				retMsg = self.composePrivMsg(channel, "I don't know that command : (")
				self.socket.send(retMsg)
				return
		elif message.find(botConf.nick) != -1:
			rudeWords = ["suck", "idiot", "dum", "dumfan", "helvete",
						"sämst", "fan", "kass", "sopa","käften", "käft", "dålig", "dåligt"]
			niceWords = ["duktig", "snäll", "bra" ,"duktigt", "good", "excellent", "smart"]
			if message.find("meet") != -1:
				retMsg = self.composePrivMsg(channel, "Hello Mr/Ms " + message.split("meet")[1].split()[0] + " I'm honored to meet you!")
			elif message.lower().find("open the pod bay doors") != -1:
				retMsg = self.composePrivMsg(channel, "I'm sorry, " + sender + ". I'm afraid I can't do that.")
			elif message.find("?") != -1:
				retMsg = self.composePrivMsg(channel, sender + ": " +self.magic8Ball())
			elif any(word in message.lower() for word in rudeWords ):
				retMsg = self.composePrivMsg(channel, sender +" Amendurå!")
			elif any(word in message.lower() for word in niceWords):
				retMsg = self.composePrivMsg(channel, "Why thank you " + sender + "!")
			else:	
				retMsg = self.composePrivMsg(channel, "Hello Mr/Ms " + sender)
			if retMsg != "":	
				self.socket.send(retMsg)
		elif message.isupper() and message.find("!") != -1:
			retMsg = self.composePrivMsg(channel, sender + ": No need to yell, we can all hear you just fine.")
			self.socket.send(retMsg)

		possibleURL = self.__checkForURL(message)
		if possibleURL != "":
			title = self.getURLTitle(possibleURL)
			if title != "":
				retMsg = self.composePrivMsg(channel, title)
				self.socket.send(retMsg)			

	def greetVisitor(self, channel, visitor):
		retMsg = self.composePrivMsg(channel[1:], "Welcome " + visitor + "!")
		print (retMsg)
		self.socket.send(retMsg)
	def update(self):
		if len(self.rpsGameList) != 0:
			timePlayed = time.time() - self.rpsGameList[0].initTime
			if (timePlayed) > self.rpsGameList[0].playTime:
				retMsg = self.composePrivMsg(self.rpsGameList[0].originChannel, "Game has timed out, no one wins")
				self.socket.send(retMsg)
				self.rpsGameList.pop(0)
			elif int(timePlayed) % (self.rpsGameList[0].playTime / 2) == 0 and self.rpsGameList[0].halfTimeWarningIssued == False and int(timePlayed) >= 1:
				retMsg = self.composePrivMsg(self.rpsGameList[0].originChannel, "Halftime reached "+ str(self.rpsGameList[0].playTime / 2) +"s remaining until timeout")
				self.socket.send(retMsg)
				self.rpsGameList[0].halfTimeWarningIssued = True
		time.sleep(0.1)
	def __countCode(self):
			path = "."
			loc = 0
			for root, dir, files in os.walk(path):
				print (root)
				for file in files:
					if file.endswith(".py"):
						with open(os.path.join(root ,file)) as f:
							for i, l in enumerate(f):
								pass
						loc += i
			return loc
	def __checkForURL(self, checkString):
		for x in checkString.split():
			if urlparse(x)[1] != "":
				return x
		return ""
	def magic8Ball(self):
		possibleAnwers = ["It is certain", "It is decidedly so" , 
		"Without a doubt", "Yes, definitely", "You may rely on it", 
		"As I see it, yes", "Most likely", "Outlook good", "Yes", 
		"Signs point to yes", "Reply hazy try again", "Ask again later",
		 "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
		 "Don't count on it",  "My reply is no", "My sources say no" , 
		 "Outlook not so good" ,"Very doubtful", "Ja'int' fan'vejt ja'" ]
		answer = randint(0,20)
		return possibleAnwers[answer]
	def getURLTitle(self, url):
		try:
			headers={
			    'User-Agent': 'Mozilla/5.0'
			  }
			res = urllib.request.Request(url, None, headers)
			page = urllib.request.urlopen(res)
			parsed = lxml.html.parse(page)
			return parsed.find(".//title").text
		except Exception:
			print ("Failed to load " + url)
			return ""