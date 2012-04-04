"""Editor launcher"""
"""
20-mar-2012 [kacah]   created

"""
import wx

from mainform import EditorForm
import utils

def main():
    _app = wx.PySimpleApp()
    utils.setup()
    _main_form = EditorForm(None)
    _main_form.Show()
    _main_form.Maximize(True)
    _app.MainLoop()


if __name__ == "__main__":
    main()
