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

    def __generateSentence(self, startWord):
        outputString =""
        randomWord = ""
        if len(startWord.split()) > 1:
            randomWord = startWord.split()[1]
        else:
            randomWord = random.sample(self.wordbase.keys(), 1)[0]
        words = 1
        outputString += str(randomWord) + " "
        unEndedCitation = False
        while words < 60:
            use1word = (random.randint(0,100) < self.allow1wordCoef)

            if not use1word and len(outputString.split(" ")[-3:-1]) == 2:
                randomWord = ""
                words+=1
                newWordCombo = " ".join(outputString.split(" ")[-3:-1])
                if (newWordCombo not in self.twoWordBase):
                    continue
                totalPossibilites = sum(self.twoWordBase[newWordCombo].values())
                randWord = random.randint(0, totalPossibilites)
                current = 0
                for word in self.twoWordBase[newWordCombo]:
                    current += self.twoWordBase[newWordCombo][word]
                    if current >= randWord:
                        randomWord = word
                        break
                if randomWord != "":
                    outputString += str(randomWord) + " "
                    if str(randomWord)[:-1] in self.stopSigns:
                        cont = random.randint(0,1)
                        if cont == 0:
                            break
                else:
                    break
            elif randomWord in self.wordbase: #check for 1 words
                if "\"" in randomWord:
                    unEndedCitation = not unEndedCitation
                words+=1
                randomWord = random.sample(self.wordbase[randomWord], 1)[0]
                if randomWord != "":
                    outputString += str(randomWord) + " "
                    if str(randomWord)[:-1] in self.stopSigns:
                        cont = random.randint(0,1)
                        if cont == 0:
                            break
                else:
                    break
                if unEndedCitation:
                    outputString += " \""
            else:
                break
        return outputString

    def __learnfromMessage(self, message):
        data = message.split()
        wordCount = len(data)
        next = 1
        #learn single words
        for word in data:
            #print (word)
            if word in self.wordbase:
                if next < wordCount:
                    self.wordbase[word].append(data[next])
                else:
                    self.wordbase[word].append("")
            else:
                if next < wordCount:
                    self.wordbase[word] = [data[next]]
                else:
                    self.wordbase[word] = [""]
            next += 1
        #learn double words
        next = 1
        for word in data:
            if next >= wordCount:
                break
            newWordCombo = word + " " + data[next]
            if newWordCombo in self.twoWordBase:
                if next + 1 < wordCount:
                    if data[next+1] in self.twoWordBase[newWordCombo]:
                        self.twoWordBase[newWordCombo][data[next+1]] +=1
                    else:
                        self.twoWordBase[newWordCombo].append({data[next+1] : 1})
                else:
                    if "" in self.twoWordBase[newWordCombo]:
                        self.twoWordBase[newWordCombo][""] +=1
                    else:
                        self.twoWordBase[newWordCombo].append({"" : 1})
            else:
                if next + 1 < wordCount:
                    self.twoWordBase[newWordCombo] = {data[next+1] : 1}
                else:
                    self.twoWordBase[newWordCombo] = {"" : 1}

            next += 1
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
                    retMSG = self.__generateSentence(input)
                    self.pipeEnd.send(retMSG)
                    continue
                elif input.startswith("!stop"):
                    return "Stopping"
                elif input.startswith("!markovsave"):
                    print ("saving to file")
                    self.__saveToFile("savedData/markov/" + self.channel)
                    continue
                #print (input)
                hasChanged = True
                self.__learnfromMessage(input)

        except Exception as e:
            return "!error " + str(e)       