# $Id: Makefile,v 1.1 2006/10/31 19:57:18 a1s Exp $

# History (most recent first):
# 10-jul-2006 [als]     rst2html arguments changed for docutils-0.4
#                       (embed-stylesheet is now default,
#                       'default.css' is not default stylesheet-path)
# 10-jul-2006 [als]     use rst2html from python2.4
# 14-jun-2006 [als]     rtl.txt again renamed to prt.txt, added prp.txt;
#                       embed HTML stylesheets
# 13-jun-2006 [als]     xtr.txt renamed to rtl.txt
# 12-jun-2006 [als]     created
#

STXTOHTML = python E:\\Python24\\Scripts\\rst2html.py \
    --stylesheet-path=default.css

SOURCE = prt.txt prp.txt

HTMLS = $(SOURCE:.txt=.html)

all: ${HTMLS}

%.html: %.txt default.css
	${STXTOHTML} --report=warning -d $< $@

clean:
	rm -f ${HTMLS}
