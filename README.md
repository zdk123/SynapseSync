# SynapseSync #

A lightweight python package for syncing files/hyperlinks -
with internal provenance structures -  between various data stores
and a [Synapse](http://synapse.org) project.


The Synapse python client does allow [syncing](https://python-docs.synapse.org/build/html/synapseutils.html)
files or hyperlinks to Synapse from a manifest, but there is no easy way to sync entire project folders from remote storage.
Additionally, to downloading files via [get](https://python-docs.synapse.org/build/html/Client.html#synapseclient.Synapse.get)
methods, only standard, unsigned URL requests are possible.

This package was designed to work around in these gaps to sync with Synapse
for a microbiome bioinformatics project [manuscript](https://github.com/zdk123/SpiecEasiSLR_manuscript).
It might be useful for other purposes or it may be obsolete as [issues](https://github.com/Sage-Bionetworks/synapsePythonClient/issues)
are addressed by the excellent [Synapse team](https://sagebionetworks.jira.com/browse/SYNPY-998).

## Backends ##

Currently, only Google drive is supported, via the pydrive package.

## Basic Usage ##

This small [R project](https://drive.google.com/open?id=1Eh6jWGAUJGXaJHhyFrIpdFTmB0oVQViq) first saves and plots the iris dataset in R (`make_iris.R`). Then we fit a decision tree, saved the model as an RData object and the tree visualization (`fit_iris.R`).

Here is the Google Drive directory tree:
```
.
└── iris/
    ├── make_iris.R
    ├── fit_iris.R
    ├── data/
    │   └── iris.txt
    ├── figures/
    │   ├── iris.pdf
    │   └── irisrpart.pdf
    └── tmpdata/
        └── irisrpart.RData
```

To sync via `pydrive` client, we need to activate [the Drive API and get the credentials](https://developers.google.com/drive/api/v3/quickstart/python),
which I will assumed are saved at `~/client_secrets.json`.

```py
from synapsesync import GDriveProject

## Setup Google drive project
proj = GDriveProject("~/client_secrets.json")
 ## will launch login browser:
proj.set_project("ExampleProject")
proj.add_subproject({"iris"})
```

Create a synapse account and set up a Synapse API key, and save the config file at the default location: `~/.synapseConfig`. Create the "ExampleProject" project.

```py
from synapsesync import SynpaseProject

# Sync to synapse
syn = SynpaseProject("ExampleProject")
dtree = proj.get_project_tree()
syn.create_from_project_tree(dtree)
```

Now you should have an iris "subproject" and all subdirectories synced.

Before finalizing the file "upload", we will establish file
provenance relationships This is based on the `prov` python package. This supports a wider array of relationships than Synapse, but both are based on the W3C PROV data model.

```py
from synapsesync import ProvProject

iris = ProvProject("ExampleProject/iris")
make = iris.entity("rcode:make_iris.R")
fit = iris.entity("rcode:fit_iris.R")
irisdata = iris.entity("txt:data/iris.txt")
irismod = iris.entity("rdata:tmpdata/irisrpart.RData")
```

Entities associated with a project are organized around namespaces.
`rcode` and `txt` is a built-in namespace, but others can be added:
```py
iris.add_namespace("pdf", "pdf")
pairplot = iris.entity("pdf:figures/iris.pdf")
treeplot = iris.entity("pdf:figures/irisrpart.pdf")
```

If a copy of ExampleProject exists locally, and the `ProvProject`
constructor was given a location that actually exists
(i.e. `ExampleProject/iris` exists under the current working directory) then you can check to make sure the entities also exist as files:
```py
iris.check()
```
This will throw an error if any files are missing.

We can now establish provenance relationships between the entities: see the [prov tutorial](https://trungdong.github.io/prov-python-short-tutorial.html) for more details.

```py
iris.wasGeneratedBy(irisdata, make)
iris.wasGeneratedBy(pairplot, make)
iris.used(fit, irisdata)
iris.wasGeneratedBy(irismod, fit)
iris.wasGeneratedBy(treeplot, fit)
```

Finally, complete the project syncing:
```py
syn.store_files({"iris": iris})
```

The example synapse project can be seen here: https://www.synapse.org/#!Synapse:syn21306223/files


# Syncing from Synapse #

This package contains a customized request Session class for pulling
down synapse data hosted on Google drive.

This is needed even for public Google drive links,
since Google redirects pages to confirm that a user wants to download large files. See this [stackoverflow answer](https://stackoverflow.com/questions/25010369/wget-curl-large-file-from-google-drive/39225039#39225039) for details.

```py
from synapsesync import SynpaseProject, GDriveSession
from synapseutils.sync import syncFromSynapse

## If credentials are stored at ~/.synapseConfig
syn = SynpaseProject("ExampleProject")

## OR ##
## email/password login:
syn = SynpaseProject()
syn.login("<user>", "<pass>")
syn.set_project("ExampleProject")

## Continue:
syn.set_session(GDriveSession())
syncFromSynapse(syn, "syn21306223", path="./ExampleProject")
```