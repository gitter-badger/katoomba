import pprint, re
import requests

def escape(text):
    import cgi
    return cgi.escape(text).encode('ascii', 'xmlcharrefreplace').replace('\n', '<br />')

titleRE = re.compile('<title>([^<]+)</title>', re.IGNORECASE)

def massageLink(link):
    html = '<a href="%s"><code>%s</code></a>' % (link, link)
    action = None
    try:
        response = requests.get(link, verify = False)
    except requests.exceptions.ConnectionError:
        action = 'Check documentation link: %s' % html
        html += ' <span style="color: rgb(255,0,0);">(Link did not respond)</span>'
    else:
        status_code = response.status_code
        if status_code < 400:
            m = titleRE.search(response.text)
            if m:
                title = m.group(1).strip().replace('\n', ' ')
                if title:
                    html = '<a href="%s">%s</a>' % (link, escape(title))
        else:
            action = 'Check documentation link: %s' % html
            html += ' <span style="color: rgb(255,0,0);">(Link returned status %d)</span>' % status_code
    return html, action

requestJSON = {'Accept': 'application/json'}

def getAll(requestLink):
    page = 0
    totalPages = 1
    results = []
    while page < totalPages:
        params = {
            'page': page + 1, # URL page numbers are 1-based
            'per_page': 50
        }
        request = requests.get(requestLink, params=params, headers=requestJSON)
        result = request.json()
        keys = result.keys()
        if len(keys) != 1:
            raise RuntimeError('expected single top-level result')
        key = keys[0]
        pageResults = result[key]
        totalPages = pageResults['pages']
        results.extend(pageResults['results'])
        page += 1
    return results

class Category:

    def __init__(self, dict):
        self.dict = dict

    def __str__(self):
        return '{name}'.format(**self.dict)

    def __repr__(self):
        return 'Category%s' % self.dict

class Categories:

    def __init__(self, server):
        self.server = server
        self.categories = None

    def __getitem__(self, resource):
        return self.getCategories()[resource]

    def getCategories(self):
        if self.categories is None:
            result = self.server.getAll('categories')
            self.categories = {category['resource']: Category(category) for category in result}
        return self.categories

    def __iter__(self):
        return self.getCategories().itervalues()

class Service:

    def __init__(self, dict):
        self.dict = dict
        self.summary = None

    def __str__(self):
        return '{name}'.format(**self.dict)

    def __repr__(self):
        return 'Service%s' % self.dict

    def __getattr__(self, name):
        return self.dict[name]

    def getSummary(self):
        if self.summary is None:
            response = requests.get(self.resource + '/summary', headers=requestJSON)
            self.summary = response.json()['service']
            pprint.pprint(self.summary)
        return self.summary

    @property
    def contacts(self):
        return self.getSummary()['summary']['contacts']
    @contacts.setter
    def contacts(self, value):
        raise NotImplementedError

    @property
    def documentation_urls(self):
        return self.getSummary()['summary']['documentation_urls']
    @documentation_urls.setter
    def documentation_urls(self, value):
        raise NotImplementedError

class Services:

    def __init__(self, server):
        self.server = server
        self.services = None

    def __getitem__(self, resource):
        return self.getServices()[resource]

    def getServices(self):
        if self.services is None:
            result = self.server.getAll('services')
            self.services = {service['resource']: Service(service) for service in result}
        return self.services

    def __iter__(self):
        return self.getServices().itervalues()

class ServiceCatalographer:

    def __init__(self, url):
        self.url = url
        self.categories = None
        self.services = None

    def getUrl(self):
        return self.url

    def getAll(self, url):
        return getAll(self.url + url)

    def getCategories(self):
        if self.categories is None:
            self.categories = Categories(self)
        return self.categories

    def getServices(self):
        if self.services is None:
            self.services = Services(self)
        return self.services


def report(service):
    content = '<h1>%s</h1>\n' % service.name
    level1 = []
    level2 = []
    level3 = []
    other = []
    description = service.description
    if description is None:
        level1.append('Add service description')
    elif len(description) < 10 or description == service.name:
        level1.append('Improve service description')
    else:
        content += '<p>%s</p>\n' % escape(description.strip())

    documentation_urls = service.documentation_urls
    if documentation_urls:
        for url in documentation_urls:
            link, action = massageLink(url)
            content += '<p>Documentation: %s</p>\n' % link
    else:
        level1.append('Add documentation link')

    contacts = service.contacts
    if contacts:
        for contact in contacts:
            content += '<p>Contact: %s</p>\n' % escape(contact)
    else:
        level1.append('Add contact')

    if level1:
        content += '<p>Provisional level: 0 (subject to manual review)</p>\n'
        content += '<p>To obtain level 1, this service requires the following actions:</p>\n'
        for item in level1:
            content += '<p>- %s</p>\n' % item
    elif level2:
        content += '<p>Provisional level: 1 (subject to manual review)</p>\n'
        content += '<p>To obtain level 2, this service requires the following actions:</p>\n'
        for item in level2:
            content += '<p>- %s</p>\n' % item
    elif level3:
        content += '<p>Provisional level: 2 (subject to manual review)</p>\n'
        content += '<p>To obtain level 3, this service requires the following actions:</p>\n'
        for item in level3:
            content += '<p>- %s</p>\n' % item
    else:
        content += '<p>Provisional level: TBD</p>\n'
    if other:
        content += '<p>Other actions:</p>\n'
        for item in other:
            content += '<p>- %s</p>\n' % item
    return content

from config import confluenceHost, confluenceUser, confluencePass
confluenceBase = 'https://%s/rpc/json-rpc/confluenceservice-v2' % confluenceHost
import json
from requests.auth import HTTPBasicAuth

params = dict(
    auth = HTTPBasicAuth(confluenceUser, confluencePass),
    verify = False, # not yet setup to verify the server certificate
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
        }
    )

def getPageId(space, title):
    response = requests.post(confluenceBase + '/getPage',
        data=json.dumps([space, title]), **params)
    response.raise_for_status()
    page = response.json()
    pageId = page['id']
    return pageId

def publish(content, space, title, parentId):
    response = requests.post(confluenceBase + '/getPage',
        data=json.dumps([space, title]), **params)
    print(response.url)
    response.raise_for_status()
    page = response.json()
    if page.has_key('error'):
        code = page['error']['code']
        if code == 500:
            prevContent = None
            update = {
                'space': space,
                'title': title,
                'content': content,
                'parentId': parentId
            }
            pageUpdateOptions = dict(
                versionComment = 'Triggered update',
                minorEdit = False
                )

            response = requests.post(confluenceBase + '/storePage',
                data=json.dumps([update]), **params)
            print(response.url)
            response.raise_for_status()
            print(response.text)
    else:
        prevContent = page['content']

        if prevContent != content:
            # Although Confluence documentation states that additional arguments are
            # ignored, updates fail unless we use the bare minimum of required arguments.
            update = {
                'id': page['id'],
                'space': page['space'],
                'title': page['title'],
                'content': content,
                'version': page['version'],
                'parentId': page['parentId']
            }
            pageUpdateOptions = dict(
                versionComment = 'Triggered update',
                minorEdit = False
                )

            response = requests.post(confluenceBase + '/storePage',
                data=json.dumps([update]), **params)
            print(response.url)
            response.raise_for_status()
            print(response.text)


if __name__ == '__main__':
    c = ServiceCatalographer('https://www.biodiversitycatalogue.org/')
    # for category in c.getCategories():
    #     print(category)
    for service in sorted(c.getServices(), key=lambda service: service.name.lower()):
        content = report(service)
        serviceId = service.resource.split('/')[-1]
        publish(content, 'BioVeL', 'Service %s (%s) Evaluation' % (serviceId, service.name), getPageId('BioVeL', 'Automatic Service Summary'))

