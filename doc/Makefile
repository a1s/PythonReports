STXTOHTML = python -m docutils --stylesheet-path=default.css

SOURCE = prt.txt prp.txt

HTMLS = $(SOURCE:.txt=.html)
ALL_HTMLS = $(HTMLS) README.html CHANGES.html

all: ${ALL_HTMLS}

build: ${ALL_HTMLS}

clean:
	-rm ${ALL_HTMLS} 2> /dev/null

%.html: ../% default.css
	${STXTOHTML} --report=warning $< $@

%.html: %.txt default.css
	${STXTOHTML} --report=warning $< $@
