# -*- coding: utf-8 -*-
import kobo.client
import pyfaf
import sys
from pyfaf.storage import Database, Package

class Llvm_Build(kobo.client.ClientCommand):
    """Rebuilds a RPM with LLVM"""
    enabled = True
    admin = False # admin type account required

    def options(self):
        # specify command usage
        # normalized name contains a lower-case class name with underscores converted to dashes
        self.parser.usage = "%%prog %s [options] os tag srpm_id" % self.normalized_name
        self.parser.add_option("--arch", default="x86_64", help="Architecture")
        self.parser.add_option("--channel", default="default", help="Channel")
        self.parser.add_option("--label", default=None, help="Label")

    def run(self, *args, **kwargs):
        if len(args) != 3:
            self.parser.error(self.parser.usage.replace("%prog", sys.argv[0]))

        os, tag, srpm_id = args

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
        arch = kwargs.pop("arch")
        channel = kwargs.pop("channel")
        label = kwargs.pop("label")

        if label is None:
            db = Database()
            srpm = db.session.query(Package).filter(Package.id == srpm_id).one()
            label = srpm.nvr()

        # None is not taken from the default in kwargs.pop
        # but it's the actual value of kwargs["username"]
        if username is None:
            username = config_username
        # same here
        if password is None:
            password = config_password

        # login to the hub
        self.set_hub(username, password)
        task = {
            "owner_name": username,
            "label": label,
            "method": "LlvmBuild",
            "args": {
              "os": os,
              "tag": tag,
              "srpm_id": srpm_id,
            },
            "weight": 0,
            "arch_name": arch,
            "channel_name": channel,
        }

        self.hub.client.create_task(task)
