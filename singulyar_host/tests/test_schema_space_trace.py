# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from singulyar_host.ontology import (Grammar, Instance, RelationType, Space)  # noqa: E402
from singulyar_host.schema_admit import SchemaRegistry  # noqa: E402
from singulyar_host.trace import Trace  # noqa: E402


def make_space():
    g = Grammar(version=1, relation_types={
        "SENDS": RelationType("SENDS", ("PERSON",), ("PERSON",))})
    space = Space(types={"PERSON"}, instances={"a": Instance("a", "PERSON")},
                  relations=set(), constraints=[], grammar=g, schema_version=1)
    return SchemaRegistry(current=g), space


def test_version_monotonic():
    reg, _ = make_space()
    g = Grammar(version=1, relation_types=dict(reg.current.relation_types))
    assert reg.admit_grammar_change(g).accepted is False   # не V+1


def test_adding_type_ok_and_bumps_version():
    reg, space = make_space()
    g = Grammar(version=2, relation_types=dict(reg.current.relation_types))
    g.relation_types["OWNS"] = RelationType("OWNS", ("PERSON",), ("PERSON",))
    d = reg.admit_grammar_change(g, space)
    assert d.accepted and d.new_version == 2
    assert space.grammar.has_type("OWNS") and space.schema_version == 2


def test_removal_of_used_type_rejected():
    reg, space = make_space()
    space.add_relation("SENDS", "a", "a")
    g = Grammar(version=2, relation_types={})   # удалили SENDS, он используется
    d = reg.admit_grammar_change(g, space)
    assert d.accepted is False and d.reason == "TYPE_IN_USE:SENDS"


def test_narrowing_signature_rejected():
    reg, _ = make_space()
    g = Grammar(version=2, relation_types={
        "SENDS": RelationType("SENDS", ("ROBOT",), ("PERSON",))})  # сужение
    d = reg.admit_grammar_change(g)
    assert d.accepted is False and d.reason.startswith("BACKWARD_INCOMPATIBLE")


def test_object_type_admission():
    reg, space = make_space()
    d = reg.admit_object_type(space, "GLOVE")
    assert d.accepted and "GLOVE" in space.types
    d2 = reg.admit_object_type(space, "GLOVE")
    assert d2.accepted is False and d2.reason == "TYPE_ALREADY_IN_BASIS"


def test_state_is_not_history_is_not_event():
    """STATE != HISTORY != EVENT: одна история — разные проекции."""
    tr = Trace("t")
    tr.append("X", "a", {"v": 1})
    tr.append("Y", "b", {"v": 2})
    proj1 = tr.project(lambda s, e: {**s, "n": s.get("n", 0) + 1})
    proj2 = tr.project(lambda s, e: {**s, e.type: True})
    assert len(tr.events) == 2 and proj1 != proj2
    # неизменяемость истории
    import pytest
    with pytest.raises(Exception):
        tr.events[0].type = "HACK"
