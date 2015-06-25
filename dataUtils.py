from mido import Message, MidiFile, MidiTrack
from theano import tensor
import os, copy, pickle
import numpy as np

DICE = False
if "DICE" in os.environ and os.environ["DICE"] == '1':
	DICE = True

if DICE == False:
	dataset_path = "/Users/Bernat/Dropbox/UoE/Dissertation/midiFiles/"
	test_path = "/Users/Bernat/Dropbox/UoE/Dissertation/testMidi/"
else:
	dataset_path = "/afs/inf.ed.ac.uk/user/s14/s1471922/Dissertation/midiFiles/"
	test_path = "/afs/inf.ed.ac.uk/user/s14/s1471922/Dissertation/testMidi/"



def saveRepresentation(data, fileName):
	with open(test_path + fileName, 'wb') as f:
		pickle.dump(data, f)

def loadRepresentation(fileName):
	with open(test_path + fileName, 'rb') as f:
		data = pickle.load(f)
		return data

def maxTimesteps(limitSongs):
	maxSteps = 0
	for fileName in os.listdir(dataset_path):
		if ".mid" in fileName:
			mid = MidiFile(dataset_path + fileName) 
			numSteps = 0
			for message in mid.tracks[0]:
				numSteps += message.time
			maxSteps = max([maxSteps, numSteps])
			limitSongs -= 1
			if limitSongs == 0:
				break
	return maxSteps

def getTimesteps(limitSongs):
	timesteps = []
	for fileName in os.listdir(dataset_path):
		if ".mid" in fileName:
			mid = MidiFile(dataset_path + fileName) 
			numSteps = 0
			for message in mid.tracks[0]:
				numSteps += message.time
			timesteps.append(numSteps)
			limitSongs -= 1
			if limitSongs == 0:
				break
	return timesteps


#perhaps it would make more sense to create a midi2roll function aside and simplify this one
def createRepresentation(limitSongs=0):
	#To Do: if limitSongs is bigger than the actual maximum or is 0 we should look for the number of files in the path to determine the first dimension
	#To Do: extract notes that are triggered so that we can reduce the third dimension from 128 to a smaller value
	
	#timesteps = maxTimesteps(limitSongs)
	#songs = np.zeros((limitSongs, timesteps, 128))
	timesteps = getTimesteps(limitSongs)
	songs = []
	idx = 0
	for fileName in os.listdir(dataset_path): #iterate per file
		if ".mid" in fileName: #check
			print "Loading file %d: %s" % (idx+1, fileName)
			mid = MidiFile(dataset_path + fileName)
			song = np.zeros(np.array((timesteps[idx], 128)))
			for i, track in enumerate(mid.tracks):
				if i != 0: #track 0 contains meta info we don't need
					ts = 0 #init time
					notesOn = []
					for message in track:
						ticks = message.time #indicates delta change where next event is happening
						while ticks > 0: #advance timestep pointer to delta while we keep enabling the activated notes
							for note in notesOn:
								#songs[idx][ts][note-1] = 1
								song[ts][note-1] = 1
							ticks -= 1
							ts += 1

						#update state at current timestep according to message
						if message.type == 'note_on':
							notesOn.append(message.note)
						if message.type == 'note_off':
							notesOn.remove(message.note) #To do: check if ValueError is triggered

			#add to songs
			songs.append(song)

			#check limit of songs for collection
			limitSongs -= 1
			if limitSongs == 0:
				break
			idx += 1 #next song...
			#could merge idx with limitsongs

	return songs


def roll2midi(roll): #roll is a (1, ts, input_dim) tensor
	mid = MidiFile()

	track = MidiTrack()
	mid.tracks.append(track)

	#To Do: translate representation from real to binary values

	tones = np.zeros(len(roll.shape[2]))
	ticks = 0
	for ts in roll[0]:
		for i in range(len(ts)):
			if ts[i] == 1 and tones[i] == 0:
				#record note_on event
				track.append(midi.Message('note_on', note=i, time=ticks))
				tones[i] = 1
				ticks = 0

			if ts[i] == 0 and tones[i] == 1:
				#record note_off event
				track.append(midi.Message('note_off', note=i, time=ticks))
				tones[i] = 0
				ticks = 0

		ticks += 1




	#track.append(midi.Message('note_on', note=64, velocity=64, time=32)
	#track.append(midi.Message('note_off', note=64, velocity=127, time=32)

	mid.save("%snew_song%d.mid" % (test_path, int(time.time())))


#This function creates samples out of each song
def createModelInputs(roll, step=1024, inc=8):
	#split into arbitrary lenght sequences and extract next tone for a sequence (Y)
	#To do (idea): split into shorter melodies cutting any empty part that is long enough.
	X = []
	Y = []
	for song in roll:
		pos = 0
		#start (padding + seq)
		empty = np.zeros((step,128))
		while (pos < step and pos < song.shape[0]):
			#zeros + part of seq
			sample = np.concatenate((empty[pos:],song[:pos]))
			X.append(sample)
			Y.append(song[pos])
			pos += inc

		#if step is larger than song length
		if pos < song.shape[0]:
			continue

		#mid
		pos = 0
		while pos < song.shape[0]:
			sample = np.array(roll[pos:pos+step])
			X.append(sample)
			Y.append(song[pos+step])
			pos += inc

		#don't implement end (seq + padding) because that could encourage stopping


	return np.array(X), np.array(Y)


