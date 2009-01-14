#!/usr/bin/env python
# simple app
from lib.pyrtm.rtm import createRTM, RTM
import logging
from string import Template
import datetime

# Globals
CONFIG_DEFAULT='simp.cfg'

# logging init
logging.basicConfig(format="%(asctime)-15s %(message)s")
log = logging.getLogger('rtmsimp')
log.setLevel(logging.INFO)

def printdict(d):
    print '\n'.join([("%s : %s" % (k,v)) for (k,v) in d.items()])

def printer(*kargs,**kwargs):
    if len(kargs) > 1:
        print 'kargs: ', kargs
    if len(kwargs) > 0:
        printdict(kwargs)

class RMilk(RTM):
    def __init__(self,api_key,api_secret,api_token,lists=None):
        super(RMilk,self).__init__(api_key,api_secret,api_token)
        
        if 0 and token is None:
            print 'No token found'
            print 'Login here:', self.getAuthURL()
            raw_input('Press enter after log.in at the link above')
            token = self.getToken()
            print 'Remember this token:', token
            super(RMilk,self).__init__(self,api_key,api_secret,api_token)

        self._tl = self.timelines.current = self.timelines.create().timeline

        self.LISTS = lists or self.getListDict()

    def getTimezones(self):
        print '\n'.join([' : '.join(
            [x.name, x.id, x.dst, x.offset, x.current_offset])
            for x in tz.timezones.timezone if 'America' in x.name])

    def getListDict(self):
        """ Filter, cache, and return lists as dict """
        if self.LISTS:
            return self.LISTS
        self.LISTS = dict(
		map(lambda x:(x.name, x.id), 
            		filter(lambda x: x.smart == u'0',
				self.lists.getList().lists.list) ))
        return self.LISTS

    def getList(self, filter='', list_id=None, showcompleted=False):
        if not showcompleted:
            filter = "%s AND status:incomplete" % filter

        if not list_id:
            results = self.tasks.getList(filter=filter)
        else:
            results = self.tasks.getList(list_id=list_id,filter=filter)

        log.debug(results.__dict__)
        if not results.tasks:
            print "No Search Results"
            exit()

        if type(results.tasks.list) is not list:
            results.tasks.list = [results.tasks.list]

        ret = []

        # TODO: handle recurring tasks

        for l in results.tasks.list:
            list_id = l.id
            if type(l.taskseries) is not list:
                l.taskseries = [l.taskseries]
            for s in ifilter(lambda x: not x.__dict__.get('rrule'), l.taskseries):
                taskseries_id = s.id
                ret.append(self._createTask(s,list_id,taskseries_id))

        return ret

        
    def _createTask(self,task,list_id,taskseries_id):
        log.debug(str(task))
        kw = {  'name':task.name,
                'tags':task.tags and task.tags.tag or [],
                'completed':task.task.completed or '',
                'due':task.task.due,
                'id':task.task.id,
                'list_id':list_id,
                'taskseries_id':taskseries_id,
                'priority':task.task.priority,
                'estimate':task.task.estimate }
        return RTMTask(self,new=False,**kw)


TEMPLATE_TASK = Template(
'''${name} (${tags}) [${due}] { ${priority} }''')

TASK_ATTRS = ['name','tags','due','estimate','recurrence','priority',
        'parse','id','list_id','taskseries_id','completed']

class Task(object):
    def __init__(self, **kwargs):
        # Set all attrs to none by default
        self.__dict__.update([(k,None) for k in TASK_ATTRS])

        # Whitelist kwargs
        for (k,v) in kwargs.items():
            if k in TASK_ATTRS:
                self.__dict__.update({k:v})
            else:
                log.error("'%s' property not supported by task object" % k)

    def __str__(self):
        return TEMPLATE_TASK.substitute(self._dict())


    def _dict(self):
        # TODO: display logic in the wrong place?
        return {
            'name':self.name,
            'tags':self.tags and ', '.join(self.tags) or '',
            'due': self.due or '',
            'estimate': self.estimate or '',
            'priority': self.priority or '',
            'due_human': datetime.date(*map(int,self.due[:10].split('-'))).strftime("%m/%d"),
            'tags_filt':self.tags and ', '.join(filter(lambda x: not x.startswith('-'), self.tags)) or ''}

    def _tagRename(self,old,new):
        self.tags = list(set(self.tags).difference([old]).union([new]))


    def __str_detailed__(self):
        print str(self)
        print 'id  :', self.id
        print 'lid :', self.list_id
        print 'tser:', self.taskseries_id


class RTMTask(Task):
    def __init__(self,rtm,new=True,**kwargs):
        super(RTMTask,self).__init__(**kwargs)
        self.isNew = new
        self.isCurrent = False
        self.rtm = rtm
        self._updated = []
        #log.debug(printdict(self.__dict__))

    def __setattr__(self, attr, val):
        # track which attrs have changed since init
        if attr in TASK_ATTRS and not self.isNew:
            if val != self.__dict__[attr] and attr not in self._updated:
                self._updated.append(attr)
        Task.__setattr__(self,attr,val)

    def __set(self, attr, val):
        Task.__setattr__(self,attr,val)

    def _params(self):
        return {'timeline':self.rtm._tl,
                'list_id':self.list_id,
                'taskseries_id':self.taskseries_id,
                'task_id':self.id,}

    def _rtmwrap(self,func,attr,val,**kwargs):
        kw = self._params()
        kw.update({attr:val})
        kw.update(kwargs)
        log.debug("_rtmwrap: %s" % kw)

        rsp = func(**kw)
        # on success
        self.__dict__[attr] = val

        log.debug("%s(%s)" % (func.__name__, val))

        if rsp.__dict__['stat'] != 'ok':
            # TODO: undo
            # raise APISetterException
            log.debug("'uh oh: stat=%s" % rsp.__dict__['stat'])

        task = rsp.list.taskseries.task

        # synchronize task changes object
        self.__set(attr,task.__dict__.get(attr))
        return rsp


    def _setName(self,name):
        return self._rtmwrap(self.rtm.tasks.setName,'name',name)

    def _setTags(self,tags):
        return self._rtmwrap(self.rtm.tasks.setTags,'tags',','.join(tags))

    def _setDue(self,due):
        return self._rtmwrap(self.rtm.tasks.setDueDate,'due',due, parse=True)

    def _setEstimate(self,estimate):
        return self._rtmwrap(self.rtm.tasks.setEstimate,'estimate',estimate)

    def _setRecurrence(self,recurrence):
        return self._rtmwrap(self.rtm.tasks.setRecurrence,'repeat',recurrence)

    def _setPriority(self,priority):
        return self._rtmwrap(self.rtm.tasks.setPriority,'priority',priority)

    def _setCompleted(self,completed):
        kw = self._params()
        if completed:
            return self.rtm.tasks.complete(**kw)
        else:
            return self.rtm.tasks.uncomplete(**kw)

    def save(self):
        # create or update
        # update
        #try:
            if self.isNew:
                log.debug("Creating a new task")
                tr = self.rtm.tasks.add(timeline=self.rtm._tl,name=self.name,parse=True)
                self.list_id = tr.list.id
                self.taskseries_id = tr.list.taskseries.id
                self.id = tr.list.taskseries.task.id
                self.isNew = False
                
                for attr in TASK_ATTRS:
                    val = self.__dict__.get(attr)
                    if val:
                        func = self.__class__.__dict__.get('_set%s' % attr.title(),printer)
                        func(self,val or '')
            else:
                for attr in self._updated:
                    val = self.__dict__.get(attr)
                    func = self.__class__.__dict__.get('_set%s' % attr.title(),printer)
                    func(self,val or '')
                    self._updated.remove(attr)
                
                    # update self with relevant
            log.info("Task saved")
            log.info(str(self))
            #log.debug(self.__dict__)
            return True
        #except:
            # TODO: undo
            log.error("Error saving task")
            return False



def test_Task(rtm=None): # = RMilk()
    t = Task(name="wow",tags=['prety','@cool'], due="tomorrow", estimate="10 minutes")
    t.save(rtm)
    print t.__str_detailed__()
    assert t.id is not None
    assert t.list_id is not None


if __name__=="__main__":
    from optparse import OptionParser
    from operator import xor
    
    from itertools import imap,ifilter,count,izip
    import re

    arg = OptionParser(version="%prog 0.21")

    arg.add_option('--config',dest='config_file',help='Path to a config file')
    arg.add_option('-c','--create',dest='create', action='store_true',help='Create a new task')
    arg.add_option('-n','--name',dest='name',help='Task name')
    arg.add_option('-t','--tags',dest='tags', help='Task tags (comma separated)')
    arg.add_option('-d','--due',dest='due', help='Due date')
    arg.add_option('-e','--estimate',dest='estimate', help='Task time estimate')
    arg.add_option('-r','--recur',dest='recurrence',help='Task recurrence')
    arg.add_option('-p','--priority',dest='priority',help='Task priority')
    arg.add_option('-l','--list',dest='get_list',help='Get list by filter')
    arg.add_option('-s','--search',dest='search',help='Keyword search for tasks')
    arg.add_option('-i','--ipython',dest='ipython',action='store_true',
            help='Create RTM connection and drop to ipython')

    arg.add_option('--tagrename',nargs=2,dest='tag_rename',
            help='Rename <original> with <tag>. Requires list filter')
    arg.add_option('--taskrename',nargs=2,dest='task_rename',
            help='Rename <regex> to <pattern>. Requires list filter')

    arg.add_option('--hipster',nargs=2,dest='template_hipster',help="Create a hipster pda with the title")
    #TODO
    #arg.add_option('--preview',dest='preview',action='store_true',help='Preview renames')


    arg.add_option("-v", action="count", dest="verbosity")
    
    arg.add_option('--test',dest='test',action='store_true',help='Testing')

    (options, args) = arg.parse_args()

    actions={'-c/--create':options.create,
            '-l/--list':options.get_list,
            '-s/--search':options.search,
            '--test':options.test}

    # Intialize tasklist
    tasklist = None

    # Logging init
    if options.verbosity > 1:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    # Exclusive actions
    if not any(actions.values()):
        log.error("What?")
        exit()
    elif not reduce(xor, map(bool, actions.values())):
        log.error("Can only select one of %s" % ', '.join(actions.keys()))
        exit()
    
    # Read values from config file
    try:
        from ConfigParser import ConfigParser
        config = ConfigParser()
        #
        config.read(options.config_file or CONFIG_DEFAULT)
        API_KEY = config.get('RTM','api_key')
        API_TOKEN = config.get('RTM','api_token')
        API_SECRET = config.get('RTM','api_secret')
        LISTS = config.get('RTM','lists')
        # Create global connection object
        rtm = RMilk(API_KEY, API_SECRET, API_TOKEN, LISTS)
    except Exception, e:
        log.error(e)
        exit()

    if options.test:
        log.info("<tests>")
        log.info(' <task creation>')
        t = RTMTask(rtm,name='cool',tags=['delete','this'],estimate='1 hour')
        log.info('  <saving>')
        t.save()
        #test_Task(rtm)
        log.info('</tests>')
        exit()

    # Normalize comma separated tags list
    if options.tags:
        options.tags = map(str.strip, options.tags.split(','))

    if options.create:
        t = RTMTask(rtm,name=options.name,
                tags=options.tags,
                due=options.due,
                estimate=options.estimate,
                recurrence=options.recurrence,
                priority=options.priority,)
        t.save()

    if options.get_list:
        tasklist = rtm.getList(filter=options.get_list)
        for task in tasklist:
            print '- %s' % task

    if options.search:
        tasklist = rtm.getList(filter='(name:"%s" OR tag:"%s")' % (options.search,options.search))
        for task in tasklist:
            print '\n',str(task)

    if options.tag_rename: # 2 options
        if not options.get_list:
            log.info("A list filter is required to rename")
            exit()

        (old,new) = options.tag_rename
        log.info("Tag Rename: %s --> %s" % (old,new))

        for t in tasklist:
            t._tagRename(old,new)
            print " - %s" % t.name
            t.save()

    if options.task_rename: # Regex
        if not options.get_list:
            log.info("A list filter is required to rename")
            exit()

        (regex,output) = options.task_rename
        reg = re.compile(regex)
        log.debug("Task Rename: %s --> %s" % (regex,output))

        # ((task,new_name),number) iterator for matching tasks
        matches = map(lambda x: (x[0],output % x[1].groups(),count()),
                    ifilter(lambda x: x[1],
                        imap(lambda x: (x, reg.search(x.name)),
                            tasklist)))

        # Confirm transform
        for (i,t) in izip(range(1,len(matches)),matches):
            print "%-2d. '%s' -> '%s'" % (i, t[0].name, t[1])
        if raw_input("Confirm rename? (Y\N Default N): ").lower() not in [
                'y','yes','sweet','doit']:
            log.info("Rename cancelled")
            exit()

        log.debug("Renaming...")
        # Rename all matches
        for t in matches:
            log.debug("Renamed: '%s' -> '%s'" % (t[0].name, t[1]))
            t[0]._setName(output % t[1])


    if options.template_hipster:
        (title,filepath)=options.template_hipster
        from string import Template
        TEMPLATE_HIPSTER_BODY=Template("""
        <html>
        <head><title>${title}</title>
        <style type="text/css">${css}</style>
        </head>
        <body><div id="content">
            <h1>${title}</h1>
            <ul>${items}</ul>
        </div></body></html>""")
        TEMPLATE_HIPSTER_TASK=Template("""<li><span class="taskname">${name}</span>
                <span class="tags">${tags_filt}</span><span class="due">${due_human}</span></li>""")

        TEMPLATE_HIPSTER_CSS="""
html, body, ul, h1, #content, #content li { padding: 0 !important; margin: 0 !important; font-family: "Trebuchet MS" }
#content { width: 400px !important; }
#content li { border-bottom: 1px solid #aaa !important; }
h1 { font-size: 1.3em; text-align: center; }
span.taskname, span.tags { float: left; }
#content li { clear: both; }
#content li span.taskname { font-weight: bold;  }
#content li span.due { font-weight: normal; float:right; text-align: right;  }
#content li span.tags { font-size: 0.8em; font-weight: normal; }
#content li span.priolist { font-weight: normal; display: none; }
        """

        tasklist = sorted(tasklist,key=lambda x: x.due)

        context = {}
        context['title'] = title
        context['items'] = '\n'.join(map(lambda x: TEMPLATE_HIPSTER_TASK.substitute(x._dict()), tasklist))
        context['css'] = TEMPLATE_HIPSTER_CSS


        file(filepath,'w+').writelines(TEMPLATE_HIPSTER_BODY.substitute(**context))
        import webbrowser
        webbrowser.open(filepath)


        

    if options.ipython:
        try:
            from IPython.Shell import IPShellEmbed
            ipshell = IPShellEmbed(argv=['-l','-lf','rtm_log.py'])
            ipshell(header='--- rtm interactive ---')
        except:
            log.error("Couldn't find IPython")

