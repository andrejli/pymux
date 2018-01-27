"""
The color scheme.
"""
from __future__ import unicode_literals
from prompt_toolkit.styles import Style, Priority

__all__ = (
    'ui_style',
)


ui_style = Style.from_dict({  # TODO: dict doesn't work here: the order is random.
    'border':                         '#888888',
    'terminal.focussed border':                '#00ff00 bold',

    #'terminal titleba':            'bg:#aaaaaa #dddddd ',
    'terminal titlebar':            'bg:#448844',
    'terminal titlebar paneindex':  'bg:#888888 #000000',

    'terminal.focussed titlebar':   'bg:#00ff00 #000000',
    'terminal.focussed titlebar paneindex':         'bg:#ff0000',

#    'titlebar title':               '',
#    'titlebar name':                '#ffffff noitalic',
#    'focussed-terminal titlebar name':       'bg:#88aa44',
#    'titlebar.line':                '#444444',
#    'titlebar.line focussed':       '#448844 noinherit',
#    'titlebar focussed':            'bg:#5f875f #ffffff bold',
#    'titlebar.title focussed':      '',
#    'titlebar.zoom':                'bg:#884400 #ffffff',
#    'titlebar paneindex':           '',
#    'titlebar.copymode':            'bg:#88aa88 #444444',
#    'titlebar.copymode.position':   '',

#    'focussed-terminal titlebar.copymode':          'bg:#aaff44 #000000',
#    'titlebar.copymode.position': '#888888',

    'commandline':                  'bg:#4e4e4e #ffffff',
    'commandline.command':          'bold',
    'commandline.prompt':           'bold',
    'statusbar':                    'noreverse bg:ansigreen #000000',
    'statusbar window':             '',
    'statusbar current-window':     'bg:#008800 #000000',
    'auto-suggestion':               'bg:#4e5e4e #88aa88',
    'message':                      'bg:#bbee88 #222222',
    'background':                   '#888888',
    'clock':                        'bg:#88aa00',
    'panenumber':                   'bg:#888888',
    'panenumber focussed':          'bg:#aa8800',
    'terminated':                   'bg:#aa0000 #ffffff',

    'confirmationtoolbar':          'bg:#880000 #ffffff',
    'confirmationtoolbar question': '',
    'confirmationtoolbar yesno':    'bg:#440000',

    'search':                       'bg:#88aa88 #444444',
    'search.text':                  '',
    'search focussed':              'bg:#aaff44 #444444',
    'search.text focussed':         'bold #000000',

    'search-match':                  '#000000 bg:#88aa88',
    'search-match.current':          '#000000 bg:#aaffaa underline',
}, priority=Priority.MOST_PRECISE)
