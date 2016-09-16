# -*- coding: utf-8 -*-

import urllib2
import xml.etree.ElementTree as ET



def do_post_request(url, data=None, headers=None):
    if data is not None:
        response = urllib2.urlopen(url, data)
    else:
        response = urllib2.urlopen(url)
    return response.read()


def do_jrodos_soap_call(param):
    url = 'http://geoserver.dev.cal-net.nl/calnet-measurements-ws/utilService'
    content = """<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                 xmlns:ws="http://service.ws.calnet.rivm.nl/">
                  <soap:Header/>
                  <soap:Body>
                    <ws:get%s />
                  </soap:Body>
                </soap:Envelope>""" % param

    response = do_post_request(url, content)
    root = ET.fromstring(response)
    # ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
    #     'ns2': 'http://service.ws.calnet.rivm.nl/'}

    result = []
    for ret in root.findall(".//return"):
        code = ret.find('code').text
        desc = ret.find('description').text
        #print code, description
        description = "%s (%s)" % (desc, code)
        result.append({'code':code, 'description':description})

    return result



# jrodos_quantities = do_jrodos_soap_call('Quantities')
# jrodos_substances = do_jrodos_soap_call('Substances')
# jrodos_units = do_jrodos_soap_call('Units')

#print type(jrodos_quantities[0])

# print len(jrodos_quantities)
# print jrodos_quantities
#
# print len(jrodos_substances)
# print jrodos_substances
#
# print len(jrodos_units)
# print jrodos_units

