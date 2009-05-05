import wmii
import socket

try:
    import mpd
except ImportError:
    mpd = None

class MPD:
    def __init__(self, name='1_mpd', format="%(artist)s - %(title)s", hostname='localhost', port=6600, bar='rbar'):
        self.format = format
        self.bar = bar
        self.name = name
        self.hostname = hostname
        self.port = port
        self._mpd = None

    def init(self):
        if mpd is None:
            wmii.unregister_plugin(self)
            return

        self.widget = wmii.Widget(self.name, self.bar)
        wmii.register_widget(self.widget)
        self.widget.clicked = self.widget_clicked
        self.widget.fg = wmii.colors.get('mpd_fg', wmii.colors['normfg'])


        self._mpd = mpd.MPDClient()
        self._buttons = {
                2 : self.toggle,
                1 : self._mpd.next,
                3 : self._mpd.previous,
                4 : self.fwd,
                5 : self.rwd,
                }
        self.update()

    def _connect(self):
        try:
            self._mpd.connect(self.hostname, self.port)
        except socket.error:
            return False

        return True

    def update(self):
        if self._mpd._sock is None and not self._connect():
            wmii.schedule(10, self.update)
            return

        self._update()
        wmii.schedule(5, self.update)

    def _update(self):
        text = None
        try:
            state = self._mpd.status()['state']
            if state == 'play':
                text = self.format % self._mpd.currentsong()
            else:
                text = state
            self.widget.show(text)
        except mpd.ConnectionError:
            self.widget.hide()
            self._mpd.disconnect()

    def toggle(self):
        state = self._mpd.status()['state']
        if state == 'play':
            self._mpd.pause()
        else:
            self._mpd.play()

    def rwd(self):
        status = self._mpd.status()
        if status['state'] in ('play', 'pause'):
            curtime, tottime = status['time'].split(':')
            curtime = max(int(curtime)-1, 0)
            self._mpd.seekid(status['songid'], curtime)

    def fwd(self):
        status = self._mpd.status()
        if status['state'] in ('play', 'pause'):
            curtime, tottime = status['time'].split(':')
            curtime = min(int(curtime)+1, tottime)
            self._mpd.seekid(status['songid'], curtime)

    def widget_clicked(self, button):
        if self._mpd._sock == None:
            return

        if button in self._buttons:
            self._buttons[button]()

        self._update()

