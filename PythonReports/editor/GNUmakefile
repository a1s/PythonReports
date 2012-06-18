PYTHON ?= python
DISTNAME = PythonReports-Editor

dist: distclean
	PYTHONPATH=../.. $(PYTHON) setup.py py2exe -d $(DISTNAME)
	cp -r res $(DISTNAME)/
	zip -9rX $(DISTNAME).zip $(DISTNAME)

distclean: clean
	rm -rf $(DISTNAME).zip

clean:
	rm -rf build $(DISTNAME)
	rm -rf *.py[co]
	rm -f tests/save1.prt
	rm -f tests/save2.prt
	