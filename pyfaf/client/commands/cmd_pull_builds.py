# -*- coding: utf-8 -*-


import kobo.client
import pyfaf

class Pull_Builds(kobo.client.ClientCommand):
    """Pulls builds for given operating system and tag"""
    enabled = True
    admin = False # admin type account required

    def options(self):
        # specify command usage
        # normalized name contains a lower-case class name with underscores converted to dashes
        self.parser.usage = "%%prog %s [options] <args>" % self.normalized_name

        # specify command options as in optparse.OptionParser
        """
        self.parser.add_option(
            "--long-option",
            default=None,
            action="store",
            help=""
        )
        """

    def run(self, *args, **kwargs):
        # load from config file
        config_username = None
        config_password = None
        try:
            if self.container.conf["AUTH_METHOD"] == "password":
                config_username = self.container.conf["USERNAME"]
                config_password = self.container.conf["PASSWORD"]
        except (AttributeError, KeyError, TypeError):
            pass

        # optparser output is passed via *args (args) and **kwargs (opts)
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        # None is not taken from the default in kwargs.pop
        # but it's the actual value of kwargs["username"]
        if username is None:
            username = config_username
        # same here
        if password is None:
            password = config_password

        if len(args) != 2:
            self.parser.error("You must specify an operating system and tag")

        # login to the hub
        self.set_hub(username, password)
        kwargs = {
            "owner_name": username,
            "label": "Pull builds for {0}/{1}".format(args[0], args[1]),
            "method": "PullBuilds",
            "args": {
                "os": args[0],
                "tag": args[1],
            },
            "weight": 0,
            "arch_name": "noarch",
            "channel_name": "default",
        }

        self.hub.client.create_task(kwargs)
