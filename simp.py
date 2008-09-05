#!/usr/bin/env python
# simple app
from rtm import createRTM, RTM
import logging
from string import Template

API_KEY="8db21291ccdbcd858059799cb44dc57c"
API_SEC="5d80e818ec7aa0b4"

API_TOK="abee05a338c1799fe8f86bde83de573e9628cfe7"

TZ_DEFAULT=84 # Chicago CDT

def printdict(d):
    print '\n'.join([("%s : %s" % (k,v)) for (k,v) in d.items()])

def printer(*kargs,**kwargs):
    if len(kargs) > 1:
        print 'kargs: ', kargs
    if len(kwargs) > 0:
        printdict(kwargs)

class RMilk(RTM):
    def __init__(self,apiKey=API_KEY,secret=API_SEC,token=API_TOK):
        super(RMilk,self).__init__(apiKey,secret,token)
        
        if 0 and token is None:
            print 'No token found'
            print 'Login here:', self.getAuthURL()
            raw_input('Press enter after logging in at the link above')
            token = self.getToken()
            print 'Remember this token:', token
            super(RMilk,self).__init__(self,apiKey,secret,token)

        self._tl = self.timelines.current = self.timelines.create().timeline

        #self.LISTS = self.getListDict()
        self.LISTS = {u'Daily': u'4574767', u'Inbox': u'3917063', u'Sent': u'3917067'}


    def getTimezones(self):
        print '\n'.join([' : '.join(
            [x.name, x.id, x.dst, x.offset, x.current_offset])
            for x in tz.timezones.timezone if 'America' in x.name])

    def getListDict(self):
        r = self.lists.getList()
        return dict(map(lambda x:(x.name, x.id), filter(lambda x: x.smart == u'0', r.lists.list)))

    def getList(self, filter='', list_id=None, showcompleted=False):
        if not showcompleted:
            filter = "%s status:incomplete" % filter

        if not list_id:
            results = self.tasks.getList(filter=filter)
        else:
            results = self.tasks.getList(list_id=list_id,filter=filter)

        logging.debug(results.__dict__)

        if type(results.tasks.list) is not list:
            results.tasks.list = [results.tasks.list]

        ret = []

        for l in results.tasks.list:
            list_id = l.id
            if type(l.taskseries) is not list:
                l.taskseries = [l.taskseries]
            for s in l.taskseries:
                taskseries_id = s.id
                ret.append(self._createTask(s,list_id,taskseries_id))

        return ret

        
    def _createTask(self,task,list_id,taskseries_id):
        kw = {  'name':task.name,
                'tags':task.tags and task.tags.tag or [],
                'completed':task.task.completed,
                'due_date':task.task.due,
                'id':task.task.id,
                'list_id':list_id,
                'taskseries_id':taskseries_id,
                'priority':task.task.priority,
                'estimate':task.task.estimate }
        return RTMTask(self,new=False,**kw)


        
        # cast return structure to task

TEMPLATE_TASK = Template(
'''Name: ${name}
Tags: ${tags}
Due : ${due_date}
Est : ${estimate}
Pri : ${priority}''')

TASK_ATTRS = ['name','tags','due_date','estimate','recurrence','priority',
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
                logging.error("'%s' property not supported by task object" % k)

    def __str__(self):
        return TEMPLATE_TASK.substitute({
            'name':self.name,
            'tags':self.tags and ', '.join(self.tags) or '',
            'due_date': self.due_date or '',
            'estimate': self.estimate or '',
            'priority': self.priority or ''})

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
        logging.debug(printdict(self.__dict__))

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
        logging.debug("_rtmwrap: %s" % kw)

        rsp = func(**kw)

        # on success
        logging.debug("API call completed, removing %s from _updated" % attr)

        if rsp.__dict__['stat'] != 'ok':
            # TODO: undo
            # raise APISetterException
            logging.debug("'uh oh: stat=%s" % rsp.__dict__['stat'])

        #print rsp.list.taskseries
        #print rsp.list.taskseries.task.__dict__
        #print rsp.list.taskseries.tags
        #print rsp.list.taskseries.url
        t = rsp.list.taskseries.task

        # synchronize task changes object
        self.__set('due_date',bool(t.due) and t.due or None)
        self.__set('priority',t.priority)
        self.__set('estimate',t.estimate)
        self.__set('completed',t.completed)
        return rsp


    def setName(self,name):
        return self._rtmwrap(self.rtm.tasks.setName,'name',name)

    def setTags(self,tags):
        return self._rtmwrap(self.rtm.tasks.setTags,'tags',','.join(tags))

    def setDuedate(self,due_date):
        return self._rtmwrap(self.rtm.setDuedate,'due_date',due_date, parse=True)

    def setEstimate(self,estimate):
        return self._rtmwrap(self.rtm.tasks.setEstimate,'estimate',estimate)

    def setRecurrence(self,recurrance):
        return self._rtmwrap(self.rtm.tasks.setRecurrence,'repeat',recurrance)

    def setPriority(self,priority):
        return self._rtmwrap(self.rtm.tasks.setPriority,'priority',priority)

    def setCompleted(self,completed):
        kw = self._params()
        if completed:
            return self.rtm.tasks.complete(**kw)
        else:
            return self.rtm.tasks.uncomplete(**kw)

    def save(self):
        # create or update
        # update
        try:
            if self.isNew:
                logging.debug("Creating a new task")
                tr = self.rtm.tasks.add(timeline=self.rtm._tl,name=self.name,parse=True)
                self.list_id = tr.list.id
                self.taskseries_id = tr.list.taskseries.id
                self.task_id = tr.list.taskseries.task.id
                self.isNew = False
                
                for attr in TASK_ATTRS:
                    val = self.__dict__[attr]
                    if bool(val):
                        func = self.__class__.__dict__.get('set%s' % attr.title(),printer)
                        func(self,val or '')
                        logging.debug("%s   %s" % (func.__name__, val))
            else:
                for attr in self._updated:
                    val = self.__dict__.get(attr)
                    func = self.__class__.__dict__.get('set%s' % attr.title(),printer)
                    func(self,val or '')
                    self._updated.remove(attr)
                
                    # update self with relevant
            logging.info("Saved task: %s (%s:%s)" % (self.name, self.list_id, self.id))
            logging.debug(self.__dict__)
            return True
        except:
            # TODO: undo
            logging.error("Error saving task")
            return False



def test_Task(rtm=RMilk()):
    t = Task(name="wow",tags=['prety','@cool'], due_date="tomorrow", estimate="10 minutes")
    t.save(rtm)
    print t.__str_detailed__()
    assert t.id is not None
    assert t.list_id is not None


if __name__=="__main__":
    from optparse import OptionParser
    from operator import xor
    arg = OptionParser(version="%prog 0.1")

    arg.add_option('-c','--create',dest='create', action='store_true',help='Create a new task')
    arg.add_option('-n','--name',dest='name',help='Task name')
    arg.add_option('-t','--tags',dest='tags', help='Task tags (comma separated)')
    arg.add_option('-d','--due',dest='due_date', help='Due date')
    arg.add_option('-e','--estimate',dest='estimate', help='Task time estimate')
    arg.add_option('-r','--recur',dest='recurrance',help='Task recurrance')
    arg.add_option('-p','--priority',dest='priority',help='Task priority')
    arg.add_option('-l','--list',dest='get_list',help='Get list by filter')

    arg.add_option('--rename',nargs=2,dest='tag_rename',help='Rename <original> with <tag>. Requires list filter')
    arg.add_option('--test',dest='test',action='store_true',help='Testing')

    (options, args) = arg.parse_args()

    actions={'-c/--create':options.create,
            '-l/--list':options.get_list,
            '--test':options.test}

    # Intialize tasklist
    tasklist = None

    # Exclusive actions
    if not any(actions.values()):
        print "What?"
    elif not reduce(xor, map(bool, actions.values())):
        logging.error("Can only select one of %s" % ', '.join(actions.keys()))
        exit()
    else:
        # Create global connection object
        rtm = RMilk()

    if options.test:
        print "<tests>"
        print ' <task creation>'
        t = RTMTask(rtm,name='cool',tags=['delete','this'],estimate='1 hour')
        print '  <saving>'
        t.save()
        #test_Task(rtm)
        print '</tests>'
        exit()

    # Normalize tags list
    if options.tags:
        options.tags = map(str.strip, options.tags.split(','))

    if options.create:
        t = Task(name=options.name,
                tags=options.tags,
                due_date=options.due_date,
                estimate=options.estimate,
                recurrance=options.recurrance,
                priority=options.priority,
                parse=True)
        t.save(rtm)

    if options.get_list:
        tasklist = rtm.getList(filter=options.get_list)
        for task in tasklist:
            print '\n',str(task)
#        print tasklist

    if options.tag_rename: # 2 options
        if not options.get_list:
            logging.info("A list filter is required to rename")
            exit()

        (old,new) = options.tag_rename
        print "%s --> %s" % (old,new)

        for t in tasklist:
            t.tags = list(set(t.tags).union([new]).difference([old]))
            logging.info(" - %s" % t.name)
            t.save()
