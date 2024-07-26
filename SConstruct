import os.path
import tomllib

from docutils.core import publish_cmdline
import enscons

meta = tomllib.load(open("pyproject.toml", "rb"))

def get_version():
    """Return package version string"""
    # don't use import to avoid fiddling with sys.path
    # and leaving behind compiled module file
    _vars = {}
    with open("PythonReports/version.py") as _script:
        exec(_script.read(), _vars)
    return _vars["__version__"]

def rst2html(target, source, env):
    """Generate HTML document from RST source"""
    src = str(source[0])
    tgt = str(target[0])
    print("Generating %s => %s" % (src, tgt))
    publish_cmdline(writer_name='html', argv=[
        "--stylesheet-path=doc/default.css", src, tgt])

meta["project"]["version"] = get_version()

env = Environment(
    tools=["default", "packaging", enscons.generate],
    PACKAGE_METADATA=meta["project"],
    WHEEL_TAG="py3-none-any",
    BUILDERS={
        "Rst": Builder(action=rst2html, suffix=".html"),
    },
)

py_sources = env.Glob("PythonReports/*.py")

doc_sources = ["README", "CHANGES", "doc/prt.txt", "doc/prp.txt"]
doc_html = [
    "doc/README.html",
    "doc/CHANGES.html",
    "doc/prt.html",
    "doc/prp.html",
]

doc = env.Alias("doc", [env.Rst(source=item[0], target=item[1])
    for item in zip(doc_sources, doc_html)])

package_sources = env.FindSourceFiles("PythonReports")

purelib = env.Whl("purelib", py_sources)
whl = env.WhlFile(purelib)
sdist = env.Alias("sdist", [
    doc,
    env.SDist(source=package_sources + doc_sources + doc_html + [
        "PKG-INFO",
        "LICENSE",
        "pyproject.toml",
        "SConstruct",
        "scripts/prd",
        "scripts/prd.bat",
    ]),
])

# Sets the default target when scons is run on the command line with no target
env.Default(whl, sdist)

# vim: set et ft=python sts=4 sw=4 :
