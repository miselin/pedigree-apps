class PupCommand:
    """Base class for all pup commands."""

    def name(self):
        """Returns the name of the command (eg makepkg)."""

    def help(self):
        """Returns help string for this command."""

    def add_arguments(self, parser):
        """Add needed arguments to the given argparse.ArgumentParser."""

    def run(self, args, config):
        """Runs the command proper."""
