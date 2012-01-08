from Tool.MediaInfo import MediaInfo
from Tool.ScreenshotMaker import ScreenshotMaker

from PtpUploaderException import *
from ScreenshotList import ScreenshotList
from Settings import Settings

import os

class ReleaseDescriptionVideoEntry:
	def __init__(self, mediaInfo, numberOfScreenshotsToTake = 5):
		self.MediaInfo = mediaInfo
		self.NumberOfScreenshotsToTake = numberOfScreenshotsToTake
		self.Screenshots = []
		self.ScaleSize = None
		
	def HaveScreenshots(self):
		return len( self.Screenshots ) > 0

	def ToReleaseDescription(self):
		releaseDescription = u""

		if self.HaveScreenshots():
			if self.ScaleSize is not None:
				releaseDescription += u"Showing the display aspect ratio. Resolution: %s.\n\n" % self.ScaleSize

			for screenshot in self.Screenshots:
				releaseDescription += u"[img=%s]\n\n" % screenshot

		releaseDescription += self.MediaInfo.FormattedMediaInfo
		return releaseDescription

class ReleaseDescriptionFormatter:
	def __init__(self, releaseInfo, videoFiles, additionalFiles, outputImageDirectory, makeScreenshots = True):
		self.ReleaseInfo = releaseInfo
		self.VideoFiles = videoFiles
		self.AdditionalFiles = additionalFiles
		self.OutputImageDirectory = outputImageDirectory
		self.MakeScreenshots = makeScreenshots
		self.VideoEntries = []
		self.MainMediaInfo = None
		
		self.__GetMediaInfo()
		self.__TakeAndUploadScreenshots()
	
	def __GetMediaInfoHandleDvdImage(self):
			# Get all IFOs.
			ifos = []
			for file in self.AdditionalFiles:
				if file.lower().endswith( ".ifo" ):
					mediaInfo = MediaInfo( self.ReleaseInfo.Logger, file, self.ReleaseInfo.GetReleaseUploadPath() )
					ifos.append( mediaInfo )
			
			# Sort them by duration.
			sortedIfos = []
			for ifo in ifos:
				item = ifo.DurationInSec, ifo # Add as a tuple.
				sortedIfos.append( item )
	
			sortedIfos.sort( reverse = True )

			# Use the longest.
			ifo = sortedIfos[ 0 ][ 1 ]
			if ifo.DurationInSec <= 0:
				raise PtpUploaderException( "None of the IFOs have duration. MediaInfo is probably too old." )

			ifoPathLower = ifo.Path.lower()
			if not ifoPathLower.endswith( "_0.ifo" ):
				raise PtpUploaderException( "Unsupported VIDEO_TS layout. The longest IFO is '%s' with duration '%'." % ( ifo.Path, ifo.DurationInSec ) )
			
			# Get the next VOB.
			# (This could be a simple replace but Linux's filesystem is case-sensitive...)
			vobPath = None
			ifoPathLower = ifoPathLower.replace( "_0.ifo", "_1.vob" )
			for file in self.VideoFiles:
				if file.lower() == ifoPathLower:
					vobPath = file
					break

			if vobPath is None:
				raise PtpUploaderException( "Unsupported VIDEO_TS layout. Can't find the next VOB for IFO '%s'." % ifo.Path )

			vobMediaInfo = MediaInfo( self.ReleaseInfo.Logger, vobPath, self.ReleaseInfo.GetReleaseUploadPath() )
			self.MainMediaInfo = vobMediaInfo
			self.VideoEntries.append( ReleaseDescriptionVideoEntry( ifo, numberOfScreenshotsToTake = 0 ) )
			self.VideoEntries.append( ReleaseDescriptionVideoEntry( vobMediaInfo ) )

	def __GetMediaInfoHandleNonDvdImage(self):
		self.VideoFiles = ScreenshotMaker.SortVideoFiles( self.VideoFiles )
		mediaInfos = MediaInfo.ReadAndParseMediaInfos( self.ReleaseInfo.Logger, self.VideoFiles, self.ReleaseInfo.GetReleaseUploadPath() )
		self.MainMediaInfo = mediaInfos[ 0 ]
		
		for i in range( len( mediaInfos ) ):
			# The most common special release ("Not main movie") is Extras.
			# We take screenshots for all videos in extras because they might be totally different content (trailers, interviews, etc.).
			if i == 0 or self.ReleaseInfo.IsSpecialRelease():
				self.VideoEntries.append( ReleaseDescriptionVideoEntry( mediaInfos[ i ] ) )
			else:
				numberOfScreenshotsToTake = 0
				if Settings.TakeScreenshotOfAdditionalFiles:
					numberOfScreenshotsToTake = 1

				self.VideoEntries.append( ReleaseDescriptionVideoEntry( mediaInfos[ i ], numberOfScreenshotsToTake ) )

	def __GetMediaInfo(self):
		if self.ReleaseInfo.IsDvdImage():
			self.__GetMediaInfoHandleDvdImage()
		else:
			self.__GetMediaInfoHandleNonDvdImage()

	def __TakeAndUploadScreenshotsForEntry(self, screenshotList, videoEntry):
		if videoEntry.NumberOfScreenshotsToTake <= 0:
			return

		screenshotMaker = ScreenshotMaker( self.ReleaseInfo.Logger, videoEntry.MediaInfo.Path )
		videoEntry.ScaleSize = screenshotMaker.GetScaleSize()

		screenshots = screenshotList.GetScreenshotsByName( videoEntry.MediaInfo.Path )
		if screenshots is None:
			takeSingleScreenshot = videoEntry.NumberOfScreenshotsToTake == 1
			screenshots = screenshotMaker.TakeAndUploadScreenshots( self.OutputImageDirectory, videoEntry.MediaInfo.DurationInSec, takeSingleScreenshot )
			screenshotList.SetScreenshots( videoEntry.MediaInfo.Path, screenshots )

		videoEntry.Screenshots = screenshots

	def __TakeAndUploadScreenshots(self):
		if not self.MakeScreenshots:
			return

		screenshotList = ScreenshotList()
		screenshotList.LoadFromString( self.ReleaseInfo.Screenshots )

		for videoEntry in self.VideoEntries:
			self.__TakeAndUploadScreenshotsForEntry( screenshotList, videoEntry )

		self.ReleaseInfo.Screenshots = screenshotList.GetAsString()

	def Format(self, includeReleaseName):
		self.ReleaseInfo.Logger.info( "Making release description" )
		releaseDescription = u""

		if includeReleaseName:
			releaseDescription = u"[size=4][b]%s[/b][/size]\n\n" % self.ReleaseInfo.ReleaseName

		if len( self.ReleaseInfo.ReleaseNotes ) > 0:
			releaseDescription += u"%s\n\n" % self.ReleaseInfo.ReleaseNotes

		# Add NFO if presents
		if len( self.ReleaseInfo.Nfo ) > 0:
			releaseDescription += u"[hide=NFO][pre]%s[/pre][/hide]\n\n" % self.ReleaseInfo.Nfo

		for i in range( len( self.VideoEntries ) ):
			entry = self.VideoEntries[ i ]

			if i > 0:
				releaseDescription += "\n\n"

			releaseDescription += entry.ToReleaseDescription()

		return releaseDescription
	
	def GetMainMediaInfo(self):
		return self.MainMediaInfo
