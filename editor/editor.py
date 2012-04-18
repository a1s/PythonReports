"""Editor launcher"""
"""
20-mar-2012 [kacah]   created

"""
from application import EditorApplication
from mainform import EditorForm
import utils

def main():
    _app = EditorApplication()
    _app.MainLoop()


if __name__ == "__main__":
    main()
