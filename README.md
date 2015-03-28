Afterdown takes care of moving completed download to their proper position in a download-box.
It is meant to monitor a folder with complete downloads periodically, actually in a cronjob.

The found files will be moved based on a set of rules and some mail will be sent to notify of what happened.
If a Kodi (ex XBMC) is configured, AD can also ask the media center to update the video library when the files are
at their place.

Everything is based on a configuration file, watch as an example `tests/playground/rules.json` for all the possible options.

# Configuration #

The configuration is a json file, with some global option (like the source and target folders), the
definition of the rules...

First of all we need to setup the source folder (the folder to monitor) and the target folder that will be the
base for all our rules targets.

*	"source":	Define the source folder, if the path is not absolute it will be relative to current folder
*	"target":	Define the target folder, this path will be joined with the target of the single rules

We can optionally setup the Kodi connection

*	kodi
	*	"host":	Define the hostname of kodi (default: localhost)
	*	"requestUpdate": true/false	(if on movement we have to ask Kodi to update)

Optionally the mail configuration

*	mail
	*	smtp:	Set the SMTP server for mail notification, default to "localhost:25"
	*	subject:	The mail subject
	*	to:	The mail recipient list
	
	Optionally we can add
	*	from:	the mail from (and also the username to login on SMTP if password is specified)
	*	password: the mail password for the user specified in "from"
	
	Probably specifying username and password in a config file is not great, so eventually you can set it on
	environment variables:
		*	AFTERDOWN_MAIL_FROM
		*	AFTERDOWN_MAIL_PASSWORD
		
And now the more important part, the rules of how the files will be moved.
They are defined with two groups of settings: rules and types.

## Using the rules ##

Each rules try to match each file found in the source folder, and if it match it gets a score called confidence.
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

The default rule priority is 50 (and only 80% of it will be taken when a non exact match is found), can be defined with
"priority": 50

You can also define other actions:
"action": "move"	the default, require the "to" parameter to be also set
"action": "skip"	will ignore the file, leaving it on the source folder (this wouldn't trigger the notification email)
"action": "delete"	delete the file from the source folder

With the match, we can match the filename, but we can also add other filters:
"extension": ["avi", "mp4"]	will match the file extensions
"size": ">500MB"	will match the file size (we can specify normal operator and a suffix M, K, B)

When moving a file we can decide to specify other options:
"folderSplit": true		Will create a folder named like the filename (without extension) inside the current target
"seasonSplit": true		Will try to extract the season&episode number from the filename and will put the files in
 						target/Sxx/	folder
"overwrite": "skip" | "rename" | "overwrite"	decide what to do when file exists on destination (default: skip)
"updateKodi": false		When set, even if the rule move the file, an update won't be triggered to Kodi

## Types ##

Common settings can be reused by using types.

Types are a special kind of rules that can be inherited by real rules in a hierarchical way.

For example, if you create many rules to move various kind of movie in different folders, and all the movies
should have size > 500MB and file extensions in ("avi", "mkv"), you can simplify your configuration in this way:

"rules": [{"target":"folder1", "match": "film1", "type":"film"}, {"target":"folder2", "match": "film2", "type":"film"}]
"types": [{"name":"film", "size": ">500MB", "extensions":["avi", "mkv"]}]

You can also have multiple inheritance by using the plural version "types" to specify an array of "types" name.

