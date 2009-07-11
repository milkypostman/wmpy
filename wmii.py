import pyxp
import subprocess
import time
import heapq
import fcntl
import re
import select
import os
import math
import sys
import signal
import logging
import string
from collections import deque
from itertools import chain
from operator import itemgetter

log = logging.getLogger('wmii')

HOME=os.path.join(os.getenv('HOME'), '.wmii-hg')
HISTORYSIZE=5

#log.debug('creating new instance of client')
client = pyxp.Wmii('unix!/tmp/ns.%s.:0/wmii' % os.getenv('USER'))

# applications
apps = {
        'terminal': 'xterm',
}

# pre-allocated tags
reserved_tags = {
        'main' : 1,
        'www' : 2,
        'dev' : 3,
        }

# initialize default colors
colors = {
    'normfg' : '#000000',
    'normbg' : '#c1c48b',
    'normborder': '#81654f',
    'focusfg' : '#000000',
    'focusbg' : '#81654f',
    'focusborder': '#000000',
}

# initialize base config
config = {
        'font': '-*-terminus-*-*-*-*-*-*-*-*-*-*-*-*',
        'bar': 'on top',
        'grabmod': 'Mod1',
        'view': 'main',
        #incmode = (ignore|show)
        'incmode': 'ignore',
        }

# default colrules
colrules = {
        'main' : '100+%d' % (100 - (200 / (1 + math.sqrt(5))), ),
}

# default tagrules
tagrules = {
    'Firefox.*': 'www',
    'Gimp.*': 'gimp+~',
    'MPlayer.*': '~',
}


class Tag(object):
    """
    This class handles all the tag operations consistent with focus,
    urgency, and visibility.
    """

    def __init__(self, name, idx, visible=True, urgent=False):
        self.name = name
        self._idx = idx
        self._urgent = urgent
        self._focused = False

        self._visible = visible
        if self._visible:
            self._create()

    def __del__(self):
        if self._visible:
            self._remove()

    def _getfocused(self):
        return self._focused

    def _setfocused(self, value):
        self._focused = value
        self._update()

    focused = property(_getfocused, _setfocused)

    def _getidx(self):
        return self._idx

    def _setidx(self, value):
        if value != self._idx:
            self._remove()
            self._idx = value
            self._create()

    idx = property(_getidx, _setidx)

    def _getvisible(self):
        return self._visible

    def _setvisible(self, value):
        if self._visible != value:
            if value:
                self._create()
            else:
                self._remove()

            self._visible = value

    visible = property(_getvisible, _setvisible)

    def _geturgent(self):
        return self._urgent

    def _seturgent(self, value):
        self._urgent = value
        self._update()

    urgent = property(_geturgent, _seturgent)

    def __lt__(self, other):
        return (self.idx < other.idx) or (self.idx == other.idx and self.name < other.name)

    def __le__(self, other):
        return (self.idx <= other.idx) or (self.idx == other.idx and self.name <= other.name)

    def __eq__(self, other):
        return (self.idx == other.idx) and (self.name == other.idx)

    def __gt__(self, other):
        return (self.idx > other.idx) or (self.idx == other.idx and self.name > other.name)

    def __ge__(self, other):
        return (self.idx >= other.idx) or (self.idx == other.idx and self.name >= other.name)

    def colorstr(self):
        global colors
        if self.focused:
            color = colors['focuscolors']
        else:
            color = colors['normcolors']

        if self.urgent:
            return ' '.join((color, '*'+self.name))

        return ' '.join((color, self.name))


    def _create(self):
        client.create(''.join(['/lbar/', str(self.idx), '_', self.name]), self.colorstr())

    def _remove(self):
        client.remove(''.join(['/lbar/', str(self.idx), '_', self.name]))

    def _update(self):
        if self._visible:
            client.write(''.join(['/lbar/', str(self.idx), '_', self.name]), self.colorstr())

_taglist = []
_taglist_reserved = []
_tags = {}
_tags_idx = {}
_tags_reserved = {}
_tags_idx_reserved = {}

_running = True

_urgent_clients = []

def get_ctl(name, path='/ctl'):
    global client
    for line in client.read(path).split('\n'):
        if line.startswith(name):
            return line[line.find(' ')+1:]

def set_ctl(name, value = None, path='/ctl'):
    global client
    if value == None and isinstance(name, dict):
        client.write(path, '\n'.join( (' '.join((n, v)) for n,v in name.iteritems()) ))
    else:
        client.write(path,' '.join((name,value)))

def _tag_startswith(char):
    global client
    global _taglist_reserved, _tags, _tags_idx, _tags_reserved, _tags_idx_reserved

    currentname = get_ctl('view')
    currentidx = -1
    possible = []
    for tag in chain(_taglist_reserved,
            (t for t in _taglist if t.name not in _tags_reserved)
            ):
        tagname = tag.name
        if tagname[0] == char:
            if tagname == currentname:
                currentidx = len(possible)
            possible.append(tag)

    if len(possible) > 0:
        return possible[(currentidx+1) % len(possible)]

    return None


def set_client_tag_startswith(char):
    tag = _tag_startswith(char)

    if tag is not None:
        client.write('/client/sel/tags', tag.name)

def set_tag_startswith(char):
    """ Set to next tag that starts with 'char'.  Includes reserved tags. """
    tag = _tag_startswith(char)

    if tag is not None:
        set_ctl('view', tag.name)

def set_tag_idx(idx):
    global _tagname_reserved, _tagname
    if idx in _tags_idx_reserved:
        set_ctl('view', _tags_idx_reserved[idx].name)
    elif idx in _tags_idx:
        set_ctl('view', _tags_idx[idx].name)

def set_client_tag_idx(idx):
    global client, _tagname_reserved, _tagname
    if idx in _tags_idx_reserved:
        client.write('/client/sel/tags', _tags_idx_reserved[idx].name)
    elif idx in _tags_idx:
        client.write('/client/sel/tags', _tags_idx[idx].name)

_programlist = None
def update_programlist():
    global _programlist

    proc = subprocess.Popen("dmenu_path", stdout=subprocess.PIPE)
    _programlist = []
    for prog in proc.stdout:
        _programlist.append(prog.strip())

def program_menu(*args):
    return menu('cmd', _programlist)

def restart():
    global _running
    execute(os.path.expandvars("$HOME/.wmii-hg/wmiirc"))
    _running = False

def quit():
    global _running
    _running = False
    client.write('/ctl', 'quit')

actions = {
    'wmiirc':restart,
    'quit':quit,
}

def action(a):
    global actions
    if a in actions and callable(actions[a]):
        actions[a]()

def action_menu(*args):
    return menu('action', actions.keys())

def menu(prompt, entries):
    histfn = os.path.join(HOME,'history.%s' % prompt)
    cmd = ['wimenu', '-h', histfn]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    for entry in entries:
        proc.stdin.write(entry)
        proc.stdin.write('\n')
    proc.stdin.close()

    out = proc.stdout.read().strip()

    if out:
        history = []
        histfile = open(histfn,'a+')
        for h in histfile:
            history.append(h.strip())
        history.append(out)

        histfile = open(histfn,'w+')
        for h in history[-HISTORYSIZE:]:
            histfile.write(h)
            histfile.write('\n')
        histfile.close()

    return out

def execute(cmd, shell=True):
    if not cmd:
        return

    setsid = getattr(os, 'setsid', None)
    if not setsid:
        setsid = getattr(os, 'setpgrp', None)


    proc = subprocess.Popen(cmd, shell=shell, preexec_fn=setsid)
    log.debug("program %s started with pid %d..." % (cmd, proc.pid))
    return proc

def set_tag(name):
    if name:
        set_ctl('view', name)

def set_client_tag(name):
    if name:
        client.write('/client/sel/tags', name)

def tag_menu():
    return menu('tag', (tag.name for tag in _taglist))

def select_client(id):
    global client
    client.write('/tag/sel/ctl', 'select client %s' % id)

def focus_urgent_client():
    global _urgent_clients, _tags
    global client

    curtag = get_ctl('view')

    while len(_urgent_clients) > 0:
        id = _urgent_clients.pop()

        try:
            clitags = client.read('/client/%s/tags' % id).split('+')
        except IOError:
            continue

        if curtag not in clitags:
            clitags = dict((name, True) for name in clitags)
            for tag in _taglist:
                if tag.name in clitags:
                    set_tag(tag.name)
                    break

        select_client(id)
        break



def previous_client():
    global _client_history
    if len(_client_history):
        cli = _client_history.pop()
        client.write('/tag/sel/ctl', 'select %s' % cli)

keybindings = {
        'Mod1-p':lambda _: execute(program_menu()),
        'Mod1-j':lambda _: client.write('/tag/sel/ctl', 'select down'),
        'Mod1-k':lambda _: client.write('/tag/sel/ctl', 'select up'),
        'Mod1-h':lambda _: client.write('/tag/sel/ctl', 'select left'),
        'Mod1-l':lambda _: client.write('/tag/sel/ctl', 'select right'),
        'Mod1-Tab':lambda _: previous_client(),
        'Mod1-Shift-j':lambda _: client.write('/tag/sel/ctl', 'send sel down'),
        'Mod1-Shift-k':lambda _: client.write('/tag/sel/ctl', 'send sel up'),
        'Mod1-Shift-h':lambda _: client.write('/tag/sel/ctl', 'send sel left'),
        'Mod1-Shift-l':lambda _: client.write('/tag/sel/ctl', 'send sel right'),
        'Mod1-Control-j':lambda _: client.write('/tag/sel/ctl', 'nudge sel sel down'),
        'Mod1-Control-k':lambda _: client.write('/tag/sel/ctl', 'nudge sel sel up'),
        'Mod1-Control-h':lambda _: client.write('/tag/sel/ctl', 'nudge sel sel left'),
        'Mod1-Control-l':lambda _: client.write('/tag/sel/ctl', 'nudge sel sel right'),
        'Mod1-d':lambda _: client.write('/tag/sel/ctl', 'colmode sel default-max'),
        'Mod1-s':lambda _: client.write('/tag/sel/ctl', 'colmode sel stack-max'),
        'Mod1-m':lambda _: client.write('/tag/sel/ctl', 'colmode sel stack+max'),
        'Mod1-t':lambda _: set_tag(tag_menu()),
        'Mod1-Shift-t':lambda _: set_client_tag(tag_menu()),
        'Mod1-comma':lambda _: setviewofs(-1),
        'Mod1-period':lambda _: setviewofs(1),
        'Mod4-@':lambda key: set_tag_startswith(key[key.rfind('-')+1]),
        'Mod4-Shift-@':lambda key: set_client_tag_startswith(key[key.rfind('-')+1]),
        'Mod4-#':lambda key: set_tag_idx(int(key[key.rfind('-')+1])),
        'Mod4-Shift-#':lambda key: set_client_tag_idx(int(key[key.rfind('-')+1])),
        'Mod1-Shift-c':lambda _: client.write('/client/sel/ctl', 'kill'),
        'Mod1-Return':lambda _: execute(apps['terminal']),
        'Mod1-a': lambda _: action(action_menu()),
        'Mod1-space':lambda _: client.write('/tag/sel/ctl', 'select toggle'),
        'Mod1-Shift-space':lambda _: client.write('/tag/sel/ctl', 'send sel toggle'),
        'Mod1-u': lambda _: focus_urgent_client(),
        }

def update_keys():
    global keybindings
    global client
    numre = re.compile('(.*-)#')
    charre = re.compile('(.*-)@')

    keys = []
    for key in keybindings:
        match = numre.match(key)
        if match:
            pfx = match.group(1)
            keys.extend([pfx+str(i) for i in range(10)])
            continue

        match = charre.match(key)
        if match:
            pfx = match.group(1)
            keys.extend([pfx+i for i in 'abcdefghijklmnopqrstuvwxyz'])
            continue

        keys.append(key)

    client.write('/keys', '\n'.join(keys))


def setviewofs(ofs):
    global client
    global _taglist

    view = get_ctl('view')
    idx = _taglist.index( _tags[view] )

    tag = _taglist[(idx + ofs) % len(_taglist)]

    set_ctl('view', tag.name)

def _obtaintagidx():
    global _tagidxheap
    return heapq.heappop(_tagidxheap)

def _releasetagidx(idx):
    global _tagidxheap, _tags_reserved
    if idx not in _tags_reserved:
        heapq.heappush(_tagidxheap, idx)

def event_urgenttag(type, name):
    global _tags
    tag = _tags[name]
    tag.urgent = True
    pass

def event_noturgenttag(type, name):
    global _tags
    tag = _tags[name]
    tag.urgent = False
    pass

def event_leftbarclick(button, id):
    global _tags_idx
    div = id.find('_')
    try:
        idx = int(id[:div])
        name = id[div+1:]
        if idx in _tags_idx and _tags_idx[idx].name == name:
            set_ctl('view', name)
    except ValueError:
        return

def event_rightbarclick(button, id):
    global _widgets
    button = int(button)
    if id in _widgets:
        _widgets[id].clicked(button)

def event_key(key):
    log.debug('key event: %s' % key)
    func = keybindings.get(key, None)
    if callable(func):
        func(key)
        return

    numkey = re.sub('-\d*$', '-#', key)
    func = keybindings.get(numkey, None)
    if callable(func):
        func(key)
        return

    charkey = re.sub('-[a-zA-Z]$', '-@', key)
    func = keybindings.get(charkey, None)
    if callable(func):
        func(key)
        return

def event_focustag(name):
    global _tags
    tag = _tags[name]
    tag.focused = True

def event_unfocustag(name):
    global _tags
    tag = _tags[name]
    tag.focused = False

def _create_tag(name):
    global  _tags, _tags_reserved, _tags_idx

    focusedtag = get_ctl('view')

    if name in _tags_reserved:
        tag = _tags_reserved[name]
        idx = tag.idx
        tag.visible = True
    else:
        idx = _obtaintagidx()
        tag = Tag(name, idx)

    _tags[name] = tag
    _tags_idx[idx] = tag
    if name == focusedtag:
        tag.focused = True

def event_createtag(name):
    global _taglist, _tags
    _create_tag(name)
    _taglist = sorted(_tags.itervalues())

def event_destroytag(name):
    global _tags, _tags_idx, _tags_reserved, _taglist

    freetag = _tags[name]
    freeidx = freetag.idx
    freetag.visible = False
    del _tags[name]

    if name not in _tags_reserved:
        for tag in _taglist:
            if tag.idx > freeidx and tag.name not in _tags_reserved:
                _tags_idx[freeidx] = tag
                freeidx, tag.idx = tag.idx, freeidx
        _releasetagidx(freeidx)

    del _tags_idx[freeidx]

    _taglist = sorted(_tags.itervalues())

def event_start(*vargs):
    global _running

    if len(vargs) < 2:
        return

    if vargs[1] == 'wmpy' and int(vargs[2]) == os.getpid():
        return

    _running = False

def event_urgent(id, type):
    global _urgent_clients
    _urgent_clients.append(id)

events = {
        'Key': [event_key],
        'FocusTag': [event_focustag],
        'UnfocusTag': [event_unfocustag],
        'CreateTag': [event_createtag],
        'DestroyTag': [event_destroytag],
        'LeftBarClick': [event_leftbarclick],
        'RightBarClick': [event_rightbarclick],
        'Start': [event_start],
        'Urgent': [event_urgent],
        'UrgentTag': [event_urgenttag],
        'NotUrgentTag': [event_noturgenttag],
        }

def _initialize_tags():
    global _tagidx, _tag, _tagidxname, _tagidxheap, _tagname_reserved, _tag_reserved, _taglist, _taglist_reserved
    global reserved_tags
    global client

    for name, idx in reserved_tags.iteritems():
        tag = Tag(name, idx, False)
        _tags_reserved[name] = tag
        _tags_idx_reserved[idx] = tag

    _taglist_reserved = sorted(_tags_reserved.itervalues())

    _tagidxheap = [i for i in range(1,10) if i not in _tags_idx_reserved]
    heapq.heapify(_tagidxheap)

    for tagname in filter(lambda n: n != 'sel', client.ls('/tag')):
        _create_tag(tagname)

    _taglist = sorted(_tags.itervalues())

def _configure():
    global client
    colors['normcolors'] = ' '.join((colors['normfg'], colors['normbg'], colors['normborder']))
    colors['focuscolors'] = ' '.join((colors['focusfg'], colors['focusbg'], colors['focusborder']))

    if 'normwin' in colors:
        config['normcolors'] = colors['normwin']
    else:
        config['normcolors'] = colors['normcolors']

    if 'focuswin' in colors:
        config['focuscolors'] = colors['focuswin']
    else:
        config['focuscolors'] = colors['focuscolors']

    set_ctl(config)

    cr = []
    for regex, width in colrules.iteritems():
        cr.append('/' + regex + '/ -> ' + width)

    client.write('/colrules', '\n'.join(cr) + '\n')

    tr = []
    for regex, tag in tagrules.iteritems():
        tr.append('/' + regex + '/ -> ' + tag)

    client.write('/tagrules', '\n'.join(tr) + '\n')

_timers = []
def schedule(timeout, func):
    heapq.heappush(_timers, (timeout + int(time.time()), func))

#def process_timers():
    #global _timers
    #now = time.time()
    #while _timers[0][0] < now:
        #timeout, func = heapq.heappop(_timers)
        #func()
#
    #return _timers[0][0] - now

def set_theme(theme):
    colors.update(theme)

_widgets = {}
def register_widget(widget):
    _widgets[widget.name] = widget

_plugins = []
def register_plugin(plugin):
    global _plugins
    _plugins.append(plugin)

def unregister_plugin(plugin):
    global _plugins
    _plugins.remove(plugin)

def _initialize_plugins():
    global _plugins
    for p in _plugins:
        p.init()


def _process_event(event):
    global events
    log.debug('processing event %s' % event.split())
    edata = event.split()
    event = edata[0]
    rest = edata[1:]

    print "Event:", event
    for handler in events.get(event, []):
        handler(*rest)

def _clearbar():
    for i in client.ls('/lbar'):
        client.remove('/'.join(('/lbar', i)))

    for i in client.ls('/rbar'):
        client.remove('/'.join(('/rbar', i)))

def _wmiir():
    p = subprocess.Popen(('wmiir','read','/event'), stdout=subprocess.PIPE)
    #fcntl.fcntl(p.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
    return p

def mainloop():
    global client, _running, _timers

    client.write ('/event', 'Start wmiirc ' + str(os.getpid()))

    _clearbar()
    _configure()
    _initialize_tags()
    _initialize_plugins()
    update_programlist()
    update_keys()

    eventproc = _wmiir()
    poll = select.poll()
    poll.register(eventproc.stdout.fileno(), select.POLLIN)

    timeout = 0
    while _running:
        #print timeout
        p = poll.poll(timeout*1000)
        if p:
            fd, event = p[0]
            if event == select.POLLIN:
                line = eventproc.stdout.readline()
                _process_event(line)
            elif event in (select.POLLHUP, select.POLLNVAL):
                os.kill(eventproc.pid, signal.SIGHUP)
                poll.unregister(eventproc.stdout.fileno())
                eventproc = _wmiir()
                poll.register(eventproc.stdout.fileno(), select.POLLIN)

        #timeout = math.ceil(process_timers()*1000)
        now = time.time()
        while _timers[0][0] <= now:
            #sys.stdout.write(".")
            timeout, func = heapq.heappop(_timers)
            func()
        #sys.stdout.write("\n")

        timeout = max(_timers[0][0] - time.time(), 1)


    os.kill(eventproc.pid, signal.SIGHUP)
    log.debug("Exiting...")


if __name__ == '__main__':
    mainloop()

class Widget:
    def __init__(self, name, bar='rbar'):
        self.name = name
        self.visible = False
        self.bar = bar
        self.fg = colors['normfg']
        self.bg = colors['normbg']
        self.border = colors['normborder']

    def show(self, message):
        colors = ' '.join((self.fg, self.bg, self.border))
        if self.visible:
            client.write('/%s/%s' % (self.bar, self.name), ' '.join((colors, message)))
        else:
            client.create('/%s/%s' % (self.bar, self.name), ' '.join((colors, message)))

    def hide(self):
        client.remove('/%s/%s' % (self.bar, self.name))
        self.visible = False

    def clicked(self, button):
        pass

