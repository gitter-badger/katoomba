import json
import requests
from requests.auth import HTTPBasicAuth

import ServiceCatalographer, PublicServiceReporter
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
    pageNameMap = {
        # Any services that are not in BiodiversityCatalogue can be placed here.
        # 'Service Name': 'Wiki Page Title'
        'Rserve': 'Rserve service',
        'WebDAV': 'WebDav_FileSharingService'
    }
    parentId = getPageId('doc', 'BioVeL Services')
    bdc = ServiceCatalographer.ServiceCatalographer('https://www.biodiversitycatalogue.org/')
    services = bdc.getServices()
    for service in services:
        serviceId = service.self.split('/')[-1]
        try:
            content = PublicServiceReporter.report(service)
        except PublicServiceReporter.DoNotInclude:
            pass
        else:
            print(content)
            pageName = 'BioVeL Service - %s' % service.name
            publish(content, 'doc', pageName, parentId)
            pageNameMap[service.name] = pageName
    content = '<ac:layout>'
    content += '<ac:layout-section ac:type="two_equal">\n'
    sortedKeys = sorted(pageNameMap, key=str.lower)
    split = (len(pageNameMap) + 1) // 2
    for subKeys in (sortedKeys[:split], sortedKeys[split:]):
        content += '<ac:layout-cell>'
        for serviceName in subKeys:
            content += '''
<ac:structured-macro ac:name="panel">
  <ac:parameter ac:name="bgColor">#f3ffac</ac:parameter>
  <ac:parameter ac:name="borderWidth">2</ac:parameter>
  <ac:parameter ac:name="borderStyle">solid</ac:parameter>
  <ac:parameter ac:name="borderColor">#cccc66</ac:parameter>
  <ac:rich-text-body>
    <p><b>
      <ac:link>
        <ri:page ri:content-title="%s" />
          <ac:plain-text-link-body><![CDATA[%s]]></ac:plain-text-link-body>
      </ac:link>
    </b></p>
  </ac:rich-text-body>
</ac:structured-macro>''' % (pageNameMap[serviceName], serviceName)
        content += '</ac:layout-cell>\n'
    content += '</ac:layout-section>\n'
    content += '''<ac:layout-section ac:type="single">
    <ac:layout-cell>
    <p>To find additional services, search in <ac:structured-macro ac:name="biodivcat"></ac:structured-macro>.</p>
    </ac:layout-cell>
    </ac:layout-section>
'''
    content += '</ac:layout>\n'

    publish(content, 'doc', 'BioVeL Services', getPageId('doc', 'Start'))
