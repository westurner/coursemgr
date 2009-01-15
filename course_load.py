#!/usr/bin/env python2.5
import copy
from pyparsing import \
        Literal, Word, ZeroOrMore, OneOrMore, White, Group, Dict, Optional, \
                printables, ParseException, Suppress, restOfLine, QuotedString
import pyparsing

class Course(object):
    def __init__(self):
        self.name = None
        self.exams_online = False
        self.quizzes_online = False
        self.exams = []
        self.quizzes = []
        self.assignments = []
        self.reading = []


def loadClass(classtag='.d.whatwhat',exams_online=False,quizzes_online=False):
    # all must have classtag
    # assume everythin is a next action
    tagbase = [classtag,'-next']

    tags['assignments'] = copy(tagbase)
    tags['assignments'].append('@pc')

    tags['exams'] = copy(tagbase)
    if exams_online:
        tags['exams'].append('@pc')
    else:
        tags['exams'].append('@campus')

    tags['quizzes'] = copy(tagbase)
    if quizzes_online:
        tags['quizzes'].append('@pc')
    else:
        tags['quizzes'].append('@campus')

    tags['reading'] = copy(tagbase)
    tags['reading'].append('@reading')

    for t in assignments:
        priority=1
        # add task to rtm and gcal
        
    for t in exams:
        priority=1
        # add task to gcal and rtm

    for t in quizzes:
        priority=1
        # ad task to gcal and rtm

    for t in reading:
        priority=2
        # add task to rtm



__moredoc__="""
Class Name (.d.classtag) [exam_online, 
========================
Exams ?(online)
------
exam info (freeform_date) ?[additional,tags]

Quizzes
-------
xxxxxxxxxxxxxxxxx

Assignments
-----------
xxxxxxxxxxxxxxxxx

Reading
--------
xxxxxxxxxxxxxxxxx

"""


def parse_title(line):
    """[course name name name (exams online, quizzes online)"""
    #TODO: pyparsing - extract tag name
    line_lower = line.lower()

    # Assume course is administered in meatspace
    exams_online = quizzes_online = False

    if 'exams online' in line_lower:
        exams_online = True
    if 'quizzes online' in line_lower:
        quizzes_online = True
    
    if '(' in line:
        name = line.split('(')[0].strip()
    else:
        name = line.strip()

    return {'name':name,
        'exams_online':exams_online,
        'quizzes_online':quizzes_online}

GRAMMAR_LINE_ITEM = None
def grammar_line_item():
    global GRAMMAR_LINE_ITEM

    valid_chars = ''.join(set(pyparsing.printables).difference(set('[]()')))+' '
    tag_chars = valid_chars.replace(',','')

    if not GRAMMAR_LINE_ITEM:
        ws = Optional(Suppress(ZeroOrMore(White())))
        name = (OneOrMore(Word(valid_chars)+ws))("name")
        date = Suppress(Literal('(')) + Group(OneOrMore(Word(valid_chars)))("date") + Suppress(Literal(')'))
        tag = Word(tag_chars)
        tagsep = Optional(Suppress(Literal(',')+ws))
        tags = Suppress(Literal('[')) + Group(ZeroOrMore(tag+tagsep))("tags") + Suppress(Literal(']'))
        GRAMMAR_LINE_ITEM = name + ws + Optional(date) + ws + Optional(tags) + ws + Suppress(restOfLine)

    return GRAMMAR_LINE_ITEM

def parse_line_item(line):
    """ [ task name name name    (freeform_date @ 7:00pm) [additional,t.ags]  ] """
    def pr(string): print string
    #[pr('%s %s' % (i,c)) for (i,c) in enumerate(line)]
    d = grammar_line_item().parseString(line)
    ret = {'name':d.name.asList()[0].strip() or '',
        'due':d.date and d.date.asList()[0].strip() or 'today',
        'tags':d.tags and d.tags.asList() or ''}
    return ret


def split_to_sections(filename):
    """ given a file, return a course object """
    f = file(filename,'r+')

    c = Course()
    # yea...
    lines = f.readlines()

    in_section = False

    for (i,line) in enumerate(lines):
        if line.startswith('==='):
            c.__dict__.update(**parse_title(lines[i-1].strip()))
        elif line.startswith('---'):
            if not in_section:
                in_section = lines[i-1].split()[0].strip().lower()
            elif in_section:
                # Remove this section title from last section
                c.__dict__[in_section].pop()
                in_section = lines[i-1].split()[0].strip().lower()
        elif in_section and line.strip():
            c.__dict__[in_section].append(parse_line_item(line.strip()))

    return c

if __name__=="__main__":
    print split_to_sections('sample.txt').__dict__
    parse_line_item('course name name name   (11/27 @ 9:00pm) [dude, .d.cool, @pc]')
    parse_line_item(""" dude that's crazy (tomorrow at 2) [whats, .d.sweet, @deal]""")
    parse_line_item(""" what's the story (morning glory)""")
    parse_line_item(""" this one has no [date, information]""")
