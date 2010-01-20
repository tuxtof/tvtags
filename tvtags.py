#!/usr/bin/env python
#encoding:utf-8
#author:tuxtof
#project:tvtags
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

"""
tvtags.py
Automatic TV episode tagger.
Uses data from www.thetvdb.com via tvdb_api,

thanks goes to:
dbr/Ben - http://github.com/dbr - for python help, tvdb_api and tvnamer.py
Rodney - http://kerstetter.net - for MP4Tagger help
ccjensen/Chris - for mp4tvtagger (source of this code)
"""

__author__ = "tuxtof"
__version__ = "0.5"

import os
import sys
import re
import glob
import unicodedata
import tempfile

from optparse import OptionParser

from tvdb_api.tvdb_api import Tvdb
from tvdb_api.tvdb_exceptions import (tvdb_error, tvdb_userabort, tvdb_shownotfound,
    tvdb_seasonnotfound, tvdb_episodenotfound, tvdb_attributenotfound)

class Program:
	"""docstring for Program"""
	def __init__(self, opts, filePath, fileName):
		if opts.verbose:
			print "Connecting to the TVDB... "
		#end if verbose
		tvDebug = False
		if opts.verbose > 1:
			tvDebug = True
		self.tvdb = Tvdb(debug = tvDebug, interactive = opts.interactive, banners = True, language = "fr")
		self.MP4Tagger = "MP4Tagger"
		self.filePath = filePath
		self.fileName = fileName
	#end def __init__
#end class Program

class Series:
	"""docstring for Series"""
	artworkFileName = ""
	
	def __init__(self, verbose, program, series, seasonNumber):
		#get show specific meta data
		if verbose:
			print "Retrieving Show Information... "
		#end if verbose
		self.seriesName = getShowSpecificInfo(verbose, program.tvdb, series, 'seriesname')
		
		self.actorsUnsplit = getShowSpecificInfo(verbose, program.tvdb, self.seriesName, 'actors')
		self.actors = self.actorsUnsplit.split('|')
		
		self.contentRating = getShowSpecificInfo(verbose, program.tvdb, self.seriesName, 'contentrating')
		#self.firstaired  = getShowSpecificInfo(verbose, program.tvdb, self.seriesName, 'firstaired') #currently not used for anything
		
		self.genresUnsplit  = getShowSpecificInfo(verbose, program.tvdb, self.seriesName, 'genre')
		self.genres = self.genresUnsplit.split('|')
		
		self.network  = getShowSpecificInfo(verbose, program.tvdb, self.seriesName, 'network')
		#seriesOverview  = getShowSpecificInfo(verbose, program.tvdb, self.seriesName, 'overview') #currently not used for anything
		
		self.seasonNumber = int(seasonNumber)
	#end def __init__
#end class Series

class Episode:
	"""docstring for Episode"""
	def __init__(self, verbose, program, series, seasonNumberEpisode, episodeNumber):
		self.fileName = program.fileName
		self.filePath = program.filePath
		
		
		#pattern = re.compile('[\D]+')
		
		
		
		#Parse the file name for information: 1x01 - Pilot.mp4
		(fileBaseName, self.fileExtension) = os.path.splitext(self.fileName)
		#(seasonNumberEpisode, episodeNumber, tail) = pattern.split(fileBaseName,2)
		
		#check if filename was of correct format, else set it to an incorrect value
		if len(seasonNumberEpisode) > 0:
			self.seasonNumberEpisode = int(seasonNumberEpisode)
		else:
			self.seasonNumberEpisode = 9999
		#end if len(seasonNumberEpisode)
		
		self.episodeNumber = int(episodeNumber)
		
		#get other episode specific meta data
		self.episodeName = getEpisodeSpecificInfo(verbose, program, series, self.episodeNumber, 'episodename')
		self.firstAired = getEpisodeSpecificInfo(verbose, program, series, self.episodeNumber, 'firstaired') + "T09:00:00Z"
		
		self.guestStarsUnsplit = getEpisodeSpecificInfo(verbose, program, series, self.episodeNumber, 'gueststars')
		# if self.guestStarsUnsplit:
		# 	self.guestStars = self.guestStarsUnsplit.split('|')
		# else:
		# 	self.guestStars = ""
		
		self.directorsUnsplit = getEpisodeSpecificInfo(verbose, program, series, self.episodeNumber, 'director')
		self.directors = self.directorsUnsplit.split('|')
		
		self.writersUnsplit = getEpisodeSpecificInfo(verbose, program, series, self.episodeNumber, 'writer')
		self.writers = self.writersUnsplit.split('|')
		
		self.productionCode = getEpisodeSpecificInfo(verbose, program, series, self.episodeNumber, 'productioncode')
		self.overview = getEpisodeSpecificInfo(verbose, program, series, self.episodeNumber, 'overview')
	#end def __init__
#end class Episode

def whichBin(execName):
	for path in os.environ["PATH"].split(":"):
		if os.path.exists(os.path.join(path,execName)):
			return 1

def openurl(urls):
	for url in urls:
		if len(url) > 0:
			os.popen("open \"%s\"" % url)
		#end if len
	#end for url
	return
#end openurl

def correctFileName(verbose, program, series, episode):
	"""docstring for correctFilename"""
	#Correct file name if incorrect
	if episode.fileName != "%s.%01dx%02d%s" % (series.seriesName.encode("utf-8").replace('/', "-"),series.seasonNumber, episode.episodeNumber,  episode.fileExtension):
		newFileName = "%s.%01dx%02d%s" % (series.seriesName.encode("utf-8").replace('/', "-"),series.seasonNumber, episode.episodeNumber,  episode.fileExtension)
		renameCmd = "mv -n \"%s/%s\" \"%s/%s\"" % (episode.filePath, episode.fileName, episode.filePath, newFileName)
		os.popen(renameCmd)
		if verbose:
			print "Filename corrected from \"%s\" to \"%s\"" % (episode.fileName, newFileName)
		#end if verbose
		episode.fileName = newFileName
	else:
		if verbose:
			print "Filename \"%s\" already correct" % episode.fileName
		#end if verbose
	#end if fileName
#end correctFileName

def tagFile(opts, program, series, episode):
	"""docstring for tagFile"""
	#setup tags for the MP4Tagger function
	if series.artworkFileName != "":
		addArtwork = " --artwork \"%s\"" % series.artworkFileName #the file we downloaded earlier
	else:
		addArtwork = ""
	#end if series.artworkFileName != ""
	addName = " --name=\"%s %ix%02i\"" % (series.seriesName, series.seasonNumber, episode.episodeNumber)
	addStik = " --media_kind=\"TV Show\"" #set type to TV Show
	addArtist = " --artist \"%s\"" % series.seriesName
	addTitle =  " --tv_episode_id \"%s\"" % episode.episodeName
	addAlbum = " --album \"%s - Season %s\"" % (series.seriesName, series.seasonNumber)
	addGenre = " --genre \"%s\"" % series.genres[1] #cause first one is an empty string, and genre can only have one entry
	addAlbumArtist = " --album_artist \"%s\"" % series.seriesName
	addDescription = " --description \"%s\"" % episode.overview
	addLongDescription = " --long_description \"%s\"" % episode.overview
	addTVNetwork = " --tv_network \"%s\"" % series.network
	addTVShowName = " --tv_show \"%s\"" % series.seriesName
	addTVSeasonNum = " --tv_season \"%i\"" % series.seasonNumber
	addTVEpisodeNum = " --tv_episode_n \"%i\"" % episode.episodeNumber
	addDisk = " --disk_n \"%i\"" % series.seasonNumber
	addTracknum = " --track_n \"%i\"" % episode.episodeNumber
	addContentRating = " --rating \"%s\"" % series.contentRating
	addYear = " --release_date \"%s\"" % episode.firstAired
	addComment = " --comments \"tagged by tvtags\""
	if len(series.actors) > 0:
		addCast = " --cast \"%s\"" % series.actors
	if len(episode.directors) > 0:
		addDirectors = " --director \"%s\"" % episode.directors
	if len(episode.writers) > 0:
		addScreenWriters = " --screenwriters \"%s\"" % episode.writers
	
	#Create the command line string
	tagCmd = "\"" + program.MP4Tagger + "\" -i \"" + episode.filePath + "/" + episode.fileName + "\"" \
	+ addName + addArtwork + addStik + addArtist + addTitle + addAlbum + addGenre + addAlbumArtist + addDescription \
	+ addTVNetwork + addTVShowName +  addTVSeasonNum + addTVEpisodeNum + addDisk + addTracknum \
	+ addContentRating  + addYear + addComment + addCast + addDirectors + addScreenWriters
	
	#run MP4Tagger using the arguments we have created
	if opts.verbose > 1:
		print tagCmd
	#end if debug
	
	os.popen(tagCmd)
	
	
	if opts.verbose:
		print "Tagged: " + episode.fileName
	#end if verbose

#end tagFile


def artwork(opts, interactive, program, series):
	cacheDir = os.path.join(tempfile.gettempdir(), "tvtags")
	
	if not os.path.exists(cacheDir):
		os.mkdir(cacheDir)
	
	try:
		potentialArtworkFileName = series.seriesName + " Season " + str(series.seasonNumber)
		for fullFileName in glob.glob(cacheDir + "/*.jpg"):
			(fileBaseName, fileExtension) = os.path.splitext(fullFileName)
			(filePath,fileName) = os.path.split(fileBaseName)
			
			if fileName == potentialArtworkFileName:
				if opts.verbose > 0:
					print "Using Previously Downloaded Artwork: " + fileName
				#end if verbose
				series.artworkFileName = fullFileName
				return
			#end if fileBaseName
		#end for fileName
		
		tvdb = program.tvdb
		
		if 'season' in tvdb[series.seriesName]['_banners']:
			if 'season' in tvdb[series.seriesName]['_banners']['season']:
				artworks = []
				for banner_id, banner_info in tvdb[series.seriesName]['_banners']['season']['season'].items():
					if banner_info['season'] == str(series.seasonNumber):
						artworks.append(banner_info['_bannerpath'])
		
		#check if we didn't find any artwork, if so do not continue
		if len(artworks) == 0:
			raise tvdb_attributenotfound
		#end if len(artworks) == 0
		
		if interactive:
			artworkCounter = 0
			print "\nList of available artwork"
			for artwork in artworks:
				print "%s. %s" % (artworkCounter, artwork)
				artworkCounter += 1
			#end for artwork
			
			#allow user to preview images
			print "Example of listing: 0 2 4"
			artworkPreviewRequestNumbers = raw_input("List Images to Preview: ")
			artworkPreviewRequests = artworkPreviewRequestNumbers.split()
			
			artworkPreviewUrls = []
			for artworkPreviewRequest in artworkPreviewRequests:
				artworkPreviewUrls.append(artworks[int(artworkPreviewRequest)])
			#end for artworkPreviewRequest
			openurl(artworkPreviewUrls)
			
			#ask user what artwork he wants to use
			artworkChoice = int(raw_input("Artwork to use: "))
		else:
			artworkChoice = 0
		#end if interactive
		
		artworkUrl = artworks[artworkChoice]
		
		(artworkUrl_base, artworkUrl_fileName) = os.path.split(artworkUrl)
		(artworkUrl_baseFileName, artworkUrl_fileNameExtension)=os.path.splitext(artworkUrl_fileName)
		
		artworkFileName = series.seriesName + " Season " + str(series.seasonNumber) + artworkUrl_fileNameExtension
		
		
		artworkFullFileName = cacheDir + "/" + artworkFileName
		
		if opts.verbose == 0:
			curlVerbosity ="-s"
		elif opts.verbose == 1:
			print "Downloaded Artwork: " + artworkFileName
			curlVerbosity ="-#"
		elif opts.verbose == 2:
			curlVerbosity ="-v"
		#end if verbose
		os.popen("curl %s -o \"%s\" \"%s\"" % (curlVerbosity, artworkFullFileName, artworkUrl))
		
		
		series.artworkFileName = artworkFullFileName
	except tvdb_attributenotfound:
		# The attribute wasn't found, not critical
		if opts.verbose:
			sys.stderr.write("!! Non-Critical Show Error: %s not found for %s\n" % ("artwork", series.seriesName))
		#end if verbose
#end artwork

def getShowSpecificInfo(verbose, tvdb, seriesName, attribute):
	"""docstring for getEpisodeSpecificInfo"""
	try:
		value = tvdb[seriesName][attribute]
		if not value:
			return ""
		#clean up string
		value =  value.replace('&quot;', "\\\"")
		return value
	except tvdb_error, errormsg:
		# Error communicating with thetvdb.com
		sys.stderr.write("!!!! Critical Show Error: Error contacting www.thetvdb.com:\n%s\n" % (errormsg))
		sys.exit(2)
	except tvdb_shownotfound:
		# No such series found.
		sys.stderr.write("!!!! Critical Show Error: Show %s not found\n" % (seriesName))
		sys.exit(2)
	except tvdb_seasonnotfound, errormsg:
		#the season name could not be found
		sys.stderr.write("!! Critical Show Error: The series name was not found for %s\n" % (seriesName))
		return 2
	except tvdb_attributenotfound, errormsg:
		# The attribute wasn't found, not critical
		if verbose:
			sys.stderr.write("!! Non-Critical Show Error: %s not found for %s\n" % (attribute, seriesName))
		#end if verbose
#end getEpisodeSpecificInfo

def getEpisodeSpecificInfo(verbose, program, series, episodeNumber, attribute):
	"""docstring for getEpisodeSpecificInfo"""
	try:
		value = program.tvdb[series.seriesName][series.seasonNumber][episodeNumber][attribute]
		if not value:
			return ""
		#clean up string
		value = value.replace('&quot;', "\\\"")
		value = value.replace('`', "'")
		return value
	except tvdb_episodenotfound:
		# The episode was not found wasn't found
		sys.stderr.write("!!!! Critical Episode Error: Episode name not found for %s - %02dx%02d\n" % (series.seriesName, series.seasonNumber, episodeNumber))
		sys.exit(2)
	except tvdb_error, errormsg:
		# Error communicating with thetvdb.com
		sys.stderr.write("!!!! Critical Episode Error: Error contacting www.thetvdb.com:\n%s\n" % (errormsg))
		sys.exit(2)
	except tvdb_attributenotfound:
		# The attribute wasn't found, not critical
		if verbose:
			sys.stderr.write("!! Non-Critical Episode Error: %s not found for %02dx%02d\n" % (attribute, series.seasonNumber, episodeNumber))
		#end if verbose
		return ""
#end getEpisodeSpecificInfo

def tvtags(opts, fullPath):
	
	if not whichBin("MP4Tagger"):
		print "MP4Tagger tools not found"
		sys.exit(0)
	
	(filePath, fileName) = os.path.split(fullPath)
	
	if not os.path.isfile(fullPath):
		sys.stderr.write("!!!! Critical Error:  file \"%s\" does not exist\n" % (fileName))
		sys.exit(2)
	#end if not os.path.isfile
	
	if len(filePath) == 0:
		filePath = "."
	
	m1 = re.match('(\w+).+[sS]([0-9]+)[eE]([0-9]+).+', fileName)
	m2 = re.match('(\w+).+([0-9]+)[xX]([0-9]+).+', fileName)
	if m1:
		(series, seasonNumber, episodeNumber) = m1.groups()
	elif m2:
		(series, seasonNumber, episodeNumber) = m2.groups()
	else :
		sys.stderr.write("!!!! Critical Error: file name \"%s\" is of incorrect format\nExample of file name: invasion.s01e02.hr.hdtv.xvid-nbs.m4v\n" % (fileName))
		sys.exit(2)
	
	if opts.verbose > 1:
		print ("analyse => serie: %s saison: %s episode: %s" % (series, seasonNumber,episodeNumber))
	#end if debug
	
	
	program = Program(opts, filePath, fileName)
	
	series = Series(opts, program, series, seasonNumber)
	
	#request user to select artwork
	artworkFileName = artwork(opts, opts.interactive, program, series)
	
	#check if the image we have needed resizing/dpi changed -> use this new temp file that was created for all the other episodes
	(imageFile, imageExtension) = os.path.splitext(series.artworkFileName)
	if series.artworkFileName.count("-resized-") == 0:
		for imageFileName in glob.glob("*" + imageExtension):
			if imageFileName.count("-resized-"):
				series.artworkFileName = imageFileName
				if opts.verbose:
					print "Using resized artwork file \"%s\"" % imageFileName
				#end if opts.verbose
				break
			#end if imageFileName.count
		#end for imageFileName
	#end if series.artworkFileName.count
	
	#create an episode which will populate it's fields using data from thetvdb
	episode = Episode(opts.verbose, program, series, seasonNumber, episodeNumber)
	
	
	if opts.rename:
		#fix the filename
		correctFileName(opts.verbose, program, series, episode)
	#end if opts.rename
	
	
	
	tagFile(opts, program, series, episode)

#end tvtags

def main():
	parser = OptionParser(usage="%prog [options] <path to video file(s)>\n%prog -h for full list of options")
	
	parser.add_option(  "-b", "--batch", action="store_false", dest="interactive", help="selects first search result, requires no human intervention once launched [default]")
	parser.add_option(  "-i", "--interactive", action="store_true", dest="interactive", help="interactivly select correct show from search results")
	parser.add_option(  "-d", "--debug", action="store_const", const=2, dest="verbose", help="shows all debugging info")
	parser.add_option(  "-v", "--verbose", action="store_const", const=1, dest="verbose", help="Will provide some feedback [default]")
	parser.add_option(  "-q", "--quiet", action="store_const", const=0, dest="verbose", help="For ninja-like processing")
	parser.add_option(  "-n", "--renaming", action="store_true", dest="rename", help="enable cleaning name")
	parser.set_defaults( interactive=False, verbose=1, rename=False  )
	
	opts, args = parser.parse_args()
	
	if len(args) == 0:
	    parser.error("No video file supplied")
	#end if len(args)
	
	for fullPath in args:
		tvtags(opts, fullPath)
#end main

if __name__ == '__main__':
		sys.exit(main())
#end if __name__