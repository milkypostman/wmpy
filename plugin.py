
class Plugin:
    def __init__(self):
        init = getattr(self, 'init')
        if callable(init):
            self.init()
