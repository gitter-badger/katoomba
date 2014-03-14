import re, requests

def escape(text):
    import cgi
    return cgi.escape(text).encode('ascii', 'xmlcharrefreplace').replace('\n', '<br />')

titleRE = re.compile('<title>([^<]+)</title>', re.IGNORECASE)

def massageLink(link):
    html = '<a href="%s"><code>%s</code></a>' % (link, link)
    try:
        response = requests.get(link, verify = False)
    except requests.exceptions.ConnectionError:
        html += ' <span style="color: rgb(255,0,0);">(Link did not respond)</span>'
    except requests.exceptions.MissingSchema:
        html = '%s (Not a valid link)' % escape(link)
    else:
        status_code = response.status_code
        if status_code < 400:
            m = titleRE.search(response.text)
            if m:
                title = m.group(1).strip().replace('\n', ' ')
                if title:
                    html = '<a href="%s">%s</a>' % (link, escape(title))
        else:
            html += ' <span style="color: rgb(255,0,0);">(Link returned status %d)</span>' % status_code
    return html

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
    print serviceJson
    content = ''
    serviceLink = serviceJson['resource']
    name = serviceJson['name']
    submitterLink = serviceJson['submitter']
    response = requests.get(submitterLink, headers=requestJSON)
    json = response.json()
    print json
    user = json['user']
    submitter = user['name']
    org = user['affiliation']
    if org:
        submitter += ', ' + org
    email = user['public_email']
    if email:
        submitter += ' (%s)' % email
    serviceId = serviceLink[serviceLink.rfind('/') + 1:]
    content += '<p><small>Submitted as <a href="%s">BiodiversityCatalogue service #%s</a> by %s</small></p>\n' % (serviceLink, serviceId, submitter)
    annotations = getAll(serviceLink + '/annotations')
    categoryIds = []
    for annotation in annotations:
        if annotation['attribute']['identifier'] == 'http://biodiversitycatalogue.org/attribute/category':
            categoryIds.append(annotation['value']['resource'])
    if categoryIds:
        content += '<p>Categories: %s</p>\n' % ', '.join([escape(categoryName[categoryId]) for categoryId in categoryIds])
    description = serviceJson['description']
    if description is None:
        description = '<p><span style="color: rgb(255,0,0);">No description provided</span></p>'
    else:
        description = '<p>' + escape(description.strip()) + '</p>'
    content += '%s\n' % description
    response = requests.get(serviceLink + '/summary', headers=requestJSON)
    json = response.json()
    print json
    service = json['service']
    summary = service['summary']
    docLinks = summary['documentation_urls']
    if docLinks:
        for docLink in docLinks:
            content += '<p>Documentation: %s</p>\n' % massageLink(docLink)
            if docLink.startswith('http://wiki.biovel.eu') or docLink.startswith('https://wiki.biovel.eu'):
                if docLink.startswith('http://wiki.biovel.eu/x/') or docLink.startswith('https://wiki.biovel.eu/x/'):
                    pass
                else:
                    content += '<p><span style="color: rgb(255,0,0);">Links to BioVeL Wiki should use short links</span></p>\n'
    else:
        content += '<p><span style="color: rgb(255,0,0);">No link to documentation</span></p>\n'
    content += '<p>Service provider: %s</p>\n' % escape(', '.join([provider['service_provider']['name'] for provider in summary['providers']]))
    # content += '<p>Service protocol: %s</p>\n' % escape(', '.join(service['service_technology_types']))

    contacts = summary['contacts']
    if contacts:
        for contact in contacts:
            content += '<p>Contact: %s</p>\n' % escape(contact)
    else:
        content += '<p><span style="color: rgb(255,0,0);">No support contact listed</span></p>\n'
    publications = summary['publications']
    for publication in publications:
        content += '<p>Publication: %s</p>\n' % escape(publication)

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

final = """
<div class="contentLayout" data-atlassian-layout="{&quot;name&quot;:&quot;pagelayout-two-simple-right&quot;,&quot;columns&quot;:[&quot;large&quot;,&quot;aside&quot;]}">
  <div class="columnLayout twoColumns">
      <div class="cell large">
          <div class="innerCell">
"""


for catName, services in sorted(categorisedServices.items()):
    if services:
        final += '<hr/>\n\n<h2>%s</h2>\n<hr/>\n' % escape(catName)
        for name, service in sorted(services.items()):
            final += '\n<h3>%s</h3>\n' % escape(name)
            final += service
            final += '<hr/>\n'
if uncategorisedServices:
    final += '<hr/>\n\n<h2>Uncategorised Services</h2>\n<hr/>\n'
    for name, service in sorted(uncategorisedServices.items()):
        final += '\n<h3>%s</h3>\n' % escape(name)
        final += service
        final += '<hr/>\n'

final += """
          </div>
      </div>
      <div class="cell aside">
          <div class="innerCell">
              <ac:macro ac:name="toc" />
          </div>
      </div>
  </div>
</div>
"""

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
