from distutils.core import setup
import py2exe

setup(
    console=["editor.py"],
    options={"py2exe": dict(
        dll_excludes=[
            "MPR.dll",
            "MSWSOCK.dll",
            "POWRPROF.dll",
            "Secur32.dll",
            "SHFOLDER.dll",
        ]
    )},
    zipfile="library.dat",
)
