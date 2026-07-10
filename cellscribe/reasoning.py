"""Reasoning over drafted definitions (roadmap: EL reasoner to auto-classify + verify).

Two layers, matching the tool's design:
  * a Python STRUCTURAL check that always runs (validates grounding of the axiom);
  * an optional ELK check via ROBOT that materialises the equivalence axiom into
    real OWL and asks the reasoner whether it is coherent and how the term
    classifies — and can demonstrate the incoherency detection that underpins
    taxon-constraint verification (Tan et al. 2026, Methods).

Two grades of reasoning are offered:
  * `classify()` reasons over the self-contained draft (genus + differentia) — fast,
    no ontology download, verifies the axiom is satisfiable and subsumes its genus;
  * `classify_against_cl()` merges the candidate into a real CL import module
    (e.g. `cl-base.owl`) and runs ELK over the whole ontology, so it reports the
    term's inferred CL superclasses AND whether it is EQUIVALENT to an existing CL
    class (duplicate detection) — the payoff a self-contained draft cannot give.
"""
from __future__ import annotations

import os
import re
import tempfile
from typing import Any, Dict, List

from .tools.robot_tools import reason, robot_available, run_robot

OBO = "http://purl.obolibrary.org/obo/"
NEW = "https://w3id.org/cellscribe/NEW_0000001"


def _iri(curie: str) -> str:
    return "<%s%s>" % (OBO, curie.replace(":", "_"))


def _obo_to_curie(tok: str) -> str:
    """`obo:CL_0000099` (ROBOT functional-syntax prefixed name) -> `CL:0000099`."""
    m = re.match(r"obo:([A-Za-z]+)_(\w+)$", tok)
    return "%s:%s" % (m.group(1), m.group(2)) if m else tok


def structural_check(dossier) -> Dict[str, Any]:
    """Always-on: is the axiom built from grounded, well-typed CURIEs?"""
    issues = []
    p = dossier.parent
    if not (p and p.curie.startswith("CL:")):
        issues.append("genus is not a grounded CL class — axiom cannot classify")
    if dossier.location and not dossier.location.curie.startswith("UBERON:"):
        issues.append("location is not a Uberon class")
    for f in dossier.functions:
        if not f.curie.startswith("GO:"):
            issues.append("function %s is not a GO class" % f.label)
    return {"ok": not issues, "issues": issues}


def owl_from_dossier(dossier) -> str:
    """Functional-syntax OWL for the drafted term's equivalence axiom + declarations."""
    genus = dossier.parent.curie if (dossier.parent and dossier.parent.curie.startswith("CL:")) else "CL:0000000"
    decls, conj = set(), []
    decls.add(_iri(genus)); decls.add(_iri("CL:0000000"))
    conj.append(_iri(genus))
    if dossier.location and dossier.location.curie.startswith("UBERON:"):
        decls.add(_iri(dossier.location.curie))
        conj.append("ObjectSomeValuesFrom(%s %s)" % (_iri("BFO:0000050"), _iri(dossier.location.curie)))
    for f in dossier.functions:
        if f.curie.startswith("GO:"):
            decls.add(_iri(f.curie))
            conj.append("ObjectSomeValuesFrom(%s %s)" % (_iri("RO:0002215"), _iri(f.curie)))
    for s in dossier.surface:
        if s.curie.startswith("PR:"):
            decls.add(_iri(s.curie))
            conj.append("ObjectSomeValuesFrom(%s %s)" % (_iri("RO:0002104"), _iri(s.curie)))
    obj_props = [_iri("BFO:0000050"), _iri("RO:0002215"), _iri("RO:0002104")]
    lines = ["Prefix(owl:=<http://www.w3.org/2002/07/owl#>)",
             "Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)",
             "Ontology(<https://w3id.org/cellscribe/draft>"]
    lines.append("  Declaration(Class(<%s>))" % NEW)
    for d in sorted(decls):
        lines.append("  Declaration(Class(%s))" % d)
    for op in obj_props:
        lines.append("  Declaration(ObjectProperty(%s))" % op)
    if genus != "CL:0000000":
        lines.append("  SubClassOf(%s %s)" % (_iri(genus), _iri("CL:0000000")))
    body = _iri(genus) if len(conj) == 1 else "ObjectIntersectionOf(%s)" % " ".join(conj)
    lines.append("  EquivalentClasses(<%s> %s)" % (NEW, body))
    lines.append(")")
    return "\n".join(lines)


def classify(dossier, timeout: int = 180) -> Dict[str, Any]:
    """Run ELK over the drafted axiom: coherent? classifies under genus?"""
    struct = structural_check(dossier)
    result = {"structural": struct, "reasoner": None}
    if not robot_available():
        result["reasoner"] = {"available": False,
                              "note": "install a JRE + robot.jar for ELK reasoning"}
        return result
    tmp = tempfile.mkdtemp()
    ofn = os.path.join(tmp, "draft.ofn"); out = os.path.join(tmp, "reasoned.ofn")
    with open(ofn, "w") as fh:
        fh.write(owl_from_dossier(dossier))
    coherent, msg = reason(ofn, out, reasoner="ELK", timeout=timeout)
    genus = dossier.parent.curie if dossier.parent else "CL:0000000"
    result["reasoner"] = {"available": True, "coherent": coherent,
                          "classifies_under_genus": coherent and bool(dossier.parent),
                          "genus": genus, "message": msg}
    return result


# ------------------------------------------------ classification against real CL
def _candidate_owl_for_merge(dossier) -> str:
    """The candidate's equivalence axiom in functional-syntax OWL, referencing the
    REAL genus + differentia CURIEs and nothing else — so it can be merged into a
    CL import module and classified by ELK against the whole ontology (no self-
    contained root collapse; CL supplies the real superclass hierarchy)."""
    genus = dossier.parent.curie
    conj = [_iri(genus)]
    decls = {_iri(genus)}
    if dossier.location and dossier.location.curie.startswith("UBERON:"):
        decls.add(_iri(dossier.location.curie))
        conj.append("ObjectSomeValuesFrom(%s %s)" % (_iri("BFO:0000050"), _iri(dossier.location.curie)))
    for f in dossier.functions:
        if f.curie.startswith("GO:"):
            decls.add(_iri(f.curie))
            conj.append("ObjectSomeValuesFrom(%s %s)" % (_iri("RO:0002215"), _iri(f.curie)))
    for s in dossier.surface:
        if s.curie.startswith("PR:"):
            decls.add(_iri(s.curie))
            conj.append("ObjectSomeValuesFrom(%s %s)" % (_iri("RO:0002104"), _iri(s.curie)))
    props = [_iri("BFO:0000050"), _iri("RO:0002215"), _iri("RO:0002104")]
    lines = ["Prefix(owl:=<http://www.w3.org/2002/07/owl#>)",
             "Ontology(<https://w3id.org/cellscribe/candidate>",
             "  Declaration(Class(<%s>))" % NEW]
    lines += ["  Declaration(Class(%s))" % c for c in sorted(decls)]
    lines += ["  Declaration(ObjectProperty(%s))" % p for p in props]
    body = conj[0] if len(conj) == 1 else "ObjectIntersectionOf(%s)" % " ".join(conj)
    lines.append("  EquivalentClasses(<%s> %s)" % (NEW, body))
    lines.append(")")
    return "\n".join(lines)


def _parse_classification(reasoned_ofn: str) -> Dict[str, Any]:
    """Read ELK's inferred axioms for the NEW class out of a reasoned functional-
    syntax ontology: its direct named superclasses and any named class it was
    inferred EQUIVALENT to (i.e. the proposed term already exists in CL)."""
    txt = open(reasoned_ofn).read()
    labels = {}
    for m in re.finditer(r'AnnotationAssertion\(rdfs:label\s+(obo:\S+)\s+"([^"]*)"', txt):
        labels[_obo_to_curie(m.group(1))] = m.group(2)
    new = re.escape("<%s>" % NEW)
    supers: List[Dict[str, str]] = []
    equivs: List[Dict[str, str]] = []
    named = re.compile(r"^obo:[A-Za-z]+_\w+$")
    for ln in txt.splitlines():
        s = ln.strip()
        m = re.match(r"SubClassOf\(%s\s+(\S+)\)$" % new, s)
        if m and named.match(m.group(1)):
            cur = _obo_to_curie(m.group(1))
            supers.append({"curie": cur, "label": labels.get(cur, "")})
            continue
        # equivalence can be rendered NEW-first or CL-first; a bare named operand = redundancy
        m = re.match(r"EquivalentClasses\((?:%s\s+(obo:\S+)|(obo:\S+)\s+%s)\)$" % (new, new), s)
        if m:
            tok = m.group(1) or m.group(2)
            if tok and named.match(tok):
                cur = _obo_to_curie(tok)
                equivs.append({"curie": cur, "label": labels.get(cur, "")})
    # de-dup, keep order
    def _uniq(xs):
        seen, out = set(), []
        for x in xs:
            if x["curie"] not in seen:
                seen.add(x["curie"]); out.append(x)
        return out
    return {"inferred_superclasses": _uniq(supers), "equivalent_to": _uniq(equivs)}


def classify_against_cl(dossier, cl_owl: str, timeout: int = 600) -> Dict[str, Any]:
    """Full classification: merge the candidate's equivalence axiom into a real CL
    import module (e.g. `cl-base.owl`) and run ELK over the whole ontology. Reports
    whether the axiom is coherent, the term's inferred CL superclasses, and — the
    payoff a self-contained draft cannot give — whether ELK finds it EQUIVALENT to
    an existing CL class (redundancy / duplicate detection before a term is minted).
    """
    struct = structural_check(dossier)
    res: Dict[str, Any] = {"structural": struct, "available": False, "cl_owl": cl_owl}
    if not robot_available():
        res["note"] = "install a JRE + robot.jar for ELK classification"
        return res
    if not (cl_owl and os.path.exists(cl_owl)):
        res["note"] = "CL ontology not found at %r (download cl-base.owl)" % cl_owl
        return res
    if not (dossier.parent and dossier.parent.curie.startswith("CL:")):
        res["note"] = "no grounded CL genus — cannot classify against CL"
        return res
    tmp = tempfile.mkdtemp()
    cand = os.path.join(tmp, "candidate.ofn")
    out = os.path.join(tmp, "classified.ofn")
    with open(cand, "w") as fh:
        fh.write(_candidate_owl_for_merge(dossier))
    # merge CL + candidate, then reason — chained in one ROBOT invocation.
    rc, so, se = run_robot(["merge", "--input", cl_owl, "--input", cand,
                            "reason", "--reasoner", "ELK",
                            "--axiom-generators", "subclass equivalentclass",
                            "--output", out], timeout=timeout)
    if rc != 0 or not os.path.exists(out):
        # non-zero from `reason` => an unsatisfiable class (e.g. a taxon-constraint
        # or disjointness violation the draft introduced): a real, useful signal.
        res.update({"available": True, "coherent": False,
                    "note": "ELK reported an incoherency: " + (se or so or "")[:300]})
        return res
    parsed = _parse_classification(out)
    redundant = bool(parsed["equivalent_to"])
    res.update({"available": True, "coherent": True, "redundant_with_existing": redundant,
                "disposition": "DUPLICATE_OF_EXISTING" if redundant else "NOVEL_placed_under_CL",
                **parsed})
    return res


# --------------------------------------------------------------------------- taxon
def taxon_incoherence_demo(timeout: int = 120) -> Dict[str, Any]:
    """Self-contained ELK demo of the incoherency detection that taxon constraints
    rely on: two disjoint taxa + a class asserted to be in both -> unsatisfiable.

    Mirrors the never_in_taxon -> DisjointWith mechanism (Tan et al. 2026, Methods):
    if a cell type is constrained never_in_taxon A yet ends up in_taxon A, the
    reasoner reports an incoherency, letting a curator fix it before commit.
    """
    if not robot_available():
        return {"available": False, "note": "ROBOT/Java required"}
    # 'cell in Chordata' vs 'cell in Arthropoda' are disjoint (a cell is in one taxon).
    # A cell asserted to be in both -> unsatisfiable. Pure-EL (DisjointClasses +
    # SubClassOf), which ELK supports; this is what never_in_taxon expands to.
    A = _iri("NCBITaxon:7711")   # in Chordata
    B = _iri("NCBITaxon:6656")   # in Arthropoda
    X = "<https://w3id.org/cellscribe/BadCell>"
    ofn = "\n".join([
        "Prefix(owl:=<http://www.w3.org/2002/07/owl#>)",
        "Ontology(<https://w3id.org/cellscribe/taxon-demo>",
        "  Declaration(Class(%s))" % A, "  Declaration(Class(%s))" % B,
        "  Declaration(Class(%s))" % X,
        "  DisjointClasses(%s %s)" % (A, B),
        # asserted in BOTH disjoint taxa -> the taxon-constraint violation
        "  SubClassOf(%s %s)" % (X, A),
        "  SubClassOf(%s %s)" % (X, B),
        ")"])
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "taxon.ofn"); out = os.path.join(tmp, "r.ofn")
    with open(src, "w") as fh:
        fh.write(ofn)
    coherent, msg = reason(src, out, reasoner="ELK", timeout=timeout)
    return {"available": True, "incoherency_detected": (not coherent),
            "message": msg[:300]}
