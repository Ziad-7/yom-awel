from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.persistence.repository_contract import (
    assert_preferred_language_update,
    assert_progress_rollback_and_cas,
    assert_reservation_and_finalization,
)
from yom_awel.persistence.memory import FrozenClock, MemoryUnitOfWorkFactory
from yom_awel.persistence.sqlite import SQLiteUnitOfWorkFactory


@pytest.fixture(params=["memory", "sqlite"], ids=["memory", "sqlite"])
def repository_factory(request: pytest.FixtureRequest, tmp_path: Path) -> Any:
    if request.param == "memory":
        from tests.persistence.repository_contract import NOW

        return MemoryUnitOfWorkFactory(clock=FrozenClock(NOW))
    return SQLiteUnitOfWorkFactory(tmp_path / "repository-contract.sqlite")


@pytest.mark.asyncio
async def test_reservation_and_finalization_contract(repository_factory: Any) -> None:
    await assert_reservation_and_finalization(repository_factory)


@pytest.mark.asyncio
async def test_progress_rollback_and_cas_contract(repository_factory: Any) -> None:
    await assert_progress_rollback_and_cas(repository_factory)


@pytest.mark.asyncio
async def test_preferred_language_update_contract(repository_factory: Any) -> None:
    await assert_preferred_language_update(repository_factory)
