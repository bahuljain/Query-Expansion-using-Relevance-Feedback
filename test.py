# -*- coding: utf-8 -*-
#
import re
from goose import Goose

url = 'http://en.wikipedia.org/wiki/Bill_Gates'
g= Goose()
article = g.extract(url=url)
#print article.title
#print article.meta_description
x = ''.join(article.cleaned_text[:])


x = x.encode('ascii','ignore').decode('ascii')
pagewords = re.split(' |, |\. |; |: |:|\(|\) |\? |\n', x)
y = ' '.join(pagewords)
print y

