from Database import Database
from MyGlobals import MyGlobals
from Logger import Logger
from PtpUploaderException import PtpUploaderException
from ReleaseInfo import ReleaseInfo
from Settings import Settings

import os
import re
		
class AnnouncementWatcher:
	# Example: [source=gft][id=44][title=Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS]
	@staticmethod
	def __ProcessAnnouncementFile(announcementFilename):
		matches = re.match( r"\[source=(.+)\]\[id=(\d+)\]\[title=(.+)\]", announcementFilename )			
		if not matches:
			MyGlobals.Logger.info( "Invalid announcement name format: '%s'." % announcementFilename )
			return None
			
		announcementSourceName = matches.group( 1 )
		announcementId = matches.group( 2 )
		releaseName = matches.group( 3 )
			
		announcementSource = MyGlobals.SourceFactory.GetSource( announcementSourceName )
		if announcementSource is None:
			MyGlobals.Logger.error( "Unknown announcement source: '%s'." % announcementSourceName )
			return None
		
		releaseInfo = ReleaseInfo()
		releaseInfo.ReleaseName = releaseName
		releaseInfo.AnnouncementSource = announcementSource
		releaseInfo.AnnouncementSourceName = announcementSource.Name
		releaseInfo.AnnouncementId = announcementId
		releaseInfo.Logger = Logger( releaseInfo.GetLogFilePath() )
		Database.DbSession.add( releaseInfo )
		Database.DbSession.commit()
		return releaseInfo
	
	# No logging here because it would result in spamming.
	@staticmethod
	def LoadAnnouncementFilesIntoTheDatabase():
		announcements = []

		announcementsPath = Settings.GetAnnouncementWatchPath()
		entries = os.listdir( announcementsPath )
		files = [];
		for entry in entries:
			filePath = os.path.join( announcementsPath, entry )
			if os.path.isfile( filePath ):
				modificationTime = os.path.getmtime( filePath )
				item = modificationTime, filePath # Add as a tuple.
				files.append( item )

		files.sort()
		for item in files:
			path = item[ 1 ] # First element is the modification time, second is the path.
			filename = os.path.basename( path ) # Get the filename.
			releaseInfo = AnnouncementWatcher.__ProcessAnnouncementFile( filename )
			if releaseInfo is None:
				invalidFilePath = os.path.join( Settings.GetAnnouncementInvalidPath(), filename )
				os.rename( path, invalidFilePath )
			else:
				announcements.append( releaseInfo ) 
				os.remove( path )

		return announcements