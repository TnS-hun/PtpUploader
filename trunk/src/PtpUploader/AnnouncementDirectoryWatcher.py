from MyGlobals import MyGlobals
from PtpUploaderMessage import *
from Settings import Settings

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import sys

class MyWatchdogEventHandler( FileSystemEventHandler ):
	def on_moved( self, event ):
		super( MyWatchdogEventHandler, self ).on_moved( event )

		if not event.is_directory:
			MyGlobals.PtpUploader.AddMessage( PtpUploaderMessageNewAnnouncementFile( event.dest_path ) )

	def on_created( self, event ):
		super( MyWatchdogEventHandler, self ).on_created( event )

		if not event.is_directory:
			MyGlobals.PtpUploader.AddMessage( PtpUploaderMessageNewAnnouncementFile( event.src_path ) )

	def on_modified( self, event ):
		super( MyWatchdogEventHandler, self ).on_modified( event )

		if not event.is_directory:
			MyGlobals.PtpUploader.AddMessage( PtpUploaderMessageNewAnnouncementFile( event.src_path ) )

class AnnouncementDirectoryWatcher:
	def __init__( self ):
		MyGlobals.Logger.info( "Starting announcement directory watcher." )

		# "When you call observer.schedule() path should be str properly encoded to what the file system is, not unicode"
		# https://github.com/gorakhargosh/watchdog/issues/157#issuecomment-16584053
		path = Settings.GetAnnouncementWatchPath().encode( sys.getfilesystemencoding() )

		eventHandler = MyWatchdogEventHandler()
		self.Observer = Observer()
		self.Observer.schedule( eventHandler, path, recursive = False )
		self.Observer.start()

	def StopWatching( self ):
		MyGlobals.Logger.info( "Stopping announcement directory watcher." )
		self.Observer.stop()
		self.Observer.join()