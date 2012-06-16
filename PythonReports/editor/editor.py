"""Editor launcher"""
"""
26-may-2012 [als]   move to PythonReports subpackage
20-mar-2012 [kacah] created
"""

from PythonReports.editor.application import EditorApplication

def main():
    _app = EditorApplication(False)
    _app.MainLoop()


if __name__ == "__main__":
    main()
