import html, re
import requests

from ServiceCatalographer import ServiceCatalographer


def htmlText(text):
    return html.escape(text, quote=False).encode('ascii', 'xmlcharrefreplace').decode('ascii').replace('\n', '<br />')

def htmlAttr(value):
    return html.escape(str(value))

def alert(text):
    return '<span style="color: rgb(255,0,0);">%s</span>' % htmlText(text)


def check(text, err):
    if text is None:
        wrapped = alert(err)
    else:
        wrapped = htmlText(text)
    return wrapped


titleRE = re.compile('<title>([^<]+)</title>', re.IGNORECASE)


def massageLink(link):
    html = '<a href="%s"><code>%s</code></a>' % (htmlAttr(link), htmlText(link))
    action = None
    try:
        response = requests.get(link, verify = False)
    except requests.exceptions.ConnectionError:
        action = 'Check documentation link: %s' % html
        html += alert(' (Link did not respond)')
    except requests.exceptions.MissingSchema:
        action = 'Remove text from documentation links'
        html = '%s %s' % (htmlText(link), alert('(Not a valid link)'))
    else:
        status_code = response.status_code
        if status_code < 400:
            m = titleRE.search(response.text)
            if m:
                title = m.group(1).strip().replace('\n', ' ')
                if title:
                    html = '<a href="%s">%s</a>' % (htmlAttr(link), htmlText(title))
            if link.startswith('http://wiki.biovel.eu') or link.startswith('https://wiki.biovel.eu'):
                if link.startswith('http://wiki.biovel.eu/x/') or link.startswith('https://wiki.biovel.eu/x/'):
                    pass
                else:
                    html += alert(' (BioVeL Wiki long link)')
                    action = 'Change BioVeL Wiki long link to tiny link (using Wiki menu Tools -> Link to this page...)'
        else:
            action = 'Check documentation link: %s' % html
            html += alert(' (Link returned status %d)' % status_code)
    return html, action

def report(service):
    content = '<h1>%s</h1>\n' % htmlText(service.name)
    level = ([], [], [], [])
    other = []

    submitter = service.submitter.user
    user = submitter.name
    org = submitter.affiliation
    if org:
        user += ', ' + org
    email = submitter.public_email
    if email:
        user += ' (%s)' % email
    content += '<p><small>Submitted to <a href="%s">BiodiversityCatalogue</a> by %s</small></p>\n' % (htmlAttr(service.self), htmlText(user))

    # Getting the first summary attribute fetches the summary contents. Those
    # contents have 'service' and 'summary' objects to get to the real content.
    summary = service.summary.service.summary

    categories = summary.categories
    if categories:
        content += '<p>Categories: %s</p>\n' % ', '.join([htmlText(category.name) for category in categories])
    else:
        level[2].append('Add service to a category')

    descriptions = summary.descriptions
    if descriptions is None:
        level[1].append('Add service description')
    elif len(descriptions) == 1 and descriptions[0] == service.name:
        level[1].append('Improve service description')
    else:
        for description in descriptions:
            content += '<p>%s</p>\n' % htmlText(description.strip())

    documentation_urls = summary.documentation_urls
    if documentation_urls:
        for url in documentation_urls:
            link, action = massageLink(url)
            if action:
                other.append(action)
            content += '<p>Documentation: %s</p>\n' % link
    else:
        level[1].append('Add documentation link')

    licenses = summary.licenses
    if licenses:
        for license in licenses:
            content += '<p>License: %s</p>\n' % htmlText(license)
    else:
        level[2].append('Add license details')

    contacts = summary.contacts
    if contacts:
        for contact in contacts:
            content += '<p>Contact: %s</p>\n' % htmlText(contact)
    else:
        level[1].append('Add contact')

    class Variant:
        pass

    variants = {}
    for variant in service.variants:
        v = variants[str(variant.resource)] = Variant()
        name = variant.name
        if hasattr(variant.resource, 'soap_service'):
            name += ' (SOAP)'
        else:
            assert hasattr(variant.resource, 'rest_service'), variant.resource
            name += ' (REST)'
        v.description = '<a href="%s">%s</a>' % (htmlAttr(variant.resource), htmlText(name))
        v.deployments = []
    for deployment in service.deployments:
        provided_variant = deployment.resource.service_deployment.provided_variant
        variant = variants.get(str(provided_variant.resource))
        if variant is None:
            variant = variants[str(provided_variant.resource)] = Variant()
            variant.description = '<a href="%s">%s</a> %s' % (htmlAttr(provided_variant.resource), htmlText(provided_variant.description), alert('(Unknown variant)'))
            variant.deployments = []
        variant.deployments.append('<code>%s</code><br />(%s - %s)' % (
            check(deployment.endpoint, 'No endpoint'),
            check(deployment.provider.name, 'No provider name'),
            check(deployment.provider.description, 'No provider description')
            ))
    content += '<table><tr><th>Variant</th><th>Deployment</th></tr>\n'
    for variant in variants.values():
        rowspan = len(variant.deployments)
        if rowspan == 0:
            variant.deployments.append(alert('No deployments for this variant'))
            rowspan = 1
        if rowspan == 1:
            attr = ''
        else:
            attr = ' rowspan="%d"' % rowspan
        content += '<tr><td%s>%s</td>\n' % (attr, variant.description)
        text = ['<td>%s</td></tr>\n' % deployment for deployment in variant.deployments]
        content += '<tr>'.join(text)
    content += '</table>\n'

    for variant in service.variants:
        resource = variant.resource
        if hasattr(resource, 'soap_service'):
            interface = resource.soap_service
            name = '%s (SOAP)' % variant.name
            content += '<h2>%s</h2>\n' % htmlText(name)
            wsdl_location = interface.wsdl_location
            if wsdl_location is None:
                content += '<p>%s</p>' % alert('No WSDL document')
                level[2].append('Add link to WSDL document')
            else:
                content += '<p>WSDL: <a href="%s"><code>%s</code></a></p>\n' % (htmlAttr(interface.wsdl_location), htmlText(interface.wsdl_location))
            documentation_url = interface.documentation_url
            if documentation_url is not None:
                link, action = massageLink(documentation_url)
            else:
                link = alert('No documentation')
            content += '<p>Documentation: %s</p>\n' % link
            if not interface.operations:
                level[2].append('Add description of available operations for variant %s' % name)
            for operation in interface.operations:
                soap_operation = operation.resource.soap_operation
                content += '<h3>%s</h3>\n' % htmlText(soap_operation.name)
                descriptions = [soap_operation.description]
                annotations = soap_operation.annotations.annotations.results
                for annotation in annotations:
                    if annotation.attribute.identifier == 'http://biodiversitycatalogue.org/attribute/description':
                        descriptions.append(annotation.value.content)
                for description in descriptions:
                    content += '<p>%s</p>\n' % htmlText(description)

                inputs = soap_operation.inputs
                if inputs:
                    content += '<h4>Inputs</h4>\n'
                    for input in inputs:
                        content += '<p><b>%s</b> - %s</p>\n' % (htmlText(input.name), check(input.description, 'No description'))
                        if input.description is None:
                            level[3].append('Add description to operation "%s" input "%s"' % (htmlText(soap_operation.name), htmlText(input.name)))
                        annotations = input.resource.soap_input.annotations.annotations.results
                        for annotation in annotations:
                            if annotation.attribute.identifier == 'http://biodiversitycatalogue.org/attribute/exampledata':
                                example = annotation.value.content
                                content += '<p>Example:\n<code>%s</code></p>\n' % htmlText(example)
                outputs = soap_operation.outputs
                if outputs:
                    content += '<h4>Outputs</h4>\n'
                    for output in outputs:
                        content += '<p><b>%s</b> - %s</p>\n' % (htmlText(output.name), check(output.description, 'No description'))
                        if output.description is None:
                            level[3].append('Add description to operation "%s" output "%s"' % (htmlText(soap_operation.name), htmlText(output.name)))
                        annotations = output.resource.soap_output.annotations.annotations.results
                        for annotation in annotations:
                            if annotation.attribute.identifier == 'http://biodiversitycatalogue.org/attribute/exampledata':
                                example = annotation.value.content
                                content += '<p>Example:\n<code>%s</code></p>\n' % htmlText(example)
        else:
            interface = resource.rest_service
            name = '%s (REST)' % variant.name
            content += '<h2>%s</h2>\n' % htmlText(name)
            documentation_url = interface.documentation_url
            if documentation_url is not None:
                link, action = massageLink(documentation_url)
            else:
                link = alert('No documentation')
            content += '<p>Documentation: %s</p>\n' % link
            if not interface.resources:
                level[2].append('Add description of available operations for variant %s' % name)
            for operation in interface.resources:
                rest_operation = operation.resource.rest_resource.methods
                for method in rest_operation:
                    content += '<h3>%s</h3>\n' % htmlText(method.endpoint_label)
                    if method.description:
                        descriptions = [method.description]
                        for description in descriptions:
                            content += '<p>%s</p>\n' % htmlText(description)
                    else:
                        content += '<p>%s</p>' % alert('No description')
                        level[2].append('Add description to operation "%s"' % htmlText(method.endpoint_label))

                    inputs = method.resource.rest_method.inputs.parameters
                    if inputs:
                        content += '<h4>Inputs</h4>\n'
                        for input in inputs:
                            if input.description:
                                description = htmlText(input.description)
                            else:
                                description = alert('No description')
                                level[3].append('Add description to operation "%s" input "%s"' % (htmlText(method.endpoint_label), htmlText(input.name)))
                            content += '<p><b>%s</b> - %s</p>\n' % (htmlText(input.name), description)
                            annotations = input.resource.rest_parameter.annotations.annotations.results
                            for annotation in annotations:
                                if annotation.attribute.identifier == 'http://biodiversitycatalogue.org/attribute/exampledata':
                                    example = annotation.value.content
                                    content += '<p>Example:\n<code>%s</code></p>\n' % htmlText(example)
                    outputs = method.resource.rest_method.outputs.parameters
                    if outputs:
                        content += '<h4>Outputs</h4>\n'
                        for output in outputs:
                            if output.description:
                                description = htmlText(output.description)
                            else:
                                description = alert('No description')
                                level[3].append('Add description to operation "%s" output "%s"' % (htmlText(method.endpoint_label), htmlText(input.name)))
                            content += '<p><b>%s</b> - %s</p>\n' % (htmlText(output.name), description)
                            annotations = output.resource.rest_parameter.annotations.annotations.results
                            for annotation in annotations:
                                if annotation.attribute.identifier == 'http://biodiversitycatalogue.org/attribute/exampledata':
                                    example = annotation.value.content
                                    content += '<p>Example:\n<code>%s</code></p>\n' % htmlText(example)

    evaluation = ''
    if level[0]:
        evaluation += '<p>To allow further evaluation, please solve these problems:</p>'
        for item in level[0]:
            evaluation += '<p>- %s</p>\n' % item
    elif level[1]:
        evaluation += '<p><b>Provisional maturity level: 0</b></p>\n'
        evaluation += '<p>To obtain level 1, this service requires the following %d actions:</p>\n' % len(level[1])
        for item in level[1]:
            evaluation += '<p>- %s</p>\n' % item
    elif level[2]:
        evaluation += '<p><b>Provisional maturity level: 1</b> (subject to manual review)</p>\n'
        evaluation += '<p>To obtain level 2, this service requires the following %d actions:</p>\n' % len(level[2])
        for item in level[2]:
            evaluation += '<p>- %s</p>\n' % item
    elif level[3]:
        evaluation += '<p><b>Provisional maturity level: 2</b> (subject to manual review)</p>\n'
        evaluation += '<p>To obtain level 3, this service requires the following %d actions:</p>\n' % len(level[3])
        for item in level[3]:
            evaluation += '<p>- %s</p>\n' % item
    else:
        evaluation += '<p><b>Provisional maturity level: 3</b> (subject to manual review)</p>\n'
    if other:
        evaluation += '<p>Other issues, not affecting maturity level:</p>\n'
        for item in other:
            evaluation += '<p>- %s</p>\n' % item

    content = evaluation + content
    return content

if __name__ == '__main__':
    bdc = ServiceCatalographer('https://www.biodiversitycatalogue.org/')
    service = bdc.getServiceId(32)
    content = report(service)
    print(content)
    # print(repr(service.variants[0].resource.rest_service.resources[2].resource.rest_resource.methods[0].resource.rest_method.inputs.parameters[0].resource.rest_parameter.annotations))
