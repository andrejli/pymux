# encoding: utf-8
"""
The layout engine. This builds the prompt_toolkit layout.
"""
from __future__ import unicode_literals

from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.layout.containers import VSplit, HSplit, Window, FloatContainer, Float, ConditionalContainer, Container, Align, to_container
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.dimension import to_dimension, is_dimension
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import BeforeInput, ShowArg, AppendAutoSuggestion, Processor, Transformation, HighlightSelectionProcessor, merge_processors
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.layout.screen import Point
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.widgets.toolbars import FormattedTextToolbar

from six.moves import range
from functools import partial

import pymux.arrangement as arrangement
import datetime
import weakref

from .filters import WaitsForConfirmation
from .format import format_pymux_string
from .log import logger

__all__ = (
    'LayoutManager',
)


class Justify:
    " Justify enum for the status bar. "
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'

    _ALL = [LEFT, CENTER, RIGHT]


class Z_INDEX:
    HIGHLIGHTED_BORDER = 2
    STATUS_BAR = 5
    COMMAND_LINE = 6
    MESSAGE_TOOLBAR = 7


class Background(Container):
    """
    Generate the background of dots, which becomes visible when several clients
    are attached and not all of them have the same size.

    (This is implemented as a Container, rather than a UIControl wrapped in a
    Window, because it can be done very effecient this way.)
    """
    def reset(self):
        pass

    def preferred_width(self, max_available_width):
        return D()

    def preferred_height(self, width, max_available_height):
        return D()

    def write_to_screen(self, screen, mouse_handlers, write_position,
                        parent_style, erase_bg, z_index):
        " Fill the whole area of write_position with dots. "
        default_char = Char(' ', 'class:background')
        dot = Char('.', 'class:background')

        ypos = write_position.ypos
        xpos = write_position.xpos

        for y in range(ypos, ypos + write_position.height):
            row = screen.data_buffer[y]

            for x in range(xpos, xpos + write_position.width):
                row[x] = dot if (x + y) % 3 == 0 else default_char

    def get_children(self):
        return []


# Numbers for the clock and pane numbering.
_numbers = list(zip(*[  # (Transpose x/y.)
    ['#####', '    #', '#####', '#####', '#   #', '#####', '#####', '#####', '#####', '#####'],
    ['#   #', '    #', '    #', '    #', '#   #', '#    ', '#    ', '    #', '#   #', '#   #'],
    ['#   #', '    #', '#####', '#####', '#####', '#####', '#####', '    #', '#####', '#####'],
    ['#   #', '    #', '#    ', '    #', '    #', '    #', '#   #', '    #', '#   #', '    #'],
    ['#####', '    #', '#####', '#####', '    #', '#####', '#####', '    #', '#####', '#####'],
]))


def _draw_number(screen, x_offset, y_offset, number, style='class:clock',
                 transparent=False):
    " Write number at position. "
    fg = Char(' ', 'class:clock')
    bg = Char(' ', '')

    for y, row in enumerate(_numbers[number]):
        screen_row = screen.data_buffer[y + y_offset]
        for x, n in enumerate(row):
            if n == '#':
                screen_row[x + x_offset] = fg
            elif not transparent:
                screen_row[x + x_offset] = bg


class BigClock(Container):
    """
    Display a big clock.
    """
    WIDTH = 28
    HEIGHT = 5

    def __init__(self, on_click):
        assert callable(on_click)
        self.on_click = on_click

    def reset(self):
        pass

    def write_to_screen(self, screen, mouse_handlers, write_position,
                        parent_style, erase_bg, z_index):
        xpos = write_position.xpos
        ypos = write_position.ypos

        # Erase background.
        bg = Char(' ')

        for y in range(ypos, self.HEIGHT + ypos):
            row = screen.data_buffer[y]
            for x in range(xpos, xpos + self.WIDTH):
                row[x] = bg

        # Display time.
        now = datetime.datetime.now()
        _draw_number(screen, xpos + 0, ypos, now.hour // 10)
        _draw_number(screen, xpos + 6, ypos, now.hour % 10)
        _draw_number(screen, xpos + 16, ypos, now.minute // 10)
        _draw_number(screen, xpos + 23, ypos, now.minute % 10)

        # Add a colon
        screen.data_buffer[ypos + 1][xpos + 13] = Char(' ', 'class:clock')
        screen.data_buffer[ypos + 3][xpos + 13] = Char(' ', 'class:clock')

        screen.width = self.WIDTH
        screen.height = self.HEIGHT

        mouse_handlers.set_mouse_handler_for_range(
            x_min=xpos,
            x_max=xpos + write_position.width,
            y_min=ypos,
            y_max=ypos + write_position.height,
            handler=self._mouse_handler)

    def _mouse_handler(self, cli, mouse_event):
        " Click callback. "
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.on_click(cli)
        else:
            return NotImplemented

    def preferred_width(self, max_available_width):
        return D.exact(BigClock.WIDTH)

    def preferred_height(self, width, max_available_height):
        return D.exact(BigClock.HEIGHT)

    def get_children(self):
        return []


class PaneNumber(Container):  # XXX: make FormattedTextControl
    """
    Number of panes, to be drawn in the middle of the pane.
    """
    WIDTH = 5
    HEIGHT = 5

    def __init__(self, pymux, arrangement_pane):
        self.pymux = pymux
        self.arrangement_pane = arrangement_pane

    def reset(self):
        pass

    def _get_index(self):
        window = self.pymux.arrangement.get_active_window()
        try:
            return window.get_pane_index(self.arrangement_pane)
        except ValueError:
            return 0

    def preferred_width(self, max_available_width):
        # Enough to display all the digits.
        return Dimension.exact(6 * len('%s' % self._get_index()) - 1)

    def preferred_height(self, width, max_available_height):
        return Dimension.exact(self.HEIGHT)

    def write_to_screen(self, screen, mouse_handlers, write_position,
                        parent_style, erase_bg, z_index):
        style = 'class:panenumber'

        for i, d in enumerate('%s' % (self._get_index())):
            _draw_number(screen, write_position.xpos + i * 6, write_position.ypos,
                         int(d), style=style, transparent=True)

    def get_children(self):
        return []


class MessageToolbar(FormattedTextToolbar):
    """
    Pop-up (at the bottom) for showing error/status messages.
    """
    def __init__(self, client_state):
        def get_message():
            # If there is a message to be shown for this client, show that.
            if client_state.message:
                return client_state.message
            else:
                return ''

        def get_tokens():
            message = get_message()
            if message:
                return FormattedText([
                    ('class:message', message),
                    ('[SetCursorPosition]', ''),
                    ('class:message', ' '),
                ])
            else:
                return ''

        @Condition
        def is_visible():
            return bool(get_message())

        super(MessageToolbar, self).__init__(get_tokens,
#                filter=f,
#                has_focus=f
                )


class LayoutManager(object):
    """
    The main layout class, that contains the whole Pymux layout.
    """
    def __init__(self, pymux, client_state):
        self.pymux = pymux
        self.client_state = client_state
        self.layout = self._create_layout()

        # Keep track of render information.
        self.pane_write_positions = {}

    def reset_write_positions(self):
        """
        Clear write positions right before rendering. (They are populated
        during rendering).
        """
        self.pane_write_positions = {}

    def _create_select_window_handler(self, window):
        " Return a mouse handler that selects the given window when clicking. "
        def handler(mouse_event):
            if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                self.pymux.arrangement.set_active_window(window)
                self.pymux.invalidate()
            else:
                return NotImplemented  # Event not handled here.
        return handler

    def _get_status_tokens(self):
        " The tokens for the status bar. "
        result = []

        # Display panes.
        for i, w in enumerate(self.pymux.arrangement.windows):
            if i > 0:
                result.append(('', ' '))

            if w == self.pymux.arrangement.get_active_window():
                style = 'class:window.current'
                format_str = self.pymux.window_status_current_format

            else:
                style = 'class:window'
                format_str = self.pymux.window_status_format

            result.append((
                style,
                format_pymux_string(self.pymux, format_str, window=w),
                self._create_select_window_handler(w)))

        return result

    def _get_status_left_tokens(self):
        return format_pymux_string(self.pymux, self.pymux.status_left)

    def _get_status_right_tokens(self):
        return format_pymux_string(self.pymux, self.pymux.status_right)

    def _get_align(self):
        if self.pymux.status_justify == Justify.RIGHT:
            return Align.RIGHT
        elif self.pymux.status_justify == Justify.CENTER:
            return Align.CENTER
        else:
            return Align.LEFT

    def _before_prompt_command_tokens(self):
        return [('class:commandline.prompt', '%s ' % (self.client_state.prompt_text, ))]

    def _create_layout(self):
        """
        Generate the main prompt_toolkit layout.
        """
        waits_for_confirmation = WaitsForConfirmation(self.pymux)

        return FloatContainer(
            content=HSplit([
                # The main window.
                FloatContainer(
                    Background(),
                    floats=[
                        Float(width=lambda: self.pymux.get_window_size().columns,
                              height=lambda: self.pymux.get_window_size().rows,
                              content=DynamicBody(self.pymux))
                    ]),
                # Status bar.
                ConditionalContainer(
                    content=VSplit([
                        # Left.
                        Window(
                            height=1,
                            width=(lambda: D(max=self.pymux.status_left_length)),
                            dont_extend_width=True,
                            content=FormattedTextControl(self._get_status_left_tokens)),
                        # List of windows in the middle.
                        Window(
                            height=1,
                            char=' ',
                            align=self._get_align,
                            content=FormattedTextControl(self._get_status_tokens)),
                        # Right.
                        Window(
                            height=1,
                            width=(lambda: D(max=self.pymux.status_right_length)),
                            dont_extend_width=True,
                            align=Align.RIGHT,
                            content=FormattedTextControl(self._get_status_right_tokens))
                    ], z_index=Z_INDEX.STATUS_BAR, style='class:statusbar'),
                    filter=Condition(lambda: self.pymux.enable_status),
                )
            ]),
            floats=[
                Float(bottom=1, left=0, z_index=Z_INDEX.MESSAGE_TOOLBAR,
                      content=MessageToolbar(self.client_state)),
                Float(left=0, right=0, bottom=0, content=HSplit([
                    # Wait for confirmation toolbar.
                    ConditionalContainer(
                        content=Window(
                            height=1,
                            content=ConfirmationToolbar(self.pymux, self.client_state),
                            z_index=Z_INDEX.COMMAND_LINE,
                        ),
                        filter=waits_for_confirmation,
                    ),
                    # ':' prompt toolbar.
                    ConditionalContainer(
                        content=Window(
                            height=D(min=1),  # Can be more if the command is multiline.
                            style='class:commandline',
                            dont_extend_height=True,
                            content=BufferControl(
                                buffer=self.client_state.command_buffer,
                                preview_search=True,
                                input_processors=[
                                    AppendAutoSuggestion(),
                                    BeforeInput(':', style='class:commandline-prompt'),
                                    ShowArg(),
                                    HighlightSelectionProcessor(),
                                ]),
                            z_index=Z_INDEX.COMMAND_LINE,
                        ),
                        filter=has_focus(self.client_state.command_buffer),
                    ),
                    # Other command-prompt commands toolbar.
                    ConditionalContainer(
                        content=Window(
                            height=1,
                            style='class:commandline',
                            content=BufferControl(
                                buffer=self.client_state.prompt_buffer,
                                input_processors=[
                                    BeforeInput(self._before_prompt_command_tokens),
                                    AppendAutoSuggestion(),
                                    HighlightSelectionProcessor(),
                                ]),
                            z_index=Z_INDEX.COMMAND_LINE,
                        ),
                        filter=has_focus(self.client_state.prompt_buffer),
                    ),
                ])),
                Float(xcursor=True, ycursor=True, content=CompletionsMenu(max_height=12)),
            ]
        )


class ConfirmationToolbar(FormattedTextControl):
    """
    Window that displays the yes/no confirmation dialog.
    """
    def __init__(self, pymux, client_state):
        def get_tokens():
            return [
                ('class:question', ' '),
                ('class:question', format_pymux_string(
                    pymux, client_state.confirm_text or '')),
                ('class:question', ' '),
                ('class:yesno', '  y/n'),
                ('[SetCursorPosition]', ''),
                ('class:yesno', '  '),
            ]

        super(ConfirmationToolbar, self).__init__(
            get_tokens, style='class:confirmationtoolbar')


class DynamicBody(Container):
    """
    The dynamic part, which is different for each CLI (for each client). It
    depends on which window/pane is active.

    This makes it possible to have just one main layout class, and
    automatically rebuild the parts that change if the windows/panes
    arrangement changes, without doing any synchronisation.
    """
    def __init__(self, pymux):
        self.pymux = pymux
        self._bodies_for_app = weakref.WeakKeyDictionary()  # Maps Application to (hash, Container)

    def _get_body(self):
        " Return the Container object for the current CLI. "
        new_hash = self.pymux.arrangement.invalidation_hash()

        # Return existing layout if nothing has changed to the arrangement.
        app = get_app()

        if app in self._bodies_for_app:
            existing_hash, container = self._bodies_for_app[app]
            if existing_hash == new_hash:
                return container

        # The layout changed. Build a new layout when the arrangement changed.
        new_layout = self._build_layout()
        self._bodies_for_app[app] = (new_hash, new_layout)
        return new_layout

    def _build_layout(self):
        " Rebuild a new Container object and return that. "
        logger.info('Rebuilding layout.')

        if not self.pymux.arrangement.windows:
            # No Pymux windows in the arrangement.
            return Window()

        active_window = self.pymux.arrangement.get_active_window()

        # When zoomed, only show the current pane, otherwise show all of them.
        if active_window.zoom:
            return to_container(_create_container_for_process(
                self.pymux, active_window, active_window.active_pane, zoom=True))
        else:
            window = self.pymux.arrangement.get_active_window()
            return HSplit([
                # Some spacing for the top status bar.
                ConditionalContainer(
                    content=Window(height=1),
                    filter=Condition(lambda: self.pymux.enable_pane_status)),
                # The actual content.
                _create_split(self.pymux, window, window.root)
            ])

    def reset(self):
        for invalidation_hash, body in self._bodies_for_app.values():
            body.reset()

    def preferred_width(self, max_available_width):
        body = self._get_body()
        return body.preferred_width(max_available_width)

    def preferred_height(self, width, max_available_height):
        body = self._get_body()
        return body.preferred_height(width, max_available_height)

    def write_to_screen(self, screen, mouse_handlers, write_position,
                        parent_style, erase_bg, z_index):
        body = self._get_body()
        body.write_to_screen(screen, mouse_handlers, write_position,
                             parent_style, erase_bg, z_index)

    def get_children(self):
        # (Required for prompt_toolkit.layout.utils.find_window_for_buffer_name.)
        body = self._get_body()
        return [body]


class SizedBox(Container):
    """
    Container whith enforces a given width/height without taking the children
    into account (even if no width/height is given).

    :param content: `Container`.
    :param report_write_position_callback: `None` or a callable for reporting
        back the dimensions used while drawing.
    """
    def __init__(self, content, width=None, height=None,
                 report_write_position_callback=None):
        assert is_dimension(width)
        assert is_dimension(height)
        assert report_write_position_callback is None or callable(report_write_position_callback)

        self.content = to_container(content)
        self.width = width
        self.height = height
        self.report_write_position_callback = report_write_position_callback

    def reset(self):
        self.content.reset()

    def preferred_width(self, max_available_width):
        return to_dimension(self.width)

    def preferred_height(self, width, max_available_height):
        return to_dimension(self.height)

    def write_to_screen(self, screen, mouse_handlers, write_position,
                        parent_style, erase_bg, z_index):
        # Report dimensions.
        if self.report_write_position_callback:
            self.report_write_position_callback(write_position)

        self.content.write_to_screen(
            screen, mouse_handlers, write_position, parent_style, erase_bg, z_index)

    def get_children(self):
        return [self.content]


def _create_split(pymux, window, split):
    """
    Create a prompt_toolkit `Container` instance for the given pymux split.
    """
    assert isinstance(split, (arrangement.HSplit, arrangement.VSplit))
    is_vsplit = isinstance(split, arrangement.VSplit)

    def get_average_weight():
        """ Calculate average weight of the children. Return 1 if none of
        the children has a weight specified yet. """
        weights = 0
        count = 0

        for i in split:
            if i in split.weights:
                weights += split.weights[i]
                count += 1

        if weights:
            return max(1, weights // count)
        else:
            return 1

    def report_write_position_callback(item, write_position):
        """
        When the layout is rendered, store the actial dimensions as
        weights in the arrangement.VSplit/HSplit classes.

        This is required because when a pane is resized with an increase of +1,
        we want to be sure that this corresponds exactly with one row or
        column. So, that updating weights corresponds exactly 1/1 to updating
        the size of the panes.
        """
        if is_vsplit:
            split.weights[item] = write_position.width
        else:
            split.weights[item] = write_position.height

    def get_size(item):
        return D(weight=split.weights.get(item) or average_weight)

    content = []
    average_weight = get_average_weight()

    for i, item in enumerate(split):
        # Create function for calculating dimensions for child.
        width = height = None
        if is_vsplit:
            width = partial(get_size, item)
        else:
            height = partial(get_size, item)

        # Create child.
        if isinstance(item, (arrangement.VSplit, arrangement.HSplit)):
            child = _create_split(pymux, window, item)
        elif isinstance(item, arrangement.Pane):
            child = _create_container_for_process(pymux, window, item)
        else:
            raise TypeError('Got %r' % (item,))

        # Wrap child in `SizedBox` to enforce dimensions and sync back.
        content.append(SizedBox(
            child, width=width, height=height,
            report_write_position_callback=partial(report_write_position_callback, item)))

    # Create prompt_toolkit Container.
    if is_vsplit:
        return_cls = VSplit
        padding_char = _border_vertical
    else:
        return_cls = HSplit
        padding_char = _border_horizontal

    return return_cls(content,
            padding=1,
            padding_char=padding_char)


class _UseCopyTokenListProcessor(Processor):
    """
    In order to allow highlighting of the copy region, we use a preprocessed
    list of (Token, text) tuples. This processor returns just that list for the
    given pane.
    """
    def __init__(self, arrangement_pane):
        self.arrangement_pane = arrangement_pane

    def apply_transformation(self, document, lineno, source_to_display, tokens):
        tokens = self.arrangement_pane.copy_get_tokens_for_line(lineno)
        return Transformation(tokens[:])

    def invalidation_hash(self, document):
        return document.text


def _create_container_for_process(pymux, window, arrangement_pane, zoom=False):
    """
    Create a `Container` with a titlebar for a process.
    """
    @Condition
    def clock_is_visible():
        return arrangement_pane.clock_mode

    @Condition
    def pane_numbers_are_visible():
        return pymux.display_pane_numbers

    terminal_is_focused = has_focus(arrangement_pane.terminal)

    def get_terminal_style():
        if terminal_is_focused():
            result = 'class:terminal.focused'
        else:
            result = 'class:terminal'
        return result

    def get_titlebar_text_fragments():
        result = []

        if zoom:
            result.append(('class:titlebar-zoom', ' Z '))

        if arrangement_pane.process.is_terminated:
            result.append(('class:terminated', ' Terminated '))

        # Scroll buffer info.
        if arrangement_pane.display_scroll_buffer:
            result.append(('class:copymode', ' %s ' % arrangement_pane.scroll_buffer_title))

            # Cursor position.
            document = arrangement_pane.scroll_buffer.document
            result.append(('class:copymode.position', ' %i,%i ' % (
                document.cursor_position_row, document.cursor_position_col)))

        if arrangement_pane.name:
            result.append(('class:name', ' %s ' % arrangement_pane.name))
            result.append(('', ' '))

        return result + [
            ('', format_pymux_string(pymux, ' #T ', pane=arrangement_pane))  # XXX: Make configurable.
        ]

    def get_pane_index():
        try:
            w = pymux.arrangement.get_active_window()
            index = w.get_pane_index(arrangement_pane)
        except ValueError:
            index = '/'

        return '%3s ' % index

    def on_click():
        " Click handler for the clock. When clicked, select this pane. "
        arrangement_pane.clock_mode = False
        pymux.arrangement.get_active_window().active_pane = arrangement_pane
        pymux.invalidate()


    return HighlightBordersIfActive(
        window,
        arrangement_pane,
        get_terminal_style,
        FloatContainer(
            HSplit([
                # The terminal.
                TracePaneWritePosition(
                    pymux, arrangement_pane,
                    content=arrangement_pane.terminal),
            ]),

            #
            floats=[
                # The title bar.
                Float(content=
                    ConditionalContainer(
                        content=VSplit([
                                Window(
                                    height=1,
                                    content=FormattedTextControl(
                                        get_titlebar_text_fragments)),
                                Window(
                                    height=1,
                                    width=4,
                                    content=FormattedTextControl(get_pane_index),
                                    style='class:paneindex')
                            ], style='class:titlebar'),
                        filter=Condition(lambda: pymux.enable_pane_status)),
                    left=0, right=0, top=-1, height=1, z_index=100),

                # The clock.
                Float(content=ConditionalContainer(BigClock(on_click),
                      filter=clock_is_visible)),

                # Pane number.
                Float(content=ConditionalContainer(
                      content=PaneNumber(pymux, arrangement_pane),
                      filter=pane_numbers_are_visible)),
            ]
        )
    )


class _ContainerProxy(Container):
    def __init__(self, content):
        self.content = content

    def reset(self):
        self.content.reset()

    def preferred_width(self, max_available_width):
        return self.content.preferred_width(max_available_width)

    def preferred_height(self, width, max_available_height):
        return self.content.preferred_height(width, max_available_height)

    def write_to_screen(self, screen, mouse_handlers, write_position, parent_style, erase_bg, z_index):
        self.content.write_to_screen(screen, mouse_handlers, write_position, parent_style, erase_bg, z_index)

    def get_children(self):
        return [self.content]


_focused_border_titlebar = '┃'
_focused_border_vertical = '┃'
_focused_border_horizontal = '━'
_focused_border_left_top = '┏'
_focused_border_right_top = '┓'
_focused_border_left_bottom = '┗'
_focused_border_right_bottom = '┛'

_border_vertical = '│'
_border_horizontal = '─'
_border_left_bottom = '└'
_border_right_bottom = '┘'
_border_left_top = '┌'
_border_right_top = '┐'


class HighlightBordersIfActive(object):
    """
    Put borders around this control if active.
    """
    def __init__(self, window, pane, style, content):
        @Condition
        def is_selected():
            return window.active_pane == pane

        def conditional_float(char, left=None, right=None, top=None,
                              bottom=None, width=None, height=None):
            return Float(
                content=ConditionalContainer(
                    Window(char=char, style='class:border'),
                    filter=is_selected),
                left=left, right=right, top=top, bottom=bottom, width=width, height=height,
                z_index=Z_INDEX.HIGHLIGHTED_BORDER)

        self.container = FloatContainer(
            content,
            style=style,
            floats=[
                # Sides.
                conditional_float(_focused_border_vertical, left=-1, top=0, bottom=0, width=1),
                conditional_float(_focused_border_vertical, right=-1, top=0, bottom=0, width=1),
                conditional_float(_focused_border_horizontal, left=0, right=0, top=-1, height=1),
                conditional_float(_focused_border_horizontal, left=0, right=0, bottom=-1, height=1),

                # Corners.
                conditional_float(_focused_border_left_top, left=-1, top=-1, width=1, height=1),
                conditional_float(_focused_border_right_top, right=-1, top=-1, width=1, height=1),
                conditional_float(_focused_border_left_bottom, left=-1, bottom=-1, width=1, height=1),
                conditional_float(_focused_border_right_bottom, right=-1, bottom=-1, width=1, height=1),
            ])

    def __pt_container__(self):
        return self.container


class TracePaneWritePosition(_ContainerProxy):   # XXX: replace with SizedBox
    " Trace the write position of this pane. "
    def __init__(self, pymux, arrangement_pane, content):
        content = to_container(content)
        _ContainerProxy.__init__(self, content)

        self.pymux = pymux
        self.arrangement_pane = arrangement_pane

    def write_to_screen(self, screen, mouse_handlers, write_position, parent_style, erase_bg, z_inedx):
        _ContainerProxy.write_to_screen(self, screen, mouse_handlers, write_position, parent_style, erase_bg, z_inedx)
        self.pymux.get_client_state().layout_manager.pane_write_positions[self.arrangement_pane] = write_position


def focus_left(pymux):
    " Move focus to the left. "
    _move_focus(pymux,
                lambda wp: wp.xpos - 2,  # 2 in order to skip over the border.
                lambda wp: wp.ypos)


def focus_right(pymux):
    " Move focus to the right. "
    _move_focus(pymux,
                lambda wp: wp.xpos + wp.width + 1,
                lambda wp: wp.ypos)


def focus_down(pymux):
    " Move focus down. "
    _move_focus(pymux,
                lambda wp: wp.xpos,
                lambda wp: wp.ypos + wp.height + 2)
        # 2 in order to skip over the border. Only required when the
        # pane-status is not shown, but a border instead.


def focus_up(pymux):
    " Move focus up. "
    _move_focus(pymux,
                lambda wp: wp.xpos,
                lambda wp: wp.ypos - 2)


def _move_focus(pymux, get_x, get_y):
    " Move focus of the active window. "
    window = pymux.arrangement.get_active_window()

    try:
        write_pos = pymux.get_client_state().layout_manager.pane_write_positions[window.active_pane]
    except KeyError:
        pass
    else:
        x = get_x(write_pos)
        y = get_y(write_pos)

        # Look for the pane at this position.
        for pane, wp in pymux.get_client_state().layout_manager.pane_write_positions.items():
            if (wp.xpos <= x < wp.xpos + wp.width and
                    wp.ypos <= y < wp.ypos + wp.height):
                window.active_pane = pane
                return


#class Vt100Window(Container):
#    """
#    Container that holds the VT100 control.
#    """
#    def __init__(self, process, has_focus, set_focus):
#        self.process = process
#        self.has_focus = to_filter(has_focus)
#        self.set_focus = set_focus
#
#    def reset(self):
#        pass
#
#    def preferred_width(self, max_available_width):
#        return Dimension()
#
#    def preferred_height(self, width, max_available_height):
#        return Dimension()
#
#    def write_to_screen(self, screen, mouse_handlers, write_position, parent_style, erase_bg, z_index):
#        """
#        Write window to screen. This renders the user control, the margins and
#        copies everything over to the absolute position at the given screen.
#        """
#        # Set size of the screen.
#        self.process.set_size(write_position.width, write_position.height)
#
#        vertical_scroll = self.process.screen.line_offset
#
#        # Render UserControl.
#        temp_screen = self.process.screen.pt_screen
#
#        # Write body to screen.
#        self._copy_body(temp_screen, screen, write_position, vertical_scroll,
#                        write_position.width)
#
#        # Set mouse handlers.
#        def mouse_handler(mouse_event):
#            """ Wrapper around the mouse_handler of the `UIControl` that turns
#            absolute coordinates into relative coordinates. """
#            position = mouse_event.position
#
#            # Call the mouse handler of the UIControl first.
#            self._mouse_handler(
#                MouseEvent(
#                    position=Point(x=position.x - write_position.xpos,
#                                   y=position.y - write_position.ypos + vertical_scroll),
#                    event_type=mouse_event.event_type))
#
#        mouse_handlers.set_mouse_handler_for_range(
#            x_min=write_position.xpos,
#            x_max=write_position.xpos + write_position.width,
#            y_min=write_position.ypos,
#            y_max=write_position.ypos + write_position.height,
#            handler=mouse_handler)
#
#        # If reverse video is enabled for the whole screen.
#        if self.process.screen.has_reverse_video:
#            data_buffer = screen.data_buffer
#
#            for y in range(write_position.ypos, write_position.ypos + write_position.height):
#                row = data_buffer[y]
#
#                for x in range(write_position.xpos, write_position.xpos + write_position.width):
#                    char = row[x]
#                    token = list(char.token or DEFAULT_TOKEN)
#
#                    # The token looks like ('C', *attrs). Replace the value of the reverse flag.
#                    if token and token[0] == 'C':
#                        token[-1] = not token[-1]  # Invert reverse value.
#                        row[x] = Char(char.char, tuple(token))
#
#    def _copy_body(self, temp_screen, new_screen, write_position,
#                   vertical_scroll, width):
#        """
#        Copy characters from the temp screen that we got from the `UIControl`
#        to the real screen.
#        """
#        xpos = write_position.xpos
#        ypos = write_position.ypos
#        height = write_position.height
#
#        temp_buffer = temp_screen.data_buffer
#        new_buffer = new_screen.data_buffer
#        temp_screen_height = temp_screen.height
#
#        vertical_scroll = self.process.screen.line_offset
#        y = 0
#
#        # Now copy the region we need to the real screen.
#        for y in range(0, height):
#            # We keep local row variables. (Don't look up the row in the dict
#            # for each iteration of the nested loop.)
#            new_row = new_buffer[y + ypos]
#
#            if y >= temp_screen_height and y >= write_position.height:
#                # Break out of for loop when we pass after the last row of the
#                # temp screen. (We use the 'y' position for calculation of new
#                # screen's height.)
#                break
#            else:
#                temp_row = temp_buffer[y + vertical_scroll]
#
#                # Copy row content, except for transparent tokens.
#                # (This is useful in case of floats.)
#                for x in range(0, width):
#                    new_row[x + xpos] = temp_row[x]
#
#        if self.has_focus():
#            new_screen.cursor_position = Point(
#                y=temp_screen.cursor_position.y + ypos - vertical_scroll,
#                x=temp_screen.cursor_position.x + xpos)
#
#            new_screen.show_cursor = temp_screen.show_cursor
#
#        # Update height of the output screen. (new_screen.write_data is not
#        # called, so the screen is not aware of its height.)
#        new_screen.height = max(new_screen.height, ypos + y + 1)
#
#    def _mouse_handler(self, mouse_event):
#        """
#        Handle mouse events in a pane. A click in a non-active pane will select
#        it, one in an active pane, will send the mouse event to the application
#        running inside it.
#        """
#        process = self.process
#        x = mouse_event.position.x
#        y = mouse_event.position.y
#
#        # The containing Window translates coordinates to the absolute position
#        # of the whole screen, but in this case, we need the relative
#        # coordinates of the visible area.
#        y -= self.process.screen.line_offset
#
#        if not self.has_focus():
#            # Focus this process when the mouse has been clicked.
#            if mouse_event.event_type == MouseEventType.MOUSE_UP:
#                self.set_focus()
#        else:
#            # Already focused, send event to application when it requested
#            # mouse support.
#            if process.screen.sgr_mouse_support_enabled:
#                # Xterm SGR mode.
#                ev, m = {
#                    MouseEventType.MOUSE_DOWN: ('0', 'M'),
#                    MouseEventType.MOUSE_UP: ('0', 'm'),
#                    MouseEventType.SCROLL_UP: ('64', 'M'),
#                    MouseEventType.SCROLL_DOWN: ('65', 'M'),
#                }.get(mouse_event.event_type)
#
#                self.process.write_input(
#                    '\x1b[<%s;%s;%s%s' % (ev, x + 1, y + 1, m))
#
#            elif process.screen.urxvt_mouse_support_enabled:
#                # Urxvt mode.
#                ev = {
#                    MouseEventType.MOUSE_DOWN: 32,
#                    MouseEventType.MOUSE_UP: 35,
#                    MouseEventType.SCROLL_UP: 96,
#                    MouseEventType.SCROLL_DOWN: 97,
#                }.get(mouse_event.event_type)
#
#                self.process.write_input(
#                    '\x1b[%s;%s;%sM' % (ev, x + 1, y + 1))
#
#            elif process.screen.mouse_support_enabled:
#                # Fall back to old mode.
#                if x < 96 and y < 96:
#                    ev = {
#                            MouseEventType.MOUSE_DOWN: 32,
#                            MouseEventType.MOUSE_UP: 35,
#                            MouseEventType.SCROLL_UP: 96,
#                            MouseEventType.SCROLL_DOWN: 97,
#                    }.get(mouse_event.event_type)
#
#                    self.process.write_input('\x1b[M%s%s%s' % (
#                        six.unichr(ev),
#                        six.unichr(x + 33),
#                        six.unichr(y + 33)))
#
#    def get_children(self):
#        # Only yield self. A window doesn't have children.
#        return []
