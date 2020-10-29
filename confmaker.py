#!/usr/bin/python3

import re
import xml.dom.minidom
from string import punctuation
from iso639 import languages
import unicodedata
import configparser
from collections import OrderedDict
import logging
import datetime

import argparse
from jinja2 import Template


class ConfigParserMultiValues(OrderedDict):

    def __setitem__(self, key, value):
        if key in self and isinstance(value, list):
            self[key].extend(value)
        else:
            super().__setitem__(key, value)

    @staticmethod
    def getlist(value):
        return value.split(os.linesep)

def find_language(lang):

  found = False
  #print(lang)
  try:
    lang_639 = languages.get(part1 = lang)
    found = True
  except:
    pass

  if not found:
    try:
      lang_639 = languages.get(part2b = lang)
      found = True
    except:
      pass

  if not found:
    try:
      lang_639 = languages.get(part2t = lang)
      found = True
    except:
      pass

  if not found:
    try:
      lang_639 = languages.get(part3 = lang)
      found = True
    except:
      pass

  if not found:
    try:
      lang_639 = languages.get(part5 = lang)
      found = True
    except:
      pass
  return (lang_639, found)

description = '''
confmaker.py - provides a initial conf file for a new module by analysing  given OSIS xml file. 
The programme searches for relevant tags and creates the GlobalOptionFilter entries and other relevant conf entries
'''

parser = argparse.ArgumentParser(description=description, epilog='', formatter_class=argparse.RawTextHelpFormatter)
#requiredNamed = parser.add_argument_group('required arguments')
#requiredNamed.add_argument('--required-param', '-p', nargs='?' ,help='', required=True)
parser.add_argument(
  '--output', '-o', 
  nargs='?',
  help='output file name [STDOUT]', 
  default=None
)
parser.add_argument(
  '--input', '-i', 
  nargs='?',
  help='input config file', 
  default=None
)
parser.add_argument(
  '--language', '-l', 
  nargs='?',
  help='language code',
  default=None
)
parser.add_argument(
    '--versification', '-v', 
    nargs='?',
    help='versification', 
    default=None
)
parser.add_argument(
    '--makefile', '-m', 
    action='store_const', default=False, const=True,
    help='if the -m option is used no -i option may be used. -m expects parametres added by other means, e.g. a makefile'
)
parser.add_argument(
    '-d', '--debug',
    help='enable debug logs',
    action='store_const', dest='loglevel', 
    const=logging.DEBUG,
    default=logging.ERROR
)
parser.add_argument(
    '-n', '--verbose',
    help='enable verbose logging',
    action='store_const', 
    dest='loglevel', 
    const=logging.INFO
)

parser.add_argument('osis', help='OSIS XML file')

args = parser.parse_args()

logging.basicConfig(level=args.loglevel)

version = {
 'KJV':  '1.5.9',
 'KJVA':  '1.6.0',
 'NRSV':  '1.6.0',
 'NRSVA':  '1.6.0',
 'MT':  '1.6.0',
 'Leningrad':  '1.6.0',
 'Synodal':  '1.6.1',
 'Vulg':  '1.6.1',
 'Luther':  '1.6.1',
 'German':  '1.6.1',
 'Catholic':  '1.6.2',
 'Catholic2':  '1.6.2',
 'LXX':  '1.7.2',
 'Orthodox':  '1.7.2',
 'SynodalProt':  '1.7.2',
 'DarbyFr':  '1.8.0',
 'Segond':  '1.8.0',
 'Calvin':  '1.8.0'
}

av11n = version.keys()
default_versification = 'KJV'

with open(args.osis, 'r') as reader:
  xmltext = reader.read()

doc = xml.dom.minidom.parse(args.osis)

manager = {
  'Hebrew Vowel Points': 'Off',
  'Hebrew Cantillation': 'Off',
  'Arabic Vowel Points': 'Off',
  'Greek Accents': 'Off'
}

document_configuration = {
  'name': doc.getElementsByTagName('osisText')[0].getAttribute('osisIDWork'),
  'lang_text': doc.getElementsByTagName('osisText')[0].getAttribute('xml:lang'),
  'type': doc.getElementsByTagName('osisText')[0].getAttribute('osisRefWork'),
  'features': [],
  'GlobalOptionFilters': [],
  'makefile': args.makefile
}

(document_configuration['lang'], lang_found) = find_language(document_configuration['lang_text'])


if not args.language and not lang_found:
  logging.error('The language is undefined and no language was given on the commandline !')
  exit(1)

if args.language and lang_found and document_configuration['lang'].part1 != args.language:
  logging.error('The language ({}) given on the commandline and the language of the document ({}) appear not to agree with each other !'.format(args.language, document_configuration['lang'].part1))
  exit(1)


try:
#get versification from XML
  document_configuration['versification'] = doc.getElementsByTagName('refSystem')[0].firstChild.data.replace('Bible.', '')
except:
  if args.versification:
    document_configuration['versification'] = args.versification
  else:
    document_configuration['versification'] = default_versification

if args.versification and document_configuration['versification'] != args.versification: 
  logging.error('The versification ({}) given on the commandline and the versification of the document ({}) appear not to agree with each other !'.format(args.versification, document_configuration['versification']))
  exit(1)

if document_configuration['versification'] not in version.keys():
  logging.error('This versification does not exist (yet): {}'.format(document_configuration['versification']))
  logging.info('Valid versification systems are {}'.format(', '.join(av11n)))
  exit(1)

#remove <header> tag and child nodes as its presence can cause confusion
for header in doc.getElementsByTagName('header'):
  parent = header.parentNode
  parent.removeChild(header)

document_features = ['title', 'note', 'reference', 'q', 'figure', 'rdg', 'seg']

word_features = ['lemma', 'strong', 'gloss', 'morph']

char_features = ['Hebrew Vowel Points', 'Arabic Vowel Points', 'Hebrew Cantillation', 'Greek Accents']

filters = {
  'title': 'OSISHeadings',
  'note': 'OSISFootnotes',
  'reference': 'OSISScripref',
  'gloss': 'OSISGlosses',
  'lemma': 'OSISLemma',
  'strong': 'OSISStrongs',
  'morph': 'OSISMorph',
  'q': 'OSISRedLetterWords',
  'rdg': 'OSISVariants',
  'enum': 'OSISEnum',
  'xlit': 'OSISXlit',
  'seg': 'OSISMorphSegmentation'
}

features_map = {
  'strong': 'StrongsNumbers',
  'figure': 'Images',
  'p': 'NoParagraphs'
}

diacritics = { 
  'Hebrew Vowel Points': 'UTF8HebrewPoints',
  'Arabic Vowel Points': 'UTF8ArabicPoints',
  'Hebrew Cantillation': 'UTF8Cantillation',
  'Greek Accents': 'UTF8GreekAccents'
}

#doc_has_feature => doc_features

document_configuration['features'] = list(
  filter(lambda document_feature: len(doc.getElementsByTagName(document_feature)) > 0, document_features)
)

w_elements = doc.getElementsByTagName('w')

for word_feature in word_features:
  for w in w_elements:
    if w.hasAttribute(word_feature):
      document_configuration['features'].append(word_feature)
      break


if 'lemma' in document_configuration['features']:
  for w in w_elements:
    if 'strong' in w.getAttribute('lemma').lower():
      document_configuration['features'].append('strong')

if len(doc.getElementsByTagName('p')) > 0:
  document_configuration['features'].append('p')    

ModDrvs = {
  'Bible': 'zText',
  'Commentary': 'zCom'  
}

DataPaths = {
  'Bible': './modules/texts/ztext/',
  'Commentary': './modules/comments/zcom/'
}

document_configuration['ModDrv'] = ModDrvs.get(document_configuration['type'], '')
document_configuration['DataPath'] = '{}{}'.format(DataPaths.get(document_configuration['type'], ''), document_configuration['name'].lower())
document_configuration['SwordVersionDate'] = datetime.date.today()
document_configuration['MinimumVersion'] = version[document_configuration['versification']]


for feature in document_features + word_features:
  if feature in document_configuration['features']:
    document_configuration['GlobalOptionFilters'].append(filters[feature])

for document_feature in document_features:
  if document_feature in document_configuration['features'] and document_feature in features_map:
    document_configuration['raw_features'] = document_configuration.get('raw_features', []).append(features_map[document_feature])


for word_feature in word_features:
  if word_feature in document_configuration['features'] and word_feature in features_map:
    document_configuration['raw_features'] = document_configuration.get('raw_features', []).append(features_map[word_feature])

if 'p' in document_configuration['features']:
  document_configuration['raw_features'] = document_configuration.get('raw_features', []).append(features_map['p'])

# Assemble and print out
configuration_template = """[{{ name }}]
ModDrv={{ ModDrv }}
DataPath={{ DataPath }}
CompressType=ZIP
BlockType=BOOK
Encoding=UTF-8
SourceType=OSIS
SwordVersionDate={{ SwordVersionDate }}
Lang={{ lang.part1 }}
{% for GlobalOptionFilter in GlobalOptionFilters -%}
GlobalOptionFilter={{ GlobalOptionFilter }}
{%- endfor %}{% for raw_feature in raw_features -%}
Feature=raw_feature
{%- endfor %}
LCSH={{ type }}. {{ lang.name }}.
Versification={{ versification }}
{% if not makefile -%}
DistributionLicense=copyrighted. Do not distribute
Description={{ name }} Bible in {{ lang.name }}
About={{ name }} Bible in {{ lang.name }}
Version=1.0
History_1.0=First release
MinimumVersion={{ MinimumVersion }}
{%- endif %}
"""

configuration = Template(configuration_template).render(document_configuration)

if not args.output:
  print(configuration)
else:
  with open(args.output, "w") as configuration_file:
    print(f"{configuration}", file=configuration_file)