from Job.JobRunningState import JobRunningState
from Source.SourceBase import SourceBase

from Helper import GetSizeFromText
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from PtpUploaderException import *
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser

import re
import urllib
import urllib2

class TorrentLeech(SourceBase):
	def __init__(self):
		self.Name = "tl"
		self.NameInSettings = "TorrentLeech"
		self.MaximumParallelDownloads = 3

	def IsEnabled(self):
		return len( self.Username ) > 0 and len( self.Password ) > 0

	def Login(self):
		MyGlobals.Logger.info( "Logging in to TorrentLeech." )
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "username": self.Username, "password": self.Password } )
		request = urllib2.Request( "http://www.torrentleech.org/user/account/login/", postData )
		result = opener.open( request )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response )
	
	def CheckIfLoggedInFromResponse(self, response):
		if response.find( '<div class="recaptcha">' ) != -1:
			raise PtpUploaderInvalidLoginException( "Can't login to TorrentLeech because there is a captcha on the login page." )
		
		if response.find( '<form method="post" action="/user/account/login/">' ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to TorrentLeech. Probably due to the bad user name or password in settings." )

	# Release names on TL don't contain periods. This function restores them.
	# Eg.: "Far From Heaven 2002 720p BluRay x264-HALCYON" instead of "Far.From.Heaven.2002.720p.BluRay.x264-HALCYON"
	def __RestoreReleaseName(self, releaseName):
		return releaseName.replace( " ", "." )
	
	# On TorrentLeech the torrent page doesn't contain the NFO, and the NFO page doesn't contain the release name so we have to read them separately. 
	def __GetReleaseNameAndSize(self, logger, releaseInfo):
		url = "http://www.torrentleech.org/torrent/%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading release name and size from page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response )

		# Get release name.
		matches = re.search( "<title>Torrent Details for (.+) :: TorrentLeech.org</title>", response )
		if matches is None:
			raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Release name can't be found on torrent page." )
		releaseName = self.__RestoreReleaseName( matches.group( 1 ) )

		# Get size.
		# <td class="label">Size</td><td>5.47 GB</td></tr>
		size = 0
		matches = re.search( r"""<td class="label">Size</td><td>(.+)</td></tr>""", response )
		if matches is None:
			logger.warning( "Size not found on torrent page." )
		else:
			size = GetSizeFromText( matches.group( 1 ) )

		return releaseName, size

	# On TorrentLeech the torrent page doesn't contain the NFO, and the NFO page doesn't contain the release name so we have to read them separately. 
	def __ReadImdbIdFromNfoPage(self, logger, releaseInfo):
		if releaseInfo.HasImdbId() or releaseInfo.HasPtpId():
			return
		
		url = "http://www.torrentleech.org/torrents/torrent/nfotext?torrentID=%s" % releaseInfo.AnnouncementId
		logger.info( "Downloading NFO from page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response )

		releaseInfo.ImdbId = NfoParser.GetImdbId( response )
	
	def __HandleUserCreatedJob(self, logger, releaseInfo):
		if ( not releaseInfo.IsReleaseNameSet() ) or releaseInfo.Size == 0:
			releaseName, releaseInfo.Size = self.__GetReleaseNameAndSize( logger, releaseInfo )
			if not releaseInfo.IsReleaseNameSet():
				releaseInfo.ReleaseName = releaseName

		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		releaseNameParser.GetSourceAndFormat( releaseInfo )

		# Pretime is not indicated on TorrentLeech so we have to rely on our scene groups list.
		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

		self.__ReadImdbIdFromNfoPage( logger, releaseInfo )

	def __HandleAutoCreatedJob(self, logger, releaseInfo):
		releaseInfo.ReleaseName = self.__RestoreReleaseName( releaseInfo.ReleaseName )
		
		# In case of automatic announcement we have to check the release name if it is valid.
		# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.
		releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
		isAllowedMessage = releaseNameParser.IsAllowed()
		if isAllowedMessage is not None:
			raise PtpUploaderException( JobRunningState.Ignored, isAllowedMessage )

		releaseNameParser.GetSourceAndFormat( releaseInfo )
		
		releaseName, releaseInfo.Size = self.__GetReleaseNameAndSize( logger, releaseInfo )
		if releaseName != releaseInfo.ReleaseName:
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on page '%s' are different." % ( releaseInfo.ReleaseName, releaseName, url ) )

		# Pretime is not indicated on TorrentLeech so we have to rely on our scene groups list.
		if releaseNameParser.Scene:
			releaseInfo.SetSceneRelease()

		if ( not releaseInfo.IsSceneRelease() ) and self.AutomaticJobFilter == "SceneOnly":
			raise PtpUploaderException( JobRunningState.Ignored, "Non-scene release." )

		self.__ReadImdbIdFromNfoPage( logger, releaseInfo )
	
	def PrepareDownload(self, logger, releaseInfo):
		# TODO: temp
		# TorrentLeech has a bad habit of logging out, so we put this here.
		self.Login()
		
		if releaseInfo.IsUserCreatedJob():
			self.__HandleUserCreatedJob( logger, releaseInfo )
		else:
			self.__HandleAutoCreatedJob( logger, releaseInfo )
	
	def DownloadTorrent(self, logger, releaseInfo, path):
		# Filename in the URL could be anything.
		url = "http://www.torrentleech.org/download/%s/TL.torrent" % releaseInfo.AnnouncementId
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )		
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		self.CheckIfLoggedInFromResponse( response )
		
		file = open( path, "wb" )
		file.write( response )
		file.close()

		# Calling Helper.ValidateTorrentFile is not needed because NfoParser.IsTorrentContainsMultipleNfos will throw an exception if it is not a valid torrent file.

		# If a torrent contains multiple NFO files then it is likely that the site also showed the wrong NFO and we have checked the existence of another movie on PTP.
		# So we abort here. These errors happen rarely anyway.
		# (We could also try read the NFO with the same name as the release or with the same name as the first RAR and reschedule for checking with the correct IMDb id.)
		if NfoParser.IsTorrentContainsMultipleNfos( path ):
			raise PtpUploaderException( "Torrent '%s' contains multiple NFO files." % path )  

	def GetIdFromUrl(self, url):
		result = re.match( r".*torrentleech\.org/torrent/(\d+).*", url )
		if result is None:
			return ""
		else:
			return result.group( 1 )

	def GetUrlFromId(self, id):
		return "http://www.torrentleech.org/torrent/" + id