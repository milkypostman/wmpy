import wmii
import time

class Clock:
    def __init__(self, name='999_clock', bar='rbar', format='%Y-%m-%d %H:%M:%S'):
        self.bar = bar
        self.format = format
        self.name = name

    def init(self):
        self.widget = wmii.Widget(self.name, self.bar)
        wmii.register_widget(self.widget)
        self.widget.clicked = self.widget_clicked
        self.update()

    def update(self):
        self.widget.show(time.strftime(self.format))
        wmii.schedule(1, self.update)

    def widget_clicked(self, button):
        print "clock clicked"
