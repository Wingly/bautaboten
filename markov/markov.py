import random
import time
def start(pipeEnd, channel):
	
	markovChain = MarkovChain(pipeEnd, channel)
	retMsg = markovChain.start()
	pipeEnd.send(retMsg)

class MarkovChain:

	def __init__(self, pipeEnd, channel):
		self.pipeEnd = pipeEnd
		self.channel = channel
		self.wordbase = {}
		self.stopSigns = [".", "!" , "?"]

	def __saveToFile(self, path):
		saveFile = open(path, 'w')
		output = ""
		for key in self.wordbase:
			output += key + ":" + " ".join(word for word in self.wordbase[key]) +"\n"
		saveFile.write(output)	
		saveFile.close()
	def __readFromFile(self, path):
		dostuff = 2

	def start(self):
		try:
			while 1:
				if not self.pipeEnd.poll(0.1):
					time.sleep(0.1)
					continue
				input = self.pipeEnd.recv()
				if input.startswith("!speak"):
					outputString =""
					randomWord = random.sample(self.wordbase.keys(), 1)[0]
					outputString += str(randomWord) + " "
					while 1:	
						randomWord = random.sample(self.wordbase[randomWord], 1)[0]
						if randomWord != "":
							#print (randomWord)
							outputString += str(randomWord) + " "
							if str(randomWord)[:-1] in self.stopSigns:
								cont = randint(0,1)
								if cont == 0:
									break
						else:
							break
					self.pipeEnd.send(outputString)
					continue
				elif input.startswith("!stop"):
					return "Stopping"
				elif input.startswith("!markovsave"):
					print ("saving to file")
					self.__saveToFile("savedData/markov/" + self.channel + ".data")
					continue
				#print (input)
				data = input.split()
				stringEnd = len(data)
				next = 1
				for word in data:
					#print (word)
					if word in self.wordbase:
						if next < stringEnd:
							self.wordbase[word].append(data[next])
						else:
							self.wordbase[word].append("")
					else:
						if next < stringEnd:
							self.wordbase[word] = [data[next]]
						else:
							self.wordbase[word] = [""]
					next += 1
		except Exception as e:
			return "!error " + str(e)		