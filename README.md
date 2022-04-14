# No longer maintained

I do not use this program anymore, so it is no longer maintained. Use [this](https://github.com/kannibalox/PtpUploader) fork instead.

#### Original README

With the PtpUploader's WebUI you can upload to PTP by specifying a torrent file and an IMDb or PTP link.
There is also an automatic mode built-in that can check announcements from IRC or RSS and upload everything automatically.

Supported sites for automatic mode:
* AlphaRatio
* Cinemageddon
* Cinematik
* DigitalHive
	* Thanks to CoFix!
* GFT
* HDBits
	* Thanks to cerbere!
* HD-Torrents
	* Thanks to Mako_1!
*  Karagarga
* TorrentBytes
* TorrentLeech
* FunFile
	* Thanks to dhosha!

SceneAccess support was removed on the 9th of July 2013 because of staff pressure...
RevolutionTT support was removed on the 15th of May 2015 because of staff pressure...

There is a helper [Greasemonkey script](https://raw.githubusercontent.com/TnS-hun/PtpUploader/master/PtpUploaderTorrentSender.user.js) available at to send torrents from a wide variety of sites directly to PtpUploader.

#### Command line only usage

PtpUploader can create release description (with media info and screenshots) for manual uploading from command line.
Syntax:
* `ReleaseInfoMaker.py <target directory or filename>` creates the release description and starts seeding the torrent.
* `ReleaseInfoMaker.py --notorrent <target directory or filename>` creates the release description.
		
Use the resulting torrent that starts with PTP for uploading to the tracker.

#### Questions, help

Support is provided on [PTP](https://passthepopcorn.me/forums.php?action=viewthread&threadid=9245).
