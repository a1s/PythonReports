"""Editor launcher"""
"""
20-mar-2012 [kacah]   created

"""
import wx

from mainform import EditorForm

def main():
    _app = wx.PySimpleApp()
    _main_form = EditorForm(None)
    _main_form.Show()
    _app.MainLoop()


if __name__ == "__main__":
    main()
