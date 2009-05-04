import wmii
import time
import ossaudiodev
import operator

class Volume():
    def __init__(self, name='800_volume', device='volume', bar='rbar', med=30, high=70):
        self.device_mask = getattr(ossaudiodev, "SOUND_MIXER_%s" % device.upper(), "SOUND_MIXER_VOLUME")
        self.bar = bar
        self.name = name
        self.med = med
        self.high = high

    def init(self):
        self.widget = wmii.Widget(self.name, self.bar)
        self.mixer = ossaudiodev.openmixer()
        wmii.register_widget(self.widget)
        self.widget.clicked = self.widget_clicked

        self.fglow = wmii.colors.get('volume_fglow', wmii.colors['normfg'])
        self.fgmed = wmii.colors.get('volume_fgmed', wmii.colors['normfg'])
        self.fghigh = wmii.colors.get('volume_fghigh', wmii.colors['normfg'])

        self.update()

    def update(self, reschedule=True):
        self.current = self.mixer.get(self.device_mask)
        avg = reduce(operator.add, self.current)/2

        fg = self.fglow
        if avg > self.high:
            fg = self.fghigh
        elif avg > self.med:
            fg = self.fgmed

        self.widget.fg = fg
        self.widget.show("%d%%" % self.current[0])
        if reschedule:
            wmii.schedule(4, self.update)

    def widget_clicked(self, button):
        if button == '5':
            newval =  map(lambda v: max(v-2, 0), self.current)
            self.mixer.set(self.device_mask, newval)
            self.update(False)
        elif button == '4':
            newval =  map(lambda v: min(v+2, 100), self.current)
            self.mixer.set(self.device_mask, newval)
            self.update(False)
