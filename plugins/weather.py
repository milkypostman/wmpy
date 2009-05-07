import wmii
import urllib
import threading
import time
import thread
import logging
log = logging.getLogger('wmii.weather')

try:
    import xml.etree.ElementTree as ElementTree
except ImportError:
    import elementtree.ElementTree as ElementTree

WEATHER_URL = 'http://xml.weather.yahoo.com/forecastrss?p=%s'
WEATHER_NS = 'http://xml.weather.yahoo.com/ns/rss/1.0'

class Weather:
    def __init__(self, name='600_weather', zipcode=52245, bar='rbar'):
        self.name = name
        self.zipcode = zipcode
        self.bar = bar
        self.available = False

    def init(self):
        self.widget = wmii.Widget(self.name, self.bar)
        wmii.register_widget(self.widget)
        #self.thread = threading.Thread(target=self.update)
        #self.thread.daemon = True
        #self.thread.start()
        thread.start_new_thread(self.update, ())

    def update(self):
        while True:
            log.debug("updating...")
            url = WEATHER_URL % self.zipcode
            try:
                log.debug("retrieving url...")
                rss = ElementTree.parse(urllib.urlopen(url)).getroot()
            except IOError:
                log.debug("IOError when retrieving url, retrying in 30 seconds.")
                self.widget.show('N/A')
                time.sleep(30)
                continue
            #forecasts = []
            #for element in rss.findall('channel/item/{%s}forecast' % WEATHER_NS):
                #forecasts.append({
                    #'date': element.get('date'),
                    #'low': element.get('low'),
                    #'high': element.get('high'),
                    #'condition': element.get('text')
                #})
            #print url
            self.temp = rss.find('channel/item/{%s}condition' % WEATHER_NS).get('temp')
            self.units = rss.find('channel/{%s}units' % WEATHER_NS).get('temperature')

            self.widget.show(self.temp+self.units)
            time.sleep(60)
