
from . import schema


class PupCommand(object):
    """Base class for all pup commands."""

    def name(self):
        """Returns the name of the command (eg makepkg)."""
        return None

    def help(self):
        """Returns help string for this command."""
        return None

    def add_arguments(self, parser):
        """Add needed arguments to the given argparse.ArgumentParser."""
        pass

    def run(self, args, config):
        """Runs the command proper."""
        pass
