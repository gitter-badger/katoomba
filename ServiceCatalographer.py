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
    except requests.exceptions.MissingSchema:
        action = 'Remove text from documentation links'
        html = '%s <span style="color: rgb(255,0,0);">(Not a valid link)</span>' % escape(link)
    else:
        status_code = response.status_code
        if status_code < 400:
            m = titleRE.search(response.text)
            if m:
                title = m.group(1).strip().replace('\n', ' ')
                if title:
                    html = '<a href="%s">%s</a>' % (link, escape(title))
            if link.startswith('http://wiki.biovel.eu') or link.startswith('https://wiki.biovel.eu'):
                if link.startswith('http://wiki.biovel.eu/x/') or link.startswith('https://wiki.biovel.eu/x/'):
                    pass
                else:
                    html += ' <span style="color: rgb(255,0,0);">(BioVeL Wiki long link)</span>'
                    action = 'Change BioVeL Wiki long link to tiny link (using Wiki menu Tools -> Link to this page...)'
        else:
            action = 'Check documentation link: %s' % html
            html += ' <span style="color: rgb(255,0,0);">(Link returned status %d)</span>' % status_code
    return html, action

requestJSON = {'Accept': 'application/json'}

def getAll(requestLink, resultKey=None):
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
        assert key == resultKey, key
        pageResults = result[key]
        totalPages = pageResults['pages']
        results.extend(pageResults['results'])
        page += 1
    return results

class Category:

    def __init__(self, dict):
        self.dict = dict

    def __getattr__(self, name):
        try:
            return self.dict[name]
        except KeyError:
            raise AttributeError(name)

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

    def __init__(self, server, dict):
        self.server = server
        self.dict = dict
        self.annotations = None
        self.deployments = None
        self.summary = None
        self.variants = None

    def __str__(self):
        return '{name}'.format(**self.dict)

    def __repr__(self):
        return 'Service%s' % self.dict

    def __getattr__(self, name):
        try:
            return self.dict[name]
        except KeyError:
            raise AttributeError(name)

    def getAll(self, url, tag=None):
        if tag is None:
            tag = url
        return getAll(self.resource + '/' + url, tag)

    def getSummary(self):
        if self.summary is None:
            response = requests.get(self.resource + '/summary', headers=requestJSON)
            self.summary = response.json()['service']
            # pprint.pprint(self.summary)
        return self.summary

    def getAnnotations(self):
        if self.annotations is None:
            self.annotations = self.getAll('annotations')
        return self.annotations

    def getVariants(self):
        if self.variants is None:
            response = requests.get(self.resource + '/variants', headers=requestJSON)
            self.variants = response.json()['service']
            # pprint.pprint(self.variants)
        return self.variants

    @property
    def categories(self):
        categoryList = []
        categoryMap = self.server.getCategories()
        annotations = self.getAnnotations()
        for annotation in annotations:
            # pprint.pprint(annotation)
            if annotation['attribute']['identifier'] == 'http://biodiversitycatalogue.org/attribute/category':
                categoryId = annotation['value']['resource']
                categoryList.append(categoryMap[categoryId])
        return categoryList
    @categories.setter
    def categories(self, value):
        raise NotImplementedError

    @property
    def contacts(self):
        return self.getSummary()['summary']['contacts']
    @contacts.setter
    def contacts(self, value):
        raise NotImplementedError

    @property
    def descriptions(self):
        description0 = service.description
        summary = service.getSummary()
        descriptions = summary['summary']['descriptions']
        if description0 and (not descriptions or descriptions[0] != description0):
            # REST services repeat the main description in the additional descriptions
            # SOAP services don't - because the main description comes from the WSDL?
            descriptions.insert(0, description0)
        return descriptions or None
    @descriptions.setter
    def descriptions(self, value):
        raise NotImplementedError

    @property
    def documentation_urls(self):
        return self.getSummary()['summary']['documentation_urls']
    @documentation_urls.setter
    def documentation_urls(self, value):
        raise NotImplementedError

    @property
    def licenses(self):
        return self.getSummary()['summary']['licenses']
    @licenses.setter
    def licenses(self, value):
        raise NotImplementedError

    @property
    def submitter(self):
        return self.server.getUsers()[self.dict['submitter']]
    @submitter.setter
    def submitter(self, value):
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
            self.services = {service['resource']: Service(self.server, service) for service in result}
        return self.services

    def __iter__(self):
        return self.getServices().itervalues()

class ServiceProvider:

    def __init__(self, dict):
        self.dict = dict

    def __getattr__(self, name):
        try:
            return self.dict[name]
        except KeyError:
            raise AttributeError(name)

    def __str__(self):
        return '{name}'.format(**self.dict)

    def __repr__(self):
        return 'ServiceProvider%s' % self.dict

class ServiceProviders:

    def __init__(self, server):
        self.server = server
        self.providers = {}

    def __getitem__(self, resource):
        provider = self.providers.get(resource)
        if provider is None:
            response = requests.get(resource, headers=requestJSON)
            result = response.json()['service_provider']
            provider = ServiceProvider(result)
            self.providers[resource] = provider
        return provider

class User:

    def __init__(self, dict):
        self.dict = dict

    def __getattr__(self, name):
        try:
            return self.dict[name]
        except KeyError:
            raise AttributeError(name)

    def __str__(self):
        return '{name}'.format(**self.dict)

    def __repr__(self):
        return 'User%s' % self.dict

class Users:

    def __init__(self, server):
        self.server = server
        self.users = {}

    def __getitem__(self, resource):
        user = self.users.get(resource)
        if user is None:
            response = requests.get(resource, headers=requestJSON)
            result = response.json()['user']
            user = User(result)
            self.users[resource] = user
        return user

class RestMethod:

    def __init__(self, dict):
        self.dict = dict

    def __getattr__(self, name):
        try:
            return self.dict[name]
        except KeyError:
            raise AttributeError(name)

    def __str__(self):
        return '{name}'.format(**self.dict)

    def __repr__(self):
        return 'RestMethod%s' % self.dict

class RestMethods:

    def __init__(self, server):
        self.server = server
        self.methods = {}

    def __getitem__(self, resource):
        method = self.methods.get(resource)
        if method is None:
            response = requests.get(resource, headers=requestJSON)
            result = response.json()['rest_method']
            method = RestMethod(result)
            self.methods[resource] = method
        return method

class ServiceCatalographer:

    def __init__(self, url):
        self.url = url
        self.categories = Categories(self)
        self.services = Services(self)
        self.users = Users(self)

    def getUrl(self):
        return self.url

    def getAll(self, url, tag=None):
        if tag is None:
            tag = url
        return getAll(self.url + url, tag)

    def getCategories(self):
        return self.categories

    def getServices(self):
        return self.services

    def getUsers(self):
        return self.users

def reportRest(level):
    method = RestMethods(c)['https://www.biodiversitycatalogue.org/rest_methods/71.json']
    content = '<h4>%s</h4>\n' % escape(method.endpoint_label)
    content += '<p>%s</p>\n' % escape(method.description)
    content += '<p><code>%s %s</code></p>\n' % (escape(method.http_method_type), escape(method.url_template))
    content += '<table>\n'
    content += '<tr><th colspan="2">Inputs</th></tr>'
    for parameter in method.inputs['parameters']:
        name = parameter['name']
        description = parameter['description']
        if not description:
            level[3].append('Method %s parameter %s: add description' % (escape(method.endpoint_label), escape(name)))
            description = ''
        content += '<tr><td>%s</td><td>%s</td></tr>\n' % (name, description)
    content += '</table>'

def report(service):
    content = '<h1>%s</h1>\n' % service.name
    level = ([], [], [], [])

    submitter = service.submitter
    user = submitter.name
    org = submitter.affiliation
    if org:
        user += ', ' + org
    email = submitter.public_email
    if email:
        user += ' (%s)' % email
    content += '<p><small>Submitted to <a href="%s">BiodiversityCatalogue</a> by %s</small></p>\n' % (service.resource, escape(user))

    categories = service.categories
    if categories:
        content += '<p>Categories: %s</p>\n' % ', '.join([escape(category.name) for category in categories])
    else:
        level[2].append('Add service to a category')

    descriptions = service.descriptions
    if descriptions is None:
        level[1].append('Add service description')
    elif len(descriptions) == 1 and descriptions[0] == service.name:
        level[1].append('Improve service description')
    else:
        for description in descriptions:
            content += '<p>%s</p>\n' % escape(description.strip())

    documentation_urls = service.documentation_urls
    if documentation_urls:
        for url in documentation_urls:
            link, action = massageLink(url)
            if action:
                level[0].append(action)
            content += '<p>Documentation: %s</p>\n' % link
    else:
        level[1].append('Add documentation link')

    licenses = service.licenses
    if licenses:
        for license in licenses:
            content += '<p>License: %s</p>\n' % escape(license)
    else:
        level[2].append('Add license details')

    contacts = service.contacts
    if contacts:
        for contact in contacts:
            content += '<p>Contact: %s</p>\n' % escape(contact)
    else:
        level[1].append('Add contact')

    # deployments = service.deployments
    # for deployment in service.deployments:
    #     endpoint = deployment['endpoint']
    #     content += '<h2><code>%s</code></h2>\n' % escape(endpoint)

    # for variant in service.getVariants()['variants']:

    if level[0]:
        content += '<p>To allow further evaluation, please solve these problems:</p>'
        for item in level[0]:
            content += '<p>- %s</p>\n' % item
    elif level[1]:
        content += '<p>Provisional level: 0</p>\n'
        content += '<p>To obtain level 1, this service requires the following actions:</p>\n'
        for item in level[1]:
            content += '<p>- %s</p>\n' % item
    elif level[2]:
        content += '<p>Provisional level: 1 (subject to manual review)</p>\n'
        content += '<p>To obtain level 2, this service requires the following actions:</p>\n'
        for item in level[2]:
            content += '<p>- %s</p>\n' % item
    elif level[3]:
        content += '<p>Provisional level: 2 (subject to manual review)</p>\n'
        content += '<p>To obtain level 3, this service requires the following actions:</p>\n'
        for item in level[3]:
            content += '<p>- %s</p>\n' % item
    else:
        content += '<p>Provisional level: TBD</p>\n'
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
    print(title)
    response = requests.post(confluenceBase + '/getPage',
        data=json.dumps([space, title]), **params)
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
            response.raise_for_status()
    else:
        prevContent = page['content']

        if prevContent != content:
            # Although Confluence documentation states that additional arguments are
            # ignored, updates fail unless we use the bare minimum of required arguments.
            with open('old%s.html' % page['id'], 'wt') as f:
                f.write(prevContent)
            with open('new%s.html' % page['id'], 'wt') as f:
                f.write(content)
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
            response.raise_for_status()


if __name__ == '__main__':
    c = ServiceCatalographer('https://www.biodiversitycatalogue.org/')
    # for category in c.getCategories():
    #     print(category)
    for service in sorted(c.getServices(), key=lambda service: service.name.lower()):
        content = report(service)
        serviceId = service.resource.split('/')[-1]
        publish(content, 'BioVeL', 'Service %s (%s) Evaluation' % (serviceId, service.name), getPageId('BioVeL', 'Automatic Service Summary'))

