"""
Flingo Play

This is a service that runs in the background, doing a flingo.tv longpoll to
wait for videos being flung in this direction.  Settings control what is done when
a new video arrives ... Play It, Let the user know, or ignore it.  You can also 
configure whether to pop from top or bottom of queue (longpoll does not know which
vid to play, only that the queue item count has changed).
"""
import sys
import os
import xbmc
import xbmcgui
import xbmcaddon
import socket

import uuid
import httplib, urllib
import re

settings = xbmcaddon.Addon(id='script.service.flingo')

ROOT_FOLDER = settings.getAddonInfo('path')
RESOURCE_FOLDER = os.path.join(str(ROOT_FOLDER), 'resources')
LIB_FOLDER = os.path.join(str(RESOURCE_FOLDER), 'lib')
WORKING_FOLDER = os.path.normpath( xbmc.translatePath(settings.getAddonInfo("profile")) )
LINKS_FOLDER = os.path.join(str(WORKING_FOLDER), 'links')
REAL_LINK_PATH = os.path.join(str(WORKING_FOLDER), 'links')
USERINFO_FOLDER = WORKING_FOLDER
XBMCPROFILE = xbmc.translatePath('special://profile')

PLUGIN_USERINFO = os.path.join( os.path.dirname( str(USERINFO_FOLDER) ), 'plugin.video.flingo/userinfo.txt' )

try:
    import json as simplejson
    if not hasattr( simplejson, "loads" ):
        raise Exception( "Hmmm! Error with json %r" % dir( simplejson ) )
except Exception, e:
    print "[FlingoPlay] %s" % str( e )
    import simplejson

service = None

# This UUID is not used.  The persistent GUID for this device is kept in a file, 
# generated if the file does not exist.
#
UUID = '9f3ab0ca-01ca-11e2-a1f4-b8ac6f8bf825'

class Service:

    def __init__(self, guid):
        self.guid = guid
        self.post_headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}

    def announce(self):
        hostname = socket.gethostname()
        params = urllib.urlencode({'guid': self.guid, 
                                   'name': 'XBMC Queue', 
                                   'description': 'XBMC Flingo Queue on ' + hostname, 
                                   'make': 'XBMC', 
                                   'model': 'XBMC', 
                                   'dev_name': 'XBMC Queue', 
                                   'dev_description': 'XBMC Flingo Queue on ' + hostname, 
                                   'version': '0.1'})
        try:
            conn = httplib.HTTPConnection("flingo.tv")
            conn.request("POST", "/fling/announce", params, self.post_headers)
            res = conn.getresponse()
        except:
            return({'error': 'Failed to send announcement'})

        data = {}
        if res.status == 200:
            try:
                data = simplejson.loads( res.read() )
            except:
                data = {'error': 'Failed to parse JSON'}
        else:
            data = {'error': 'Bad Status', 'status': res.status, 'reason': res.reason}

        return data

    def discover(self):
        try:
            conn = httplib.HTTPConnection("flingo.tv")
            conn.request("POST", "/fling/discover")
            res = conn.getresponse()
        except:
            return({'error': 'Failed to discover'})

        data = {}
        if res.status == 200:
            try:
                data = simplejson.loads( res.read() )
            except:
                data = {'error': 'Failed to parse JSON'}
        else:
            data = {'error': 'Bad Status', 'status': res.status, 'reason': res.reason}

        return data

    def longpoll(self):
        params = urllib.urlencode({'guid': self.guid, 'wait': '3000'})
        try:
            conn = httplib.HTTPConnection("flingo.tv", timeout=30)
            conn.request("POST", "/fling/longpoll", params, self.post_headers)
            res = conn.getresponse()
        except:
            return({'error': 'FAILED TO LONGPOLL'})

        data = {}
        if res.status == 200:
            try:
                data = simplejson.loads( res.read() )
                # print simplejson.dumps( data, indent=2 )
            except:
                data = {} # This is OK
        else:
            data = {'error': 'Bad Status', 'status': res.status, 'reason': res.reason}

        return data

    def queue(self, start, num):
        p = {'guid': self.guid}
        if start != None:
            p['index'] = start
        if num != None:
            p['howmany'] = num
        params = urllib.urlencode(p)
        try:
            conn = httplib.HTTPConnection("flingo.tv")
            conn.request("POST", "/fling/queue", params, self.post_headers)
            res = conn.getresponse()
        except:
            return({'error': 'Failed to get queue'})

        data = {}
        if res.status == 200:
            try:
                string = res.read()
                data = simplejson.loads( string )
            except:
                data = {} # This is OK
        else:
            data = {'error': 'Bad Status', 'status': res.status, 'reason': res.reason}

        return data

    def rm(self,id):
        params = urllib.urlencode({'guid': self.guid, 'link_id': id})
        try:
            conn = httplib.HTTPConnection("flingo.tv")
            conn.request("POST", "/fling/remove_queue", params, self.post_headers)
            res = conn.getresponse()
        except:
            return({'error': 'Failed to remove from queue'})

        data = {}
        if res.status == 200:
            try:
                data = simplejson.loads( res.read() )
            except:
                data = {} # This is OK
        else:
            data = {'error': 'Bad Status', 'status': res.status, 'reason': res.reason}

        return data

    def get_vimeo_url(self,data):
        context = data['deobfuscator_context']
        params = urllib.urlencode({'video_id': context})
        try:
            conn = httplib.HTTPConnection("flingo.tv")
            conn.request("POST", "/api/vimeo", params, self.post_headers)
            res = conn.getresponse()
        except:
            return None
        if res.status == 200:
            return res.read()
        else:
            return None

# Return the persistent GUID, or generate and save a new one.
#
def getUUID():
    path = os.path.join( str(USERINFO_FOLDER), 'userinfo.txt' )
    # If the script.service.flingo version exists, use that
    if os.path.isfile( PLUGIN_USERINFO ):
        path = PLUGIN_USERINFO
    UUID = None
    if os.path.isfile( path ):
        f = open( path )
        s = f.read()
        f.close()
        reobj = re.compile( r"guid=(.*)\n")
        match = reobj.search( s )
        if match:
            UUID = match.group(1).strip()
    if UUID == None:
        UUID = str( uuid.uuid4() )
        if not os.path.isdir( str(USERINFO_FOLDER) ):
            os.makedirs( str(USERINFO_FOLDER) )
        f = open( os.path.join( str(USERINFO_FOLDER), 'userinfo.txt' ), 'w' )
        f.write( 'guid=' + UUID + '\n' )
        f.close()
    return UUID

# Extract reliable metadata from a queue item for display
#
def metadata(item):
    md = {}
    md['title'] = item.has_key('title') and item['title'] or 'No Title'
    md['description'] = item.has_key('description') and item['description'] or 'No Description'
    md['publisher'] = item.has_key('publisher') and item['publisher'] or 'No Publisher'
    image = None
    if item.has_key('image'):
        image = item['image']
    if not image and item.has_key('coverimage'):
        image = item['coverimage']
    if not image and item.has_key('thumbnail'):
        image = item['thumbnail']
    icon = None
    if item.has_key('thumbnail'):
        icon = item['thumbnail']
    if not image:
        image = defaultImage()
    if not icon:
        icon = image
    md['image'] = image
    md['icon'] = icon
    url = None
    dur = '0'
    if item.has_key( 'page_url' ) and re.match('.*vimeo.*', item['page_url']):
        # Vimeo can be reverse engineered
        url = service.get_vimeo_url( item )
    elif item.has_key( 'encodings' ):
        # Pick the first encoding choise out of lazyness
	if item['encodings'][0].has_key('url'):
          url = item['encodings'][0]['url']
	if item['encodings'][0].has_key('duration'):
          dur = str(item['encodings'][0]['duration'])
    md['url'] = url
    md['dur'] = dur

    if url == None:
        print "[Flingo Play] Cannot play:"
        print simplejson.dumps( item, indent=2 )

    return md

if (__name__ == '__main__'):
    UUID = getUUID()
    print "[FlingoPlay] GUID=%s" % UUID
    service = Service( UUID )
    res = service.announce()
    if res.has_key('error'):
        print "[FlingoPlay] Error: %s" % res['error']
        sys.exit(1)

    # Longpoll returns when the queue changes, not just when a vid is flung.
    # So a removal can trigger a longpoll.  To avoid playing a video when 
    # the queue has been deleted from, we need to keep track of the queue size.
    # We only view a vid if the queue size is greater than when we last looked at
    # it.
    #
    # Get a reference queue size ...
    #
    QSIZE = 0
    res = service.queue(None,None)
    if res.has_key('count'):
        QSIZE = int( res['count'] )

    while (not xbmc.abortRequested):
        # print "[FlingoPlay] Starting longpoll ..."
        res = service.longpoll()
        if res.has_key('error'):
            print "[FlingoPlay] Error: %s" % res['error']
        # print "[FlingoPlay] Return from longpoll ..."
        if res.has_key('method') and res['method'] == 'update':
            fopt = int(settings.getSetting("fopt"))
            qopt = int(settings.getSetting("qopt"))
            print "[FlingoPlay] Its an update and options are: fopt=%d, qopt=%d" % (fopt, qopt)
            if fopt != 2:
                # 2 means to ignore
                res = service.queue(None,None)
                item = None
                if res.has_key('count') and res.has_key('items'):
                    # Check to see if this was an add or a remove!
                    if int( res['count'] ) > QSIZE:
                        QSIZE = res['count']
                        items = res['items']
                        if qopt == 0:
                            # top
                            item = items[0]
                        else:
                            item = items[ int(res['count']) - 1 ]
                    else:
                        QSIZE = res['count']

                if item != None:
                    md = metadata( item )
                    if md['url'] == None:
                        # Can't play this ... YouTube for example uses .swf based
                        # obfuscator dohicky, which I don't think I can deal with
                        # here ...
                        print "[FlingoPlay] Cannot play '%s' on this device." % md['title']
                        dialog = xbmcgui.Dialog()
                        ok = dialog.ok("Flingo Play: Cannot Play.", md['title'])
                    elif fopt == 0:
                        # Play it
                        print "[FlingoPlay] Playing %s" % md['url']
                        playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
                        playlist.clear()
                        playlist.add(md['url'])
                        xbmc.Player().play( playlist)
                    else:
                        # Prompt the user
                        print "[FlingoPlay] Prompting user that video has arrived"
                        dialog = xbmcgui.Dialog()
                        ok = dialog.ok("Flingo Play: A new video has been queued.", md['title'])
            else:
                print "[FlingoPlay] User has elected to ignore flings."
