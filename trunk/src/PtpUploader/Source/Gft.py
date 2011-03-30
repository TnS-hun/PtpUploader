from Globals import Globals
from NfoParser import NfoParser
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from ReleaseNameParser import ReleaseNameParser
from Settings import Settings

import re
import time
import urllib
import urllib2

class Gft:
	def __init__(self):
		self.Name = "gft"
		self.MaximumParallelDownloads = Settings.GftMaximumParallelDownloads
	
	@staticmethod
	def Login():
		Globals.Logger.info( "Loggin in to GFT." );
		# GFT stores a cookie when login.php is loaded that is needed for takelogin.php. 
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		result = opener.open( "http://www.thegft.org/login.php" )
		response = result.read()

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		postData = urllib.urlencode( { "username": Settings.GftUserName, "password": Settings.GftPassword } )
		result = opener.open( "http://www.thegft.org/takelogin.php", postData )
		response = result.read()
		Gft.CheckIfLoggedInFromResponse( response );
	
	@staticmethod
	def CheckIfLoggedInFromResponse(response):
		if response.find( """action='takelogin.php'""" ) != -1 or response.find( """<a href='login.php'>Back to Login</a>""" ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to GFT. Probably due to the bad user name or password in settings." )
	
	@staticmethod
	def __DownloadNfo(logger, releaseInfo, getReleaseName = False, checkPretime = True):
		url = "http://www.thegft.org/details.php?id=%s" % releaseInfo.AnnouncementId;
		logger.info( "Downloading NFO from page '%s'." % url );
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
		request = urllib2.Request( url );
		result = opener.open( request );
		response = result.read();
		Gft.CheckIfLoggedInFromResponse( response );

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( """<p><a name="startcomments"></a></p>""" )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( "Description can't found on page '%s'. Probably the layout of the site has changed." % url )
		
		description = response[ :descriptionEndIndex ]			

		# Get release name.
		matches = re.search( r"<title>GFT 2011 :: Details for torrent &quot;(.+)&quot;</title>", description );
		if matches is None:
			raise PtpUploaderException( "Release name can't be found on page '%s'." % url );
	
		releaseName = matches.group( 1 );
		if getReleaseName:
			releaseInfo.ReleaseName = releaseName;
		elif releaseName != releaseInfo.ReleaseName:
			raise PtpUploaderException( "Announcement release name '%s' and release name '%s' on page '%s' are different." % ( releaseInfo.ReleaseName, releaseName, url ) );

		# For some reason there are announced, but non visible releases on GFT that never start seeding. Ignore them.
		if description.find( """<td class="heading" align="right" valign="top">Visible</td><td align="left" valign="top"><b>no</b> (dead)</td>""" ) != -1:
			raise PtpUploaderException( "Ignoring release '%s' at '%s' because it is set to not visible." % ( releaseName, url ) ); 

		return description
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		nfoText = ""
		
		if releaseInfo.IsManualAnnouncement:
			# Download the NFO and get the release name.
			nfoText = Gft.__DownloadNfo( logger, releaseInfo, getReleaseName = True, checkPretime = False )
			releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
			releaseNameParser.GetSourceAndFormat( releaseInfo )
			if releaseNameParser.Scene:
				releaseInfo.Scene = "on"
		else:
			# In case of automatic announcement we have to check the release name if it is valid.
			# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.
			releaseNameParser = ReleaseNameParser( releaseInfo.ReleaseName )
			if not releaseNameParser.IsAllowed():
				logger.info( "Ignoring release '%s' because of its name." % releaseInfo.ReleaseName )
				return None

			releaseNameParser.GetSourceAndFormat( releaseInfo )

			if releaseNameParser.Scene:
				releaseInfo.Scene = "on"

			# TODO: temp
			time.sleep( 30 ) # "Tactical delay" because of the not visible torrents. These should be rescheduled.

			# Download the NFO.
			# If the release is from a known scene releaser group we skip the pretime checking.
			# This is useful because the pretime sometime not presents on GFT.
			nfoText = Gft.__DownloadNfo( logger, releaseInfo, getReleaseName = False, checkPretime = not releaseNameParser.Scene )
		
		releaseInfo.ImdbId = NfoParser.GetImdbId( nfoText )
		return releaseInfo
	
	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		url = "http://www.thegft.org/download.php?torrent=%s" % releaseInfo.AnnouncementId;
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) );

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );		
		request = urllib2.Request( url );
		result = opener.open( request );
		response = result.read();
		Gft.CheckIfLoggedInFromResponse( response );
		
		file = open( path, "wb" );
		file.write( response );
		file.close();

		# If a torrent contains multiple NFO files then it is likely that the site also showed the wrong NFO and we have checked the existence of another movie on PTP.
		# So we abort here. These errors happen rarely anyway.
		# (We could also try read the NFO with the same name as the release or with the same name as the first RAR and reschedule for checking with the correct IMDb id.)
		if NfoParser.IsTorrentContainsMultipleNfos( path ):
			raise PtpUploaderException( "Torrent '%s' contains multiple NFO files." % path )  

	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		# Extract the release.
		nfoPath = ReleaseExtractor.Extract( releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )
		if nfoPath is not None:
			releaseInfo.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath )

	@staticmethod
	def RenameRelease(logger, releaseInfo):
		pass
				
	@staticmethod
	def IsSingleFileTorrentNeedsDirectory():
		return True
	
	@staticmethod
	def IncludeReleaseNameInReleaseDescription():
		return True