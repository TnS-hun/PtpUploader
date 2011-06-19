from Tool.ImageMagick import ImageMagick
from Tool.Ffmpeg import Ffmpeg
from Tool.Mplayer import Mplayer

from ImageUploader import ImageUploader
from PtpUploaderException import PtpUploaderException
from Settings import Settings

import os

class ScreenshotMaker:
	def __init__(self, logger, inputVideoPath):
		self.Logger = logger

		self.InternalScreenshotMaker = None
		self.UsingMplayer = False
		
		if Mplayer.IsEnabled():
			self.InternalScreenshotMaker = Mplayer( logger, inputVideoPath )
			self.UsingMplayer = True
		else:
			self.InternalScreenshotMaker = Ffmpeg( logger, inputVideoPath )
			
	def GetScaleSize(self):
		return self.InternalScreenshotMaker.ScaleSize

	def __MakeUsingMplayer(self, timeInSeconds, outputImageDirectory):
		return self.InternalScreenshotMaker.MakeScreenshotInJpg( timeInSeconds, outputImageDirectory )

	def __MakeUsingFfmpeg(self, timeInSeconds, outputImageDirectory):
		outputPngPath = os.path.join( outputImageDirectory, "00000001.png" )
		self.InternalScreenshotMaker.MakeScreenshotInPng( timeInSeconds, outputPngPath )

		if ImageMagick.IsEnabled():
			outputJpgPath = os.path.join( outputImageDirectory, "00000001.jpg" )
			ImageMagick.ConvertImageToJpg( self.Logger, outputPngPath, outputJpgPath )
			os.remove( outputPngPath )
			return outputJpgPath
		else:
			return outputPngPath

	# Returns with the URL of the uploaded image.
	def __TakeAndUploadScreenshot(self, timeInSeconds, outputImageDirectory):
		screenshotPath = None
		
		if self.UsingMplayer:
			screenshotPath = self.__MakeUsingMplayer( timeInSeconds, outputImageDirectory )
		else:
			screenshotPath = self.__MakeUsingFfmpeg( timeInSeconds, outputImageDirectory )
		
		imageUrl = ImageUploader.Upload( self.Logger, imagePath = screenshotPath )
		os.remove( screenshotPath )
		return imageUrl

	# Takes five screenshots from the first 30% of the video.
	# Returns with the URLs of the uploaded images.
	def TakeAndUploadScreenshots(self, outputImageDirectory, durationInSec, takeSingleScreenshot):
		urls = []
		urls.append( self.__TakeAndUploadScreenshot( int( durationInSec * 0.10 ), outputImageDirectory ) )

		if not takeSingleScreenshot:
			urls.append( self.__TakeAndUploadScreenshot( int( durationInSec * 0.15 ), outputImageDirectory ) )
			urls.append( self.__TakeAndUploadScreenshot( int( durationInSec * 0.20 ), outputImageDirectory ) )
			urls.append( self.__TakeAndUploadScreenshot( int( durationInSec * 0.25 ), outputImageDirectory ) )
			urls.append( self.__TakeAndUploadScreenshot( int( durationInSec * 0.30 ), outputImageDirectory ) )

		return urls

	# We sort video files by their size (less than 50 MB difference is ignored) and by their name.
	# Sorting by name is needed to ensure that the screenshot is taken from the first video to avoid spoilers when a release contains multiple videos.
	# Sorting by size is needed to ensure that we don't take the screenshots from the sample or extras included.
	# Ignoring less than 50 MB differnece is needed to make sure that CD1 will be sorted before CD2 even if CD2 is larger than CD1 by 49 MB.
	@staticmethod
	def SortVideoFiles(files):
		class SortItem:
			def __init__(self, path):
				self.Path = path
				self.LowerPath = path.lower()
				self.Size = os.path.getsize( path )

			@staticmethod
			def Compare( item1, item2 ):
				ignoreSizeDifference = 50 * 1024 * 1024
				sizeDifference = item1.Size - item2.Size 
				if abs( sizeDifference ) > ignoreSizeDifference:
					if item1.Size > item2.Size:
						return -1
					else:
						return 1

				if item1.LowerPath < item2.LowerPath:
					return -1
				elif item1.LowerPath > item2.LowerPath:
					return 1
				else:
					return 0

		filesToSort = []
		for file in files:
			item = SortItem( file )
			filesToSort.append( item )

		filesToSort.sort( cmp = SortItem.Compare )

		files = []
		for item in filesToSort:
			files.append( item.Path )

		return files