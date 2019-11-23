#!/bin/env python

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFile
from treelib import Node, Tree, exceptions as texp
from synapseclient import Synapse, Entity, Project, Folder, File, Link
from typing import Set, List, Dict, Tuple, Sequence, Union
import re, os


class GDriveNode(Node):
    def __init__(self, gdrivefile: GoogleDriveFile, tag=None, id=None, data=None):
        self.gdrivefile = gdrivefile
        id = self.gdrivefile.get("id", None) if id is None else id
        tag = self.gdrivefile.get("title", None) if tag is None else tag
        super().__init__(tag=tag, identifier=id, data=data)

    def is_file(self):
        return "fileSize" in self.gdrivefile


class GDriveTree(Tree):
    def __init__(self, tree=None, deep=False):
        super().__init__(tree, deep, GDriveNode)

    def create_node(self, gdrivefile, tag=None, id=None, parent=None, data=None):
        node = self.node_class(gdrivefile, id=id, tag=tag, data=data)
        try:  ## parent could be a gdrivefile or dict
            parent = parent["title"]
        except KeyError:
            pass
        except TypeError:
            pass
        self.add_node(node, parent)
        return node

    def path_to_leaves(self, tags=True):
        res = super().paths_to_leaves()
        if tags:
            ## translate to tags
            res = [[(id, self.get_node(id).tag) for id in path] for path in res]
        return res

    def filter_to_leaves(self, func):
        """
        returns a path to leaves, asserting that nodes along the path pass
        """
        res = super().paths_to_leaves()
        nodesli = [[self.get_node(id) for id in path] for path in res]
        res = []
        for i, nodes in enumerate(nodesli):
            if func(nodes):
                res.append(nodes)
        return res

    def subtree(self, nid):
        return GDriveTree(super().subtree(nid))


## Mirror google drive links to a hosted synapse project ##
class GDriveProject(GoogleDrive):
    """
    A GoogleDrive derivate class for managing files/directories in a top-level
    or a subdirectory of projects
    """

    def __init__(self, client_config_file: str = None):
        gauth = GoogleAuth()
        gauth.LoadClientConfigFile(client_config_file)
        self._ignorepatt = "^$"
        super().__init__(gauth)  ## super sets self.auth = gauth
        # http = drive.auth.Get_Http_Object()

    def list_children(self, id: str) -> List[GoogleDriveFile]:
        """
        List child files and folders in a subdirectory (id) of client google drive
        """
        query = "'%s' in parents and trashed=false"
        return self.ListFile({"q": query % id}).GetList()

    def list_roots(self) -> List[GoogleDriveFile]:
        """
        List all top-level files and directories in a client google drive
        """
        return self.list_children("root")

    def set_project(self, project: str):
        """
        Set the top level project for the class.

        This needs to corresponds to a top level directory in client google drive
        """
        self._project_str = project
        root_list = self.list_roots()
        self._project = [f for f in root_list if f["title"] == self._project_str]
        assert len(self._project) == 1, "Only 1 top level project is allowed"
        self._project = self._project[0]
        self._project_tree = GDriveTree()
        self._project_tree.create_node(self._project, "project", self._project_str)

    def get_project(self) -> GoogleDriveFile:
        """
        Returns the project as a GoogleDriveFile
        """
        return self._project

    def get_project_tree(self) -> Tree:
        """
        Return the project tree (subprojects if set and all subdirectories)
        """
        return self._project_tree

    def add_subproject(self, subproject: Union[str, Set[str]], grow=True):
        """
        Adds a subproject to the project tree.

        By convention, subprojects are subdirectories within the GoogleDrive project
        without any cross-provenance.
        """
        # initialize or append
        try:
            if isinstance(subproject, set):
                self._subprojects_str.union(subproject)
            else:
                self._subprojects_str.add(subproject)
        except AttributeError:
            if isinstance(subproject, set):
                self._subprojects_str = subproject
            else:
                self._subprojects_str = {subproject}

        children = self.list_children(self._project["id"])
        self._subprojects = [f for f in children if f["title"] in self._subprojects_str]
        for subproj in self._subprojects:
            assert subproj["title"] in self._subprojects_str, (
                "Subproject title missing: %s" % subproj["title"]
            )
        for subproj in self._subprojects:
            try:
                self._project_tree.create_node(
                    subproj, "subproject", subproj["title"], parent=self._project
                )
            except texp.DuplicatedNodeIdError:
                pass
            if grow:
                self.grow_subtree(subproj["title"])

    def set_ignore(self, ignore: Set[str]):
        """
        Set a '.gitignore' style in glob format.
        Matching files/subdirectories patterns will be excluded from the
        project/subproject directory tree.
        """
        ## glob to regex
        def glob2rx(s):
            # s = s.replace("/", "")
            s = re.sub("^/", "^", s)
            s = re.sub("/$", "$", s)
            s = re.sub("^\*\/", "^", s)
            s = re.sub("/\*$", "$", s)
            s = s.replace(".", "\\.")
            s = s.replace("*", ".*")
            return s

        self._ignorepatt = "^(" + "|".join([glob2rx(i) for i in ignore]) + ")$"

    def grow_subtree(self, id: str = None):
        ## TODO: add to add_subproject loop (?)
        tree = self._project_tree
        if id is None:
            id = tree.root
        parent = tree.get_node(id)  ## implicit check that parent exists
        children = self.list_children(parent.gdrivefile["id"])
        for child in children:
            if not re.match(self._ignorepatt, child["title"]):
                tree.create_node(child, parent=id)
                self.grow_subtree(child["id"])

    def grow_subproject(self, subproject: str):
        assert subproject in self._subprojects_str, (
            "%s subproject missing" % subproject["title"]
        )
        self.grow_subtree(subproject)


# ## keep only critical data
# keep = ("*.biom", "*RData", "*xlsx", "*fasta", "*mapping_file.txt", "*/.*")
# with open("../.gitignore", "r") as f:
#     ignore = {i.rstrip() for i in f.readlines()}.difference(keep)
# ignore.add(".*")
#
# proj = GDriveProject("../../client_secrets.json")
# proj.set_project("LRSpiecEasi")
# proj.set_ignore(ignore)
#
# ## TODO: merge these steps ##
# proj.add_subproject(["QMP"])
# proj.grow_subproject("QMP")
#
# ## proj.get_project_tree().show(idhidden=False)
