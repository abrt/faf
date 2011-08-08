import tty
import sys
import termios
import curses
import re

class Controller:
    """
    A class that can be used to portably generate formatted output to
    a terminal.

    `Controller` defines a set of instance variables whose
    values are initialized to the control sequence necessary to
    perform a given action.  These can be simply included in normal
    output to the terminal:

        >>> term = Controller()
        >>> print 'This is '+term.GREEN+'green'+term.NORMAL

    Alternatively, the `render()` method can used, which replaces
    '${action}' with the string required to perform 'action':

        >>> term = Controller()
        >>> print term.render('This is ${GREEN}green${NORMAL}')

    If the terminal doesn't support a given action, then the value of
    the corresponding instance variable will be set to ''.  As a
    result, the above code will still work on terminals that do not
    support color, except that their output will not be colored.
    Also, this means that you can test whether the terminal supports a
    given action by simply testing the truth value of the
    corresponding instance variable:

        >>> term = Controller()
        >>> if term.CLEAR_SCREEN:
        ...     print 'This terminal supports clearning the screen.'

    Finally, if the width and height of the terminal are known, then
    they can be obtained by calling `cols()` and `lines()` methods.

    Copyright (C) Edward Loper
    Licensed under the PSF License.
    Obtained from http://code.activestate.com/recipes/475116-using-\
    terminfo-for-portable-color-output-cursor-co/

    """
    # Cursor movement:
    BOL = ''             #: Move the cursor to the beginning of the line
    UP = ''              #: Move the cursor up one line
    DOWN = ''            #: Move the cursor down one line
    LEFT = ''            #: Move the cursor left one char
    RIGHT = ''           #: Move the cursor right one char

    # Deletion:
    CLEAR_SCREEN = ''    #: Clear the screen and move to home position
    CLEAR_EOL = ''       #: Clear to the end of the line.
    CLEAR_BOL = ''       #: Clear to the beginning of the line.
    CLEAR_EOS = ''       #: Clear to the end of the screen

    # Output modes:
    BOLD = ''            #: Turn on bold mode
    BLINK = ''           #: Turn on blink mode
    DIM = ''             #: Turn on half-bright mode
    REVERSE = ''         #: Turn on reverse-video mode
    NORMAL = ''          #: Turn off all modes

    # Cursor display:
    HIDE_CURSOR = ''     #: Make the cursor invisible
    SHOW_CURSOR = ''     #: Make the cursor visible

    # Foreground colors:
    BLACK = BLUE = GREEN = CYAN = RED = MAGENTA = YELLOW = WHITE = ''

    # Background colors:
    BG_BLACK = BG_BLUE = BG_GREEN = BG_CYAN = ''
    BG_RED = BG_MAGENTA = BG_YELLOW = BG_WHITE = ''

    _STRING_CAPABILITIES = """
    BOL=cr UP=cuu1 DOWN=cud1 LEFT=cub1 RIGHT=cuf1
    CLEAR_SCREEN=clear CLEAR_EOL=el CLEAR_BOL=el1 CLEAR_EOS=ed BOLD=bold
    BLINK=blink DIM=dim REVERSE=rev UNDERLINE=smul NORMAL=sgr0
    HIDE_CURSOR=cinvis SHOW_CURSOR=cnorm""".split()
    _COLORS = """BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE""".split()
    _ANSICOLORS = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE".split()

    def __init__(self, term_stream=sys.stdout):
        """Create a `Controller` and initialize its attributes
        with appropriate values for the current terminal.
        `term_stream` is the stream that will be used for terminal
        output; if this stream is not a tty, then the terminal is
        assumed to be a dumb terminal (i.e., have no capabilities).

        """
        # If the stream isn't a tty, then assume it has no capabilities.
        if not term_stream.isatty(): return

        # Check the terminal type.  If we fail, then assume that the
        # terminal has no capabilities.
        try: curses.setupterm()
        except: return

        # Look up string capabilities.
        for capability in self._STRING_CAPABILITIES:
            (attrib, cap_name) = capability.split('=')
            setattr(self, attrib, self._tigetstr(cap_name) or '')

        # Colors
        set_fg = self._tigetstr('setf')
        if set_fg:
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, color, curses.tparm(set_fg, i) or '')
        set_fg_ansi = self._tigetstr('setaf')
        if set_fg_ansi:
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, color, curses.tparm(set_fg_ansi, i) or '')
        set_bg = self._tigetstr('setb')
        if set_bg:
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, 'BG_'+color, curses.tparm(set_bg, i) or '')
        set_bg_ansi = self._tigetstr('setab')
        if set_bg_ansi:
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, 'BG_'+color, curses.tparm(set_bg_ansi, i) or '')

    def cols(self):
        return self.gettermres()[0]

    def lines(self):
        return self.gettermres()[1]

    def gettermres(self):
        """
        returns the current terminal size in columns and lines
        """
        import struct, fcntl, sys, termios
        lines, cols = struct.unpack("HHHH",
                                    fcntl.ioctl(sys.stdout.fileno(),
                                                termios.TIOCGWINSZ ,
                                                struct.pack("HHHH",
                                                            0, 0, 0, 0)))[:2]
        return cols, lines

    def _tigetstr(self, cap_name):
        # String capabilities can include "delays" of the form "$<2>".
        # For any modern terminal, we should be able to just ignore
        # these, so strip them out.
        import curses
        cap = curses.tigetstr(cap_name) or ''
        return re.sub(r'\$<\d+>[/*]?', '', cap)

    def render(self, template):
        """Replace each $-substitutions in the given template string
        with the corresponding terminal control string (if it's
        defined) or '' (if it's not).

        """
        return re.sub(r'\$\$|\${\w+}', self._render_sub, template)

    def _render_sub(self, match):
        s = match.group()
        if s == '$$': return s
        else: return getattr(self, s[2:-1])

class ProgressBar(object):
    """Terminal progress bar class

    Copyright: 2009 Nadia Alramli
    License: BSD
    Obtained from http://nadiana.com/animated-terminal-progress-bar-in-python

    """
    TEMPLATE = ('%(percent)-2s%% [%(progress)s%(normal)s%(empty)s] %(message)s\n')
    PADDING = 10

    def __init__(self, terminal_controller, width=None, block='=', empty='-'):
        """
        color -- color name
        width -- bar width (optinal)
        block -- progress display character (default '=')
        empty -- bar display character (default '-')
        """
        self.terminal_controller = terminal_controller
        if width and width < terminal_controller.cols() - self.PADDING:
            self.width = width
        else:
            # Adjust to the width of the terminal
            self.width = terminal_controller.cols() - self.PADDING
        self.block = block
        self.empty = empty
        self.progress = None
        self.lines = 0

    def render(self, percent, message = ''):
        """Print the progress bar
        percent -- the progress percentage %
        message -- message string (optional)
        """
        inline_msg_len = 0
        if message:
            # The length of the first line in the message
            inline_msg_len = len(message.splitlines()[0])
        if inline_msg_len + self.width + self.PADDING > self.terminal_controller.cols():
            # The message is too long to fit in one line.
            # Adjust the bar width to fit.
            bar_width = self.terminal_controller.cols() - inline_msg_len - self.PADDING
        else:
            bar_width = self.width

        # Check if render is called for the first time
        if self.progress != None:
            self.clear()
        self.progress = (bar_width * percent) / 100
        data = self.TEMPLATE % {
            'percent': percent,
            'progress': self.block * self.progress,
            'normal': self.terminal_controller.NORMAL,
            'empty': self.empty * (bar_width - self.progress),
            'message': message
        }
        sys.stdout.write(data)
        sys.stdout.flush()
        # The number of lines printed
        self.lines = len(data.splitlines())

    def clear(self):
        """Clear all printed lines"""
        sys.stdout.write(self.lines * (self.terminal_controller.UP +
                                       self.terminal_controller.BOL +
                                       self.terminal_controller.CLEAR_EOL))

def getch():
    """Read a character from the standard input and return it.

    It works on Linux. Doesn't work on Windows.

    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch
