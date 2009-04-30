import pyxp
import subprocess
import time
import heapq
import re
import select
import os
import sys
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('wmii')

HOME=os.path.join(os.getenv('HOME'), '.wmii-hg')
HISTORYSIZE=5

#log.debug('creating new instance of client')
client = pyxp.Wmii('unix!/tmp/ns.dcurtis.:0/wmii')

apps = {
        'terminal': 'xterm',
}

tags = { 'main' : 1,
        'www' : 2,
        }


colors = {
    'fg_normal' : '#000000',
    'bg_normal' : '#c1c48b',
    'border_normal': '#81654f',
    'fg_focus' : '#000000',
    'bg_focus' : '#81654f',
    'border_focus': '#000000',
}

config = {
        'bar': 'on top',
        'grabmod': 'Mod1',
        'view': 'main',
        }

_tagidxheap = []
_tagidx = {}
_tagname = {}
_tagname_reserved = {}
_tagidxname = ()

def getctl(name):
    global client
    for line in client.read('/ctl').split('\n'):
        if line.startswith(name):
            return line[line.find(' ')+1:]

def setctl(name, value = None):
    global client
    if value == None and isinstance(name, dict):
        client.write('/ctl', '\n'.join( (' '.join((n, v)) for n,v in name.iteritems()) ))
    else:
        client.write('/ctl',' '.join((name,value)))

def settagidx(idx):
    if idx in _tagname_reserved:
        setctl('view', _tagname_reserved[idx])
    if idx in _tagname:
        setctl('view', _tagname[idx])

_programlist = None
def update_programlist():
    global _programlist

    proc = subprocess.Popen("dmenu_path", stdout=subprocess.PIPE)
    _programlist = []
    for prog in proc.stdout:
        _programlist.append(prog.strip())

def program_menu():
    global _programlist
    if _programlist is None:
        update_programlist()

    prog = menu('cmd', _programlist)

    if prog:
        execute(prog).pid
        #log.debug("program %s started with pid %d..." % (prog, pid))

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

def execute(cmd):
    setsid = getattr(os, 'setsid', None)
    if not setsid:
        setsid = getattr(os, 'setpgrp', None)

    return subprocess.Popen(cmd, shell=True, preexec_fn=setsid)

keybindings = {
        'Mod1-p':lambda _: program_menu(),
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
        'Mod1-comma':lambda _: setviewofs(-1),
        'Mod1-period':lambda _: setviewofs(1),
        'Mod4-#':lambda key: settagidx(int(key[key.find('-')+1:])),
        'Mod1-Shift-c':lambda _: client.write('/client/sel/ctl', 'kill'),
        'Mod1-Return':lambda _: execute(apps['terminal']),
        }

def _update_keys():
    global keybindings
    global client
    numre = re.compile('(.*-)#')

    keys = []
    for key in keybindings:
        match = numre.match(key)
        if match:
            pfx = match.group(1)
            keys.extend([pfx+str(i) for i in range(10)])

        keys.append(key)

    client.write('/keys', '\n'.join(keys))


def setviewofs(ofs):
    global client
    global _tagidx

    view = getctl('view')
    idx = _tagidxname.index( (_tagidx[view], view) )

    idx,view = _tagidxname[(idx + ofs) % len(_tagidxname)]

    setctl('view', view)

def _obtaintagidx():
    global _tagidxheap
    return heapq.heappop(_tagidxheap)

def _releasetagidx(idx):
    global _tagidxheap
    heapq.heappush(_tagidxheap, idx)

def event_leftbarclick(button, id):
    global _tagname
    div = id.find('_')
    try:
        idx = int(id[:div])
        tag = id[div+1:]
        if _tagname[idx] == tag:
            setctl('view', tag)
    except ValueError:
        return

def event_key(key):
    #log.debug('key event: %s' % key)
    func = keybindings.get(key, None)
    if callable(func):
        func(key)
    else:
        numkey = re.sub('-\d*', '-#', key)
        func = keybindings.get(numkey, None)
        if callable(func):
            func(key)

def event_focustag(tag):
    global _tagidx
    idx = _tagidx[tag]
    client.write(''.join(['/lbar/', str(idx), '_', tag]), ' '.join((
    (config['focuscolors'], tag)
    )))

def event_unfocustag(tag):
    global _tagidx
    idx = _tagidx[tag]
    client.write(''.join(['/lbar/', str(idx), '_', tag]), ' '.join((
    (config['normcolors'], tag)
    )))

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
    global _tagname, _tagidx, _tagidxname, tags
    idx = _tagidx[tag]
    del _tagname[idx]
    del _tagidx[tag]

    _tagidxname = sorted(_tagname.iteritems())
    client.remove(''.join(['/lbar/', str(idx), '_', tag]))

events = {
        'Key': [event_key],
        'FocusTag': [event_focustag],
        'UnfocusTag': [event_unfocustag],
        'CreateTag': [event_createtag],
        'DestroyTag': [event_destroytag],
        'LeftBarClick': [event_leftbarclick],
        }

def _initialize_tags():
    global _tagidx, _tagname, _tagidxname, _tagidxheap, _tagname_reserved
    global client

    for i in client.ls('/lbar'):
        client.remove('/'.join(('/lbar', i)))

    focusedtag = getctl('view')
    print focusedtag

    for tag, idx in tags.iteritems():
        _tagname_reserved[idx] = tag

    print _tagname_reserved
    _tagidxheap = [i for i in range(1,10) if i not in _tagname_reserved]
    heapq.heapify(_tagidxheap)

    print _tagidxheap

    for tag in filter(lambda n: n != 'sel', client.ls('/tag')):
        if tag in tags:
            idx = tags[tag]
        else:
            idx = _obtaintagidx()

        _tagidx[tag] = idx
        _tagname[idx] = tag
        if tag == focusedtag:
            color = getctl('focuscolors')
        else:
            color = getctl('normcolors')

        client.create(''.join(['/lbar/', str(idx), '_', tag]), ' '.join((color, tag)))

    _tagidxname = sorted(_tagname.iteritems())

def _configure():
    global client
    if 'normcolors' not in config:
        config['normcolors'] = ' '.join((colors['fg_normal'], colors['bg_normal'], colors['border_normal']))
    if 'focuscolors' not in config:
        config['focuscolors'] = ' '.join((colors['fg_focus'], colors['bg_focus'], colors['border_focus']))

    setctl(config)


plugins = []
def _load_plugins():
    global plugins
    plugin = __import__('clock').plugin()
    plugins.append(plugin)

def process_event(event):
    global events
    log.debug('processing event %s' % event.split())
    edata = event.split()
    event = edata[0]
    rest = edata[1:]

    for handler in events.get(event, []):
        handler(*rest)

def mainloop():
    global client

    sys.path.append(os.path.expandvars('$HOME/.wmii-hg/plugins'))

    _configure()

    _initialize_tags()

    _update_keys()

    _load_plugins()

    eventproc = subprocess.Popen(("wmiir","read","/event"), stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    while True:
        timeout = 5
        while True:
            s = time.time()
            rdy, _, _ = select.select([eventproc.stdout], [], [], timeout)
            if not rdy:
                break
            e = time.time()

            line = rdy[0].readline()
            process_event(line)

            timeout -= e-s


if __name__ == '__main__':
    mainloop()
