import cgi, requests

def escape(text):
    return cgi.escape(text).encode('ascii', 'xmlcharrefreplace')

requestJSON = {'Accept': 'application/json'}

class Service:

    pass

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

categories = getAll('https://www.biodiversitycatalogue.org/categories')

categoryParent = {}
categoryName = {}
categorisedServices = {}
uncategorisedServices = {}

for category in categories:
    link = category['resource']
    response = requests.get(link, headers=requestJSON)
    cat = response.json()['category']
    catName = cat['name']
    categoryName[link] = catName
    parent = cat.get('broader')
    if parent:
        categoryParent[link] = parent['resource']
    else:
        categoryParent[link] = None
        categorisedServices[catName] = {}

results = getAll('https://www.biodiversitycatalogue.org/services')

for serviceJson in results:
    content = ''
    serviceLink = serviceJson['resource']
    name = serviceJson['name']
    description = serviceJson['description']
    if description is None:
        description = '<p><strong>No description provided</strong></p>'
    else:
        description = '<p>' + escape(description.strip()) + '</p>'
    content += '%s\n' % description
    submitterLink = serviceJson['submitter']
    request = requests.get(submitterLink, headers=requestJSON)
    user = request.json()['user']
    submitter = user['name']
    org = user['affiliation']
    if org:
        submitter += ', ' + org
    email = user['public_email']
    if email:
        submitter += ' (%s)' % email
    annotations = getAll(serviceLink + '/annotations')
    categoryIds = []
    for annotation in annotations:
        if annotation['attribute']['identifier'] == 'http://biodiversitycatalogue.org/attribute/category':
            categoryIds.append(annotation['value']['resource'])
    if categoryIds:
        content += '<p>Categories:\n<ul>\n'
        for categoryId in categoryIds:
            content += '<li>%s</li>\n' % escape(categoryName[categoryId])
            pass
        content += '</ul></p>\n'
    request = requests.get(serviceLink + '/summary', headers=requestJSON)
    summary = request.json()['service']['summary']
    docLinks = summary['documentation_urls']
    if docLinks:
        for docLink in docLinks:
            content += '<p>Documentation: <code><a href="%s">%s</a></code></p>\n' % (docLink, docLink)
            if docLink.startswith('http://wiki.biovel.eu') or docLink.startswith('https://wiki.biovel.eu'):
                if docLink.startswith('http://wiki.biovel.eu/x/') or docLink.startswith('https://wiki.biovel.eu/x/'):
                    pass
                else:
                    content += '<p><strong>Links to BioVeL Wiki should use short links</strong></p>\n'
    else:
        content += '<p><strong>No documentation</strong></p>\n'
    contacts = summary['contacts']
    if contacts:
        for contact in contacts:
            content += '<p>Contact: %s</p>\n' % escape(contact)
    else:
        content += '<p><strong>No contact listed</strong></p>\n'
    publications = summary['publications']
    for publication in publications:
        content += '<p>Publication: %s</p>\n' % escape(publication)
    content += '<p>More information at <a href="%s">BiodiversityCatalogue</a>, submitted by %s\n' % (serviceLink, submitter)

    if categoryIds:
        tlc = set()
        for categoryId in categoryIds:
            parentId = categoryParent[categoryId]
            while parentId is not None:
                categoryId = parentId
                parentId = categoryParent[categoryId]
            tlc.add(categoryName[categoryId])
        for topLevel in tlc:
            categorisedServices[topLevel][name] = content
    else:
        uncategorisedServices[name] = content

final = '<ac:macro ac:name="toc" />\n'
# '''<ac:structured-macro ac:name="toc" xmlns:ac="http://www.atlassian.com/schema/confluence/4/ac/">
#   <ac:parameter ac:name="printable">true</ac:parameter>
#   <ac:parameter ac:name="style">square</ac:parameter>
#   <ac:parameter ac:name="maxLevel">2</ac:parameter>
#   <ac:parameter ac:name="indent">5px</ac:parameter>
#   <ac:parameter ac:name="minLevel">2</ac:parameter>
#   <ac:parameter ac:name="class">bigpink</ac:parameter>
#   <ac:parameter ac:name="exclude">[1//2]</ac:parameter>
#   <ac:parameter ac:name="type">list</ac:parameter>
#   <ac:parameter ac:name="outline">true</ac:parameter>
#   <ac:parameter ac:name="include">.*</ac:parameter>
# </ac:structured-macro>
# '''

for catName, services in sorted(categorisedServices.items()):
    if services:
        final += '<h1>%s</h1>\n<hr/>\n' % escape(catName)
        for name, service in sorted(services.items()):
            final += '<h2>%s</h2>\n' % escape(name)
            final += service
if uncategorisedServices:
    final += '<h1>Uncategorised Services</h1>\n'
    for name, service in sorted(uncategorisedServices.items()):
        final += '<h2>%s</h2>\n' % escape(name)
        final += service

content = final

# Ensure the remote API has been enabled 
# https://confluence.atlassian.com/display/DOC/Enabling+the+Remote+API

requestJSON = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

from config import *

confluenceBase = 'https://%s/rpc/json-rpc/confluenceservice-v2' % confluenceHost

import json
from requests.auth import HTTPBasicAuth

kw = dict(
    auth = HTTPBasicAuth(confluenceUser, confluencePass),
    verify = False, # not yet setup to verify the server certificate
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
        }
    )

response = requests.post(confluenceBase + '/getPage', 
    data=json.dumps(['BioVeL', 'Automatic Service Summary']), **kw)
print response.url
response.raise_for_status()
print response.text
page = response.json()

if page['content'] != content:
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
        data=json.dumps([update]), **kw)
    print response.url
    response.raise_for_status()
    print response.text
