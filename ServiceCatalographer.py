import sys, urllib.parse
import requests


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
        if len(result) != 1:
            raise RuntimeError('expected single top-level result')
        for key in result:
            # assign the last (and only) key value to the variable 'key'
            pass
        assert key == resultKey, key
        pageResults = result[key]
        totalPages = pageResults['pages']
        results.extend(pageResults['results'])
        page += 1
    return results


def convert(result, cache):

    if isinstance(result, dict):
        result = Resource(result, cache)
    elif isinstance(result, list):
        result = [convert(value, cache) for value in result]
    elif cache.isResource(result):
        result = CacheResource(result, cache)
    return result



class Resource:

    def __init__(self, result, cache):

        self._values = result
        self._cache = cache
        if 'self' in self._values:
            self._values['annotations'] = self._values['self'] + '/annotations'


    def __getitem__(self, name):

        result = self._values[name]
        if name != 'self':
            result = convert(result, self._cache)
        return result


    def __setitem__(self, name, value):

        self._values[name] = value


    def __getattr__(self, name):

        try:
            return self[name]
        except KeyError:
            sys.stderr.write('%r\n' % self)
            raise AttributeError(name)


    def __contains__(self, name):

        return name in self._values


    def __iter__(self):

        return iter(self._values)


    def __str__(self):

        return repr(self)


    def __repr__(self):

        return '\n'.join(['%s: %r' % (name, self._values[name]) for name in self])



# A resource that acts like a string if used as a string, but fetches data
# when attributes are requested
class CacheResource(Resource):

    def __init__(self, resource, cache):

        result = cache.getResource(resource)
        super().__init__(result, cache)
        self._resource = resource


    def __str__(self):

        return self._resource


class NotValidResource(Exception):

    pass



class ServiceCatalographer:

    def __init__(self, url):
        self.url = url
        self.cache = {}


    def getFullURL(self, urlStub):
        return urllib.parse.urljoin(self.url, urlStub)


    def isResource(self, resource):
        if isinstance(resource, str):
            return resource.startswith(self.url)
        return False


    def getResource(self, resource):

        result = self.cache.get(resource)
        if result is None:
            if self.isResource(resource):
                response = requests.get(resource, headers={'Accept': 'application/json'})
                response.raise_for_status()
                result = Resource(response.json(), self)
                self.cache[resource] = result
            else:
                raise NotValidResource(resource)
        return result


    def getServices(self):

        services = getAll(self.getFullURL('services'), 'services')
        return [self.getService(service['resource']) for service in services]


    def getService(self, url):

        service = self.getResource(url).service
        service['summary'] = service.self + '/summary'
        return service


    def getServiceId(self, serviceId):

        return self.getService(self.getFullURL('services/%d' % serviceId))



if __name__ == '__main__':

    bdc = ServiceCatalographer('https://www.biodiversitycatalogue.org/')
    resource = bdc.getFullURL('services/1')
    service = bdc.getServiceId(1)
    print(service)
