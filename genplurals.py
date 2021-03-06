#!/usr/bin/env python3

# Adapted from Aaron Bockover's Vernacular: https://github.com/rdio/vernacular/

"""
Copyright 2012 Rdio, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import urllib.request
from html.parser import HTMLParser
from html.entities import name2codepoint
import re

url = 'http://translate.sourceforge.net/wiki/l10n/pluralforms'
html = urllib.request.urlopen(url).read().decode('utf-8')

class Parser(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)

    self.data = ''
    self.current_node = []
    self.in_td = False
    self.below_td = 0

    self.rules = {}

  def handle_current_node(self):
    code, name, rule = self.current_node
    m = re.match(r'^ *nplurals *=*(\d+); *plural *=(.*);', rule)
    if not m:
      return

    nplurals = int(m.group(1))
    rule = m.group(2).replace(';', '').strip()

    rule = re.sub(r'^\(?n *([\<\>\!\=]{1,2}) *(\d+)\)?$', r'n\1\2 ? 1 : 0', rule)
    rule = rule.replace('and', '&&')
    rule = rule.replace('or', '||')

    if '?' not in rule and rule != '0':
      rule += ' ? 1 : 0'

    if rule == 'n!=1 ? 1 : 0':
        return

    if rule in self.rules:
      self.rules[rule].append((code, name, nplurals))
    else:
      self.rules[rule] = [(code, name, nplurals)]

  def handle_starttag(self, tag, attrs):
    if self.in_td:
      self.below_td += 1
      return
    self.in_td = tag == 'td'

  def handle_endtag(self, tag):
    if self.below_td:
      self.below_td -= 1
      return
    if not self.in_td or tag != 'td':
      return

    self.in_td = False
    self.data = self.data.strip()

    field = len(self.current_node)

    if (field == 0 and re.match(r'^[a-zA-Z_]{2,5}$', self.data)) or field in [1, 2]:
      self.current_node.append(self.data)
      if field == 2:
        self.handle_current_node()
        self.current_node = []
    else:
      self.current_node = []

    self.data = ''

  def handle_data(self, data):
    if self.in_td and self.below_td == 0:
      self.data += data

  def handle_entityref(self, name):
    if self.in_td:
      self.data += chr(name2codepoint[name])

parser = Parser()
parser.feed(html)

rules = [rule for rule in parser.rules.items()]
rules.sort(key = lambda rule: (str(rule[1][0][2]) + rule[0]))

print('// Do not edit this file, it is autogenerated using genplurals.py!');
print('angular.module("gettext").factory("gettextPlurals", function () {');
print('    return function (langCode, n) {')
print('        if (langCode.indexOf("_") !== -1) {');
print('            langCode = langCode.split("_")[0];');
print('        };')
print('        switch (langCode) {')
for rule, langs in rules:
  last_forms = 0
  langs.sort(key = lambda lang: lang[0])
  for code, name, forms in langs:
    last_forms = forms
    space = '  '
    if len(code) == 3:
      space = ' '
    print('            case "%s":%s// %s' % (code, space, name))
  if last_forms == 1:
    print('                // %d form' % last_forms)
  else:
    print('                // %d forms' % last_forms)
  print('                return %s;' % rule)
print('            default: // Everything else')
print('                return n != 1 ? 1 : 0;')
print('        }')
print('    }')
print('});')
