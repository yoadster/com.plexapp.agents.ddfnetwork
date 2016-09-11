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
        'MetadataDate': '//*[@id="sets_details"]/div[3]/div[1]/div[1]/div',
        'SceneTitleAnchor': '//p[contains(@class,"set_title")]//a'
}
LOGMESSAGES = {
    'SearchNormal': '***SEARCH*** Normal search being used',
    'SearchUserDefined': '***SEARCH*** User defined search being used',
    'SearchWildcard': '***SEARCH*** Wildcard search being used',
    'TitleFilename': '***SEARCH*** Using filename as title',
    'TitlePrimaryMetadata': '***SEARCH*** Using primary metadata as title',
    'TitleMediaName': '***SEARCH*** Using media name as title'
}
CONSTS = {
    'SearchUrl': 'http://ddfnetwork.com/tour-search-scene.php?freeword=',
    'UserDefinedString': 'http://',
    'WildcardString': '_'
}

def any(s):
    for v in s:
        if v:
            return True
    return False

def Start():
    HTTP.CacheTime = CACHE_1DAY

class EXCAgent(Agent.Movies):
    
    name = 'DDF Network'
    languages = [Locale.Language.English]
    accepts_from = ['com.plexapp.agents.localmedia']
    primary_provider = True

    def search(self, results, media, lang):

        for scene in SearchResultsCollection(self.GetTitleFromMedia(media)).Results:      
            results.Append(MetadataSearchResult(id = scene.id, name = scene.title, score = scene.score, lang = lang))
        results.Sort('score', descending=True)            

    def update(self, metadata, media, lang):

        Log('******UPDATE CALLED*******')
        metadata.studio = 'DDF Network'
        url = str(metadata.id).replace('_','/')

        detailsPageElements = HTML.ElementFromURL(url)
        metadata.title = detailsPageElements.xpath('//h1')[0].text_content()
        metadata.summary = detailsPageElements.xpath('//div[@id="sets_story"]')[0].text_content().replace('&13;', '').strip(' \t\n\r"') + "\n\n"
        metadata.tagline = detailsPageElements.xpath('/html/head/title')[0].text_content()
        metadata.originally_available_at = self.SetDateMetadata(detailsPageElements.xpath(XPATHS['MetadataDate'])[0].text_content())
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
            role.title = actor
            metadata.collections.add(member.text_content().strip())

        #Background
        #backgroundUrl = detailsPageElements.xpath('//video[@id="html5_trailer_player"]')[0].get('data-preview')
        #metadata.art[backgroundUrl] = Proxy.Preview(HTTP.Request(backgroundUrl, headers={'Referer': 'http://www.google.com'}).content, sort_order = 0)
        #coverPage = HTML.ElementFromURL('http://ddfnetwork.com/tour-search-scene.php?freeword=' + urllib.quote(metadata.title).replace('%5Cu2019','%E2%80%99'))
        #cover = coverPage.xpath('//a[contains(@href,"' + url + '")]//img')[0].get('src')

        #metadata.posters[cover] = Proxy.Preview(HTTP.Request(cover).content, sort_order = 0)

    def GetTitleFromMedia(self, media):     
        title = media.name
        if CONSTS['UserDefinedString'] not in title or CONSTS['WildcardString'] not in title:
            if media.filename is not None:
                Log(LOGMESSAGES['TitleFilename'])
                filePath = urllib.unquote(media.filename).decode('utf8')
                filePathSegments = filePath.split("\\")
                title = filePathSegments[len(filePathSegments) -1].split(".")[0]
            else:
                if media.primary_metadata is not None:
                    Log(LOGMESSAGES['TitlePrimaryMetadata'])
                    title = media.primary_metadata.title
        else:
            Log(LOGMESSAGES['TitleMediaName'])
        return title

    def SetDateMetadata(self, date):
            return datetime.strptime(date, DATEFORMAT)

#A class defining a search result
class SearchResult:
    
    def __init__(self, searchResultElement, keyword):
        if CONSTS['UserDefinedString'] in searchResultElement:
            self.title = searchResultElement
            self.id = searchResultElement.replace("/","_")
            self.score = 100
        else:
            try:
                titleAnchor = searchResultElement.xpath(XPATHS['SceneTitleAnchor'])[0]
                self.title = titleAnchor.text_content()
                self.cover = '' #TODO: Append cover url to url
                self.score = 100 - Util.LevenshteinDistance(keyword, self.title)
                self.id = titleAnchor.get('href').replace("/","_")
            except:
                pass        
        
#A collection of SearchResult classes derived from a keyword search
class SearchResultsCollection:
    
    #Init the collection
    def __init__(self, keyword):
        self.Results = []
        if not (keyword is None):
            if CONSTS['UserDefinedString'] not in keyword and CONSTS['WildcardString'] not in keyword:
                Log(LOGMESSAGES['SearchNormal'])
                results = self.performSearch(keyword)
            else:
                if CONSTS['WildcardString'] in keyword:
                    Log(LOGMESSAGES['SearchWildcard'])
                    results = self.performSearch(keyword.replace(CONSTS['WildcardString'],": "))
                    if len(results) == 1:
                        results = self.performSearch(keyword.replace(CONSTS['WildcardString']," - "))
                        if len(results) == 1:
                            return
                else:
                    if CONSTS['UserDefinedString'] in keyword:
                        Log(LOGMESSAGES['SearchUserDefined'])
                        self.Results.append(SearchResult(keyword,None))
                        return
            
            for searchResultObject in results:
                self.Results.append(SearchResult(searchResultObject, keyword))

    #Perform a search based on a keyword provided
    def performSearch(self, keyword):
        return HTML.ElementFromURL(CONSTS['SearchUrl'] + urllib.quote(keyword)).xpath('//div[contains(@class,"scene")]')


