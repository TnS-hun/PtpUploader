from Source.Cinemageddon import Cinemageddon
from Source.Cinematik import Cinematik
from Source.File import File
from Source.FunFile import FunFile
from Source.Gft import Gft
from Source.Karagarga import Karagarga
from Source.Torrent import Torrent
from Source.TorrentLeech import TorrentLeech
from Source.TorrentShack import TorrentShack

from MyGlobals import MyGlobals
from Settings import Settings

class SourceFactory:
	def __init__(self):
		self.Sources = {}

		self.__AddSource( File() )
		self.__AddSource( Torrent() )

		self.__AddSource( Cinemageddon() )
		self.__AddSource( Cinematik() )
		self.__AddSource( FunFile() )
		self.__AddSource( Gft() )
		self.__AddSource( Karagarga() )
		self.__AddSource( TorrentLeech() )
		self.__AddSource( TorrentShack() )

		MyGlobals.Logger.info( "Sources initialized." )

	def __AddSource(self, source):
		source.LoadSettings( Settings )
		if source.IsEnabled():
			source.Login()
		self.Sources[ source.Name ] = source

	def GetSource(self, sourceName):
		# We don't want to throw KeyError exception, so we use get.
		return self.Sources.get( sourceName ) 

	def GetSourceAndIdByUrl(self, url):
		for key, source in self.Sources.iteritems():
			id = source.GetIdFromUrl( url )
			if len( id ) > 0:
				return source, id
		
		return None, ""
