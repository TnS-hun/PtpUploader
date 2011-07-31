from MyGlobals import MyGlobals
from PtpUploaderException import PtpUploaderException
from Settings import Settings
from Tool.Unrar import Unrar

import fnmatch
import os

class ReleaseExtractorInternal:
	def __init__(self, sourcePath, destinationPath, topLevelDirectoriesToIgnore = [], handleSceneFolders = False):
		self.SourcePath = sourcePath
		self.DestinationPath = destinationPath
		self.TopLevelDirectoriesToIgnore = topLevelDirectoriesToIgnore
		self.HandleSceneFolders = handleSceneFolders
		self.DestinationPathCreated = False

	def __MakeDestinationDirectory(self):
		if not self.DestinationPathCreated:
			if os.path.exists( self.DestinationPath ):
				if not os.path.isdir( self.DestinationPath ):
					raise PtpUploaderException( "Can't make destination directory '%s' because path already exists." % self.DestinationPath )
			else:
				os.makedirs( self.DestinationPath )

			self.DestinationPathCreated = True

		return self.DestinationPath

	def Extract(self):
		# Extract RARs.
		rars = Unrar.GetRars( self.SourcePath )
		for rar in rars:
			if not Settings.IsFileOnIgnoreList( rar ):
				Unrar.Extract( rar, self.__MakeDestinationDirectory() )

		entries = os.listdir( self.SourcePath )
		for entryName in entries:
			entryPath = os.path.join( self.SourcePath, entryName )
			if os.path.isdir( entryPath ):
				self.__HandleDirectory( entryName, entryPath )
			elif os.path.isfile( entryPath ):
				self.__HandleFile( entryName, entryPath )
				
	def __IsDirectoryOnTheIgnoreList(self, directoryName):
		return directoryName in self.TopLevelDirectoriesToIgnore
		
	def __HandleDirectory(self, entryName, entryPath):
		entryLower = entryName.lower()
		if self.HandleSceneFolders and ( fnmatch.fnmatch( entryLower, "cd*" ) or entryLower == "sub" or entryLower == "subs" or entryLower == "subtitle" or entryLower == "subtitles" ):
			# Special scene folders in the root will be extracted without making a directory for them in the destination.
			releaseExtractor = ReleaseExtractorInternal( entryPath, self.DestinationPath )
			releaseExtractor.Extract()
		elif self.__IsDirectoryOnTheIgnoreList( entryLower ):
			# We don't need these.
			# (The if is nicer this way than combining this and the next block.)
			pass
		else:
			# Handle other directories normally.
			destinationDirectoryPath = os.path.join( self.DestinationPath, entryName )
			releaseExtractor = ReleaseExtractorInternal( entryPath, destinationDirectoryPath )
			releaseExtractor.Extract()

	def __HandleFile(self, entryName, entryPath):
		if Settings.IsFileOnIgnoreList( entryName ):
			return

		if ( not Settings.HasValidVideoExtensionToUpload( entryName ) ) and ( not Settings.HasValidAdditionalExtensionToUpload( entryName ) ):
		 	return

		# Make hard link from supported files.
		destinationFilePath = os.path.join( self.__MakeDestinationDirectory(), entryName )
		if os.path.exists( destinationFilePath ):
			raise PtpUploaderException( "Can't make link from file '%s' to '%s' because destination already exists." % ( entryPath, destinationFilePath ) )

		os.link( entryPath, destinationFilePath )		

class ReleaseExtractor:
	# Makes sure that path only contains supported extensions.
	# Returns with a tuple of list of the video files and the list of additional files.
	@staticmethod
	def ValidateDirectory(logger, path, throwExceptionForUnsupportedFiles = True):
		logger.info( "Validating directory '%s'." % path )
			
		videos = []
		additionalFiles = []
		for root, dirs, files in os.walk( path ):
			for file in files:
				filePath = os.path.join( root, file )
				if Settings.HasValidVideoExtensionToUpload( filePath ):
					videos.append( filePath )
				elif Settings.HasValidAdditionalExtensionToUpload( filePath ):
					additionalFiles.append( filePath )
				elif throwExceptionForUnsupportedFiles:
					raise PtpUploaderException( "File '%s' has unsupported extension." % filePath )

		return videos, additionalFiles

	# Extracts RAR files and creates hard links from supported files from the source to the destination directory.
	# Except of special scene folders (CD*, Subs) in the root, the directory hierarchy is kept.  
	@staticmethod
	def Extract( logger, sourcePath, destinationPath, topLevelDirectoriesToIgnore = [] ):
		logger.info( "Extracting directory '%s' to '%s'." % ( sourcePath, destinationPath ) )

		topLevelDirectoriesToIgnore.append( "proof" )
		topLevelDirectoriesToIgnore.append( "sample" )
		topLevelDirectoriesToIgnore.append( "!sample" ) # Used in ESiR releases.

		releaseExtractor = ReleaseExtractorInternal( sourcePath, destinationPath, topLevelDirectoriesToIgnore, handleSceneFolders = True )
		releaseExtractor.Extract()

		# Extract and delete RARs at the destination directory. Subtitles in scene releases usually are compressed twice. Yup, it is stupid.
		rars = Unrar.GetRars( destinationPath )
		for rar in rars:
			Unrar.Extract( rar, destinationPath )
			os.remove( rar )