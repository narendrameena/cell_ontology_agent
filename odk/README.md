# CellScribe → ROBOT → ODK round-trip

This directory scaffolds the paper's Fig 7 workflow into an ODK-style edit cycle:
a CellScribe draft becomes real OWL via **ROBOT**, is reasoned with **ELK**, and is
then reviewed by a curator before `robot merge` into an Ontology Development Kit
(ODK) edit file and a Pull Request. CellScribe never commits — it drafts.

```
issue / cluster ─▶ cellscribe curate ─▶ ROBOT template ─▶ candidate.owl ─▶ ELK reason
                                                                              │
                        curator review ◀── candidate.reasoned.owl ◀──────────┘
                              │
                              ▼  (approved)
                    robot merge ─▶ src/ontology/cl-edit.owl ─▶ Pull Request
```

## Run it (needs Java + `../.tools/robot.jar`)

```bash
make term NAME="striatal parvalbumin-positive GABAergic interneuron" \
          MARKERS="GAD1,GAD2,PVALB" LOCATION="striatum" \
          FUNCTIONS="GABA biosynthetic process"
# -> build/candidate.owl  (ROBOT-materialised)
# -> build/candidate.reasoned.owl  (ELK-classified; check for unsatisfiable classes)
```

The generated OWL is a **candidate**: a curator inspects `build/candidate.reasoned.owl`
(and the dossier CellScribe printed), and only then merges it into the ontology's
`-edit` file. In a real ODK repo you would `robot merge --input cl-edit.owl --input
build/candidate.owl --output cl-edit.owl` and open a PR, keeping the human in the loop.
