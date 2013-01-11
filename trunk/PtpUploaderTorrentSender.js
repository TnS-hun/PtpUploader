﻿// ==UserScript==
// @name        PtpUploader Torrent Sender
// @author      TnS
// @description Creates a send to PtpUploader link on the torrent details page.
// @homepage    http://userscripts.org/scripts/show/133847
// @version     1.02
// @date        2013-01-11
// @namespace   http://greasemonkey.mozdev.com

// @include     http*://*all.hdvnbits.org/*
// @include     http*://*awesome-hd.net/torrents.php*
// @include     http*://*bit-hdtv.com/details.php*
// @include     http*://*chdbits.org/details.php*
// @include     http*://*cinemageddon.net/details.php*
// @include     http*://*fuckyeahtorrents.com/details.php*
// @include     http*://*hd-torrents.org/details.php*
// @include     http*://*hdahoy.net/torrents.php*
// @include     http*://*hdbits.org/details.php*
// @include     http*://*hdme.eu/details.php*
// @include     http*://*iptorrents.com/details.php*
// @include     http*://*iptorrents.me/details.php*
// @include     http*://*iptorrents.ru/details.php*
// @include     http*://*karagarga.net/details.php*
// @include     http*://*piratethenet.org/details.php*
// @include     http*://*pretome.info/details.php*
// @include     http*://*sceneaccess.eu/details*
// @include     http*://*tehconnection.eu/torrents.php*
// @include     http*://*thedarksyndicate.me/browse.php*
// @include     http*://*thegft.org/details.php*
// ==/UserScript==

// START OF SETTINGS

// Set the URL of your PtpUploader in the following link.
var ptpUploaderUrl = "http://address.of-ptpuploader.com:5500";

// The GreasemonkeyTorrentSenderPassword set in your Settings.ini.
var ptpUploaderTorrentSenderPassword = "password";

// Set this "true" (without the quotes) to open PTP and PtpUploader in a new tab, instead of the current tab
// when clicking on the PTP or the Up link.
var openPtpAndPtpUploaderInNewTab = false;

// END OF SETTINGS

function SendTorrentToPtpUploader( rawTorrentData, imdbUrl, sendToLink )
{
	var uploadUrl = ptpUploaderUrl + "/ajaxexternalcreatejob/";

	var formData = new FormData();
	formData.append( "Password", ptpUploaderTorrentSenderPassword );
	formData.append( "Torrent", rawTorrentData );
	formData.append( "ImdbUrl", imdbUrl );

	var xhr = new XMLHttpRequest();
	xhr.onload = function( e )
	{
		var showError = true;
		var error = this.response;

		if ( this.status == 200 )
		{
			var jsonResponse = JSON.parse( this.response );
			if ( jsonResponse && jsonResponse.result )
			{
				if ( jsonResponse.result == "OK" )
				{
					showError = false;

					sendToLink.innerHTML = "OK";
					sendToLink.onclick = function()
					{
						return false;
					};

					var editJobUrl = ptpUploaderUrl + "/job/" + jsonResponse.jobId + "/edit/"
					if ( openPtpAndPtpUploaderInNewTab )
						window.open( editJobUrl );
					else
						window.location = editJobUrl;
				}
				else
				{
					error = jsonResponse.message;
				}
			}
		}

		if ( showError )
			alert( "An error happened while trying to send the torrent to PtpUploader!\n\n" + error );
	};
	xhr.onerror = function()
	{
		alert( "An error happened while trying to send the torrent to PtpUploader!" );
	};
	
	xhr.open( 'POST', uploadUrl, true );
	xhr.send( formData );
}

function DownloadTorrent( downloadUrl, imdbUrl, sendToLink )
{
	// Use XMLHttpRequest Level 2.
	var xhr = new XMLHttpRequest();
	xhr.open( 'GET', downloadUrl, true );
	xhr.responseType = 'arraybuffer'; // blob response type resulted in gzipped response on SCC...
	xhr.onload = function( e )
	{
		if ( this.status == 200 )
		{
			var blob = new Blob( [ this.response ], { type: "application/x-bittorrent" } );
			SendTorrentToPtpUploader( blob, imdbUrl, sendToLink );
		}
		else
		{
			alert( "An error happened while trying to download the torrent from the source site!\n\n" + this.response );
		}
	};
	xhr.onerror = function()
	{
		alert( "An error happened while trying to download the torrent from the source site!" );
	};
	
	xhr.send();
}

function CreateSendToPtpUploaderLink( downloadLink, imdbUrl )
{
	var ptpLink = document.createElement( "a" );
	ptpLink.title = "Check movie page on PTP";
	ptpLink.innerHTML = "PTP";
	ptpLink.href = "https://tls.passthepopcorn.me/torrents.php?searchstr=" + imdbUrl;
	if ( openPtpAndPtpUploaderInNewTab )
		ptpLink.setAttribute( "target", "_blank" );

	downloadLink.parentNode.insertBefore( ptpLink, downloadLink );

	downloadLink.parentNode.insertBefore( document.createTextNode( " | " ), downloadLink );

	var sendToLink = document.createElement( "a" );
	sendToLink.title = "Send to PtpUploader";
	sendToLink.innerHTML = "Up";
	sendToLink.href = "#";
	sendToLink.onclick = function()
	{
		var downloadUrl = downloadLink.href;
		DownloadTorrent( downloadUrl, imdbUrl, sendToLink );
		return false;
	};

	downloadLink.parentNode.insertBefore( sendToLink, downloadLink );
	downloadLink.parentNode.insertBefore( document.createTextNode( " | " ), downloadLink );
}

// Make sure to get the correct IMDb link that is in the IMDB info section.
function IsCorrectAhdImdbUrl( urlNode )
{
	while ( true )
	{
		urlNode = urlNode.parentNode;
		if ( !urlNode )
			break;
		
		if ( urlNode.id && urlNode.id.indexOf( "movieinfo_" ) != -1 )
			return true;
	}

	return false;
}

function GetImdbUrl( urlNode, siteName )
{
	var url = urlNode.href;
	if ( /.*?imdb\.com.*?title.*?tt\d+.*/.test( url ) )
	{
		if ( siteName == "ahd" && !IsCorrectAhdImdbUrl( urlNode ) )
			return "";

		// Handle urlencoded anonymized IMDb links too. E.g.: http://anonym.to/?http%3A%2F%2Fakas.imdb.com%2Ftitle%2Ftt0401729
		return decodeURIComponent( url );
	}

	return "";
}

function Main()
{
	var downloadLinkRegEx = null;
	var siteName = null;
	var imdbUrl = "";

	if ( /https?:\/\/all\.hdvnbits\.org\/.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\?id=\d+.*/;
	else if ( /https?:\/\/.*?awesome-hd\.net\/torrents\.php\?id=.*/.test( document.URL ) )
	{
		downloadLinkRegEx = /torrents.php\?action=download.*?id=\d+.*/;
		siteName = "ahd";
	}
	else if ( /https?:\/\/.*?bit-hdtv\.com\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\?\/\d+\/.*/;
	else if ( /https?:\/\/.*?chdbits\.org\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\?id=\d+.*/;
	else if ( /https?:\/\/.*?cinemageddon\.net\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\?id=\d+.*/;
	else if ( /https?:\/\/.*?fuckyeahtorrents\.com\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\?torrent=\d+.*/;
	else if ( /https?:\/\/.*?hd-torrents\.org\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\?id=.+/;
	else if ( /https?:\/\/.*?hdahoy\.net\/torrents\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /torrents.php\?action=download.*?id=\d+.*/;
	else if ( /https?:\/\/.*?hdbits\.org\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\/.*?\?id=\d+.*/;
	else if ( /https?:\/\/.*?hdme\.eu\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\?torrent=\d+.*/;
	else if ( /https?:\/\/.*?iptorrents\.(?:com|me|ru)\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\/\d+\/.*/;
	else if ( /https?:\/\/.*?karagarga\.net\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /down.php\/\d+\/.*/;
	else if ( /https?:\/\/.*?piratethenet\.org\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\?torrent=\d+.*/;
	else if ( /https?:\/\/.*?pretome\.info\/details\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download.php\/\d+\/.*/;
	else if ( /https?:\/\/.*?sceneaccess\.eu\/details\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /download\/\d+\/.*/;
	else if ( /https?:\/\/.*?tehconnection\.eu\/torrents\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /torrents.php\?action=download.*?id=\d+.*/;
	else if ( /https?:\/\/.*?thedarksyndicate\.me\/browse\.php\?id=.*/.test( document.URL ) )
		downloadLinkRegEx = /browse.php\?action=download.*?id=\d+.*/;
	else if ( /https?:\/\/.*?thegft\.org\/details\.php\?id=.*/.test( document.URL ) )
	{
		downloadLinkRegEx = /download.php\?torrent=\d+.*/;

		// Links in the NFO are not linkified on GFT.
		var match = document.body.innerHTML.match( /imdb\.com\/title\/tt\d+/ );
		if ( match )
			imdbUrl = match[ 0 ];
	}

	if ( !downloadLinkRegEx )
		return;

	var allLinks = new Array();
	for ( var i = 0; i < document.links.length; ++i )
	{
		var urlNode = document.links[ i ];
		allLinks.push( urlNode );

		if ( imdbUrl.length <= 0 )
			imdbUrl = GetImdbUrl( urlNode, siteName );
	}

	if ( imdbUrl.length <= 0 )
		return;

	for ( var i = 0; i < allLinks.length; ++i )
	{
		var link = allLinks[ i ];
		if ( downloadLinkRegEx.test( link.href ) )
			CreateSendToPtpUploaderLink( link, imdbUrl );
	}
}

Main();
