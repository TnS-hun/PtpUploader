'''

jQuery File Tree
http://abeautifulsite.net/blog/2008/03/jquery-file-tree/

jQuery File Upload
https://github.com/blueimp/jQuery-File-Upload/

'''

from Job.JobStartMode import JobStartMode

from Authentication import requires_auth
from Database import Database
from Globals import Globals
from NfoParser import NfoParser
from Ptp import Ptp
from PtpUploader import PtpUploader
from ReleaseInfo import ReleaseInfo
from Settings import Settings

from flask import Flask, jsonify, render_template, request, redirect, url_for
from werkzeug import secure_filename

import os
import re
import urlparse

app = Flask(__name__)

def IsFileAllowed(filename):
	root, extension = os.path.splitext( filename )
	return extension == ".torrent"

def GetYouTubeId(text):
	url = urlparse.urlparse( text )
	if url.netloc == "youtube.com" or url.netloc == "www.youtube.com":
		params = urlparse.parse_qs( url.query )
		youTubeId = params.get( "v" )
		if youTubeId is not None:
			return youTubeId

	return ""

def GetPtpOrImdbId(releaseInfo, text):
	imdbId = NfoParser.GetImdbId( text )
	if len( imdbId ) > 0:
		releaseInfo.ImdbId = imdbId 
	else:
		# Using urlparse because of torrent permalinks:
		# https://passthepopcorn.me/torrents.php?id=9730&torrentid=72322
		url = urlparse.urlparse( text )
		if url.netloc == "passthepopcorn.me" or url.netloc == "www.passthepopcorn.me":
			params = urlparse.parse_qs( url.query )
			ptpId = params.get( "id" )
			if ptpId is not None:
				releaseInfo.PtpId = ptpId

@app.route( '/', methods=[ 'GET', 'POST' ] )
@requires_auth
def index():
	if request.method == 'POST':
		release = ReleaseInfo()
	
		file = request.files.get( "file_input" )
		if ( file is not None ) and IsFileAllowed( file.filename ):
			filename = secure_filename( file.filename )
			release.SourceTorrentPath = os.path.join( Settings.GetTemporaryPath(), filename )
			file.save( release.SourceTorrentPath )
		
		# Announcement
		release.AnnouncementSourceName = "torrent" # TODO
		release.ReleaseName = file.filename.replace( ".torrent", "" )  # TODO
		#release.AnnouncementSourceName = "" # TODO: announcementSource # A name of a class from the Source namespace.
		#release.AnnouncementId = "" # TODO: announcementId
		#release.ReleaseName = request.values[ "" ]

		forceUpload = request.values.get( "force_upload" )
		if forceUpload is None:
			release.JobStartMode = JobStartMode.Manual
		else:
			release.JobStartMode = JobStartMode.ManualForced

		# For PTP		
		release.Type = request.values[ "type" ]
		GetPtpOrImdbId( release, request.values[ "imdb" ] )
		release.Directors = request.values[ "artists[]" ]
		release.Title = request.values[ "title" ]
		release.Year = request.values[ "year" ]
		release.Tags = request.values[ "tags" ]
		release.MovieDescription = request.values[ "album_desc" ]
		release.CoverArtUrl = request.values[ "image" ]
		release.YouTubeId = GetYouTubeId( request.values[ "trailer" ] )
		release.MetacriticUrl = request.values[ "metacritic" ]
		release.RottenTomatoesUrl = request.values[ "tomatoes" ]
		
		release.Scene = request.values.get( "scene" )
		if release.Scene is not None:
			release.Scene = "on"
		
		quality = request.values[ "quality" ]
		if quality != "---":
			release.Quality = quality

		codec = request.values[ "codec" ]
		if codec != "---":
			release.Codec = codec
			 
		release.CodecOther = request.values[ "other_codec" ]

		container = request.values[ "container" ]
		if container != "---": 
			release.Container = container
		
		release.ContainerOther = request.values[ "other_container" ]
		
		resolutionType = request.values[ "resolution" ]
		if resolutionType != "---": 
			release.ResolutionType = resolutionType
		
		release.Resolution = request.values[ "other_resolution" ] 
		
		source = request.values[ "source" ]
		if source != "---":
			release.Source = source
			
		release.SourceOther = request.values[ "other_source" ]
		
		release.ReleaseDescription = request.values[ "release_desc" ]
		release.RemasterTitle = request.values[ "remaster_title" ]
		release.RemasterYear = request.values[ "remaster_year" ]
		
		# Other
		#release.InternationalTitle = "" # International title of the movie. Eg.: The Secret in Their Eyes. Needed for renaming releases coming from Cinemageddon.
		#release.Nfo = u""
		#release.SourceTorrentInfoHash = ""
		#release.ReleaseUploadPath = "" # Empty if using the default path. See GetReleaseUploadPath.
		
		# TODO: error if no ptp and imdb id presents
		
		Database.DbSession.add( release )
		Database.DbSession.commit()
		
		PtpUploader.AddToDatabaseQueue( release.Id )
	
	return render_template('index.html')

@app.route( '/jobs/' )
@requires_auth
def jobs():
	text = ""
	for releaseInfo in Database.DbSession.query( ReleaseInfo ):#.order_by( DbRelease.id ):
		text += "Id: %s, Title: %s<br/>" % ( releaseInfo.Id, releaseInfo.ReleaseName )
		
	return text

@app.route( '/job/<int:jobId>/' )
@requires_auth
def job(jobId):
	text = ""
	
	releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()
	
	text += "Id: %s<br/>IMDb id: %s" % ( releaseInfo.Id, releaseInfo.ImdbId )
		
	return text

# TODO: make it more simple: preset for: SD, 720p, 1080p
@app.route( "/checkifexists/", methods=[ "GET", "POST" ] )
@requires_auth
def checkIfExists():
	if request.method == 'POST':
		Ptp.Login()
		
		releaseInfo = ReleaseInfo()		
		releaseInfo.Codec = request.values[ "codec" ]
		releaseInfo.Container = request.values[ "container" ]
		releaseInfo.ResolutionType = request.values[ "resolution" ]
		releaseInfo.Source = request.values[ "source" ]
		
		if releaseInfo.ResolutionType == "720p" or releaseInfo.ResolutionType == "1080p":
			releaseInfo.Quality = "High Definition"
		else:
			releaseInfo.Quality = "Standard Definition"
		
		imdbIds = request.values[ "imdb" ]
		
		resultHtml = ""
	   
		matches = re.findall( r"imdb.com/title/tt(\d+)", imdbIds )
		for match in matches:
			movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId( Globals.Logger, match )
			existingRelease = movieOnPtpResult.IsReleaseExists( releaseInfo )
			if existingRelease is None: 
				resultHtml += """<a href="http://www.imdb.com/title/tt%s">%s</a> - NOT ON PTP</br>""" % ( match, match )
			else:
				resultHtml += """<a href="http://www.imdb.com/title/tt%s">%s</a> - <a href="http://passthepopcorn.me/torrents.php?id=%s">PTP</a></br>""" % ( match, match, movieOnPtpResult.PtpId )
			
		return resultHtml

	return render_template( "checkifexists.html" )