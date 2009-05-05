import wmii
import urllib
import xml.etree.ElementTree as ElementTree

WEATHER_URL = 'http://xml.weather.yahoo.com/forecastrss?p=%s'
WEATHER_NS = 'http://xml.weather.yahoo.com/ns/rss/1.0'

class Weather:
    def __init__(self, name='600_weather', zipcode=52245, bar='rbar'):
        self.name = name
        self.zipcode = zipcode
        self.bar = bar

    def init(self):
        self.widget = wmii.Widget(self.name, self.bar)
        wmii.register_widget(self.widget)
        self.update()

    def update(self):
        url = WEATHER_URL % self.zipcode
        try:
            rss = ElementTree.parse(urllib.urlopen(url)).getroot()
        except IOError:
            self.widget.show('N/A')
            wmii.schedule(30, self.update)
            return
        #forecasts = []
        #for element in rss.findall('channel/item/{%s}forecast' % WEATHER_NS):
            #forecasts.append({
                #'date': element.get('date'),
                #'low': element.get('low'),
                #'high': element.get('high'),
                #'condition': element.get('text')
            #})
        #print url
        temp = rss.find('channel/item/{%s}condition' % WEATHER_NS).get('temp')
        units = rss.find('channel/{%s}units' % WEATHER_NS).get('temperature')
        self.widget.show(temp+units)
        wmii.schedule(60, self.update)
