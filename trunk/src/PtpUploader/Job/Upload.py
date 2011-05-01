from Job.FinishedJobPhase import FinishedJobPhase
from Job.JobRunningState import JobRunningState
from Job.WorkerBase import WorkerBase
from Tool.MakeTorrent import MakeTorrent
from Tool.MediaInfo import MediaInfo
from Tool.ScreenshotMaker import ScreenshotMaker

from Database import Database
from ImageUploader import ImageUploader
from Ptp import Ptp
from PtpUploaderException import *
from ReleaseDescriptionFormatter import ReleaseDescriptionFormatter
from ReleaseExtractor import ReleaseExtractor
from Settings import Settings

import os
import subprocess

class Upload(WorkerBase):
	def __init__(self, jobManager, jobManagerItem, rtorrent):
		phases = [
			self.__CreateUploadPath,
			self.__ExtractRelease,
			self.__ValidateExtractedRelease,
			self.__GetMediaInfo,
			self.__TakeAndUploadScreenshots,
			self.__MakeReleaseDescription,
			self.__MakeTorrent,
			self.__CheckIfExistsOnPtp,
			self.__RehostPoster,
			self.__StartTorrent,
			self.__UploadMovie,
			self.__ExecuteCommandOnSuccessfulUpload ]

		WorkerBase.__init__( self, phases, jobManager, jobManagerItem )
		
		self.Rtorrent = rtorrent
		self.VideoFiles = []
		self.AdditionalFiles = []
		self.MediaInfos = []
		self.ScreenshotMediaInfo = None
		self.ScaleSize = ""
		self.ReleaseDescription = u""

	def __CreateUploadPath(self):
		if self.ReleaseInfo.IsJobPhaseFinished( FinishedJobPhase.Upload_CreateUploadPath ):
			self.ReleaseInfo.Logger.info( "Upload path creation phase has been reached previously, not creating it again." )
			return

		uploadPath = self.ReleaseInfo.GetReleaseUploadPath()
		customUploadPath = self.ReleaseInfo.AnnouncementSource.GetCustomUploadPath( self.ReleaseInfo.Logger, self.ReleaseInfo )
		if len( customUploadPath ) > 0:
			uploadPath = customUploadPath

		self.ReleaseInfo.Logger.info( "Creating upload path at '%s'." % uploadPath )
		
		if os.path.exists( uploadPath ):
			raise PtpUploaderException( "Upload directory '%s' already exists." % uploadPath )	
		
		os.makedirs( uploadPath )

		if len( customUploadPath ) > 0:
			self.ReleaseInfo.SetReleaseUploadPath( customUploadPath )
		self.ReleaseInfo.SetJobPhaseFinished( FinishedJobPhase.Upload_CreateUploadPath )
		Database.DbSession.commit()

	def __ExtractRelease(self):
		if self.ReleaseInfo.IsJobPhaseFinished( FinishedJobPhase.Upload_ExtractRelease ):
			self.ReleaseInfo.Logger.info( "Extract release phase has been reached previously, not extracting release again." )
			return
		
		self.ReleaseInfo.AnnouncementSource.ExtractRelease( self.ReleaseInfo.Logger, self.ReleaseInfo )

		self.ReleaseInfo.SetJobPhaseFinished( FinishedJobPhase.Upload_ExtractRelease )
		Database.DbSession.commit()

	def __ValidateExtractedRelease(self):
		self.VideoFiles, self.AdditionalFiles = ReleaseExtractor.ValidateDirectory( self.ReleaseInfo.Logger, self.ReleaseInfo.GetReleaseUploadPath() )
		if len( self.VideoFiles ) < 1:
			raise PtpUploaderException( "Upload path '%s' doesn't contains any video files." % self.ReleaseInfo.GetReleaseUploadPath() )

	def __GetMediaInfoContainer(self, mediaInfo):
		container = ""

		if mediaInfo.IsAvi():
			container = "AVI"
		elif mediaInfo.IsMkv():
			container = "MKV"
		elif mediaInfo.IsVob():
			container = "VOB IFO"
		
		if self.ReleaseInfo.IsContainerSet():
			if container != self.ReleaseInfo.Container:
				if self.ReleaseInfo.IsForceUpload():
					self.ReleaseInfo.Logger.info( "Container is set to '%s', detected MediaInfo container is '%s' ('%s'). Ignoring mismatch because of force upload." % ( self.ReleaseInfo.Container, container, mediaInfo.Container ) )
				else:
					raise PtpUploaderException( "Container is set to '%s', detected MediaInfo container is '%s' ('%s')." % ( self.ReleaseInfo.Container, container, mediaInfo.Container ) )
		else:
			if len( container ) > 0:
				self.ReleaseInfo.Container = container
			else:
				raise PtpUploaderException( "Unsupported container: '%s'." % mediaInfo.Container )

	def __GetMediaInfoCodec(self, mediaInfo):
		codec = ""

		if mediaInfo.IsX264():
			codec = "x264"
			if mediaInfo.IsAvi():
				raise PtpUploaderException( "X264 in AVI is not allowed." )
		elif mediaInfo.IsXvid():
			codec = "XviD"
			if mediaInfo.IsMkv():
				raise PtpUploaderException( "XviD in MKV is not allowed." )
		elif mediaInfo.IsDivx():
			codec = "DivX"
			if mediaInfo.IsMkv():
				raise PtpUploaderException( "DivX in MKV is not allowed." )
		elif self.ReleaseInfo.IsDvdImage():
			# Codec type DVD5 and DVD9 can't be figured out from MediaInfo.
			codec = self.ReleaseInfo.Codec

		if self.ReleaseInfo.IsCodecSet():
			if codec != self.ReleaseInfo.Codec:
				if self.ReleaseInfo.IsForceUpload():
					self.ReleaseInfo.Logger.info( "Codec is set to '%s', detected MediaInfo codec is '%s' ('%s'). Ignoring mismatch because of force upload." % ( self.ReleaseInfo.Codec, codec, mediaInfo.Codec ) )
				else:
					raise PtpUploaderException( "Codec is set to '%s', detected MediaInfo codec is '%s' ('%s')." % ( self.ReleaseInfo.Codec, codec, mediaInfo.Codec ) )
		else:
			if len( codec ) > 0:
				self.ReleaseInfo.Codec = codec
			else:
				raise PtpUploaderException( "Unsupported codec: '%s'." % mediaInfo.Codec )

	def __GetMediaInfoResolution(self, mediaInfo):
		resolution = ""

		# Indicate the exact resolution for standard definition releases.
		# It is not needed for DVD images.
		if self.ReleaseInfo.IsStandardDefinition() and ( not self.ReleaseInfo.IsDvdImage() ):
			resolution = "%sx%s" % ( mediaInfo.Width, mediaInfo.Height )
			
		if len( self.ReleaseInfo.Resolution ) > 0:
			if resolution != self.ReleaseInfo.Resolution:
				if self.ReleaseInfo.IsForceUpload():
					self.ReleaseInfo.Logger.info( "Resolution is set to '%s', detected MediaInfo resolution is '%s' ('%sx%s'). Ignoring mismatch because of force upload." % ( self.ReleaseInfo.Resolution, resolution, mediaInfo.Width, mediaInfo.Height ) )
				else:
					raise PtpUploaderException( "Resolution is set to '%s', detected MediaInfo resolution is '%s' ('%sx%s')." % ( self.ReleaseInfo.Resolution, resolution, mediaInfo.Width, mediaInfo.Height ) )
		else:
			self.ReleaseInfo.Resolution = resolution

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
			ifoPathLower = ifo.Path.lower()
			if not ifoPathLower.endswith( "_0.ifo" ):
				raise PtpUploaderException( "Unsupported VIDEO_TS layout. The longest IFO is: '%s'." % ifo.Path )
			
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
			self.MediaInfos = [ ifo, vobMediaInfo ]
			self.ScreenshotMediaInfo = vobMediaInfo

	def __GetMediaInfo(self):
		if self.ReleaseInfo.IsDvdImage():
			self.__GetMediaInfoHandleDvdImage()
		else:
			self.VideoFiles = ScreenshotMaker.SortVideoFiles( self.VideoFiles )
			self.MediaInfos = MediaInfo.ReadAndParseMediaInfos( self.ReleaseInfo.Logger, self.VideoFiles, self.ReleaseInfo.GetReleaseUploadPath() )
			self.ScreenshotMediaInfo = self.MediaInfos[ 0 ] 
		
		self.__GetMediaInfoContainer( self.ScreenshotMediaInfo )
		self.__GetMediaInfoCodec( self.ScreenshotMediaInfo )
		self.__GetMediaInfoResolution( self.ScreenshotMediaInfo )

	def __TakeAndUploadScreenshots(self):
		screenshotPathWithoutExtension = os.path.join( self.ReleaseInfo.GetReleaseRootPath(), "screenshot" )
		screenshotMaker = ScreenshotMaker( self.ReleaseInfo.Logger, self.ScreenshotMediaInfo.Path )
		self.ScaleSize = screenshotMaker.ScaleSize

		if len( self.ReleaseInfo.Screenshots ) > 0:
			self.ReleaseInfo.Logger.info( "Screenshots are set, not making new ones." )			
		else:
			screens = screenshotMaker.TakeAndUploadScreenshots( screenshotPathWithoutExtension, self.ScreenshotMediaInfo.DurationInSec )
			self.ReleaseInfo.SetScreenshotList( screens )

	def __MakeReleaseDescription(self):
		releaseDescriptionFilePath = os.path.join( self.ReleaseInfo.GetReleaseRootPath(), "release description.txt" )
		includeReleaseName = self.ReleaseInfo.AnnouncementSource.IncludeReleaseNameInReleaseDescription()
		self.ReleaseDescription = ReleaseDescriptionFormatter.Format( self.ReleaseInfo, self.ScaleSize, self.MediaInfos, includeReleaseName )

	def __MakeTorrent(self):
		if len( self.ReleaseInfo.UploadTorrentFilePath ) > 0:
			self.ReleaseInfo.Logger.info( "Upload torrent file path is set, not making torrent again." )
			return
		
		# We save it into a separate folder to make sure it won't end up in the upload somehow. :)
		uploadTorrentName = "PTP " + self.ReleaseInfo.ReleaseName + ".torrent"
		uploadTorrentFilePath = os.path.join( self.ReleaseInfo.GetReleaseRootPath(), uploadTorrentName )

		# Make torrent with the parent directory's name included if there is more than one file or requested by the source (it is a scene release).
		totalFileCount = len( self.VideoFiles ) + len( self.AdditionalFiles )
		if totalFileCount > 1 or ( self.ReleaseInfo.AnnouncementSource.IsSingleFileTorrentNeedsDirectory() and not self.ReleaseInfo.IsForceDirectorylessSingleFileTorrent() ):
			MakeTorrent.Make( self.ReleaseInfo.Logger, self.ReleaseInfo.GetReleaseUploadPath(), uploadTorrentFilePath )
		else: # Create the torrent including only the single video file.
			MakeTorrent.Make( self.ReleaseInfo.Logger, self.ScreenshotMediaInfo.Path, uploadTorrentFilePath )
			
		# Local variable is used temporarily to make sure that UploadTorrentFilePath is only gets stored in the database if MakeTorrent.Make succeeded.
		self.ReleaseInfo.UploadTorrentFilePath = uploadTorrentFilePath
		Database.DbSession.commit()

	def __CheckIfExistsOnPtp(self):
		# TODO: this is temporary here. We should support it everywhere.
		# If we are not logged in here that could mean that the download took a lot of time and the user got logged out for some reason. 
		Ptp.Login()

		# This could be before the Ptp.Login() line, but this way we can hopefully avoid some logging out errors.
		if self.ReleaseInfo.IsZeroImdbId():
			self.ReleaseInfo.Logger.info( "IMDb ID is set zero, ignoring the check for existing release." )
			return

		movieOnPtpResult = None

		if self.ReleaseInfo.HasPtpId():
			# If we already got the PTP id then we only need the existing formats if this is not a forced upload.
			if not self.ReleaseInfo.IsForceUpload():
				movieOnPtpResult = Ptp.GetMoviePageOnPtp( self.ReleaseInfo.Logger, self.ReleaseInfo.GetPtpId() )
		else:
			movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )
			self.ReleaseInfo.PtpId = movieOnPtpResult.PtpId
		
		if not self.ReleaseInfo.IsForceUpload():
			# If this is not a forced upload then we have to check (again) if is it already on PTP.
			existingRelease = movieOnPtpResult.IsReleaseExists( self.ReleaseInfo )
			if existingRelease is not None:
				raise PtpUploaderException( JobRunningState.DownloadedAlreadyExists, "Got uploaded to PTP while we were working on it. Skipping upload because of format '%s'." % existingRelease )

	def __RehostPoster(self):
		# If this movie has no page yet on PTP then we will need the cover, so we rehost the image to an image hoster.
		if self.ReleaseInfo.HasPtpId() or ( not self.ReleaseInfo.IsCoverArtUrlSet() ):
			return

		# Rehost the image only if not already on an image hoster.
		url = self.ReleaseInfo.CoverArtUrl
		if url.find( "ptpimg.me" ) != -1 or url.find( "imageshack.us" ) != -1 or url.find( "photobucket.com" ) != -1:
			return

		self.ReleaseInfo.CoverArtUrl = ImageUploader.Upload( self.ReleaseInfo.Logger, imageUrl = url )

	def __StartTorrent(self):
		if len( self.ReleaseInfo.UploadTorrentInfoHash ) > 0:
			self.ReleaseInfo.Logger.info( "Upload torrent info hash is set, not starting torrent again." )
			return
		
		# Add torrent without hash checking.
		self.ReleaseInfo.UploadTorrentInfoHash = self.Rtorrent.AddTorrentSkipHashCheck( self.ReleaseInfo.Logger, self.ReleaseInfo.UploadTorrentFilePath, self.ReleaseInfo.GetReleaseUploadPath() )
		Database.DbSession.commit()

	def __UploadMovie(self):
		# This is not possible because finished jobs can't be restarted.
		if self.ReleaseInfo.IsJobPhaseFinished( FinishedJobPhase.Upload_UploadMovie ):
			self.ReleaseInfo.Logger.info( "Upload movie phase has been reached previously, not uploading it again." )
			return

		Ptp.UploadMovie( self.ReleaseInfo.Logger, self.ReleaseInfo, self.ReleaseInfo.UploadTorrentFilePath, self.ReleaseDescription )
		self.ReleaseInfo.Logger.info( "'%s' has been successfully uploaded to PTP." % self.ReleaseInfo.ReleaseName )

		self.ReleaseInfo.SetJobPhaseFinished( FinishedJobPhase.Upload_UploadMovie )
		self.ReleaseInfo.JobRunningState = JobRunningState.Finished
		Database.DbSession.commit()

	def __ExecuteCommandOnSuccessfulUpload(self):
		# Execute command on successful upload.
		if len( Settings.OnSuccessfulUpload ) <= 0:
			return

		uploadedTorrentUrl = "http://passthepopcorn.me/torrents.php?id=" + self.ReleaseInfo.PtpId
		command = Settings.OnSuccessfulUpload % { "releaseName": self.ReleaseInfo.ReleaseName, "uploadedTorrentUrl": uploadedTorrentUrl }
		
		# We don't care if this fails. Our upload is complete anyway. :)
		try: 
			subprocess.Popen( command, shell = True )
		except ( KeyboardInterrupt, SystemExit ):
			raise
		except Exception, e:
			logger.exception( "Got exception while trying to run command '%s' after successful upload." % command )