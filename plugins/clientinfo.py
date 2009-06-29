import wmii
import math
import time
import re

class ClientInfo:
    def init(self):
        self.widget = wmii.Widget(self.name, self.bar)
        wmii.register_widget(self.widget)
        self.widget.fg = wmii.colors.get('client_fg', wmii.colors['normfg'])

        wmii.events['ClientFocus'] = wmii.events.get('ClientFocus', []).append(self.update)


        self.update()

    def update(self):
        try:
            label = wmii.client.read('/client/sel/label')
        except IOError:
            return

        self.widget.show(label)

