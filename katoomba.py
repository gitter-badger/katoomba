import config
from ServiceCatalographer import ServiceCatalographer
from ServiceReporter import report
from ServiceUploader import publish, getPageId

parentId = getPageId(config.confluenceSpaceKey, config.confluenceParentTitle)

catalog = ServiceCatalographer(config.serviceCatalographerUrl)

for service in catalog.getServices():
    content = report(service)
    serviceId = service.self.split('/')[-1]
    pageTitle = 'Service %s (%s) Evaluation' % (serviceId, service.name)
    publish(content, config.confluenceSpaceKey, pageTitle, parentId)
