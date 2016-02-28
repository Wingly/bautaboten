import socket
import time
import markov.markov as markov
import bautenmessageHandler.bautenMsgH as msgHandler
import bautenmessageHandler.bautenConf as botConf
import bautenmessageHandler.bautenQuizH as quizHandler

from multiprocessing import Process, Pipe
import importlib
import imp
import select
import re
import sys
def checkforPing(p_checkforSec):
	ready = select.select([irc], [irc], [irc], p_checkforSec)
	if ready[0]:
		text = irc.recv(2040)
		text = text.decode('utf-8')
		print (text)
		
		if text.find('PING') != -1:
			print ("ping ponging")
			irc.send(bytes('PONG ' + text.split()[1] + '\r\n', 'utf-8'))



irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print ("Connecting to " + botConf.server)
irc.connect((botConf.server, 6667))
#checkforPing(1)
#print "sending pass"
#irc.send("PASS" + "secret" + "\r\n")
checkforPing(2)
print ("sending nick")
irc.send(bytes("NICK " + botConf.nick + botConf.stopsign, 'utf-8'))
#checkforPing(1)
print ("sending user")
irc.send(bytes("USER "+ botConf.nick +" 2 "+ " * "+ " :Iam a bot(im still learning how to do this)" + botConf.stopsign, 'utf-8'))

checkforPing(4)
print ("joining channel")
irc.send(bytes("JOIN " + botConf.channel + botConf.stopsign, 'utf-8'))

admin =[]
allowCommands = True
quizMode = False
handler = msgHandler.MsgHandler(irc) #Standard handler
quizModule = None #Use in quiz mode
channel_conn, markov_conn = Pipe()
markov_Process = Process(target=markov.start, args=(markov_conn, botConf.channel,))
markov_Process.start()
while 1:
	ready = select.select([irc], [irc], [irc], 0.1)
	if ready[0]:
		text = irc.recv(2040)
		text = text.decode('utf-8')

		if text.find('PING') != -1:
				print ("ping ponging")
				irc.send(bytes('PONG ' + text.split()[1] + '\r\n', 'utf-8'))
				continue
		removeOperator = re.compile(r'[@\+%]')
		data = text.split()
		sender = removeOperator.sub('',data[0][1:].split('!')[0])
		msgType = data[1]
		target = data[2]

		if target == botConf.nick:
			target = sender
		if msgType == "PRIVMSG":
			message =data[3]
			for i in range(4,len(data)):
				message += " "+data[i]
			message = message[1:]
		if msgType == "PRIVMSG" and sender != botConf.nick:
			if not message.startswith("!"):
				channel_conn.send(message)
			if (sender in botConf.superAdmin or (sender in admin and not allowCommands)) and message == "!reload":
				irc.send(bytes("PRIVMSG" +" " + target + " :Attempting reload." + botConf.stopsign, 'utf-8'))
				try:
					quizMode = False
					try:
						channel_conn.send("!stop")
						markov_Process.join()
						markov_Process = None
						channel_conn = None
						markov_conn = None
					except Exception as e:
						print ("Error when stopping markov" + str(e))
					if sys.version_info >= (3,4):
						msgHandler = importlib.reload(msgHandler)
						quizHandler = importlib.reload(quizHandler)
						markov = importlib.reload(markov)
					else:
						msgHandler = imp.reload(msgHandler)
						quizHandler = imp.reload(quizHandler)
						markov = imp.reload(markov)						
					handler = msgHandler.MsgHandler(irc)
					channel_conn, markov_conn = Pipe() 
					markov_Process = Process(target=markov.start, args=(markov_conn, botConf.channel,))
					markov_Process.start()	

					quizModule = None
					irc.send(bytes("PRIVMSG" +" " + target + " :Reload complete." + botConf.stopsign, 'utf-8'))
					allowCommands = True
				except Exception as e:
					print (e)
					allowCommands = False #Not using handler here since im not sure it's not broken after the reload attempt
					irc.send(bytes("PRIVMSG" +" " + "#teamkazzak" + " :Error reloading." + botConf.stopsign, 'utf-8'))	
				continue
			elif (sender in botConf.superAdmin or sender in admin) and message.lower() == "!quiz":
				if quizMode == False:
					quizMode = True
					quizModule = quizHandler.QuizModule(target,irc)
				continue
			elif (sender in botConf.superAdmin  or sender in admin) and message == "!abort":
				if quizMode == True:
					quizMode = False
					quizModule = None
				continue
			elif sender in botConf.superAdmin and message.startswith("!addAdmin"):
				splitted = message.split()
				if len(splitted) > 1:
					names = handler.getNames(target)
					for person in (set(splitted) & set(names)):
						admin.append(person)
				if len(admin) > 0:
					adminlist = ''.join(str(x) for x in admin)+ " "
					print ("current admins: " + adminlist)
				continue
			elif sender in botConf.superAdmin and message.startswith("!delAdmin"):
				splitted = message.split()
				if len(splitted) > 1:
					names = handler.getNames(target)
					if splitted[1] in names:
						admin.remove(splitted[1])
				if len(admin) > 0:
					adminlist = ''.join(str(x) for x in admin)  + " "
					print ("current admins: " + adminlist)
				continue
			elif sender in botConf.superAdmin and message.startswith("!quit"):
				print ("attempting to quit")
				irc.send(bytes("PRIVMSG" +" " + target + " : Okay, goodbye :(" + botConf.stopsign, 'utf-8'))
				irc.send(bytes("QUIT :Bye bye", 'utf-8'))
				sys.exit()			
			elif message.startswith("!speak"):
				if allowCommands:
					channel_conn.send(message)
					sentence = channel_conn.recv()
					if sentence.startswith("!error"):
						allowCommands = False
					retMsg = handler.composePrivMsg(target, sentence)

					irc.send(retMsg)
				continue
			elif message.startswith("!markovsave") and sender in botConf.superAdmin:
				channel_conn.send(message)
				continue
			if allowCommands:
				try:
					if quizMode == False:
						handler.handleMessage(sender, message, target)
					else:
						quizModule.handleMessage(sender, message)
				except Exception as e:
					print (e)
					allowCommands = False
					irc.send(bytes("PRIVMSG" +" " + target + " :Error in msgH " + str(e) + botConf.stopsign, 'utf-8'))
		elif msgType == "JOIN":
			handler.greetVisitor(target, sender)
	if allowCommands:
		try:
			if quizMode == True:
				if quizModule.isFinished() == False:
					quizModule.update()
				else:
					quizMode = False
					quizModule = None		
			else:
				handler.update()
		except Exception as e:
			print (e)
			allowCommands = False
			irc.send(bytes("PRIVMSG" +" " + target + " :Error in update " + str(e) + botConf.stopsign, 'utf-8'))

	time.sleep(0.1)