from Job.JobRunningState import JobRunningState
from Job.JobStartMode import JobStartMode

from Database import Database
from PtpUploaderException import PtpUploaderException
from Settings import Settings

from sqlalchemy import Column, Integer, orm, String

import codecs
import os

class ReleaseInfo(Database.Base):
	__tablename__ = "release"

	Id = Column( Integer, primary_key = True )
	
	# Announcement
	AnnouncementSourceName = Column( String )
	AnnouncementId = Column( String )
	ReleaseName = Column( String )
	
	# For PTP
	Type = Column( String )
	ImdbId = Column( String )
	Directors = Column( String )
	Title = Column( String )
	Year = Column( String )
	Tags = Column( String )
	MovieDescription = Column( String )
	CoverArtUrl = Column( String )
	YouTubeId = Column( String )
	MetacriticUrl = Column( String )
	RottenTomatoesUrl = Column( String )
	Scene = Column( String )
	Quality = Column( String )
	Codec = Column( String )
	CodecOther = Column( String )
	Container = Column( String )
	ContainerOther = Column( String )
	ResolutionType = Column( String )
	Resolution = Column( String )
	Source = Column( String )
	SourceOther = Column( String )
	ReleaseDescription = Column( String )
	RemasterTitle = Column( String )
	RemasterYear = Column( String )

	# Other
	JobStartMode = Column( Integer )
	JobRunningState = Column( Integer )
	PtpId = Column( String )
	InternationalTitle = Column( String )
	Nfo = Column( String )
	SourceTorrentPath = Column( String )
	SourceTorrentInfoHash = Column( String )
	ReleaseUploadPath = Column( String )
	
	def __init__(self):
		self.AnnouncementSourceName = "" # A name of a class from the Source namespace.
		self.AnnouncementId = ""
		self.ReleaseName = ""

		# These are the required fields needed for an upload to PTP.
		self.Type = "Movies" # Movies, Musicals, Standup Comedy, Concerts
		self.ImdbId = "" # Just the number. Eg.: 0111161 for http://www.imdb.com/title/tt0111161/
		self.Directors = "" # Stored as a comma separated list. PTP needs this as a list, use GetDirectors.
		self.Title = "" # Eg.: El Secreto de Sus Ojos AKA The Secret in Their Eyes
		self.Year = ""
		self.Tags = ""
		self.MovieDescription = u""
		self.CoverArtUrl = ""
		self.YouTubeId = "" # Eg.: FbdOnGNBMAo for http://www.youtube.com/watch?v=FbdOnGNBMAo
		self.MetacriticUrl = ""
		self.RottenTomatoesUrl = ""
		self.Scene = "" # Empty string or "on" (wihout the quotes).
		self.Quality = "" # Other, Standard Definition, High Definition
		self.Codec = "" # Other, DivX, XviD, H.264, x264, DVD5, DVD9, BD25, BD50
		self.CodecOther = "" # Codec type when Codec is Other.
		self.Container = "" # Other, MPG, AVI, MP4, MKV, VOB IFO, ISO, m2ts
		self.ContainerOther = "" # Container type when Container is Other.
		self.ResolutionType = "" # Other, PAL, NTSC, 480p, 576p, 720p, 1080i, 1080p
		self.Resolution = "" # Exact resolution when ResolutionType is Other. 
		self.Source = "" # Other, CAM, TS, VHS, TV, DVD-Screener, TC, HDTV, R5, DVD, HD-DVD, Blu-ray
		self.SourceOther = "" # Source type when Source is Other.
		self.ReleaseDescription = u""
		self.RemasterTitle = "" # Eg.: Hardcoded English
		self.RemasterYear = ""
		# Till this.
		
		self.JobStartMode = JobStartMode.Automatic
		self.JobRunningState = JobRunningState.WaitingForStart
		self.PtpId = ""
		self.InternationalTitle = "" # International title of the movie. Eg.: The Secret in Their Eyes. Needed for renaming releases coming from Cinemageddon.
		self.Nfo = u""
		self.SourceTorrentPath = ""
		self.SourceTorrentInfoHash = ""
		self.ReleaseUploadPath = "" # Empty if using the default path. See GetReleaseUploadPath.
		
		self.MyConstructor()

	# "The SQLAlchemy ORM does not call __init__ when recreating objects from database rows."
	@orm.reconstructor
	def MyConstructor(self):
		self.AnnouncementSource = None # A class from the Source namespace.
		self.Logger = None

	def GetImdbId(self):
		return self.ImdbId

	def GetPtpId(self):
		return self.PtpId

	def HasImdbId(self):
		return len( self.ImdbId ) > 0

	def HasPtpId(self):
		return len( self.PtpId ) > 0

	def IsUserCreatedJob(self):
		return self.JobStartMode == JobStartMode.Manual or self.JobStartMode == JobStartMode.ManualForced

	def IsForceUpload(self):
		return self.JobStartMode == JobStartMode.ManualForced

	def IsCoverArtUrlSet(self):
		return len( self.CoverArtUrl ) > 0

	def IsReleaseNameSet(self):
		return len( self.ReleaseName ) > 0

	def IsCodecSet(self): 
		return len( self.Codec ) > 0

	def IsSourceSet(self): 
		return len( self.Source ) > 0

	def IsQualitySet(self): 
		return len( self.Quality ) > 0

	def IsResolutionTypeSet(self): 
		return len( self.ResolutionType ) > 0
	
	def IsSourceTorrentPathSet(self):
		return len( self.SourceTorrentPath ) > 0
	
	def GetDirectors(self):
		return self.Directors.split( ", " )
	
	def SetDirectors(self, list):
		for name in list:
			if name.find( "," ) != -1:
				raise PtpUploaderException( "Director name '%s' contains a comma." % name )
		
		self.Directors = ", ".join( list )
		
	def IsSceneRelease(self):
		return self.Scene == "on"

	def SetSceneRelease(self):
		self.Scene = "on"

	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	@staticmethod
	def GetReleaseRootPathFromRelaseName(releaseName):
		releasesPath = os.path.join( Settings.WorkingPath, "release" )
		return os.path.join( releasesPath, releaseName )
		
	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	def GetReleaseRootPath(self):
		return ReleaseInfo.GetReleaseRootPathFromRelaseName( self.ReleaseName )

	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/download/"
	@staticmethod
	def GetReleaseDownloadPathFromRelaseName(releaseName):
		return os.path.join( ReleaseInfo.GetReleaseRootPathFromRelaseName( releaseName ), "download" )

	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/download/"
	def GetReleaseDownloadPath(self):
		return ReleaseInfo.GetReleaseDownloadPathFromRelaseName( self.ReleaseName )
	
	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/upload/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	# It must contain the final release name because of mktorrent.
	def GetReleaseUploadPath(self):
		if len( self.ReleaseUploadPath ) > 0:
			return self.ReleaseUploadPath
		else:
			path = os.path.join( self.GetReleaseRootPath(), "upload" )
			return os.path.join( path, self.ReleaseName )

	def SetReleaseUploadPath(self, path):
		self.ReleaseUploadPath = path
	
	def IsStandardDefintion(self):
		return self.Quality == "Standard Definition"
	
	# Fills container, codec and resolution from media info.
	def GetDataFromMediaInfo(self, mediaInfo):
		if mediaInfo.IsAvi():
			self.Container = "AVI"
		elif mediaInfo.IsMkv():
			self.Container = "MKV"
		else:
			raise PtpUploaderException( "Unsupported container: '%s'." % mediaInfo.Container )

		# TODO: check if set already and make sure it remains the same if it set
		if mediaInfo.IsX264():
			self.Codec = "x264"
			if mediaInfo.IsAvi():
				raise PtpUploaderException( "X264 in AVI is not allowed." )
		elif mediaInfo.IsXvid():
			self.Codec = "XviD"
			if mediaInfo.IsMkv():
				raise PtpUploaderException( "XviD in MKV is not allowed." )
		elif mediaInfo.IsDivx():
			self.Codec = "DivX"
			if mediaInfo.IsMkv():
				raise PtpUploaderException( "DivX in MKV is not allowed." )
		else:
			raise PtpUploaderException( "Unsupported codec: '%s'." % mediaInfo.Codec )

		# Indicate the exact resolution for standard definition releases.
		if self.IsStandardDefintion():
			self.Resolution = "%sx%s" % ( mediaInfo.Width, mediaInfo.Height )
		
	# releaseDescriptionFilePath: optional. If given the description is written to file.
	def FormatReleaseDescription(self, logger, releaseInfo, screenshots, scaleSize, mediaInfos, includeReleaseName = True, releaseDescriptionFilePath = None):
		logger.info( "Making release description for release '%s' with screenshots at %s." % ( releaseInfo.ReleaseName, screenshots ) )

		if includeReleaseName:
			self.ReleaseDescription = u"[size=4][b]%s[/b][/size]\n\n" % releaseInfo.ReleaseName
		else:
			self.ReleaseDescription = u""

		if scaleSize is not None:
			self.ReleaseDescription += u"Screenshots are showing the display aspect ratio. Resolution: %s.\n\n" % scaleSize 

		for screenshot in screenshots:
			self.ReleaseDescription += u"[img=%s]\n\n" % screenshot

		for mediaInfo in mediaInfos:
			# Add file name before each media info if there are more than one videos in the release.
			if len( mediaInfos ) > 1:
				fileName = os.path.basename( mediaInfo.Path )
				self.ReleaseDescription += u"[size=3][u]%s[/u][/size]\n\n" % fileName

			self.ReleaseDescription += mediaInfo.FormattedMediaInfo

		# Add NFO if presents
		if len( releaseInfo.Nfo ) > 0:
			self.ReleaseDescription += u"[size=3][u]NFO[/u][/size]:[pre]\n%s\n[/pre]" % releaseInfo.Nfo

		# We don't use this file for anything, we just save it for convenience.
		if releaseDescriptionFilePath is not None:
			releaseDescriptionFile = codecs.open( releaseDescriptionFilePath, encoding = "utf-8", mode = "w" )
			releaseDescriptionFile.write( self.ReleaseDescription )
			releaseDescriptionFile.close()