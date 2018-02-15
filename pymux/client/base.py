from __future__ import unicode_literals

from abc import ABCMeta
from six import with_metaclass


__all__ = (
    'Client',
    'list_clients',
)


class Client(object):
    def run_command(self, command, pane_id=None):
        """
        Ask the server to run this command.
        """

    def attach(self, detach_other_clients=False, ansi_colors_only=False, true_color=False):
        """
        Attach client user interface.
        """
