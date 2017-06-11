from __future__ import unicode_literals

import json
import logging
import os
import posixpath
import tempfile
from subprocess import CalledProcessError, check_output

logger = logging.getLogger("afterdown.dropbox")


def dropbox_sync(keyfile,
                 torrents_folder,
                 add_to_transmission,
                 move_downloaded_on,
                 ):
    try:
        # noinspection PyUnresolvedReferences
        import dropbox
    except ImportError:
        logger.error("To use Dropbox syncronization you need the Dropbox package.")
        logger.error("Use: pip install dropbox.")
        return
    if not os.path.isfile("%s" % keyfile):
        logger.error(
            "To sync with Dropbox you need a %s file with app_key and app_secret" % keyfile
        )
        return
    dropbox_config = json.load(open(keyfile, "r"))
    if "app_key" not in dropbox_config or "app_secret" not in dropbox_config:
        logger.error(
            "The dropbox config should be a json file with with app_key and app_secret")
        return
    # everything is ok, we can start the Dropbox OAuth2
    if "access_token" not in dropbox_config:
        # we have the app, but no link to an account, ask to authorize
        app_key, app_secret = dropbox_config["app_key"], dropbox_config["app_secret"]
        print("Everything is set, going to Dropbox")
        flow = dropbox.client.DropboxOAuth2FlowNoRedirect(app_key, app_secret)
        authorize_url = flow.start()
        print('1. Go to: ' + authorize_url)
        print('2. Click "Allow" (you might have to log in first)')
        print('3. Copy the authorization code.')
        code = input("Enter the Dropbox authorization code here: ").strip()
        access_token, user_id = flow.finish(code)
        dropbox_config["access_token"] = access_token
        logger.info("Storing access_token to Dropbox account")
        with open(keyfile, "w") as f:
            json.dump(dropbox_config, f)
    else:
        # we can reuse the access_token
        access_token = dropbox_config["access_token"]

    results = []
    try:
        if torrents_folder:
            client = dropbox.client.DropboxClient(access_token)
            logger.debug("Sync with Dropbox account %s" % client.account_info()['email'])
            folder_meta = client.metadata(torrents_folder)
            for content in filtered(folder_meta):
                logger.info(
                    "%s %s %s" % (content['path'], "by", content["modifier"]["display_name"]))
                if add_to_transmission:
                    results.append(
                        process_dropbox_file(client, content,
                                             add_to_transmission,
                                             move_downloaded_on,
                                             )
                    )
    except dropbox.rest.ErrorResponse as e:
        logger.error(e)
    return results


def filtered(folder_meta):
    for meta in folder_meta['contents']:
        ext = os.path.splitext(meta.get('path'))[-1]
        if meta.get('mime_type') == u'application/x-bittorrent' or ext == ".magnet":
            yield meta


def process_dropbox_file(dropbox_client, filemeta,
                         add_to_transmission, move_downloaded_on,
                         ):
    import dropbox

    # download the file to a temporary folder, then add it to transmission
    source_path = filemeta['path']
    ext = os.path.splitext(source_path)[-1]
    got_error = False

    with dropbox_client.get_file(source_path) as f:
        content = f.read()
        if ext == ".magnet":
            logger.debug("Processing magnet file %s" % source_path)
            for line in content.split():
                line = line.strip().decode('utf-8')
                if line:  # skip empty lines
                    if add_magnet_url(line) is False:
                        got_error = True
        else:
            # process the torrent
            with tempfile.NamedTemporaryFile(prefix="afterdown", suffix="temptorrent") as temp:
                # print "Get from torrent to tempfile %s" % temp.name

                temp.write(content)
                try:
                    check_output(
                        ["transmission-remote", "-a", temp.name, "--no-start-paused"]
                    )
                except CalledProcessError as e:
                    logger.error(
                        "Error parsing torrent: {error}".format(
                            error=e
                        )
                    )
                    got_error = True

        if got_error:
            logger.error(
                "Error running transmission-remote on file {path}".format(
                    path=source_path,
                )
            )
            source_path = None  # when erroring return None
        else:
            dropbox_move_target = move_downloaded_on
            if dropbox_move_target:
                filename = os.path.basename(source_path)
                target_path = posixpath.join(dropbox_move_target, filename)
                try:
                    dropbox_client.file_move(source_path, target_path)
                except dropbox.rest.ErrorResponse as e:
                    logger.error(
                        "Error moving dropbox file from {source} to {target}.\n{error_message}".format(
                            source=source_path, target=target_path, error_message=e
                        ))
    return source_path


def add_magnet_url(url):
    if not url.startswith('magnet:'):
        logger.error("Magnet line %s does not seem a magnet url" % url)
    else:
        # add every single non empty line (that should be a magnet url)
        try:
            check_output(
                ["transmission-remote", "-a", url, "--no-start-paused"]
            )
            return True  # Success
        except CalledProcessError as e:
            logger.error(
                "Error parsing magnet: %s" % e
            )
    return False
