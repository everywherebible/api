"""Generate HTML for Everywhere Bible's API."""

from argparse import ArgumentParser
from importlib import import_module
from os.path import join, dirname
import sys

from mkdirs import mkdirs


def main(argv):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--translation', default='kjv',
            help='Translation (KJV is default and the only supported)')
    parser.add_argument('outdir', metavar='OUTDIR',
            help='The directory to output the files (1 file per chapter)')
    args = parser.parse_args()
    generate = import_module('everywherebible.%s.generate' % args.translation)
    thisdir = dirname(sys.modules[__name__].__file__)
    mkdirs(args.outdir)
    generate.generate(args.outdir)


if __name__ == '__main__':
    main(sys.argv)
