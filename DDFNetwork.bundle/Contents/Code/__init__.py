import re
import random
import urllib
import urllib2 as urllib
import urlparse
import json
from datetime import datetime
from PIL import Image
from cStringIO import StringIO

VERSION_NO = '1.2013.06.02.1'
DATEFORMAT = '%B %d, %Y'
XPATHS = {
        'MetadataDate': '//*[@id="sets_details"]/div[3]/div[1]/div[1]/div'
    }

def any(s):
    for v in s:
        if v:
            return True
    return False

def PerformSearch(keyword):
    if "http://" in keyword:
        searchResults = HTML.ElementFromURL(keyword)
    else:
        searchResults = HTML.ElementFromURL('http://ddfnetwork.com/tour-search-scene.php?freeword=' + urllib.quote(keyword))
    return searchResults.xpath('//div[contains(@class,"scene")]')

def Start():
    HTTP.CacheTime = CACHE_1DAY

def SetDateMetadata(date):
    date_object = datetime.strptime(date, DATEFORMAT)
    return date_object

class EXCAgent(Agent.Movies):
    name = 'DDF Network'
    languages = [Locale.Language.English]
    accepts_from = ['com.plexapp.agents.localmedia']
    primary_provider = True

    def search(self, results, media, lang):
        
        title = media.name
        if media.primary_metadata is not None:
            title = media.primary_metadata.title

        Log('*******MEDIA TITLE****** ' + str(title))

        # Search for year
        year = media.year
        if media.primary_metadata is not None:
            year = media.primary_metadata.year

        searchResults = PerformSearch(title)

        for searchResult in searchResults[0].xpath('//p[contains(@class,"set_title")]//a'):
            resultTitle = searchResult.text_content()
            curID = searchResult.get('href').replace('/','_')
            score = 100 - Util.LevenshteinDistance(title.lower(), resultTitle.lower())
            results.Append(MetadataSearchResult(id = curID, name = resultTitle, score = score, lang = lang))
            results.Sort('score', descending=True)            

    def update(self, metadata, media, lang):

        Log('******UPDATE CALLED*******')
        metadata.studio = 'DDF Network'
        url = str(metadata.id).replace('_','/')

        detailsPageElements = HTML.ElementFromURL(url)
        metadata.title = detailsPageElements.xpath('//h1')[0].text_content()
        metadata.summary = detailsPageElements.xpath('//div[@id="sets_story"]')[0].text_content().replace('&13;', '').strip(' \t\n\r"') + "\n\n"
        metadata.tagline = detailsPageElements.xpath('/html/head/title')[0].text_content()
        metadata.originally_available_at = SetDateMetadata(detailsPageElements.xpath(XPATHS['MetadataDate'])[0].text_content())
        metadata.year = metadata.originally_available_at.year

        # Genres
        metadata.genres.clear()
        genres = detailsPageElements.xpath('//div[contains(@class,"sets_tag_list_elems")]//a')
        genreFilter=[]
        if Prefs["excludegenre"] is not None:
            Log("exclude")
            genreFilter = Prefs["excludegenre"].split(';')

        genreMaps=[]
        genreMapsDict = {}

        if Prefs["tagmapping"] is not None:
            Log("tagmapping")
            genreMaps = Prefs["tagmapping"].split(';')
            for mapping in genreMaps:
                keyVal = mapping.split("=")
                genreMapsDict[keyVal[0]] = keyVal[1]
        else:
            genreMapsDict = None

        if len(genres) > 0:
            for genreLink in genres:
                genreName = genreLink.text_content().strip('\n')
                if any(genreName in g for g in genreFilter) == False:
                    if genreMapsDict is not None:
                        if genreName in genreMapsDict:
                            Log(genreMapsDict[genreName])
                            metadata.genres.add(genreMapsDict[genreName])
                        else:
                            Log('Not Mapped')
                            metadata.genres.add(genreName)
                    else:
                        metadata.genres.add(genreName)

        metadata.roles.clear()
        metadata.collections.clear()
     
        starring = None
        starring = detailsPageElements.xpath('//h3[contains(@class,"casts")]//a')
        for member in starring:
            role = metadata.roles.new()
            actor = member.text_content().strip()
            if " aka " in actor:
                actor = actor.split(" aka ")[0]
            role.actor = actor
            metadata.collections.add(member.text_content().strip())

        #Background
        backgroundUrl = detailsPageElements.xpath('//video[@id="html5_trailer_player"]')[0].get('data-preview')
        metadata.art[backgroundUrl] = Proxy.Preview(HTTP.Request(backgroundUrl, headers={'Referer': 'http://www.google.com'}).content, sort_order = 0)
        coverPage = HTML.ElementFromURL('http://ddfnetwork.com/tour-search-scene.php?freeword=' + urllib.quote(metadata.title).replace('%5Cu2019','%E2%80%99'))
        cover = coverPage.xpath('//a[contains(@href,"' + url + '")]//img')[0].get('src')

        metadata.posters[cover] = Proxy.Preview(HTTP.Request(cover).content, sort_order = 0)
