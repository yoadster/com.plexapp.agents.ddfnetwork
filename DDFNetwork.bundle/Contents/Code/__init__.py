import re
import random
import urllib
import urllib2 as urllib
import urlparse
import json
import time
from datetime import datetime
from PIL import Image
from cStringIO import StringIO

VERSION_NO = '1.2013.06.02.1'
DATEFORMAT = '%B %d, %Y'
XPATHS = {
        'MetadataDate': '//*[@id="wrapper"]/main/div[3]/div/div[1]/h2/time',
        'SceneTitleAnchor': '//p[contains(@class,"set_title")]//a',
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
        r = SearchResultsCollection(self.GetTitleFromMedia(media)).Results
        for scene in r:
            try:  
                results.Append(MetadataSearchResult(id = scene.id, name = scene.title, score = scene.score, lang = lang))
            except:
                pass
            
        results.Sort('score', descending=True)

    def update(self, metadata, media, lang):

        Log('******UPDATE CALLED*******')

        metadata.studio = 'DDF Network'
        url = str(metadata.id).replace('_','/').replace('http://es.','http://').replace('http://fr.','http://').replace('http://it.','http://').replace("http://it.it.","http").replace("http://de.","http://")
        try:
            coverpage = url.split("&coverpage=")[1]
        except:
            coverpage = None

        try:
            accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36'
            headers = { 'Accept' : accept }

            req = urllib.Request(url)
            req.add_header('Accept', accept)
            resp = urllib.urlopen(req)
            detailsPageElements = HTML.ElementFromString(resp.read())
        except urllib.HTTPError as e:
            Log(e.code)
            Log(e.read())
        
        #detailsPageElements = HTML.ElementFromURL(url)

        
            

        metadata.title = detailsPageElements.xpath('//h1')[0].text_content()
        metadata.summary = detailsPageElements.xpath('//div[@class="about-text"]//p')[0].text_content().replace('&13;', '').replace('\n',' ').replace('\r',' ').strip(' \t\n\r"') + "\n\n"
        metadata.tagline = detailsPageElements.xpath('/html/head/title')[0].text_content()
        try:
            metadata.originally_available_at = self.GetFormattedDate(detailsPageElements.xpath(XPATHS['MetadataDate'])[0].text_content())
            metadata.year = metadata.originally_available_at.year
        except Exception, e:
            Log(str(e))
            pass

        # Genres
        metadata.genres.clear()
        genres = detailsPageElements.xpath('//ul[contains(@class,"tags")]//a')
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
        starring = detailsPageElements.xpath('//h2[@class="actors"]//a')
        if len(starring) == 0:
            starring = detailsPageElements.xpath('//*[@id="wrapper"]/main/div[4]/div/div[1]/h2//a')
            
        for member in starring:
            role = metadata.roles.new()
            actor = member.text_content().strip()
            if " aka " in actor:
                actor = actor.split(" aka ")[0]
            role.name = actor
            metadata.collections.add(member.text_content().strip())

        #Background
        try:
            backgroundUrl = detailsPageElements.xpath('//video[@id="trailer"]')[0].get('poster')
            if not self.PosterAlreadyExists(backgroundUrl,metadata):
                metadata.art[backgroundUrl] = Proxy.Preview(HTTP.Request(backgroundUrl, headers={'Referer': 'http://www.google.com'}).content, sort_order = 0)
        except:
            pass

        cover = self.GetCoverPage('http://ddfnetwork.com' + starring[0].get('href'),metadata.title.lower())
        if not self.PosterAlreadyExists(cover,metadata):
            metadata.posters[cover] = Proxy.Preview(HTTP.Request(cover).content, sort_order = 0)

    def GetCoverPage(self, url, title):
        
        Log("Getting cover page")
        Log(title)
        Log(url)

        page = 1
        while True:
            try:
                accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36'
                headers = { 'Accept' : accept }
                if 'http' in url:
                    u = url + "/" + str(page)
                    Log(u)
                    req = urllib.Request(url + "/" + str(page))
                    req.add_header('Accept', accept)
                    resp = urllib.urlopen(req)
                    ele = HTML.ElementFromString(resp.read())
                    test = ele.xpath('//h2')
                    if len(test) == 0:
                        scenes = ele.xpath('//div[contains(@class,"cover-wrap")]//img')
                        for s in scenes:
                            alt = s.get('alt').lower()
                            if alt !='':
                                Log("alt = " + alt)
                                if (alt in title) or (title in alt):
                                    return s.get('src')
                    else:
                        break
                page = page + 1
            except:
                Log("Got to page: " + str(page))
                break

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
        return title.lower()

    def GetFormattedDate(self, date):
        date = date.replace("Septembre","September")
        date = date.replace("Septiembre","September")
        date = date.replace("Mayo","May")
        date = date.replace("Junio","June")
        date = date.replace("Juin","June")
        date = date.replace("Giugno","June")
        date = date.replace("6.","June")
        date = date.replace("Januar","January")
        date = date.replace("Januaryy","January")
        date = date.replace("  ", " ")
        date = date.replace("2.","February")
        date = date.replace("11.","November")
        date = date.replace("Dicembre","December")
        date = date.replace("1.","January")
        date = date.replace("3.","March")
        date = date.replace("4.","April")
        date = date.replace("5.","May")
        date = date.replace("7.","July")
        date = date.replace("8.","August")
        date = date.replace("9.","September")
        date = date.replace("10.","October")
        date = date.replace("1February","February")
        date = date.replace("M\xc3\xa4rz","March")
        date = date.replace("Maggio","May")
        date = date.replace("Noviembre","November")
        date = date.replace("Octubre","October")
        return datetime.strptime(date, DATEFORMAT)
    
    def PosterAlreadyExists(self,posterUrl,metadata):
        if "?" in posterUrl:
            dnsSegment = posterUrl.split('?')[0].lower()
        else:
            dnsSegment = posterUrl.lower()
        for p in metadata.posters.keys():
            key = p.lower()
            if dnsSegment in p:
                return True
        for p in metadata.art.keys():
            key = p.lower()
            if dnsSegment == p:
                return True
        return False

#A class defining a search result
class SearchResult:
    
    def __init__(self, searchResultElement, keyword):

        if searchResultElement is not None:
            if CONSTS['UserDefinedString'] in searchResultElement:
                Log("OK")
                self.title = searchResultElement
                self.id = searchResultElement.replace("/","_")
                self.score = 100
            else:
                try:
                    titleAnchor = searchResultElement.xpath(XPATHS['SceneTitleAnchor'])[0]
                    self.title = titleAnchor.text_content()
                    self.cover = searchResultElement.xpath('//a[contains(@href,"' + titleAnchor.get('href') + '")]//img')[0].get('src').replace("/","_")
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
            keyword = keyword.replace('strap on','strap-on')
            if CONSTS['UserDefinedString'] not in keyword and CONSTS['WildcardString'] not in keyword:
                Log(LOGMESSAGES['SearchNormal'])
                results = []
            else:
                if CONSTS['WildcardString'] in keyword:
                    Log(LOGMESSAGES['SearchWildcard'])
		    results = []
                else:
                    if CONSTS['UserDefinedString'] in keyword:
                        Log(LOGMESSAGES['SearchUserDefined'])
                        self.Results.append(SearchResult(keyword,None))
                        return

	    Log(len(results))
            if len(results) == 0:
		Log("Performing google search")
                self.performGoogleSearch(keyword)

            #for searchResultObject in results:
                #self.Results.append(SearchResult(searchResultObject, keyword))

    def processResultUrl(self, url):
        if "jp.milf." in url:
            url = url.replace("jp.milf.","")
        if "jp.m." in url:
            url = url.replace("jp.m.","")
        if "jp.tattoo." in url:
            url = url.replace("jp.tattoo.","")
        if "join." in url:
            url = url.replace("join.","")
        if "beta." in url:
            url = url.replace("beta.","")
        if "brazzers." in url:
            url = url.replace("brazzers.","")
        if "it.it" in url:
            url = url.replace("it.it.","")
        return url.replace("join.","").replace("jp.","")

    def performGoogleSearch(self, keyword):
        k = keyword.replace(" - ","+").replace("_", "+").replace(": ","+").replace(" ","+").replace("&","and").lower()
        if Prefs["useapi"] is not False:
            key = Prefs["key"]
            siteid = Prefs["siteid"]
            res = JSON.ObjectFromURL('https://www.googleapis.com/customsearch/v1?q=' + k + '&cx=' + siteid + '&fields=items(link%2Ctitle)&key=' + key)
            for s in res['items']:
                url = s["link"].lower()
                title = s["title"].replace(": "," ").replace(" - "," ").replace("...","").replace("'","").replace("  "," ").lower().strip()
                markup = keyword.replace(": "," ").replace(" - "," ").replace("_"," ").replace("  "," ").lower().strip()

                Log("SEarch result: " + title + " - keyword: " + markup)
                
                if (markup in title) or (title in markup):
                    self.Results.append(SearchResult(self.processResultUrl(url),None))
        
