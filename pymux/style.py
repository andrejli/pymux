"""
The color scheme.
"""
from __future__ import unicode_literals
from prompt_toolkit.styles import Style

__all__ = (
    'ui_style',
)


ui_style = Style.from_dict({
    'line':                         '#888888',
    'line focussed':                '#448844',

    'titlebar':                     'bg:#888888 #dddddd ',
    'titlebar.title':               '',
    'titlebar.name':                '#ffffff noitalic',
    'titlebar.name.focussed':       'bg:#88aa44',
    'titlebar.line':                '#444444',
    'titlebar.line focussed':       '#448844 noinherit',
    'titlebar focussed':            'bg:#5f875f #ffffff bold',
    'titlebar.title focussed':      '',
    'titlebar.zoom':                'bg:#884400 #ffffff',
    'titlebar.paneindex':           '',
    'titlebar.copymode':            'bg:#88aa88 #444444',
    'titlebar.copymode.position':   '',

    'titlebar.paneindex focussed':         'bg:#88aa44 #ffffff',
    'titlebar.copymode focussed':          'bg:#aaff44 #000000',
    'titlebar.copymode.position focussed': '#888888',

    'commandline':                  'bg:#4e4e4e #ffffff',
    'commandline.command':          'bold',
    'commandline.prompt':           'bold',
    'statusbar':                    'noreverse bg:ansigreen #000000',
    'statusbar window':             '',
    'statusbar current-window':     'reverse underline',
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
})
