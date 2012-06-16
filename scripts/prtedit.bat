rem = """ PythonReports Template Editor launcher
python %0 %1 %2 %3 %4 %5 %6 %7 %8 %9
goto :eof
rem = """

from PythonReports.editor import editor
editor.main()
