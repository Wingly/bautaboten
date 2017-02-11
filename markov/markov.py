import random
import time
import os
import codecs
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
        self.__readFromFile("savedData/markov/" + channel + ".data")
        self.nextSave = time.time() + 18000

    def __saveToFile(self, path):
        saveFile = open(path, 'w', encoding='utf-8')
        output = ""
        for key in self.wordbase:
            output += key + ":" + " ".join(word for word in self.wordbase[key]) +"\n"
        saveFile.write(output)  
        saveFile.close()
    def __readFromFile(self, path):
        if not os.path.isfile(path):
            print ("no previous markov savefile for " + self.channel)
            return
        print ("Reading from " + path)
        loadFile = open(path , 'r', encoding='utf-8')
        for line in loadFile:
            data = line.split(':', 1)
            #print ("adding subwords for " + data[0])
            self.wordbase[data[0]] = []
            for word in data[1].split():        
                self.wordbase[data[0]].append(word)
            if not self.wordbase[data[0]]:
                self.wordbase[data[0]].append("")
        loadFile.close()

    def start(self):
        try:
            hasChanged = False
            while 1:
                if time.time() > self.nextSave and hasChanged:
                    self.__saveToFile("savedData/markov/" + self.channel + ".data")
                    self.nextSave = time.time() + 18000
                    hasChanged = False
                if not self.pipeEnd.poll(0.1):
                    time.sleep(0.1)
                    continue
                input = self.pipeEnd.recv()
                if input.startswith("!speak"):
                    outputString =""
                    randomWord = ""
                    if len(input.split()) > 1:
                        randomWord = input.split()[1]
                    else:
                        randomWord = random.sample(self.wordbase.keys(), 1)[0]
                    words = 1
                    outputString += str(randomWord) + " "
                    unEndedCitation = False
                    while randomWord in self.wordbase and words < 60:
                        if "\"" in randomWord:
                            unEndedCitation = not unEndedCitation
                        words+=1
                        randomWord = random.sample(self.wordbase[randomWord], 1)[0]
                        if randomWord != "":
                            #print (randomWord)
                            outputString += str(randomWord) + " "
                            if str(randomWord)[:-1] in self.stopSigns:
                                cont = random.randint(0,1)
                                if cont == 0:
                                    break
                        else:
                            break
                    if unEndedCitation:
                        outputString += " \""

                    self.pipeEnd.send(outputString)
                    continue
                elif input.startswith("!stop"):
                    return "Stopping"
                elif input.startswith("!markovsave"):
                    print ("saving to file")
                    self.__saveToFile("savedData/markov/" + self.channel + ".data")
                    continue
                #print (input)
                hasChanged = True
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