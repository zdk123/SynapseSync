#!/bin/env python
from treelib import Node, Tree, exceptions as texp
from synapseclient import Synapse, Entity, Project, Folder, File, Link
from synapseclient import Activity
from synapseclient.exceptions import SynapseHTTPError
from typing import Set, List, Dict, Tuple, Sequence, Union, Type
from requests import Session
from .gdriveproject import GDriveTree, GDriveProject
from .gdrivesession import GDriveSession
from .projectprov import *
import re, os


class SynpaseProject(Synapse):
    """
    Wrapper class for the Synapse python client.
    Contains methods for syncing file and provenence data between systems.
    """

    def __init__(self, project: str, *args, **kwargs):
        # Set up synapse client
        super().__init__(*args, **kwargs)

        try:
            self.login()
        except Exception as e:
            print("Couldn't login using default credentials file")

        self.project = self.store(Project(project))

    def create_folder(self, *args, **kwargs) -> Folder:
        return self.store(Folder(*args, **kwargs))

    def create_file(self, *args, **kwargs) -> File:
        ## Don't store files until acitity relationships can be determined
        return File(*args, **kwargs)

    def set_session(self, session: Type[Session]):
        ## Overwrite default request Session
        self._requests_session = session

    # def get(self, entity, rename: bool = True, **kwargs):
    #     out = super().get(entity, **kwargs)
    #     try:
    #         assert length(out.files) == 1
    #         ## google drive links != file name on synapse
    #         src = os.path.join(out.cacheDir, out.files[0])
    #         dst = os.path.join(out.cacheDir, out.name)
    #         os.rename(src, dst)
    #         out.files[0] = out.name
    #     except AssertionError:
    #         pass
    #     return out

    def get_activity(self, entity: Entity, version=None) -> Activity:
        try:
            act = self.getProvenance(entity, version)
        except (SynapseHTTPError, ValueError):
            act = Activity()
        return act

    def create_from_project_tree(self, dtree: Tree):
        ## dispatch methods based on class
        self._project_tree = dtree

        if isinstance(self._project_tree, GDriveTree):
            self._create_from_gdrivetree()
        dtree.show(idhidden=False)

    def _create_from_gdrivetree(self, id: str = None):
        ## start at root, recursively add children
        if id is None:
            ## attach project to root
            id = self._project_tree.root
            n = self._project_tree.get_node(id)
            n.data = self.project
        else:
            n = self._project_tree.get_node(id)
        children = self._project_tree.children(id)

        for child in children:
            if child.is_file():
                ## attach fake file name to end of externalURL: hacky way to get around
                ## that synapse uses a url split to determine the name to "download file as"
                ##`` https://github.com/Sage-Bionetworks/synapsePythonClient/blob/9d618c3015c380ebf5098fc706f0c022b685ccc8/synapseclient/client.py#L1901
                ## TODO: raise this as an issue.
                file = self.create_file(
                    externalURL=child.gdrivefile["webContentLink"] + "&/" + child.tag,
                    path=child.tag,
                    name=child.tag,
                    parent=n.data.id,
                    synapseStore=False,
                )
                child.data = file
            else:
                name = child.identifier if child.tag == "subproject" else child.tag
                folder = self.create_folder(name=name, parent=n.data.id)
                child.data = folder
                self._create_from_gdrivetree(child.identifier)

    def store_files(self, provdict: Dict[str, ProvProject] = {}):
        """
        Store synapse files while mapping provenence relationships if they exist
        """
        self._provdict = provdict
        for k, prov in provdict.items():
            subtree = self._project_tree.subtree(k)
            # self._activities[k] = []
            for record in prov.get_records():
                if record.is_relation():
                    self.store_with_activity(record, subtree)

        ## TODO: store rest of the files
        for n in self._project_tree.leaves():
            if n.is_file():
                try:
                    synid = n.data.id
                except AttributeError:
                    ## No activity relationship for this file exists, store here:
                    self.store(n.data)

    @classmethod
    def entity_to_id(cl, entity: ProvEntity, tree: Tree) -> str:
        """
        convert a provenence entity to a [leaf] node identifier of a tree.
        tree: can be a project or subproject tree
        """
        try:
            epath = entity.localpart.split("/")
        except AttributeError:
            epath = entity.identifier.localpart.split("/")
        epath = ["project", "subproject"] + epath
        filtfun = lambda nodeli: all([n.tag in epath for n in nodeli])
        nodesli = list(tree.filter_to_leaves(filtfun))
        idli = [nli[-1].identifier for nli in nodesli]
        assert len(idli) == 1, "Error: Multiple paths %s match entities" % idli
        return idli[0]

    def store_with_activity(
        self, record: Union[ProvGeneration, ProvUsage], subtree: Tree
    ) -> Activity:
        rfrom = record.formal_attributes[0][1]
        rto = record.formal_attributes[1][1]
        nfrom = subtree.get_node(self.entity_to_id(rfrom, subtree))
        nto = subtree.get_node(self.entity_to_id(rto, subtree))
        type = record.get_type().localpart
        # nfrom.data = self.get(nfrom.data.id, downloadFile=False)
        activity = self.get_activity(nfrom.data)
        nto.data = self.store(nto.data, forceVersion=False)
        if type == "Usage":
            activity.used(nto.data)
            activity["name"] = activity.get("name", "used")
        elif type == "Generation":
            activity.used(nto.data, wasExecuted=True)
            activity["name"] = activity.get("name", "generated")
        else:
            activity["name"] = activity.get("name", "notype")

        nfrom.data = self.store(nfrom.data, activity=activity, forceVersion=False)
        return activity
