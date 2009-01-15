#!/usr/bin/env python2.5

try:
    from xml.etree import ElementTree # for Python 2.5 users
except ImportError:
    from elementtree import ElementTree

import gdata.calendar.service
import gdata.service
import atom.service
import gdata.calendar
import atom
import getopt
import sys
import string
import time

# logging init 
import logging
logging.basicConfig(format="%(asctime)-15s %(message)s") 
log = logging.getLogger('rtmsimp') 
log.setLevel(logging.DEBUG)

# Globals
CONFIG_DEFAULT = 'simp.cfg'

def GetAuthSubUrl(next="https://wrd.nu/calsetup",
                  scope="http://www.google.com/calendar/feeds/",
                  secure=False,
                  session=True):

    calendar_service = gdata.calendar.service.CalendarService()
    return calendar_service.GenerateAuthSubURL(next, scope, secure, session)

def GetCalendarService(auth_token):
    calendar_service = gdata.calendar.service.CalendarService()
    calendar_service.auth_token = auth_token
    return calendar_service

def GetAuthSubSessionToken():
    authSubUrl = GetAuthSubUrl()

    try:
        import webbrowser
        webbrowser.open(authSubUrl)
    except:
        print 'Authorize @: %s' % authSubUrl

    authsub_token = raw_input("Copy the ?token variable out of the url: ")

    calendar_service = GetCalendarService(authsub_token)
    calendar_service.UpgradeToSessionToken()
    
    return calendar_service._GDataService__auth_token



def InsertSingleEvent(calendar_service, title='One-time Tennis with Beth', 
                      content='Meet for a quick lesson', location='On the courts', 
                      start_time=None, end_time=None):
    event = gdata.calendar.CalendarEventEntry()
    event.title = atom.Title(text=title)
    event.content = atom.Content(text=content)
    event.where.append(gdata.calendar.Where(value_string=location))

    if start_time is None:
      # Use current time for the start_time and have the event last 1 hour
      start_time = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
      end_time = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(time.time() + 3600))
    event.when.append(gdata.calendar.When(start_time=start_time, end_time=end_time))
    
    new_event = calendar_service.InsertEvent(event, '/calendar/feeds/default/private/full')
    
    print 'New single event inserted: %s' % (new_event.id.text,)
    print '\tEvent edit URL: %s' % (new_event.GetEditLink().href,)
    print '\tEvent HTML URL: %s' % (new_event.GetHtmlLink().href,)
    
    return new_event

if __name__=="__main__":
    from optparse import OptionParser
    arg = OptionParser(version="%prog 0.1")
    arg.add_option('-C','--config',dest="config_file",help="Path to config file")
    arg.add_option('-S','--setup',dest='setup_authsub',action="store_true",
        help="Setup authsub (requires ConfigFile)")
    arg.add_option('--test',dest='test_create',action="store_true")

    (options,args) = arg.parse_args()
    

    # Read/prepare config file
    if not options.config_file:
        log.debug("No configuration file specified, using default: %s" % CONFIG_DEFAULT)
        #exit()
        options.config_file = CONFIG_DEFAULT

    from ConfigParser import ConfigParser
    try:
        config = ConfigParser()
        config.read(options.config_file)
    except Exception, e:
        log.error(e)
        config = ConfigParser()

    try:
        config.add_section('GCal')
    except Exception, e:
        log.error(e)


    # Setup authsub
    if options.setup_authsub:
        upgraded_token = GetAuthSubSessionToken()

        config.set('GCal','authsub_token',upgraded_token)
        
        config_file = file(options.config_file,'wb')
        config.write(config_file)
        config_file.close()

    
    if options.test_create:
        calendar_service = GetCalendarService(config.get('GCal','authsub_token'))
        InsertSingleEvent(calendar_service)
