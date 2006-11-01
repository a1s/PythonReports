"""PythonReports setup script"""

"""History:
03-oct-2006 [als]   created
"""

__version__ = "$Revision: 1.1 $"[11:-2]
__date__ = "$Date: 2006/11/01 11:28:32 $"[7:-2]

from distutils.core import setup

setup(name="PythonReports",
    version="0.0.1",
    description="Database report generator",
    author="alexander smishlajev",
    author_email="alex@tycobka.lv",
    packages=["PythonReports"],
)

# vim: set et sts=4 sw=4 :
