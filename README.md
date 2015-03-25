Filesorter takes care of moving completed download to their proper position in a download-box.
It is meant to monitor a folder with complete downloads periodically, actually in a cronjob.

The found files will be moved based on a set of rules and some mail will be sent to notify of what happened.
If a Kodi (ex XBMC) is configured, we can also ask the media center to update the video library when the files are
at their place.

Everything is based on a configuration file, watch as an example `rules.json` for all the possible options.

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
		*	FILESORTER_MAIL_FROM
		*	FILESORTER_MAIL_PASSWORD
		
And now the more important part, the rules of how the files will be moved.
They are defined with two groups of settings: rules and types.

## Using the rules ##

Each rules try to match each file found in the source folder, and if it match it gets a score called confidence.
The rule matching with the higher score (if one) will decide what to do with the file.

As an example
"rules":[
	{"match": "stalker",
     "to": "Serie/Stalker"}
]

will match each file, with the word "Big Bang Theory" in the path relative to the source folder...
The string Big.Bang-Theory for example would also match the rule, but with a lower confidence.
If the rule match and has the higher score, the file will be moved (the default action) to the folder specified in "to"
under the "target" global folder definition.
