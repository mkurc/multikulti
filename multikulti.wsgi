import os, sys
PROJECT_DIR = os.path.join(os.path.dirname(path.realpath(__file__)), "multikulti") # TODO mozliwe ze to blad

sys.path.append(PROJECT_DIR)
from multikulti import app as application
