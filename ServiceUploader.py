import json
import requests
from requests.auth import HTTPBasicAuth

import ServiceCatalographer, ServiceReporter
from config import confluenceHost, confluenceUser, confluencePass

confluenceBase = 'https://%s/rpc/json-rpc/confluenceservice-v2' % confluenceHost

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
    if 'error' in page:
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
            newPage = response.json()
            if 'error' in newPage:
                raise RuntimeError(newPage['error']['message'])
        else:
            raise RuntimeError(page['error']['message'])
    else:
        prevContent = page['content']

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
        response.raise_for_status()

        newPage = response.json()
        if 'error' in newPage:
            raise RuntimeError(newPage['error']['message'])
        assert 'content' in newPage, newPage
        newContent = newPage['content']

        # if newContent == prevContent:
        #     response = requests.post(confluenceBase + '/removePageVersionByVersion',
        #         data=json.dumps([newPage['id'], page['version']]), **params)
        #     response.raise_for_status()
        #     reply = response.json()
        #     if reply.has_key('error'):
        #         raise RuntimeError(reply['error']['message'])
        #     dsd
        # else:
        #     with open('old%s.html' % page['id'], 'wt') as f:
        #         f.write(prevContent)
        #     with open('new%s.html' % page['id'], 'wt') as f:
        #         f.write(newContent)
        #     dkj

if __name__ == '__main__':
    bdc = ServiceCatalographer.ServiceCatalographer('https://www.biodiversitycatalogue.org/')
    services = bdc.getServices()
    for service in services:
        serviceId = service.self.split('/')[-1]
        if int(serviceId) != 31:
            print(serviceId)
            continue
        content = ServiceReporter.report(service)
        print(content)
        serviceId = service.self.split('/')[-1]
        publish(content, 'BioVeL', 'Service %s (%s) Evaluation' % (serviceId, service.name), getPageId('BioVeL', 'Automatic Service Summary'))
