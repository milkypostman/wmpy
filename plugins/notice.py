import wmii
import math
import time
import re

class Notice:
    def __init__(self, name='0_msgs', bar='rbar'):
        self.bar = bar
        self.name = name
        self.hexre = re.compile("[0-9a-fA-F][0-9a-fA-F]")

        self.re = re.compile('(.*):\W*(.*)')
        self.symbols = {'charging': '^', 'discharging': '_', 'charged': '='}

    def init(self):
        self.widget = wmii.Widget(self.name, self.bar)
        wmii.register_widget(self.widget)

        self.color_index = 0
        self.colors = []
        self.color_start = ((0xFF,0xFF,0xFF), (0xAA,0x22,0xAA), (0xFF,0x00,0x00))
        self.color_end   = (
                self._triple(wmii.colors['normfg']),
                self._triple(wmii.colors['normbg']),
                self._triple(wmii.colors['normborder']))
        self.color_steps = 10
        self.text = ''

        self._build_colors()

        wmii.events['Notice'] = wmii.events.get('Notice', []).append(self.message)

        self.update()

    def message(self, *args):
        self.text = ' '.join(args)
        self.color_index=9
        self.update()

    def _triple(self, c):
        ctup = []
        for s in self.hexre.findall(c):
            ctup.append(eval("0x"+s))

        return ctup

    def _build_colors(self):
        for i in range(self.color_steps):
            ctuple = []
            for s,e in zip(self.color_start, self.color_end):
                cstr = "#"
                for r in range(3):
                    d = (s[r] - e[r]) / self.color_steps
                    c = math.floor(e[r] + (i * d))
                    cstr += "%02x" % c
                ctuple.append(cstr)
            self.colors.append(ctuple)

    def update(self):
        c = self.colors[self.color_index]
        self.widget.fg = c[0]
        self.widget.bg = c[1]
        self.widget.border = c[2]
        self.widget.show(self.text)

        if self.color_index > 0:
            self.color_index -= 1
            wmii.schedule(1, self.update)
