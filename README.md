Afterdown
=========

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/67b2d500b61a476b9bbe4a01726be8f2)](https://www.codacy.com/app/dariosky/afterdown?utm_source=github.com&utm_medium=referral&utm_content=dariosky/afterdown&utm_campaign=badger)

Afterdown takes care of moving files from a source folder to their proper position in a target folder using a set of
user defined rules.

It is meant to periodically check a folder with complete downloads (actually using a cronjob) and move the
files there in their correct position (for example in some Kodi monitored folder).

The set of rules can match the file using simple string matching, regex, filesize, looking file type and are
user defined and inheritable.

An example configuration file can be found in `tests/playground/rules.json` for all the possible options.

When some rule apply (and we have only have a rule with max confidence) some action can be applyed:
*ignore the file*, *delete it* or *move it* to target folder subfolder.
At the end we can decide to receive a summary via mail or if a Kodi (ex XBMC) is configured,
we may want to ask the media center to update the video library when the files are at their place.

Quickstart
----------

1.	Download the repository or clone it with git

		git clone https://github.com/dariosky/afterdown.git

2.	Edit the example_rules.json file to define your rules,
	for example setting your TV serie folders and defining your email address
	to receive the notifications.
	
	Save your rules files as *rules.json*. 
	
	Note that to send the email, your system should be able to send email,
	otherwise you can configure something like [Mandrill](http://mandrillapp.com).
	
3.	Run afterdown.py, use `afterdown -h` to get the options (you can for example,
	change the source and destination folder from the command line).
	
	If your rules files if different than rules.json, specify the correct name with the
	`-c <rule_file_name>` command option.

Configuration
-------------

The configuration is a json file, with some global option (like the source and target folders) and the
definition of the rules.

First of all we need to setup the source folder (the folder to monitor) and the target folder that will be the
base for all our rules targets.

All paths when not absolute are relative to the current folder.

*	"source":	Define the source folder
*	"target":	Define the target folder, this path will be joined with the target of the single rules

(that can be also specified or overriden in the command line)

We can optionally setup the Kodi connection

*	kodi
	*	"host":	Define the hostname of kodi (default: localhost)
	*	"requestUpdate": true/false	(if on movement we have to ask Kodi to update)
	
From the commandline, you can disable Kodi with the --nokodi option.

Optionally the mail configuration

*	mail
	*	smtp:	Set the SMTP server for mail notification, default to "localhost:25"
	*	subject:	The mail subject
	*	to:	The mail recipient list
	
	Optionally we can add
	*	from:	the mail from (and also the username to login on SMTP if password is specified)
	*	password: the mail password for the user specified in "from" (if SMTP needs login)
	
	Specifying username and password in a config file is not great, so eventually you can set it on
	**environment variables**:
	
		AFTERDOWN_MAIL_FROM
		AFTERDOWN_MAIL_PASSWORD
		
Dropbox integration
-------------------

After applying the rules to the source folder, Afterdown can read a folder on your connected
Dropbox account in order to search torrent files to add to your local Transmission daemon
(well, I told you that Afterdown was made mostly to automate a downloader?).

The initial setup require that you connect your account, and actually you have to create
a Dropbox app in the [Developer Console](https://www.dropbox.com/developers/apps).
You'll obtain an app_key and an app_secret, you need create a file (in the current folder) named
`.afterdown_dropbox_keys.json` and you have to put that "secret there":

	{
		"app_key": "your_app_key"
		"app_secret": "your_app_secret",
	}

this file should be kept confidential, and probably should be read and write by only the user
running afterdown.py. You'll need also write access, because when the app will be linked to
an account an access_token will be added there as well.

Then in Afterdown configuration files specify that you want the Dropbox sync,
that would be something like this:

	 "dropbox": {
        "start_torrents_on": "/torrents",
        "add_torrent_to_transmission": true,
        "move_them_on": "/torrents/archive"
      },

This mean:
 
- search all torrents file in the Dropbox "/torrents" folder
- add them to Transmission (will invoke `transmission-remote -a <torrentfile>`)
- if everything is ok, move the torrent file in the "/torrents/archive" Dropbox folder

When Transmission ends the download, it should put the files on the source folder, then when
Afterdown runs again will move them to the target folder, warns Kodi and you'll be happy
ever after!

If you setup the Dropbox sync in the configuration, you can override and disable it from the commandline
with the --nodropboxsync option flag.


Using the rules
---------------

The most important part is of course the rules specifying how the files should be moved.
They are defined with two groups of settings: rules and types.

Each rules try to match each file found in the source folder,
 and if it match it gets a score called confidence.
The rule matching with the higher score (if one) will decide what to do with the file.

As an example

	"rules":[
		{"match": "Big Bang Theory",
		 "to": "Serie/Big Bang Theory"}
	]

will match each file, with the word "Big Bang Theory" in the path relative to the source folder...
The string Big.Bang-Theory for example would also match the rule, but with a lower confidence.
If the rule match and has the higher score, the file will be moved (the default action) to the folder specified in "to"
under the "target" global folder definition.

We can also match using a regex, specify them in Javascript-like format:

	match: "/big\s+bang/s+theory/i"

The default rule priority is 50 (and only 80% of it will be taken when a non exact match is found), can be defined with
`"priority": 50`

You can also define other actions:

	"action": "move"	the default, require the "to" parameter to be also set
	"action": "skip"	will ignore the file, leaving it on the source folder (this wouldn't trigger the notification email)
	"action": "delete"	delete the file from the source folder

We can match the filename, but we can also add other filters:

	"extension": ["avi", "mp4"]	will match the file extensions
	"size": ">500MB"	will match the file size (we can specify normal operator and a suffix M, K, B)

When moving a file we can decide to specify other options:

	"folderSplit": true		Will create a folder named like the filename (without extension) inside the current target. Useful in Kodi if a target folder is set as (each film in its subfolder)
	"seasonSplit": true		Will try to extract the season&episode number from the filename and will put the files in target/Sxx/ folder

	"overwrite": "skip" | "rename" | "overwrite"	decide what to do when file exists on destination (default: skip)
	"updateKodi": false		When set, even if the rule move the file, an update won't be triggered to Kodi

Types
-----

Common settings can be reused using types.

Types are a special kind of rules, with a name, that can be inherited by real rules in a hierarchical way.

For example, if you create many rules to move various kind of movie in different folders, and all the movies
must have size > 500MB and file extensions in ("avi", "mkv"), you can simplify your configuration in this way:

	"rules": [{"target":"folder1", "match": "film1", "type":"film"},
			  {"target":"folder2", "match": "film2", "type":"film"}]
	"types": [{"name":"film", "size": ">500MB", "extensions":["avi", "mkv"]}]

You can also have multiple inheritance by using the plural version "types" to specify an array of "types" name.
This apply for many parameters `match:"string"` can be used instead of `matches:["string",...]` when we need only one
possible match. The same for extension/extensions.
