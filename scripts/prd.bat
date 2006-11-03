rem = """ PythonReports Designer command-line interface
python %0 %1 %2 %3 %4 %5 %6 %7 %8 %9
goto exit
rem = """

from PythonReports import design
design.run()

rem = """
:exit
rem = """
