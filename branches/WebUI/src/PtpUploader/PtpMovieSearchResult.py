from PtpUploaderException import PtpUploaderException

import re

class PtpMovieSearchResultItem:
	def __init__(self, codec, container, source, resolution):
		self.Codec = codec
		self.Container = container
		self.Source = source
		self.Resolution = resolution
		
	def __repr__(self):
		return "%s / %s / %s / %s" % ( self.Codec, self.Container, self.Source, self.Resolution )

# Notes:
# - We treat HD-DVD and Blu-ray as same quality.
# - We treat DVD and Blu-ray rips equally in the standard definition category.
# - We treat H.264 and x264 equally because of the uploading rules: "MP4 can only be trumped by MKV if the use of that container causes problems with video or audio".
# - We treat XviD and DivX equally because of the uploading rules: "DivX may be trumped by XviD, if the latter improves on the quality of the former. In cases where the DivX is well distributed and the XviD offers no significant improvement in quality, the staff may decide to keep the former in order to preserve the availability of the movie."
class PtpMovieSearchResult:
	def __init__(self, ptpId, moviePageHtml):
		self.PtpId = ptpId;
		self.SdList = []
		self.HdList = []
		self.OtherList = []
		
		if moviePageHtml is not None:
			self.__ParseMoviePage( moviePageHtml )

	@staticmethod
	def __ParseMoviePageMakeItems(itemList, regexFindList):
		for regexFind in regexFindList:
			elements = regexFind.split( " / " )
			if len( elements ) < 4:
				raise PtpUploaderException( "Error! Unknown torrent format on movie page: '%s'." % elements );

			codec = elements[ 0 ]
			container = elements[ 1 ]
			source = elements[ 2 ]
			resolution = elements[ 3 ]
			itemList.append( PtpMovieSearchResultItem( codec, container, source, resolution ) )

	def __ParseMoviePage(self, html):
		# We divide the HTML into three sections: SD, HD and Other type torrents.
		# This is needed because we are using regular expressions and we have to know which section the torent belongs to.
		# We could use a HTML parser too, but this is faster and less resource hungry.

		# We have to sort the sections because we use the their start and end indexes in the regular expression.  	
		sortedSections = []
		sdIndex = html.find( 'class="edition_info"><strong>Standard Definition</strong>' )
		if sdIndex >= 0:
			sortedSections.append( ( sdIndex, self.SdList ) )
		hdIndex = html.find( 'class="edition_info"><strong>High Definition</strong>' )
		if hdIndex >= 0:
			sortedSections.append( ( hdIndex, self.HdList ) )
		otherIndex = html.find( 'class="edition_info"><strong>Other</strong>' )
		if otherIndex >= 0:
			sortedSections.append( ( otherIndex, self.OtherList ) )
			
		if len( sortedSections ) <= 0:
			raise PtpUploaderException( "Error! Movie page doesn't contains any torrents." );
			
		sortedSections.sort()

		# <a href="#" onclick="$('#torrent_37673').toggle(); show_description('35555', '62113'); return false;">XviD / AVI / DVD / 720x420</a>
		# <a href="#" onclick="$('#torrent_55714').toggle(); show_description('35555', '62113'); return false;"><span style="float:none;color:#E5B244;"><strong>XviD / AVI / DVD / 608x256 / Scene</strong></span></a>
		regEx = re.compile( """<a href="#" onclick="\$\('#torrent_\d+'\)\.toggle\(\); show_description\('\d+', '\d+'\); return false;">(?:<span style=".+"><strong>)?(.+?)(?:</strong></span>)?</a>""" )

		# Get the list of torrents for each section.
		for i in range( len( sortedSections ) ):
			section = sortedSections[ i ]
			currentIndex = section[ 0 ]
			currentList = section[ 1 ]
			
			endIndex = len( html )
			# If this is not the last item, we use the next item's start index for the end of the current range.
			if ( i + 1 ) < len( sortedSections ):
				nextSection = sortedSections[ i + 1 ]
				endIndex = nextSection[ 0 ]
	
			result = regEx.findall( html, currentIndex, endIndex )
			PtpMovieSearchResult.__ParseMoviePageMakeItems( currentList, result )

		# Just for absolute safety we compare the number of results with the first regulary expression.
		result = re.findall( """<a href="#" onclick="\$\('#torrent_\d+'\)\.toggle\(\);""", html )
		if ( not result ) or len( result ) == 0 or len( result ) != ( len( self.SdList ) + len( self.HdList ) + len( self.OtherList ) ):
			raise PtpUploaderException( "Error! Unknown torrent format on movie page." );  
	
	@staticmethod
	def __IsInList(list, codecs, sources = None, resolutions = None):
		for item in list:
			if ( item.Codec in codecs ) \
				and ( ( sources is None ) or ( item.Source in sources ) ) \
				and ( ( resolutions is None ) or ( item.Resolution in resolutions ) ): 
				return item
				
		return None 
	
	@staticmethod
	def __IsFineSource(source):
		return source == "DVD" or source == "Blu-ray" or source == "HD-DVD"

	def __IsHdFineSourceReleaseExists(self, releaseInfo):
		if ( releaseInfo.Source == "Blu-ray" or releaseInfo.Source == "HD-DVD" ) and releaseInfo.ResolutionType == "1080p":
			return PtpMovieSearchResult.__IsInList( self.HdList, [ "x264", "H.264" ], [ "Blu-ray", "HD-DVD" ], [ "1080p" ] )
		elif ( releaseInfo.Source == "Blu-ray" or releaseInfo.Source == "HD-DVD" ) and releaseInfo.ResolutionType == "720p":
			return PtpMovieSearchResult.__IsInList( self.HdList, [ "x264", "H.264" ], [ "Blu-ray", "HD-DVD" ], [ "720p" ] )
		
		raise PtpUploaderException( "Can't check whether the release '%s' exist on PTP because its type is unsupported." % releaseInfo.ReleaseName );

	def __IsSdFineSourceReleaseExists(self, releaseInfo):
		if releaseInfo.Source == "Blu-ray" or releaseInfo.Source == "HD-DVD" or releaseInfo.Source == "DVD":
			if releaseInfo.Codec == "x264" or releaseInfo.Codec == "H.264":
				return PtpMovieSearchResult.__IsInList( self.SdList, [ "x264", "H.264" ], [ "Blu-ray", "HD-DVD", "DVD" ] )
			elif releaseInfo.Codec == "XviD" or releaseInfo.Codec == "DivX":
				return PtpMovieSearchResult.__IsInList( self.SdList, [ "XviD", "DivX" ], [ "Blu-ray", "HD-DVD", "DVD" ] )

		raise PtpUploaderException( "Can't check whether the release '%s' exist on PTP because its type is unsupported." % releaseInfo.ReleaseName );
		
	def __IsSdNonFineSourceReleaseExists(self, releaseInfo):
		# List is ordered by quality. DVD/HD-DVD/Blu-ray is not needed in the list because these have been already checked in IsReleaseExists.
		sourceByQuality = [ "CAM", "TS", "VHS", "TV", "DVD-Screener", "TC", "HDTV", "R5" ]
		
		if releaseInfo.Source not in sourceByQuality: 
			raise PtpUploaderException( "Unsupported source '%s'." % releaseInfo.Source );
		if releaseInfo.Codec == "DivX" or releaseInfo.Codec == "XviD" or releaseInfo.Codec == "H.264" or releaseInfo.Codec == "x264":
			# We check if there is anything with same or better quality.
			sourceIndex = sourceByQuality.index( releaseInfo.Source )
			checkAgainstSources = sourceByQuality[ sourceIndex: ]	
			return PtpMovieSearchResult.__IsInList( self.SdList, [ "DivX", "XviD", "x264", "H.264" ], checkAgainstSources )

		raise PtpUploaderException( "Can't check whether the release '%s' exist on PTP because its type is unsupported." % releaseInfo.ReleaseName );

	def IsMoviePageExists(self):
		return len( self.PtpId ) > 0

	def IsReleaseExists(self, releaseInfo):
		if not self.IsMoviePageExists():
			return None

		# If source is not DVD/HD-DVD/Blu-ray then we check if there is a release with any proper quality sources.
		# If there is, we won't add this lower quality release.
		if not PtpMovieSearchResult.__IsFineSource( releaseInfo.Source ):
			for item in self.SdList:
				if PtpMovieSearchResult.__IsFineSource( item.Source ):
					return item
	
			for item in self.HdList:
				if PtpMovieSearchResult.__IsFineSource( item.Source ):
					return item

		# We can't check special releases.
		if not releaseInfo.IsSpecialRelease():
			if releaseInfo.IsHighDefinition():
				if PtpMovieSearchResult.__IsFineSource( releaseInfo.Source ):
					return self.__IsHdFineSourceReleaseExists( releaseInfo )
			elif releaseInfo.IsStandardDefinition():
				if PtpMovieSearchResult.__IsFineSource( releaseInfo.Source ):
					return self.__IsSdFineSourceReleaseExists( releaseInfo )
				else:
					return self.__IsSdNonFineSourceReleaseExists( releaseInfo )
			
		raise PtpUploaderException( "Can't check whether the release '%s' exists on PTP because its type is unsupported." % releaseInfo.ReleaseName );