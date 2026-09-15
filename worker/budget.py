"""Потолок расходов на проект.

Зачем отдельный модуль. `safe_mode` отвечает на вопрос «можно ли тратить
вообще» — да или нет. Этого хватало, пока единственным платным шагом была
озвучка за копейки. Настоящее видео стоит $0.35 за пять секунд, и ролик на
тридцать секунд при покрытии 70% съедает полтора доллара: вопрос «можно ли
тратить» превращается в «сколько осталось».

Устройство. Страж живёт ровно один проект и привязан к нему через
`for_project()`. Все платные вызовы уже проходят через `safe_mode`, поэтому
проверка остатка встроена туда же — обойти её мимо чекпойнта нельзя, а
дублировать условия по шагам запрещено: именно так появляются дыры.

Резерв на починку. Если потратить весь потолок на первую сборку, чинить
плохие кадры будет не на что. Поэтому обычная генерация видит не весь
остаток, а остаток минус резерв; починка — весь.
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

log = logging.getLogger("worker.budget")

# Доля потолка, отложенная на переделку плохих кадров. Бриф предлагает
# 10–20%: $0.35 из $3 в его же примере — это 12%.
REPAIR_RESERVE_RATIO = 0.15


class BudgetExceeded(Exception):
    """Вызов отклонён: денег на него не осталось."""


@dataclass
class BudgetGuard:
    """Учёт денег одного проекта.

    `max_budget_usd = None` означает «потолка нет» — поведение до появления
    этого модуля. Ноль означает «тратить нельзя», и это не одно и то же.
    """

    max_budget_usd: float | None = None
    spent_usd: float = 0.0
    reserve_ratio: float = REPAIR_RESERVE_RATIO
    denials: list[str] = field(default_factory=list)

    @property
    def has_ceiling(self) -> bool:
        return self.max_budget_usd is not None

    @property
    def repair_reserve_usd(self) -> float:
        if not self.has_ceiling:
            return 0.0
        return round(float(self.max_budget_usd) * self.reserve_ratio, 4)

    @property
    def remaining_usd(self) -> float:
        if not self.has_ceiling:
            return float("inf")
        return round(float(self.max_budget_usd) - self.spent_usd, 4)

    @property
    def spendable_usd(self) -> float:
        """Сколько можно потратить на обычную генерацию: остаток без резерва."""
        if not self.has_ceiling:
            return float("inf")
        return round(max(self.remaining_usd - self.repair_reserve_usd, 0.0), 4)

    def can_afford(self, estimated_usd: float, *, repair: bool = False) -> bool:
        limit = self.remaining_usd if repair else self.spendable_usd
        return estimated_usd <= limit + 1e-9

    def authorize(self, estimated_usd: float, what: str, *, repair: bool = False) -> None:
        """Разрешить платный вызов или отказать до того, как он сделан.

        Отказ — обычный ход событий, а не авария: кадр останется движением по
        картинке, ролик соберётся, покрытие честно упадёт. Молча перерасходовать
        нельзя ни при каких условиях.
        """
        if not self.has_ceiling:
            return
        if self.can_afford(estimated_usd, repair=repair):
            return
        reason = (
            f"{what}: нужно ${estimated_usd:.4f}, "
            f"доступно ${(self.remaining_usd if repair else self.spendable_usd):.4f} "
            f"из потолка ${float(self.max_budget_usd):.2f}"
            + ("" if repair else f" (резерв на починку ${self.repair_reserve_usd:.4f} не трогаем)")
        )
        self.denials.append(reason)
        log.warning("[BUDGET] отказ — %s", reason)
        raise BudgetExceeded(reason)

    def record(self, actual_usd: float, what: str = "") -> None:
        """Записать фактическую трату. Оценка и факт расходятся, и считать
        надо по факту, иначе потолок держится на обещаниях."""
        self.spent_usd = round(self.spent_usd + max(actual_usd, 0.0), 6)
        if self.has_ceiling:
            log.info(
                "[BUDGET] потрачено $%.4f%s, остаток $%.4f, резерв $%.4f",
                self.spent_usd, f" ({what})" if what else "",
                self.remaining_usd, self.repair_reserve_usd,
            )

    def summary(self) -> dict[str, float | int | None]:
        return {
            "max_budget_usd": self.max_budget_usd,
            "spent_usd": round(self.spent_usd, 4),
            "remaining_usd": None if not self.has_ceiling else self.remaining_usd,
            "repair_reserve_usd": self.repair_reserve_usd,
            "denials": len(self.denials),
        }


# Страж проекта. Воркер берёт задачи по одной, но привязка сделана к потоку:
# тест, запущенный параллельно, не должен видеть чужой потолок.
_local = threading.local()


def current() -> BudgetGuard | None:
    return getattr(_local, "guard", None)


@contextmanager
def for_project(max_budget_usd: float | None, reserve_ratio: float = REPAIR_RESERVE_RATIO) -> Iterator[BudgetGuard]:
    """Привязать страж к текущему проекту на время его сборки."""
    guard = BudgetGuard(max_budget_usd=max_budget_usd, reserve_ratio=reserve_ratio)
    previous = current()
    _local.guard = guard
    if guard.has_ceiling:
        log.info(
            "[BUDGET] потолок $%.2f, резерв на починку $%.4f",
            float(max_budget_usd), guard.repair_reserve_usd,
        )
    try:
        yield guard
    finally:
        _local.guard = previous
