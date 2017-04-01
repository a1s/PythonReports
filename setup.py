"""PythonReports setup script"""

# FIXME! generate_docs() must be reimplemented as a distutils command

from distutils.core import setup
import glob
import os

try:
    from docutils.core import publish_cmdline
except ImportError:
    publish_cmdline = None

if os.name == "nt":
    DOC_DIR = "Lib\\site-packages\\PythonReports\\doc"
    SCRIPTS=["scripts/prd", "scripts/prd.bat",
        "scripts/prtedit", "scripts/prtedit.bat"]
else:
    DOC_DIR = "share/PythonReports/doc"
    SCRIPTS=["scripts/prd", "scripts/prtedit"]

DESCRIPTION = """\
PythonReports is a toolkit aimed to build database reports
in Python programs.  The toolkit includes report template
designer, report builder and several printout renderers
for GUI and graphic file output.

Report builder applies a template to a sequence of uniform
data objects and produces a printout structure that can be
saved to file and/or rendered by one of the front-end drivers
to screen, printer, PDF etc.

"""

def get_version():
    """Return package version string"""
    # don't use import to avoid fiddling with sys.path
    # and leaving behind compiled module file
    _vars = {}
    exec file("PythonReports/version.py") in _vars
    return _vars["__version__"]

def rst2html(source, target, force=False):
    """Generate HTML document from RST source

    Parameters:
        source: source (rst) file name
        target: target (html) file name
        force: if set, generate html even if
            source file is not newer than target

    """
    if not force:
        force = (not os.path.isfile(target)) \
            or (os.stat(source).st_mtime > os.stat(target).st_mtime)
    if force:
        print "Generating %s => %s" % (source, target)
        publish_cmdline(writer_name='html', argv=[
            "--stylesheet-path=doc/default.css", source, target])

def generate_docs():
    """Generate HTML documentation from RST sources"""
    # make sure docutils are loaded
    if not publish_cmdline:
        return
    # use floating timestamps
    os.stat_float_times(True)
    for (_source, _target) in (
        ("doc/prt.txt", "doc/prt.html"),
        ("doc/prp.txt", "doc/prp.html"),
        ("README", "doc/README.html"),
        ("CHANGES", "doc/CHANGES.html"),
    ):
        rst2html(_source, _target)

def run():
    if publish_cmdline:
        # docutitls available - generate htmls
        generate_docs()
    setup(name="PythonReports",
        version=get_version(),
        url="http://pythonreports.sourceforge.net/",
        download_url="https://pypi.python.org/pypi/PythonReports",
        description="Database report generator",
        long_description=DESCRIPTION,
        author="Aleksandr Smyshliaev",
        author_email="alex@gorka.lv",
        maintainer="PythonReports Users Mailing List",
        maintainer_email="pythonreports-users@lists.sourceforge.net",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Environment :: Win32 (MS Windows)",
            "Environment :: X11 Applications",
            "Intended Audience :: Developers",
            "Intended Audience :: Information Technology",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Topic :: Database :: Front-Ends",
            "Topic :: Printing",
        ],
        # cheeseshop says "you should enter a full description here
        # only if appropriate classifiers aren't available", but
        # if license and platforms settings are not present,
        # they are filled with word "UNKNOWN" in PKG-INFO and PyPI
        # registration.
        license="MIT License",
        platforms=["OS Independent"],
        packages=["PythonReports",
            "PythonReports.editor", "PythonReports.editor.elements"],
        package_data={"PythonReports.editor": ["res/*"]},
        scripts=SCRIPTS,
        data_files=[(DOC_DIR, ["README", "LICENSE", "CHANGES"]
            + glob.glob("doc/*.txt") + glob.glob("doc/*.html"))],
    )

if __name__ == "__main__":
    run()

# vim: set et sts=4 sw=4 :
