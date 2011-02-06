from Globals import Globals;
from NfoParser import NfoParser;
from PtpUploaderException import PtpUploaderException;
from ReleaseInfo import ReleaseInfo;
from SceneRelease import SceneRelease;
from Settings import Settings;

# TODO: add support for non scene releases.
# How will we get the IMDb id and the info gained from GetSourceAndFormatFromSceneReleaseName? Probably only with a custom irc message if there is no NFO.

class Manual:
	def __init__(self):
		self.Name = "manual"
		self.MaximumParallelDownloads = 1
	
	@staticmethod
	def Login():
		pass;
	
	@staticmethod
	def PrepareDownload(logger, releaseInfo):
		nfo = NfoParser.GetNfoFile( ReleaseInfo.GetReleaseDownloadPathFromRelaseName( releaseInfo.ReleaseName ) )
		releaseInfo.ImdbId = NfoParser.GetImdbId( nfo )
		releaseInfo.Nfo = nfo;
		SceneRelease.GetSourceAndFormatFromSceneReleaseName( releaseInfo, releaseInfo.ReleaseName )
		return releaseInfo
		
	@staticmethod
	def DownloadTorrent(logger, releaseInfo, path):
		pass;
		
	@staticmethod
	def ExtractRelease(logger, releaseInfo):
		# Extract the release.
		sceneRelease = SceneRelease( releaseInfo.GetReleaseDownloadPath() )
		sceneRelease.Extract( logger, releaseInfo.GetReleaseUploadPath() )

	@staticmethod
	def RenameRelease(logger, releaseInfo):
		pass

	@staticmethod
	def IsSingleFileTorrentNeedsDirectory():
		return True
	
	@staticmethod
	def IncludeReleaseNameInReleaseDescription():
		return True