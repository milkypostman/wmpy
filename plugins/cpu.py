import wmii
import time
import re
from operator import add
from itertools import imap
import math

class CPU:
    _initialized = False
    _widgets = {}

    def __init__(self, name='750_cpu', cpu=0, bar='rbar'):
        self.cpu = cpu
        self.bar = bar
        self.name = name

    def init(self):
        if not CPU._initialized:
            CPU._clsinit()

        self.widget = wmii.Widget(self.name, self.bar)
        wmii.register_widget(self.widget)

        CPU.addwidget(self.cpu, self.widget)

    @classmethod
    def addwidget(cls, cpu, widget):
        try:
            cls._widgets[cpu].append(widget)
        except KeyError:
            cls._widgets[cpu] = [widget]

    @classmethod
    def _clsinit(cls):
        cls._re = re.compile('^cpu')
        cls._sep = re.compile('[ *]*')
        cls._file = open('/proc/stat', 'r')
        cls.data = {}

        cls._update(0)

        cls._initialized = True

    @classmethod
    def _update(cls, timeout=3):
        cls._file.seek(0)
        i = 0
        for line in cls._file:
            if cls._re.match(line):
                info = cls._sep.split(line)
                active = reduce(add, imap(int, info[1:4]))
                total = active + int(info[4])

                try:
                    difftotal = total - cls.data[i]['total']
                    diffactive = active - cls.data[i]['active']
                except KeyError:
                    difftotal = total
                    diffactive = active
                    cls.data[i] = {}

                cls.data[i]['usage'] = math.floor((float(diffactive) / difftotal) * 100)
                cls.data[i]['total'] = total
                cls.data[i]['active'] = active

                for w in cls._widgets.get(i, []):
                    w.show(str(cls.data[i]['usage']))

                i += 1

        wmii.schedule(timeout, cls._update)
