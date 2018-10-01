import os
import sys

# alter path so we can import from webfaftests in this directory
test_webfaf_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, test_webfaf_path)
os.environ["PATH"] = "{0}:{1}".format(test_webfaf_path, os.environ["PATH"])
