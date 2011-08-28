from Tool.MakeTorrent import MakeTorrent
from Tool.Rtorrent import Rtorrent

from IncludedFileList import IncludedFileList
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import *
from ReleaseDescriptionFormatter import ReleaseDescriptionFormatter
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from Settings import Settings

import codecs
import os
import sys

class ReleaseInfoMaker:
	def __init__(self, path):
		self.Path = path
		self.ReleaseName = None
		self.WorkingDirectory = None
		self.TorrentDataPath = None
		self.VideoFiles = []
		self.AdditionalFiles = []
		self.Nfo = u""

	def CollectVideoFiles(self):
		self.Path = os.path.abspath( self.Path )
		
		if os.path.isdir( self.Path ):
			# Make sure that path doesn't ends with a trailing slash or else os.path.split would return with wrong values.
			self.Path = self.Path.rstrip( "\\/" )

			includedFileList = IncludedFileList()
			self.VideoFiles, self.AdditionalFiles = ReleaseExtractor.ValidateDirectory( MyGlobals.Logger, self.Path, includedFileList, throwExceptionForUnsupportedFiles = False )
			if len( self.VideoFiles ) <= 0:
				print "Path '%s' doesn't contains any videos!" % self.Path
				return False

			# We use the parent directory of the path as the working directory.
			# Release name will be the directory's name. Eg. it will be "anything" for "/something/anything"
			self.WorkingDirectory, self.ReleaseName = os.path.split( self.Path )
			self.TorrentDataPath = self.Path
			
			self.Nfo = NfoParser.FindAndReadNfoFileToUnicode( self.TorrentDataPath )
		elif os.path.isfile( self.Path ):
			self.VideoFiles.append( self.Path )
			
			# We use same the directory where the file is as the working directory.
			# Release name will be the file's name without extension.
			self.WorkingDirectory, self.ReleaseName = os.path.split( self.Path )
			self.ReleaseName, extension = os.path.splitext( self.ReleaseName )
			self.TorrentDataPath = self.WorkingDirectory
			
			# Try to read the NFO.
			nfoPath = self.ReleaseName + ".nfo"
			if os.path.isfile( nfoPath ):
				self.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath )
		else:
			print "Path '%s' doesn't exists!" % self.Path
			return False

		return True

	def MarkAsDvdImageIfNeeded(self, releaseInfo):
		for file in self.AdditionalFiles:
			if file.lower().endswith( ".ifo" ):
				releaseInfo.Codec = "DVD5"
				# Make sure that ReleaseDescriptionFormatter will recognize this as a DVD image.
				if not releaseInfo.IsDvdImage():
					raise PtpUploaderException( "Codec is set to DVD5, yet release info says that this is not a DVD image." )
				
				return

	def SaveReleaseDescripionFile(self, logger, releaseDescriptionFilePath, createScreens):
		releaseInfo = ReleaseInfo()
		releaseInfo.Logger = logger
		releaseInfo.ReleaseName = self.ReleaseName
		releaseInfo.ReleaseUploadPath = self.TorrentDataPath
		releaseInfo.Nfo = self.Nfo
		self.MarkAsDvdImageIfNeeded( releaseInfo )

		outputImageDirectory = self.WorkingDirectory
		releaseDescriptionFormatter = ReleaseDescriptionFormatter( releaseInfo, self.VideoFiles, self.AdditionalFiles, outputImageDirectory, createScreens )
		releaseDescription = releaseDescriptionFormatter.Format( includeReleaseName = True )

		releaseDescriptionFile = codecs.open( releaseDescriptionFilePath, encoding = "utf-8", mode = "w" )
		releaseDescriptionFile.write( releaseDescription )
		releaseDescriptionFile.close()

	def MakeReleaseInfo(self, createTorrent = True, createScreens = True):
		logger = MyGlobals.Logger
		
		if not self.CollectVideoFiles():
			return
		
		# Make sure the files we are generating are not present.

		releaseDescriptionFilePath = os.path.join( self.WorkingDirectory, "release description.txt" )
		if os.path.exists( releaseDescriptionFilePath ):
			print "Can't create release description because '%s' already exists!" % releaseDescriptionFilePath
			return

		torrentName = "PTP " + self.ReleaseName + ".torrent";
		torrentPath = os.path.join( self.WorkingDirectory, torrentName );
		if createTorrent and os.path.exists( torrentPath ):
			print "Can't create torrent because '%s' already exists!" % torrentPath
			return

		# Save the release description.
		self.SaveReleaseDescripionFile( logger, releaseDescriptionFilePath, createScreens )

		# Create the torrent
		if createTorrent:
			MakeTorrent.Make( logger, self.Path, torrentPath )
			rtorrent = Rtorrent()
			rtorrent.AddTorrentSkipHashCheck( logger, torrentPath, self.TorrentDataPath )

def Main(argv):
	print "PtpUploader Release Description Maker by TnS"
	
	if len( argv ) <= 1:
		print "Usage:"
		print "\"ReleaseInfoMaker.py <target directory or filename>\" creates the release description and starts seeding the torrent."
		print "\"ReleaseInfoMaker.py --notorrent <target directory or filename>\" creates the release description."
		print "\"ReleaseInfoMaker.py --noscreens <target directory or filename>\" creates the release description without screens and starts seeding the torrent."
		return

	print ""

	Settings.LoadSettings()
	MyGlobals.InitializeGlobals( Settings.WorkingPath )

	if len( argv ) == 2:
		releaseInfoMaker = ReleaseInfoMaker( argv[ 1 ] )
		releaseInfoMaker.MakeReleaseInfo()
	elif len( argv ) == 3 and argv[ 1 ] == "--notorrent":
		releaseInfoMaker = ReleaseInfoMaker( argv[ 2 ] )
		releaseInfoMaker.MakeReleaseInfo( createTorrent = False )
	elif len( argv ) == 3 and argv[ 1 ] == "--noscreens":
		releaseInfoMaker = ReleaseInfoMaker( argv[ 2 ] )
		releaseInfoMaker.MakeReleaseInfo( createScreens = False )

if __name__ == '__main__':
	Main( sys.argv )