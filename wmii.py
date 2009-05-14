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
from itertools import chain
from operator import itemgetter

log = logging.getLogger('wmii')

HOME=os.path.join(os.getenv('HOME'), '.wmii-hg')
HISTORYSIZE=5

#log.debug('creating new instance of client')
client = pyxp.Wmii('unix!/tmp/ns.dcurtis.:0/wmii')

# applications
apps = {
        'terminal': 'xterm',
}

# pre-allocated tags
tags = { 'main' : 1,
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
    'main' : '65+35',
}

# default tagrules
tagrules = {
    'Firefox.*': 'www',
    'Gimp.*': 'gimp+~',
    'MPlayer.*': '~',
}

_tagidxheap = []
_tagidx = {}
_tagname = {}
_tagname_reserved = {}
_tagidxname = ()
_tagidxname_reserved = ()

_running = True

def get_ctl(name):
    global client
    for line in client.read('/ctl').split('\n'):
        if line.startswith(name):
            return line[line.find(' ')+1:]

def set_ctl(name, value = None):
    global client
    if value == None and isinstance(name, dict):
        client.write('/ctl', '\n'.join( (' '.join((n, v)) for n,v in name.iteritems()) ))
    else:
        client.write('/ctl',' '.join((name,value)))

def set_client_tag_startswith(char):
    global client, _tagname_reserved, _tagname, _tagidxname_reserved
    currentname = get_ctl('view')
    currentidx = -1
    possible = []
    for idx,name in chain(
            _tagidxname_reserved,
            (idxname for idxname in _tagidxname if idxname[1] not in tags)
            ):
        if name[0] == char:
            if name == currentname:
                currentidx = len(possible)
            possible.append(name)

    client.write('/client/sel/tags', possible[(currentidx+1) % len(possible)])

def set_tag_startswith(char):
    """ Set to next tag that starts with 'char'.  Includes reserved tags. """
    global _tagname_reserved, _tagname, _tagidxname_reserved
    currentname = get_ctl('view')
    currentidx = -1
    possible = []
    for idx,name in chain(
            _tagidxname_reserved,
            (idxname for idxname in _tagidxname if idxname[1] not in tags)
            ):
        if name[0] == char:
            if name == currentname:
                currentidx = len(possible)
            possible.append(name)

    set_ctl('view', possible[(currentidx+1) % len(possible)])

def set_tag_idx(idx):
    global _tagname_reserved, _tagname
    if idx in _tagname_reserved:
        set_ctl('view', _tagname_reserved[idx])
    elif idx in _tagname:
        set_ctl('view', _tagname[idx])

def set_client_tag_idx(idx):
    global client, _tagname_reserved, _tagname
    if idx in _tagname_reserved:
        client.write('/client/sel/tags', _tagname_reserved[idx])
    elif idx in _tagname:
        client.write('/client/sel/tags', _tagname[idx])

_programlist = None
def update_programlist():
    global _programlist

    proc = subprocess.Popen("dmenu_path", stdout=subprocess.PIPE)
    _programlist = []
    for prog in proc.stdout:
        _programlist.append(prog.strip())

def program_menu(*args):
    global _programlist
    if _programlist is None:
        update_programlist()

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

def set_tag(tag):
    if tag:
        set_ctl('view', tag)

def set_client_tag(tag):
    if tag:
        client.write('/client/sel/tags', tag)

def tag_menu():
    return menu('tag', (tag for idx,tag in _tagidxname))

keybindings = {
        'Mod1-p':lambda _: execute(program_menu()),
        'Mod1-j':lambda _: client.write('/tag/sel/ctl', 'select down'),
        'Mod1-k':lambda _: client.write('/tag/sel/ctl', 'select up'),
        'Mod1-h':lambda _: client.write('/tag/sel/ctl', 'select left'),
        'Mod1-l':lambda _: client.write('/tag/sel/ctl', 'select right'),
        'Mod1-Shift-j':lambda _: client.write('/tag/sel/ctl', 'send sel down'),
        'Mod1-Shift-k':lambda _: client.write('/tag/sel/ctl', 'send sel up'),
        'Mod1-Shift-h':lambda _: client.write('/tag/sel/ctl', 'send sel left'),
        'Mod1-Shift-l':lambda _: client.write('/tag/sel/ctl', 'send sel right'),
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
        }

def _update_keys():
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
    global _tagidx

    view = get_ctl('view')
    idx = _tagidxname.index( (_tagidx[view], view) )

    idx,view = _tagidxname[(idx + ofs) % len(_tagidxname)]

    set_ctl('view', view)

def _obtaintagidx():
    global _tagidxheap
    return heapq.heappop(_tagidxheap)

def _releasetagidx(idx):
    global _tagidxheap
    if idx not in _tagname_reserved:
        heapq.heappush(_tagidxheap, idx)

def event_leftbarclick(button, id):
    global _tagname
    div = id.find('_')
    try:
        idx = int(id[:div])
        tag = id[div+1:]
        if idx in _tagname and _tagname[idx] == tag:
            set_ctl('view', tag)
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

def event_focustag(tag):
    global _tagidx
    idx = _tagidx[tag]
    client.write(''.join(['/lbar/', str(idx), '_', tag]), ' '.join(
        (colors['focuscolors'], tag)
    ))

def event_unfocustag(tag):
    global _tagidx
    idx = _tagidx[tag]
    client.write(''.join(['/lbar/', str(idx), '_', tag]), ' '.join(
        (colors['normcolors'], tag)
    ))

def event_createtag(tag):
    global _tagname, _tagidx, _tagidxname

    if tag in tags:
        idx = tags[tag]
    else:
        idx = _obtaintagidx()

    _tagidx[tag] = idx
    _tagname[idx] = tag

    _tagidxname = sorted(_tagname.iteritems())

    client.create(''.join(['/lbar/', str(idx), '_', tag]), tag)

def event_destroytag(tag):
    global _tagname, _tagidx, _tagidxname, tags, _tagname_reserved, colors
    freeidx = _tagidx[tag]
    del _tagidx[tag]
    client.remove(''.join(['/lbar/', str(freeidx), '_', tag]))

    if freeidx not in _tagname_reserved:
        # FIXME: gotta be an easier way to do this.
        focusedtag = get_ctl('view')
        for idx, tag in _tagidxname:
            if idx > freeidx and idx not in _tagname_reserved:
                _tagname[freeidx] = tag
                _tagidx[tag] = freeidx
                client.remove(''.join(['/lbar/', str(idx), '_', tag]))
                if tag == focusedtag:
                    color = colors['focuscolors']
                else:
                    color = colors['normcolors']
                client.create(''.join(['/lbar/', str(freeidx), '_', tag]), ' '.join((color, tag)))
                freeidx = idx

        _releasetagidx(freeidx)

    del _tagname[freeidx]

    _tagidxname = sorted(_tagname.iteritems())

def event_start(*vargs):
    global _running

    if len(vargs) < 2:
        return

    if vargs[1] == 'wmpy' and int(vargs[2]) == os.getpid():
        return

    _running = False

events = {
        'Key': [event_key],
        'FocusTag': [event_focustag],
        'UnfocusTag': [event_unfocustag],
        'CreateTag': [event_createtag],
        'DestroyTag': [event_destroytag],
        'LeftBarClick': [event_leftbarclick],
        'RightBarClick': [event_rightbarclick],
        'Start': [event_start],
        }

def _initialize_tags():
    global _tagidx, _tagname, _tagidxname, _tagidxheap, _tagname_reserved, _tagidxname_reserved 
    global client

    focusedtag = get_ctl('view')

    for tag, idx in tags.iteritems():
        _tagname_reserved[idx] = tag
    _tagidxname_reserved = sorted(_tagname_reserved.iteritems())

    _tagidxheap = [i for i in range(1,10) if i not in _tagname_reserved]
    heapq.heapify(_tagidxheap)

    for tag in filter(lambda n: n != 'sel', client.ls('/tag')):
        if tag in tags:
            idx = tags[tag]
        else:
            idx = _obtaintagidx()

        _tagidx[tag] = idx
        _tagname[idx] = tag
        if tag == focusedtag:
            color = colors['focuscolors']
        else:
            color = colors['normcolors']

        client.create(''.join(['/lbar/', str(idx), '_', tag]), ' '.join((color, tag)))

    _tagidxname = sorted(_tagname.iteritems())

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
    _update_keys()

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
            timeout, func = heapq.heappop(_timers)
            func()

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

    def clicked(self, button):
        pass

