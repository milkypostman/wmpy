import wmii
import time

class Clock():
    def init(self):
        self.bar = getattr(self, 'bar', 'rbar')
        self.format = getattr(self, 'format', '%Y-%m-%d %H:%M:%S')
        self.name = getattr(self, 'name', '999_clock')
        self.widget = wmii.Widget(self.name)
        self.update()

    def update(self):
        self.widget.show(time.strftime(self.format))
        wmii.schedule(1, self.update)
