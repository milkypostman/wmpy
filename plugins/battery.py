import wmii
import time
import re

class Battery():
    def __init__(self, name='700_battery', battery="BAT0", bar='rbar'):
        self.battery = battery
        self.bar = bar
        self.name = name

        self.re = re.compile('(.*):\W*(.*)')
        self.symbols = {'charging': '^', 'discharging': '_', 'charged': '='}

    def init(self):
        self.widget = wmii.Widget(self.name, self.bar)
        wmii.register_widget(self.widget)

        self.file = open('/proc/acpi/battery/%s/state' %self.battery, 'r')
        self._loadinfo()

        self.update()

    def _parse(self, fileobj):
        data = {}
        for line in fileobj:
            m = self.re.match(line)
            if m:
                data[m.group(1)] = m.group(2)
        return data

    def _loadinfo(self):
        file = open('/proc/acpi/battery/%s/info' %self.battery, 'r')
        data = self._parse(file)

        self.capacity = int(data["last full capacity"].split()[0])
        self.warn = int(data["design capacity warning"].split()[0])
        self.low = int(data["design capacity low"].split()[0])

    def update(self):
        self.file.seek(0)
        data = self._parse(self.file)

        state = data['charging state']
        rate = int(data['present rate'].split()[0])
        remaining = int(data['remaining capacity'].split()[0])
        timeleft = remaining / float(rate)
        hoursleft = int(timeleft)
        minutesleft = (timeleft - hoursleft) * 60

        symbol = self.symbols[state]
        self.widget.show("%2d:%2d %s%2d%s" % (hoursleft, minutesleft, symbol, float(remaining)/self.capacity * 100, symbol) )

        wmii.schedule(60, self.update)
