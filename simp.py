# simple app
from rtm import createRTM
import logging
from rtm import createRTM
import logging

API_KEY="8db21291ccdbcd858059799cb44dc57c"
API_SEC="5d80e818ec7aa0b4"

API_TOK="abee05a338c1799fe8f86bde83de573e9628cfe7"

TZ_DEFAULT=84 # Chicago CDT


def setupSchool(rtm):
    plist=""".d.General
    .d.FileStruct
    .d.LatinAmer
    .d.TechWrit
    .d.GUID
    .d.ISAnalysis
    .d.MktPrin
    """
    projects = map(str.strip, plist.split("\n"))
    print projects

    for p in projects:
        addTask(rtm,"Add Assignments to RTM",tags=['-next','@online',p],estimate='15 minutes')


def examp(rtm):
    return [(x.id, x.name,x.tags and x.tags.tag or []) for x in rtm.tasks.getList(filter='list:Inbox').tasks.list.taskseries]


def ipy():
    # TODO: Proper subclass (ie no monkeypatch)

    rtm = createRTM(API_KEY, API_SEC, API_TOK)
    rtm._tl = rtm.timelines.current = rtm.timelines.create().timeline
    return rtm

def addTask(rtm, name, tags=None,
        due_date=None, estimate=None, repeat=None,
        priority=None, parse=True, atomic=True):
    '''Wrapper for task add.
    List defaults to Inbox
    Set atomic to false if handling batches
    '''

    if atomic:
        rtm._tl = rtm.timelines.current = rtm.timelines.create().timeline
    
    try:
        tr = rtm.tasks.add(timeline=rtm._tl,name=name,parse=parse)
        list_id = tr.list.id
        tser_id = tr.list.taskseries.id
        task_id = tr.list.taskseries.task.id
        logging.debug(':'.join([list_id, tser_id, task_id]))
        
        if tags:
            rtm.tasks.addTags(timeline=rtm._tl, list_id=list_id,
                    taskseries_id=tser_id, task_id=task_id,
                    tags=','.join(tags))
        if due_date:
            rtm.tasks.setDueDate(timeline=rtm._tl, list_id=list_id,
                    taskseries_id=tser_id, task_id=task_id,
                    due=due_date, parse=1)
        if estimate:
            rtm.tasks.setEstimate(timeline=rtm._tl, list_id=list_id,
                    taskseries_id=tser_id, task_id=task_id,
                    estimate=estimate)
        if repeat:
            rtm.tasks.setRecurrance(timeline=rtm._tl, list_id=list_id,
                    taskseries_id=tser_id, task_id=task_id,
                    repeat=repeat)
        if priority:
            rtm.tasks.setPriority(timeline=rtm._tl, list_id=list_id,
                    taskseries_id=tser_id, task_id=task_id,
                    priority=priority)
    except:
        logging.error("Problem with adding a task")
        # TODO: Handle transactions correctly

    
def test_addTask(rtm=ipy()):
    addTask(rtm,"wow",tags=['pretty','cool'],parse=False)


def getTimezones(rtm=ipy()):
    print '\n'.join([' : '.join(
        [x.name, x.id, x.dst, x.offset, x.current_offset])
        for x in tz.timezones.timezone if 'America' in x.name])

class Task(object):
    def __init__(self, name, tags=None, due_date=None, estimate=None,
                        repeat=None, priority=None, parse=None):
        self.name=name
        self.tags=tags
        self.due_date=duedate
        self.estimate=estimate
        self.repeat=repeat
        self.priority=priority
        self.parse=parse

if __name__=="__main__":
#    print '\n'.join(map(str,examp(ipy())))
    from optparse import OptionParser
    arg = OptionParser(version="%prog 0.1")

    arg.add_option('-c','--create',dest='name', help='Create a new task')
    arg.add_option('-t','--tags',dest='tags', help='Task tags')
    arg.add_option('-d','--due',dest='due_date', help='Due date')
    arg.add_option('-e','--estimate',dest='estimate', help='Task time estimate')
    arg.add_option('-r','--repeat',dest='repeat',help='Task repetition')
    arg.add_option('-p','--priority',dest='priority',help='Task priority')

    (options, args) arg.parse_args()

    if not options.name:
        logging.error("Task creation only supported at this time")
