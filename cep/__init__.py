#- coding: utf-8
from bs4 import BeautifulSoup
try:
    from HTMLParser import HTMLParser
except:
    from html.parser import HTMLParser

try:
    from http.cookiejar import LWPCookieJar
except ImportError:
    from cookielib import LWPCookieJar

import re
import urllib

try:
    from urllib import request as urlrequest
except:
    import urllib2 as urlrequest

try:
    urlencode = urllib.urlencode
except:
    urlencode = urllib.parse.urlencode

URL_CORREIOS = 'http://www.buscacep.correios.com.br/sistemas/buscacep/'

class Correios():
    def __init__(self, proxy=None):
        cj = LWPCookieJar()
        cookie_handler = urlrequest.HTTPCookieProcessor(cj)
        if proxy:
            proxy_handler = urlrequest.ProxyHandler({'http': proxy})
            opener = urlrequest.build_opener(proxy_handler, cookie_handler)

        else:
            opener = urlrequest.build_opener(cookie_handler)
        urlrequest.install_opener(opener)



    def _url_open(self, url, data=None, headers=None):
        if headers == None:
            headers = {}

        headers['User-agent'] = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
        encoded_data = urlencode(data).encode("iso-8859-1") if data else None
        url = URL_CORREIOS + url

        req = urlrequest.Request(url, encoded_data, headers)
        handle = urlrequest.urlopen(req)

        return handle

    def _parse_detalhe(self, html):
        soup = BeautifulSoup(html.decode('ISO-8859-1'),"lxml")

        value_cells = soup.findAll('td', attrs={'class': 'value'})
        values = [htmlparser.unescape(cell.text.lower()).upper() for cell in value_cells]
        localidade, uf = values[2].split('/')
        values_dict = {
            'Logradouro': values[0].strip(),
            'Bairro': values[1].strip(),
            'Localidade': localidade.strip(),
            'UF': uf,
            'CEP': values[3]
        }
        return values_dict

    def _parse_linha_tabela(self, tr):
        htmlparser = HTMLParser()
        values = [htmlparser.unescape(cell.text.lower().strip()).upper() for cell in tr.findAll('td')]
        keys = ['Logradouro', 'Bairro', 'Localidade', 'CEP']
        correios_data = dict(zip(keys, values))
        for stripf in ['Logradouro', 'Bairro', 'Localidade', 'CEP']:
            if stripf in correios_data:
                correios_data[stripf] = correios_data[stripf].strip()
        if 'Localidade' in correios_data:
            localidade,uf = correios_data['Localidade'].split('/')
            correios_data['UF'] = uf
            correios_data['Localidade'] = localidade
        return correios_data

    def _parse_tabela(self, html):
        soup = BeautifulSoup(html,"lxml")
        linhas = soup.findAll('tr')
        return list(filter(lambda x:x,[self._parse_linha_tabela(linha) for linha in linhas]))

    def _parse_faixa(self, html):
        if u"não está cadastrada" in html.decode('cp1252'):
            return None
        ceps = re.findall('\d{5}-\d{3}', html)
        if len(ceps) == 4 or len(ceps) == 6: #uf (+ uf) + cidade com range
            return tuple(ceps[-2:])
        elif len(ceps) == 3 or len(ceps) == 5: #uf (+ uf) + cidade com cep único
            return ceps[-1]
        else:
            raise ValueError("HTML recebido não é válido")

    def detalhe(self, posicao=0):
        """Retorna o detalhe de um CEP da última lista de resultados"""
        handle = self._url_open('detalheCEPAction.do', {'Metodo': 'detalhe',
                                                        'TipoCep': 2,
                                                        'Posicao': posicao + 1,
                                                        'CEP': ''})
        html = handle.read()
        return self._parse_detalhe(html)

    def consulta_faixa(self, localidade, uf):
        """Consulta site e retorna faixa para localidade"""
        url = 'consultaFaixaCepAction.do'
        data = {
            'UF': uf,
            'Localidade': localidade.encode('cp1252'),
            'cfm': '1',
            'Metodo': 'listaFaixaCEP',
            'TipoConsulta': 'faixaCep',
            'StartRow': '1',
            'EndRow': '10',
        }
        html = self._url_open(url, data).read()
        return self._parse_faixa(html)

    def consulta(self, endereco, primeiro=False,
                 uf=None, localidade=None, tipo=None, numero=None):
        """Consulta site e retorna lista de resultados"""

        if uf is None:
            url = 'resultadoBuscaCepEndereco.cfm'
            data = {
                'relaxation': endereco.encode('ISO-8859-1'),
                'TipoCep': 'ALL',
                'semelhante': 'N',
                'cfm': 1,
                'Metodo': 'listaLogradouro',
                'TipoConsulta': 'relaxation',
                'StartRow': '1',
                'EndRow': '10'
            }
        else:
            url = 'consultaLogradouroAction.do'
            data = {
                'Logradouro': endereco.encode('ISO-8859-1'),
                'UF': uf,
                'TIPO': tipo,
                'Localidade': localidade.encode('ISO-8859-1'),
                'Numero': numero,
                'cfm': 1,
                'Metodo': 'listaLogradouro',
                'TipoConsulta': 'logradouro',
                'StartRow': '1',
                'EndRow': '10'
            }

        h = self._url_open(url, data)
        html = h.read()

        if primeiro:
            return self.detalhe()
        else:
            return self._parse_tabela(html)
