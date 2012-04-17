"""Editor launcher"""
"""
20-mar-2012 [kacah]   created

"""
import wx

from mainform import EditorForm
import utils

def main():
    _app = wx.PySimpleApp()
    #disable logs to prevent automatic error windows
    wx.Log.EnableLogging(False)
    utils.setup()
    _main_form = EditorForm(None)
    _app.SetTopWindow(_main_form)
    _main_form.Show()
    _main_form.Maximize(True)
    _app.MainLoop()


if __name__ == "__main__":
    main()
