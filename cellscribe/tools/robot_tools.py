"""Optional ROBOT integration (Java) — template->OWL round-trip and ELK reasoning.

ROBOT (http://robot.obolibrary.org) is the tool the Cell Ontology is actually
built and released with, and it bundles the ELK reasoner. When a JRE and a
robot.jar are present, CellScribe can materialise its ROBOT template into real
OWL and run ELK; otherwise callers fall back gracefully.

Point CELLSCRIBE_ROBOT_JAR at robot.jar (default: <repo>/.tools/robot.jar).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import List, Optional, Tuple

# OBO/RO prefixes needed to parse CURIEs in our templates/axioms
DEFAULT_PREFIXES = [
    "CL: http://purl.obolibrary.org/obo/CL_",
    "UBERON: http://purl.obolibrary.org/obo/UBERON_",
    "GO: http://purl.obolibrary.org/obo/GO_",
    "PR: http://purl.obolibrary.org/obo/PR_",
    "RO: http://purl.obolibrary.org/obo/RO_",
    "BFO: http://purl.obolibrary.org/obo/BFO_",
    "IAO: http://purl.obolibrary.org/obo/IAO_",
    "NCBITaxon: http://purl.obolibrary.org/obo/NCBITaxon_",
    "CELLSCRIBE: https://w3id.org/cellscribe/",
]


def _java() -> Optional[str]:
    return shutil.which("java")


def robot_jar() -> Optional[str]:
    j = os.environ.get("CELLSCRIBE_ROBOT_JAR")
    if j and os.path.exists(j):
        return j
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cand = os.path.join(repo, ".tools", "robot.jar")
    return cand if os.path.exists(cand) else None


def robot_available() -> bool:
    return bool(_java() and robot_jar())


def run_robot(args: List[str], timeout: int = 180) -> Tuple[int, str, str]:
    """Run `java -jar robot.jar <args>` -> (returncode, stdout, stderr)."""
    jar = robot_jar()
    if not (_java() and jar):
        return (127, "", "ROBOT/Java unavailable")
    try:
        p = subprocess.run([_java(), "-jar", jar] + list(args),
                           capture_output=True, text=True, timeout=timeout)
        return (p.returncode, p.stdout, p.stderr)
    except Exception as e:  # noqa: BLE001
        return (1, "", str(e))


def _prefix_args(prefixes: Optional[List[str]]) -> List[str]:
    args = []
    for p in (prefixes or DEFAULT_PREFIXES):
        args += ["--prefix", p]
    return args


def _iri(curie: str) -> str:
    return "<http://purl.obolibrary.org/obo/%s>" % curie.replace(":", "_")


def template_to_owl(template_tsv: str, out_owl: str,
                    prefixes: Optional[List[str]] = None,
                    input_owl: Optional[str] = None) -> Tuple[bool, str]:
    """Materialise a ROBOT template TSV into OWL. `input_owl` supplies entity type
    declarations so ROBOT can parse CURIE-based class expressions. Returns (ok, msg)."""
    if not robot_available():
        return (False, "ROBOT unavailable")
    args = ["template"]
    if input_owl:
        args += ["--input", input_owl]
    args += ["--template", template_tsv] + _prefix_args(prefixes) + ["--output", out_owl]
    rc, out, err = run_robot(args)
    ok = rc == 0 and os.path.exists(out_owl) and os.path.getsize(out_owl) > 0
    return (ok, (err or out or "")[:400])


def reason(owl_in: str, owl_out: str, reasoner: str = "ELK",
           timeout: int = 240) -> Tuple[bool, str]:
    """Run a reasoner over an ontology. Returns (coherent, message).

    ROBOT `reason` fails (non-zero) if the ontology is incoherent (has an
    unsatisfiable class) — which is exactly how taxon-constraint violations and
    contradictory axioms are detected.
    """
    if not robot_available():
        return (False, "ROBOT unavailable")
    rc, out, err = run_robot(
        ["reason", "--reasoner", reasoner, "--input", owl_in, "--output", owl_out],
        timeout=timeout)
    return (rc == 0, (err or out or "")[:600])


_PROP_LABEL = {"BFO:0000050": "part of", "RO:0002215": "capable of",
               "RO:0002104": "has plasma membrane part"}


def _differentia(dossier):
    """[(property_curie, filler_curie, filler_label)] over grounded ontology terms."""
    out = []
    if dossier.location and dossier.location.curie.startswith("UBERON:"):
        out.append(("BFO:0000050", dossier.location.curie, dossier.location.label))
    for f in dossier.functions:
        if f.curie.startswith("GO:"):
            out.append(("RO:0002215", f.curie, f.label))
    for s in dossier.surface:
        if s.curie.startswith("PR:"):
            out.append(("RO:0002104", s.curie, s.label))
    return out


def robot_template_curie(dossier) -> str:
    """A ROBOT template that materialises with a declarations seed. The equivalence
    expression uses LABELS (ROBOT template Manchester resolves entities by label);
    bare gene markers are not OWL classes, so they are carried as an annotation."""
    p = dossier.parent
    genus_lbl = p.label if (p and p.curie.startswith("CL:")) else "cell"
    expr = "'%s'" % genus_lbl
    for _prop, _fill, flabel in _differentia(dossier):
        expr += " and ('%s' some '%s')" % (_PROP_LABEL[_prop], flabel)
    label = dossier.official_name or dossier.request.name
    defn = dossier.definition.textual if dossier.definition else ""
    markers = "|".join(dossier.panel.markers) if dossier.panel else ""
    header = ["ID", "LABEL", "TYPE", "DEFINITION", "EQUIVALENT", "MARKERS"]
    directive = ["ID", "A rdfs:label", "TYPE", "A IAO:0000115", "EC %", "A CELLSCRIBE:marker SPLIT=|"]
    row = ["CL:NEW_0000001", label, "owl:Class", defn, expr, markers]
    return "\n".join("\t".join(r) for r in (header, directive, row))


RDFS_LABEL = "<http://www.w3.org/2000/01/rdf-schema#label>"


def _seed_declarations(dossier) -> str:
    """Minimal OWL declaring the referenced entities' types AND labels, so ROBOT's
    template Manchester parser can resolve the label-based equivalence expression."""
    p = dossier.parent
    genus = p.curie if (p and p.curie.startswith("CL:")) else "CL:0000000"
    genus_lbl = p.label if (p and p.curie.startswith("CL:")) else "cell"
    classes = [(genus, genus_lbl)]
    props = {}
    for prop, fill, flabel in _differentia(dossier):
        classes.append((fill, flabel))
        props[prop] = _PROP_LABEL[prop]
    lines = ["Prefix(owl:=<http://www.w3.org/2002/07/owl#>)",
             "Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)",
             "Ontology(<https://w3id.org/cellscribe/seed>"]
    for cur, lbl in classes:
        lines.append("  Declaration(Class(%s))" % _iri(cur))
        lines.append('  AnnotationAssertion(%s %s "%s")' % (RDFS_LABEL, _iri(cur), lbl.replace('"', "'")))
    for cur, lbl in props.items():
        lines.append("  Declaration(ObjectProperty(%s))" % _iri(cur))
        lines.append('  AnnotationAssertion(%s %s "%s")' % (RDFS_LABEL, _iri(cur), lbl))
    lines.append(")")
    return "\n".join(lines)


def materialize_dossier(dossier, out_owl: str, reason_after: bool = False) -> Tuple[bool, str]:
    """Round-trip a dossier through ROBOT: build a valid template + a declarations
    seed, `robot template` into OWL, optionally reason with ELK. Returns (ok, message)."""
    if not robot_available():
        return (False, "ROBOT unavailable")
    import tempfile
    tmp = tempfile.mkdtemp()
    tsv = os.path.join(tmp, "term.robot.tsv")
    seed = os.path.join(tmp, "seed.ofn")
    with open(tsv, "w") as fh:
        fh.write(robot_template_curie(dossier))
    with open(seed, "w") as fh:
        fh.write(_seed_declarations(dossier))
    ok, msg = template_to_owl(tsv, out_owl, input_owl=seed)
    if ok and reason_after:
        rout = os.path.join(tmp, "reasoned.owl")
        coherent, rmsg = reason(out_owl, rout, reasoner="ELK")
        msg = "template->OWL ok; ELK coherent=%s. %s" % (coherent, rmsg[:150])
    return (ok, msg)
