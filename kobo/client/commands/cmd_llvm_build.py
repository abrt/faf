# -*- coding: utf-8 -*-


import kobo.client
import pyfaf

class Llvm_Build(kobo.client.ClientCommand):
    """command description"""
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
        # optparser output is passed via *args (args) and **kwargs (opts)
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        if len(args) != 1:
            self.parser.error("usage: rpm_id")

        srpm = pyfaf.run.cache_get("fedora-koji-rpm", args[0])

        # login to the hub
        self.set_hub(username, password)
        kwargs = {
            "owner_name": username,
            "label": srpm.nvr(),
            "method": "LlvmBuild",
            "args": {
                "srpm_id": args[0],
            },
            "weight": 0,
            "arch_name": "x86_64",
            "channel_name": "default",
        }

        self.hub.client.create_task(kwargs)
