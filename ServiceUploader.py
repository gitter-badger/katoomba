import Confluence, ServiceCatalographer, ServiceReporter
from config import confluenceHost, confluenceUser, confluencePass, serviceCatalographerURL

# The Wiki space and top-level page to index each service
# This page will not be modified, but new child pages may be added
confluenceSpaceKey = 'BioVeL'
confluenceParentTitle = 'Automatic Service Summary'

def upload():
    confluence = Confluence.Server(confluenceHost, confluenceUser, confluencePass)
    bdc = ServiceCatalographer.ServiceCatalographer(serviceCatalographerURL)
    services = bdc.getServices()
    for service in services:
        serviceId = service.self.split('/')[-1]
        content = ServiceReporter.report(service)
        print(content)
        confluence.publish(content, confluenceSpaceKey, 'Service %s (%s) Evaluation' % (serviceId, service.name), confluence.getPageId(confluenceSpaceKey, confluenceParentTitle))

if __name__ == '__main__':
    upload()
