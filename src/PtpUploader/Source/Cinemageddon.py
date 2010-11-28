from Globals import Globals
from PtpUploaderException import PtpUploaderException
from ReleaseExtractor import ReleaseExtractor;
from ReleaseInfo import ReleaseInfo;
from Settings import Settings

import re
import urllib
import urllib2

class Cinemageddon:
	def __init__(self):
		self.Name = "cg"
		self.MaximumParallelDownloads = Settings.CinemageddonMaximumParallelDownloads
	
	@staticmethod
	def Login():
		Globals.Logger.info( "Loggin in to Cinemageddon." )
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		postData = urllib.urlencode( { "username": Settings.CinemageddonUserName, "password": Settings.CinemageddonPassword } )
		request = urllib2.Request( "http://cinemageddon.net/takelogin.php", postData )
		result = opener.open( request )
		response = result.read()
		Cinemageddon.__CheckIfLoggedInFromResponse( response )
	
	@staticmethod
	def __CheckIfLoggedInFromResponse(response):
		if response.find( 'action="takelogin.php"' ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to Cinemageddon. Probably due to the bad user name or password in settings." )

	@staticmethod
	def __DownloadNfo(logger, announcement):
		url = "http://cinemageddon.net/details.php?id=%s&filelist=1" % announcement.AnnouncementId
		logger.info( "Collecting info from torrent page '%s'." % url )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		Cinemageddon.__CheckIfLoggedInFromResponse( response )

		# Make sure we only get information from the description and not from the comments.
		descriptionEndIndex = response.find( '<p><a name="startcomments"></a></p>' )
		if descriptionEndIndex == -1:
			raise PtpUploaderException( "Description can't found on page '%s'. Probably the layout of the site has changed." % url )
		
		description = response[ :descriptionEndIndex ]			

		# We will use the torrent's name as release name.
		matches = re.search( r'href="download.php\?id=(\d+)&name=.+">(.+)\.torrent</a>', description )
		if matches is None:
			raise PtpUploaderException( "Can't get release name from page '%s'." % url )
		
		announcement.ReleaseName = matches.group( 2 )

		# Get source and format type
		matches = re.search( r"torrent details for &quot;(.+) \[(\d+)/(.+)/(.+)\]&quot;", description )
		if matches is None:
			raise PtpUploaderException( "Can't get release source and format type from page '%s'." % url )
		
		sourceType = matches.group( 3 )
		formatType = matches.group( 4 )

		# Get IMDb id
		matches = re.search( r'imdb\.com/title/tt(\d+)', description )
		if matches is None:
			raise PtpUploaderException( "Ignoring release '%s' at '%s' because IMDb id can't be found." % ( announcement.ReleaseName, url ) )

		imdbId = matches.group( 1 )

		# Ignore XXX releases.
		if description.find( '>Type</td><td valign="top" align=left>XXX<' ) != -1:
			raise PtpUploaderException( "Ignoring release '%s' at '%s' because it is XXX." % ( announcement.ReleaseName, url ) )
		
		# Make sure that this is not a wrongly categorized DVDR.
		if re.search( ".vob</td>", description, re.IGNORECASE ) or re.search( ".iso</td>", description, re.IGNORECASE ):
			raise PtpUploaderException( "Ignoring release '%s' at '%s' because it is a wrongly categorized DVDR." % ( announcement.ReleaseName, url ) )
		
		return imdbId, sourceType, formatType

	@staticmethod
	def __MapSourceAndFormatToPtp(ptpUploadInfo, sourceType, formatType):
		sourceType = sourceType.lower()
		formatType = formatType.lower()

		# Adding BDrip support would be problematic because there is no easy way to decide if it is HD or SD.
		# Maybe we could use the resolution and file size. But what about the oversized and upscaled releases? 
		
		ptpUploadInfo.Quality = "Standard Definition"
		ptpUploadInfo.ResolutionType = "Other"

		if sourceType == "dvdrip":
			ptpUploadInfo.Source = "DVD"
		elif sourceType == "vhsrip":
			ptpUploadInfo.Source = "VHS"
		elif sourceType == "tvrip":
			ptpUploadInfo.Source = "TV"
		else:
			raise PtpUploaderException( "Got unsupported source type '%s' from Cinemageddon." % sourceType );

		if formatType == "x264":
			ptpUploadInfo.Codec = "x264"
		elif formatType == "xvid":
			ptpUploadInfo.Codec = "XviD"
		elif formatType == "divx":
			ptpUploadInfo.Codec = "DivX"
		else:
			raise PtpUploaderException( "Got unsupported format type '%s' from Cinemageddon." % formatType )
	
	@staticmethod
	def PrepareDownload(logger, announcement):
		imdbId = ""
		sourceType = ""
		formatType = ""
		
		if announcement.IsManualAnnouncement:
			imdbId, sourceType, formatType = Cinemageddon.__DownloadNfo( logger, announcement, getReleaseName = True )
		else:
			# TODO: add filterting support for Cinemageddon
			# In case of automatic announcement we have to check the release name if it is valid.
			# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source. 
			#if not ReleaseFilter.IsValidReleaseName( announcement.ReleaseName ):
			#	logger.info( "Ignoring release '%s' because of its name." % announcement.ReleaseName )
			#	return None
			imdbId, sourceType, formatType = Cinemageddon.__DownloadNfo( logger, announcement )
			
		releaseInfo = ReleaseInfo( announcement, imdbId )
		Cinemageddon.__MapSourceAndFormatToPtp( releaseInfo.PtpUploadInfo, sourceType, formatType )		
		return releaseInfo
		
	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		url = "http://cinemageddon.net/download.php?id=%s" % releaseInfo.Announcement.AnnouncementId
		logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		request = urllib2.Request( url )
		result = opener.open( request )
		response = result.read()
		Cinemageddon.__CheckIfLoggedInFromResponse( response )
		
		file = open( path, "wb" )
		file.write( response )
		file.close()
		
	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		ReleaseExtractor.Extract( releaseInfo.GetReleaseDownloadPath(), releaseInfo.GetReleaseUploadPath() )
		
	@staticmethod
	def IsSingleFileTorrentNeedsDirectory():
		return False