from InformationSource.Imdb import Imdb
from InformationSource.MoviePoster import MoviePoster
from Job.FinishedJobPhase import FinishedJobPhase
from Job.JobRunningState import JobRunningState
from Job.WorkerBase import WorkerBase

from Database import Database
from Ptp import Ptp
from PtpImdbInfo import PtpImdbInfo, PtpZeroImdbInfo
from PtpUploaderException import *

import os

class CheckAnnouncement(WorkerBase):
	def __init__(self, jobManager, jobManagerItem, rtorrent):
		phases = [
			self.__PrepareDownload,
			self.__ValidateReleaseInfo,
			self.__CheckIfExistsOnPtp,
			self.__FillOutDetailsForNewMovieByPtpApi,
			self.__FillOutDetailsForNewMovieByExternalSources ]

		# Instead of this if, it would be possible to make a totally generic downloader system through SourceBase.
		if jobManagerItem.ReleaseInfo.AnnouncementSourceName == "file":
			phases.append( self.__AddToPendingDownloads )
		else:
			phases.extend( [
				self.__CreateReleaseDirectory,
				self.__DownloadTorrentFile,
				self.__DownloadTorrent,
				self.__AddToPendingDownloads ] )

		WorkerBase.__init__( self, phases, jobManager, jobManagerItem )
		self.Rtorrent = rtorrent

	def __PrepareDownload(self):
		self.ReleaseInfo.Logger.info( "Working on announcement from '%s' with id '%s' and name '%s'." % ( self.ReleaseInfo.AnnouncementSource.Name, self.ReleaseInfo.AnnouncementId, self.ReleaseInfo.ReleaseName ) )
		
		self.ReleaseInfo.JobRunningState = JobRunningState.InProgress
		self.ReleaseInfo.ErrorMessage = ""
		
		self.ReleaseInfo.AnnouncementSource.PrepareDownload( self.ReleaseInfo.Logger, self.ReleaseInfo )

	def __ValidateReleaseInfo(self):
		# Make sure we have IMDb or PTP id.
		if ( not self.ReleaseInfo.HasImdbId() ) and ( not self.ReleaseInfo.HasPtpId() ):
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "IMDb or PTP id must be specified." )
	
		# Make sure the source is providing a name.
		self.ReleaseInfo.ReleaseName = self.ReleaseInfo.ReleaseName.strip()
		if len( self.ReleaseInfo.ReleaseName ) <= 0:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Name of the release is not specified." )

		# Make sure the source is providing release quality information.
		if len( self.ReleaseInfo.Quality ) <= 0:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Quality of the release is not specified." )

		# Make sure the source is providing release source information.
		if len( self.ReleaseInfo.Source ) <= 0:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Source of the release is not specified." )

		# Make sure the source is providing release codec information.
		if len( self.ReleaseInfo.Codec ) <= 0:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Codec of the release is not specified." )

		# Make sure the source is providing release resolution type information.
		if len( self.ReleaseInfo.ResolutionType ) <= 0:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Resolution type of the release is not specified." )

		# HD XviDs are not allowed.
		if self.ReleaseInfo.Quality == "High Definition" and ( self.ReleaseInfo.Codec == "XviD" or self.ReleaseInfo.Codec == "DivX" ):
			raise PtpUploaderException( JobRunningState.Ignored_Forbidden, "Forbidden combination of quality '%s' and codec '%s'." % ( self.ReleaseInfo.Quality, self.ReleaseInfo.Codec ) )
	
	def __CheckIfExistsOnPtpInternal(self, movieOnPtpResult):
		existingRelease = movieOnPtpResult.IsReleaseExists( self.ReleaseInfo )
		if existingRelease is not None:
			raise PtpUploaderException( JobRunningState.Ignored_AlreadyExists, "Already exists on PTP: '%s'." % existingRelease )

	def __CheckIfExistsOnPtp(self):
		# TODO: this is temporary here. We should support it everywhere.
		# If we are not logged in here that could mean that nothing interesting has been announcened for a while. 
		Ptp.Login()

		# This could be before the Ptp.Login() line, but this way we can hopefully avoid some logging out errors.
		if self.ReleaseInfo.IsZeroImdbId():
			self.ReleaseInfo.Logger.info( "IMDb ID is set zero, ignoring the check for existing release." )
			return

		if self.ReleaseInfo.HasPtpId():
			# If this is not a forced upload then we have to check if is it already on PTP.
			if not self.ReleaseInfo.IsForceUpload():
				movieOnPtpResult = Ptp.GetMoviePageOnPtp( self.ReleaseInfo.Logger, self.ReleaseInfo.GetPtpId() )
				self.__CheckIfExistsOnPtpInternal( movieOnPtpResult )
		else:
			# Try to get a PTP ID.
			movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )
			self.ReleaseInfo.PtpId = movieOnPtpResult.PtpId

			# If this is not a forced upload then we have to check if is it already on PTP.
			if not self.ReleaseInfo.IsForceUpload():
				self.__CheckIfExistsOnPtpInternal( movieOnPtpResult )
	
	def __FillOutDetailsForNewMovieByPtpApi(self):
		# If already has a page on PTP then we don't have to do anything here.
		if self.ReleaseInfo.HasPtpId():
			return

		ptpImdbInfo = None
		if self.ReleaseInfo.IsZeroImdbId():
			ptpImdbInfo = PtpZeroImdbInfo()
		else:
			ptpImdbInfo = PtpImdbInfo( self.ReleaseInfo.GetImdbId() )

		# Title
		if len( self.ReleaseInfo.Title ) > 0:
			self.ReleaseInfo.Logger.info( "Title '%s' is already set, not getting from PTP's movie info." % self.ReleaseInfo.Title )
		else:
			self.ReleaseInfo.Title = ptpImdbInfo.GetTitle()
			if len( self.ReleaseInfo.Title ) <= 0: 
				raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Movie title is not set."  )
			
		# Year
		if len( self.ReleaseInfo.Year ) > 0:
			self.ReleaseInfo.Logger.info( "Year '%s' is already set, not getting from PTP's movie info." % self.ReleaseInfo.Year )
		else:
			self.ReleaseInfo.Year = ptpImdbInfo.GetYear()
			if len( self.ReleaseInfo.Year ) <= 0: 
				raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Movie year is not set."  )

		# Movie description
		if len( self.ReleaseInfo.MovieDescription ) > 0:
			self.ReleaseInfo.Logger.info( "Movie description is already set, not getting from PTP's movie info." )
		else:
			self.ReleaseInfo.MovieDescription = ptpImdbInfo.GetMovieDescription()
			
		# Tags
		if len( self.ReleaseInfo.Tags ) > 0:
			self.ReleaseInfo.Logger.info( "Tags '%s' are already set, not getting from PTP's movie info." % self.ReleaseInfo.Tags )
		else:
			self.ReleaseInfo.Tags = ptpImdbInfo.GetTags()
			if len( self.ReleaseInfo.Tags ) <= 0:
				raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "At least one tag must be specified for a movie."  )
			
		# Cover art URL
		if self.ReleaseInfo.IsCoverArtUrlSet():
			self.ReleaseInfo.Logger.info( "Cover art URL '%s' is already set, not getting from PTP's movie info." % self.ReleaseInfo.CoverArtUrl )
		else:
			self.ReleaseInfo.CoverArtUrl = ptpImdbInfo.GetCoverArtUrl()
			
		# Directors
		if len( self.ReleaseInfo.Directors ) > 0:
			self.ReleaseInfo.Logger.info( "Director '%s' is already set, not getting from PTP's movie info." % self.ReleaseInfo.Directors )
		else:
			self.ReleaseInfo.SetDirectors( ptpImdbInfo.GetDirectors() )			
			if len( self.ReleaseInfo.Directors ) <= 0:
				raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, """The director of the movie is not set. Use "None Listed" (without the quotes) if there is no director.""" )

		# Ignore adult movies (if force upload is not set).
		if "adult" in self.ReleaseInfo.Tags:
			if self.ReleaseInfo.IsForceUpload():
				self.ReleaseInfo.Logger.info( "Movie's genre is adult, but continuing due to force upload." )
			else:
				raise PtpUploaderException( JobRunningState.Ignored_Forbidden, "Genre is adult." )

	# Uses IMDb and The Internet Movie Poster DataBase. 
	def __FillOutDetailsForNewMovieByExternalSources(self):
		if self.ReleaseInfo.HasPtpId() or self.ReleaseInfo.IsZeroImdbId():
			return

		imdbInfo = Imdb.GetInfo( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )

		# Ignore series (if force upload is not set).
		if imdbInfo.IsSeries:
			if self.ReleaseInfo.IsForceUpload():
				self.ReleaseInfo.Logger.info( "The release is a series, but continuing due to force upload." )
			else:
				raise PtpUploaderException( JobRunningState.Ignored_Forbidden, "It is a series." )

		# PTP returns with the original title, IMDb's iPhone API returns with the international English title.
		self.ReleaseInfo.InternationalTitle = imdbInfo.Title
		if self.ReleaseInfo.Title != self.ReleaseInfo.InternationalTitle and len( self.ReleaseInfo.InternationalTitle ) > 0 and self.ReleaseInfo.Title.find( " AKA " ) == -1:
			self.ReleaseInfo.Title += " AKA " + self.ReleaseInfo.InternationalTitle

		if len( self.ReleaseInfo.MovieDescription ) <= 0:
			self.ReleaseInfo.MovieDescription = imdbInfo.Plot 

		if not self.ReleaseInfo.IsCoverArtUrlSet():
			self.ReleaseInfo.CoverArtUrl = imdbInfo.PosterUrl
			if not self.ReleaseInfo.IsCoverArtUrlSet():
				self.ReleaseInfo.CoverArtUrl = MoviePoster.Get( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )
				
	def __CreateReleaseDirectory(self):
		if self.ReleaseInfo.IsJobPhaseFinished( FinishedJobPhase.Download_CreateReleaseDirectory ):
			self.ReleaseInfo.Logger.info( "Release root path creation phase has been reached previously, not creating it again." )
			return

		releaseRootPath = self.ReleaseInfo.GetReleaseRootPath()
		self.ReleaseInfo.Logger.info( "Creating release root directory at '%s'." % releaseRootPath )

		if os.path.exists( releaseRootPath ):
			raise PtpUploaderException( "Release root directory '%s' already exists." % releaseRootPath )	

		os.makedirs( releaseRootPath )

		self.ReleaseInfo.SetJobPhaseFinished( FinishedJobPhase.Download_CreateReleaseDirectory )
		Database.DbSession.commit()

	def __DownloadTorrentFile(self):
		if self.ReleaseInfo.IsSourceTorrentFilePathSet():
			self.ReleaseInfo.Logger.info( "Source torrent file path is set, not download the file again." )
			return

		torrentName = self.ReleaseInfo.AnnouncementSource.Name + " " + self.ReleaseInfo.ReleaseName + ".torrent"
		sourceTorrentFilePath = os.path.join( self.ReleaseInfo.GetReleaseRootPath(), torrentName )
		self.ReleaseInfo.AnnouncementSource.DownloadTorrent( self.ReleaseInfo.Logger, self.ReleaseInfo, sourceTorrentFilePath )
		
		# Local variable is used temporarily to make sure that SourceTorrentFilePath is only gets stored in the database if DownloadTorrent succeeded. 
		self.ReleaseInfo.SourceTorrentFilePath = sourceTorrentFilePath
		Database.DbSession.commit()

	def __DownloadTorrent(self):
		if len( self.ReleaseInfo.SourceTorrentInfoHash ) > 0:
			self.ReleaseInfo.Logger.info( "Source torrent info hash is set, not starting torent again." )
		else:
			self.Rtorrent.CleanTorrentFile( self.ReleaseInfo.Logger, self.ReleaseInfo.SourceTorrentFilePath )
			self.ReleaseInfo.SourceTorrentInfoHash = self.Rtorrent.AddTorrent( self.ReleaseInfo.Logger, self.ReleaseInfo.SourceTorrentFilePath, self.ReleaseInfo.GetReleaseDownloadPath() )
			Database.DbSession.commit()

	def __AddToPendingDownloads(self):
		self.JobManager.AddToPendingDownloads( self.ReleaseInfo )