import html, re
import requests

from ServiceCatalographer import ServiceCatalographer


def htmlText(text):
    return html.escape(text, quote=False).encode('ascii', 'xmlcharrefreplace').decode('ascii').replace('\n', '<br />')

def htmlAttr(value):
    return html.escape(str(value))

def alert(text):
    return '<span style="color: rgb(127,127,127);">%s</span>' % htmlText(text)


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
    except requests.exceptions.MissingSchema:
        action = 'Remove text from documentation links'
        html = htmlText(link)
    else:
        status_code = response.status_code
        if status_code < 400:
            m = titleRE.search(response.text)
            if m:
                title = m.group(1).strip().replace('\n', ' ')
                if title:
                    html = '<a href="%s">%s</a>' % (htmlAttr(link), htmlText(title))
    return html, action


class DoNotInclude(Exception):
    pass


def report(service):
    level = ([], [], [], [])
    other = []

    content = '<h2>Service name</h2>'
    content += '<a href="%s">%s</a>' % ((htmlAttr(service.self), htmlText(service.name)))
    content += '<h2>Created in BiodiversityCatalogue</h2>'
    content += '<p>%s</p>' % htmlText(service.created_at)

    # Getting the first summary attribute fetches the summary contents. Those
    # contents have 'service' and 'summary' objects to get to the real content.
    summary = service.summary.service.summary

    descriptions = summary.descriptions
    if service.description:
        descriptions.insert(0, service.description)
    if not descriptions:
        level[1].append('Add service description')
    else:
        assert descriptions and descriptions[0], descriptions
        if len(descriptions) > 1 and descriptions[0] == descriptions[1]:
            del descriptions[0]
        if len(descriptions) == 1 and descriptions[0] == service.name:
            level[1].append('Improve service description')
        content += '<h2>Description</h2>'
        for description in descriptions:
            # content += '<p>%s</p>\n' % htmlText(description.strip())
            import markdown
            html = markdown.markdown(description.strip(),
                extensions = ['extra'], output_format = 'xhtml1',
                safe_mode = 'escape'
                )
            assert html
            # Add each description into a panel to separate
            content += '''<ac:structured-macro ac:name="panel">
  <ac:parameter ac:name="bgColor">#ffffff</ac:parameter>
  <ac:parameter ac:name="borderWidth">2</ac:parameter>
  <ac:parameter ac:name="borderStyle">solid</ac:parameter>
  <ac:parameter ac:name="borderColor">#cccc66</ac:parameter>
  <ac:rich-text-body>'''
            content += html
            content += '''</ac:rich-text-body>
</ac:structured-macro>'''
    categories = [category.name for category in summary.categories]
    if 'BioVeL' in categories:
        categories.remove('BioVeL')
    else:
        raise DoNotInclude()
    if categories:
        content += '<h2>Categories</h2>'
        content += '<p>Categories: %s</p>\n' % ', '.join([htmlText(category) for category in categories])
    else:
        level[2].append('Add service to a category')

    documentation_urls = summary.documentation_urls
    if documentation_urls:
        content += '<h2>Documentation</h2>'
        for url in documentation_urls:
            link, action = massageLink(url)
            if action:
                other.append(action)
            content += '<p>%s</p>\n' % link
    else:
        level[1].append('Add documentation link')

    contacts = summary.contacts
    if contacts:
        content += '<h2>Contact</h2>'
        for contact in contacts:
            content += '<p>%s</p>\n' % htmlText(contact)
    else:
        level[1].append('Add contact')

    publications = summary.publications
    if publications:
        content += '<h2>Publications</h2>'
        for publication in publications:
            content += '<p>%s</p>\n' % htmlText(publication)

    citations = summary.citations
    if citations:
        content += '<h2>Citations</h2>'
        for citation in citations:
            content += '<p>%s</p>\n' % htmlText(citation)

    # licenses = summary.licenses
    # if licenses:
    #     for license in licenses:
    #         content += '<p>License: %s</p>\n' % htmlText(license)
    # else:
    #     level[2].append('Add license details')


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
        variant.deployments.append('<code>%s</code>' % (
            check(deployment.endpoint, 'No endpoint'),
        ))
    content += '<h2>Versions</h2>'
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
        # evaluation += '<p><b>Provisional maturity level: 3</b> (subject to manual review)</p>\n'
        pass
    if other:
        evaluation += '<p>Other issues, not affecting maturity level:</p>\n'
        for item in other:
            evaluation += '<p>- %s</p>\n' % item

    if evaluation:
        content += '<h2>Actions to improve the service description</h2>'
        content += evaluation

    return content

if __name__ == '__main__':
    bdc = ServiceCatalographer('https://www.biodiversitycatalogue.org/')
    service = bdc.getServiceId(32)
    content = report(service)
    print(content)
    # print(repr(service.variants[0].resource.rest_service.resources[2].resource.rest_resource.methods[0].resource.rest_method.inputs.parameters[0].resource.rest_parameter.annotations))
