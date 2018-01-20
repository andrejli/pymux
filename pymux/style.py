"""
The color scheme.
"""
from __future__ import unicode_literals

from prompt_toolkit.styles import Style, Attrs
from prompt_toolkit.styles.utils import split_token_in_parts, merge_attrs
from prompt_toolkit.token import Token

__all__ = (
    'PymuxStyle',
)


ui_style = {
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
    'statusbar':                    'reverse', #bg:#444444 #ffffff',
    'statusbar.window':             'bg:#888888',
    'statusbar.window.current':     '#88ff88 bold',
    'auto-suggestion':               'bg:#4e5e4e #88aa88',
    'message':                      'bg:#bbee88 #222222',
    'background:                   '#888888',
    'clock:                        'bg:#88aa00',
    'panenumber:                   'bg:#888888',
    'panenumber focussed:          'bg:#aa8800',
    'terminated:                   'bg:#aa0000 #ffffff',

    'confirmationtoolbar':          'bg:#880000 #ffffff',
    'confirmationtoolbar.question': '',
    'confirmationtoolbar.yesno':    'bg:#440000',

    'search':                       'bg:#88aa88 #444444',
    'search.text':                  '',
    'search focussed':              'bg:#aaff44 #444444',
    'search.text focussed':         'bold #000000',

    'search-match':                  '#000000 bg:#88aa88',
    'search-match.current':          '#000000 bg:#aaffaa underline',
}

#
#class PymuxStyle(Style):
#    """
#    The styling. It includes the UI style from above. But further, in order to
#    proxy all the output from the processes, it interprets all tokens starting
#    with ('C,) as tokens that describe their own style.
#    """
#    def __init__(self):
#        self.ui_style = Style.from_dict(ui_style)
#        self._token_to_attrs_dict = None
#
#    def get_attrs_for_token(self, token):
#        result = []
#        for part in split_token_in_parts(token):
#            result.append(self._get_attrs_for_token(part))
#        return merge_attrs(result)
#
#    def _get_attrs_for_token(self, token):
#        if token and token[0] == 'C':
#            # Token starts with ('C',). Token describes its own style.
#            c, fg, bg, bold, underline, italic, blink, reverse = token
#            return Attrs(fg, bg, bold, underline, italic, blink, reverse)
#        else:
#            # Take styles from UI style.
#            return self.ui_style.get_attrs_for_token(token)
#
#    def invalidation_hash(self):
#        return None
