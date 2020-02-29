#!/bin/env python
from prov.model import ProvDocument, ProvEntity, ProvUsage, ProvGeneration
from prov.identifier import Namespace
from prov.dot import prov_to_dot
from treelib import Node, Tree, exceptions as texp
from glob import glob
import os


class ProvProject(ProvDocument):
    """
    A class for describing provence structures within a project.
    """

    def __init__(self, homedir=None):
        super().__init__()
        ## pre-init prefix/namespaces
        #        ns = self._namespaces
        self.add_namespace("rdata", "rdata")
        self.add_namespace("rcode", "rcode")
        self.add_namespace("pycode", "pycode")
        self.add_namespace("map", "map")
        self.add_namespace("biom", "biom")
        self.add_namespace("txt", "txt")
        self.add_namespace("yml", "yml")
        self.add_namespace("pdf", "pdf")

        self.home_dir = os.path.realpath(homedir)

    def check(self):
        """
        Check that records in the document correspond to actual files
        """
        for record in self.get_records():
            if isinstance(record, ProvEntity):
                relpath = record.label.localpart
                abspath = os.path.join(self.home_dir, relpath)
                assert os.path.exists(abspath), (
                    "Record: %s doesn't exist" % record.label
                )
