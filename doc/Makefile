# $Id: Makefile,v 1.3 2006/11/03 16:11:58 a1s Exp $

# History (most recent first):
# 03-nov-2006 [als]     build htmls for toplevel documents too;
#                       don't include generation timestamp
# 01-nov-2006 [als]     added upload target
# 10-jul-2006 [als]     rst2html arguments changed for docutils-0.4
#                       (embed-stylesheet is now default,
#                       'default.css' is not default stylesheet-path)
# 10-jul-2006 [als]     use rst2html from python2.4
# 14-jun-2006 [als]     rtl.txt again renamed to prt.txt, added prp.txt;
#                       embed HTML stylesheets
# 13-jun-2006 [als]     xtr.txt renamed to rtl.txt
# 12-jun-2006 [als]     created
#

UPLOAD_PATH = a1s@shell.sourceforge.net:/home/groups/p/py/pythonreports/htdocs/
STXTOHTML = python E:\\Python24\\Scripts\\rst2html.py \
    --stylesheet-path=default.css

SOURCE = prt.txt prp.txt

HTMLS = $(SOURCE:.txt=.html)
ALL_HTMLS = $(HTMLS) README.html CHANGES.html

all: ${ALL_HTMLS}

build: ${ALL_HTMLS}

upload: ${HTMLS}
	scp $^ ${UPLOAD_PATH}

clean:
	-rm ${ALL_HTMLS} 2> /dev/null

%.html: ../% default.css
	${STXTOHTML} --report=warning $< $@

%.html: %.txt default.css
	${STXTOHTML} --report=warning $< $@
