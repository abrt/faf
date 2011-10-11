from __future__ import absolute_import
import argparse
import sys
import logging

class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, description=None, prog=sys.argv[0], usage=None,
                 add_help=True, argument_default=None, prefix_chars="-"):
        argparse.ArgumentParser.__init__(self,
                                         epilog="See 'man %(prog)s' for more information.",
                                         description=description, prog=prog, usage=usage,
                                         add_help=add_help, argument_default=argument_default,
                                         prefix_chars=prefix_chars)
        self.add_argument("-v", "--verbose", action="store_const", const=1, dest="verbose", default=0)
        self.add_argument("-vv", action="store_const", const=2, dest="verbose")
        self.add_argument("-vvv", action="store_const", const=3, dest="verbose")

    def parse_args(self, args=None, namespace=None):
        args = argparse.ArgumentParser.parse_args(self, args=args, namespace=namespace)
        if args.verbose == 0:
            level = logging.WARNING
        elif args.verbose == 1:
            level = logging.INFO
        elif args.verbose == 2:
            level = logging.DEBUG
        elif args.verbose == 3:
            level = logging.NOTSET
        else:
            sys.stderr.write("Invalid verbosity level: {0}".format(args.verbose))
            exit(1)
        logging.basicConfig(level=level)
        return args
