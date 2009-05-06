import wmii
import time
import math

try:
    import alsaaudio
except ImportError:
    alsaaudio = None

import ossaudiodev
import operator

class Volume:
    def __init__(self, name='800_volume', device='Master', bar='rbar', med=30, high=70, step=1, driver='alsa'):
        self.device = device
        self.bar = bar
        self.name = name
        self.med = med
        self.high = high
        self.step = step
        if driver == 'alsa' and alsaaudio is None :
            driver = 'oss'

        self.driver = driver

    def init(self):
        getattr(self, '_init_' + self.driver)()
        self.min = 0
        self.max = 100

        self.widget = wmii.Widget(self.name, self.bar)
        wmii.register_widget(self.widget)
        self.widget.clicked = self.widget_clicked

        self.fglow = wmii.colors.get('volume_fglow', wmii.colors['normfg'])
        self.fgmed = wmii.colors.get('volume_fgmed', wmii.colors['normfg'])
        self.fghigh = wmii.colors.get('volume_fghigh', wmii.colors['normfg'])

        self.update()

    def _init_oss(self):
        self.device_mask = getattr(ossaudiodev, "SOUND_MIXER_%s" % self.device.upper(), None)
        if self.device_mask is None:
            self.device_mask = getattr(ossaudiodev, "SOUND_MIXER_VOLUME")

        self.mixer = ossaudiodev.openmixer()

    def _init_alsa(self):
        self.mixer = alsaaudio.Mixer(self.device)
        self.min, self.max = self.mixer.getrange()

    def _update_alsa(self):
        vol = self.mixer.getvolume()
        self.current = reduce(operator.add, vol) / len(vol)
        return round((float(self.current) / self.max) * 100)

    def _update_oss(self):
        vol = self.mixer.get(self.device_mask)
        self.current = reduce(operator.add, vol) / len(vol)
        return round((float(self.current) / self.max) * 100)

    def update(self):
        self._update()
        wmii.schedule(5, self.update)

    def _update(self):
        percent = getattr(self, '_update_' + self.driver)()
        fg = self.fglow
        if percent > self.high:
            fg = self.fghigh
        elif percent > self.med:
            fg = self.fgmed

        self.widget.fg = fg
        self.widget.show("%d%%" % percent)

    def _set_alsa(self, value):
        self.mixer.setvolume(value)

    def _set_oss(self, value):
        self.mixer.set(self.device_mask, (value,value))

    def widget_clicked(self, button):
        if button == 5:
            newval =  max(self.current-self.step, self.min)
            getattr(self, "_set_" + self.driver)(newval)
            self._update()
        elif button == 4:
            newval =  min(self.current+self.step, self.max)
            getattr(self, "_set_" + self.driver)(newval)
            self._update()
