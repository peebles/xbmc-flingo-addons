"""
Flingo TV Queue/Player for XBMC

Announce, then display the Flingo queue
"""
import sys
import os
import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import socket

import uuid
import httplib, urllib
import re

settings = xbmcaddon.Addon(id='plugin.video.flingo')
# dbg = settings.getSetting("debug") == "true"
ROOT_FOLDER = settings.getAddonInfo('path')
RESOURCE_FOLDER = os.path.join(str(ROOT_FOLDER), 'resources')
LIB_FOLDER = os.path.join(str(RESOURCE_FOLDER), 'lib')
WORKING_FOLDER = os.path.normpath( xbmc.translatePath(settings.getAddonInfo("profile")) )
LINKS_FOLDER = os.path.join(str(WORKING_FOLDER), 'links')
REAL_LINK_PATH = os.path.join(str(WORKING_FOLDER), 'links')
USERINFO_FOLDER = WORKING_FOLDER
XBMCPROFILE = xbmc.translatePath('special://profile')

# The userinfo.txt file (with persistent GUID) might be
# in the working folder for the script.service.flingo addon
# if that was started first.  That addon will also consider
# this addon's file.  script.service.flingo (the longpoll
# handler) must operate as a standalone thing.
#

SERVICE_USERINFO = os.path.join( os.path.dirname( str(USERINFO_FOLDER) ), 'script.service.flingo/userinfo.txt' )

print "[FlingoTV] root folder: " + ROOT_FOLDER
print "[FlingoTV] working folder: " + WORKING_FOLDER
print "[FlingoTV] links folder: " + LINKS_FOLDER
print "[FlingoTV] real link path: " + REAL_LINK_PATH
print "[FlingoTV] resource folder: " + RESOURCE_FOLDER
print "[FlingoTV] lib folder: " + LIB_FOLDER
print "[FlingoTV] userinfo folder: " + USERINFO_FOLDER

try:
    import json as simplejson
    if not hasattr( simplejson, "loads" ):
        raise Exception( "Hmmm! Error with json %r" % dir( simplejson ) )
except Exception, e:
    print "[FlingoTV] %s" % str( e )
    import simplejson

thisPlugin = int(sys.argv[1])
service = None

"""
The GUID for this device is stored in USERINFO_FOLDER/userinfo.txt
"""
UUID = '9f3ab0ca-01ca-11e2-a1f4-b8ac6f8bf825'

class Service:

    def __init__(self, guid):
        self.guid = guid
        self.post_headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}

    def announce(self):
        hostname = socket.gethostname()
        params = urllib.urlencode({'guid': self.guid, 
                                   'name': 'XBMC Queue', 
                                   'description': 'XBMC Flingo Queue on' + hostname, 
                                   'make': 'XBMC', 
                                   'model': 'XBMC', 
                                   'dev_name': 'XBMC Queue', 
                                   'dev_description': 'XBMC Flingo Queue on ' + hostname, 
                                   'version': '0.1'})
        conn = httplib.HTTPConnection("flingo.tv")
        conn.request("POST", "/fling/announce", params, self.post_headers)
        try:
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
        conn = httplib.HTTPConnection("flingo.tv")
        conn.request("POST", "/fling/discover")
        try:
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
        params = urllib.urlencode({'guid': self.guid})
        conn = httplib.HTTPConnection("flingo.tv")
        conn.request("POST", "/fling/longpoll", params, self.post_headers)
        try:
            res = conn.getresponse()
        except:
            return({'error': 'Failed to longpoll'})

        data = {}
        if res.status == 200:
            try:
                data = simplejson.loads( res.read() )
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
        conn = httplib.HTTPConnection("flingo.tv")
        conn.request("POST", "/fling/queue", params, self.post_headers)
        try:
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
        conn = httplib.HTTPConnection("flingo.tv")
        conn.request("POST", "/fling/remove_queue", params, self.post_headers)
        try:
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
        conn = httplib.HTTPConnection("flingo.tv")
        conn.request("POST", "/api/vimeo", params, self.post_headers)
        try:
            res = conn.getresponse()
        except:
            return None
        if res.status == 200:
            return res.read()
        else:
            return None

# Extract URL-style parameters from the string passed
# into this plugin when performing sub-actions.  This
# is a lot like CGI ...
#
def getParameters(parameterString):
    commands = {}
    splitCommands = parameterString[parameterString.find('?') + 1:].split('&')

    for command in splitCommands:
        if (len(command) > 0):
            splitCommand = command.split('=')
            key = splitCommand[0]
            value = splitCommand[1]
            commands[key] = value

    return commands

# Execute a plugin action
#
def executeAction(args):
    global service
    if args['action'] == 'remove':
        service.rm( args['link_id'] )
        xbmc.executebuiltin("Container.Refresh")

# Return the persistent GUID, or generate and save a new one.
#
def getUUID():
    path = os.path.join( str(USERINFO_FOLDER), 'userinfo.txt' )
    # If the script.service.flingo version exists, use that
    if os.path.isfile( SERVICE_USERINFO ):
        path = SERVICE_USERINFO
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

# If I wasn't lazy, I'd return a default 256x256 png to display
# when/if a queue item does not have an image.
#
def defaultImage():
    return None

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
    return md

if (__name__ == '__main__'):
    UUID = getUUID()
    service = Service( UUID )

    if sys.argv[2]:
        # Perform a sub-action
        args = getParameters(sys.argv[2])
        executeAction( args )
    else:
        res = service.announce()
        if res.has_key('error'):
            print "[FlingoTV] Error: %s" % res['error']
        res = service.queue(None, None)
        if res.has_key('error'):
            print "[FlingoTV] Error: %s" % res['error']
        if res.has_key( 'items' ):
            for item in res['items']:
                print "[FlingoTV] item: %s" % repr(item['title'])
                md = metadata( item )
                if md['url'] != None:
                    listitem = xbmcgui.ListItem(md['title'],
                                                '[' + md['publisher'] + ']',
                                                iconImage=md['icon'], 
                                                thumbnailImage=md['image'])
                    # Add metadata for vids; as much as Flingo supplies
                    listitem.setInfo( type='video',
                                      infoLabels={'title': md['title'],
                                                  'duration': md['dur'],
                                                  'plot': md['description']})
                    # Attach our link id for context menu operations
                    listitem.setProperty('link_id', item['link_id'])
                    # Add the context menu operations
                    cm = []
                    cm.append(( 'Remove from Queue',
                                "XBMC.RunPlugin(%s?action=remove&link_id=%s&)" % (sys.argv[0], item['link_id'])))
                    listitem.addContextMenuItems(cm, False)
                    # Add it along with the playable url
                    xbmcplugin.addDirectoryItem(thisPlugin,md['url'],listitem)

            xbmcplugin.endOfDirectory(thisPlugin)

