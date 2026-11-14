# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from singulyar_host.activation import (ActivationRegistry, BranchStatus)  # noqa: E402
from singulyar_host.capability import CapabilityError, CapabilityStore  # noqa: E402
from singulyar_host.continuity import continuity_vector  # noqa: E402
from singulyar_host.ontology import Commitment, Subject  # noqa: E402


def test_fork_single_authoritative_successor():
    reg = ActivationRegistry()
    res = reg.activate_fork("L1", None, ["c1", "c2"])
    assert res.outcome == "ONE_ACTIVE_SUCCESSOR"
    assert res.head == "c1"
    assert res.branches[1].status == BranchStatus.FORKED
    assert res.branches[1].identity == "NEW_BRANCH"


def test_second_activation_rejected():
    reg = ActivationRegistry()
    reg.cas_head("L1", None, "c1")
    assert reg.cas_head("L1", None, "c2") is False


def test_partition_prefers_no_assignment():
    reg = ActivationRegistry(partition=True)
    res = reg.activate_fork("L1", None, ["c1", "c2"])
    assert res.outcome == "NO_AUTHORITY_GRANTED" and res.head is None


def test_dual_activation_only_when_disabled():
    reg = ActivationRegistry(allow_dual_activation=True)
    res = reg.activate_fork("L1", None, ["c1", "c2"])
    assert res.outcome == "DUAL_ACTIVATION_ACCEPTED"
    assert len(reg.conflicting_heads("L1")) == 2


def test_delegation_attenuates_only():
    store = CapabilityStore()
    parent = store.issue("p", "agent", "root", scope={"read", "write"})
    child = store.delegate(parent, "c", {"read"}, "sub")
    assert child.scope == frozenset({"read"})
    with pytest.raises(CapabilityError):
        store.delegate(parent, "c2", {"read", "admin"}, "sub")


def test_revocation_chain():
    store = CapabilityStore()
    parent = store.issue("p", "agent", "root", scope={"read"})
    store.delegate(parent, "c", {"read"}, "sub")
    assert store.revoke_chain("p", "root") >= 2
    assert store.check("c", "sub", "read") is False


def test_capability_expiry():
    store = CapabilityStore()
    store.issue("p", "agent", "root", scope={"read"}, ttl_ticks=5)
    for _ in range(6):
        store.advance_tick()
    assert store.check("p", "agent", "read") is False


def test_continuity_four_situations_differ():
    c = (Commitment("c1", "S", "x", True),)
    s0 = Subject("S0", "L1", commitments=c, state_hash="h")
    dev = continuity_vector(s0, Subject("S0", "L1", commitments=c,
                                        state_hash="h2"),
                            "DEVELOPMENT", activation_granted=True)
    mig = continuity_vector(s0, Subject("S0-p", "L1", commitments=c,
                                        state_hash="h3"),
                            "MIGRATION", activation_granted=True)
    fork = continuity_vector(s0, s0.copy_for_fork("S-f"), "FORK")
    rep = continuity_vector(s0, Subject("S-i", "L-imp", commitments=c,
                                        state_hash="h"),
                            "REPLACEMENT")
    assert dev.overall.value == "PASS"
    assert mig.overall.value == "PASS"
    assert fork.overall.value == "CONTESTED"
    assert rep.overall.value == "FAIL"
