"""
Classes to manage runs.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from pkgutil import resolve_name

RateFunc = Callable[[float, float], float]
RateType = float | RateFunc | str


class Property:
    def __init__(
        self,
        name: str,
        initial: float = 0.0,
        *,
        target: float | None = None,
        validrange: tuple[float, float] | None = None,
        rate: tuple[RateType, RateType] | RateType | None = None,
        rate_up: RateType | None = None,
        rate_down: RateType | None = None,
        always_advance: bool = False,
        units: str = "",
    ) -> None:
        self.name = name
        self.current = initial
        self.units = units

        match rate, rate_up, rate_down:
            case _, None, None if rate is not None:
                self.rate = rate
            case None, _, _ if rate_up is not None and rate_down is not None:
                self.rate_up, self.rate_down = rate_up, rate_down
            case _:
                raise ValueError("`rate` OR `rate_up` and `rate_down` must be provided")

        self.always_advance = always_advance
        self.target = target
        self.validrange = validrange
        self.runcontrol = False
        self.data = [initial]

    @property
    def current_rate(self) -> float:
        if self.target is None:
            return self.always_advance * (self.rate_up or self.rate_down)

        if math.isclose(
            self.target,
            self.current,
            abs_tol=max(self.rate_up, self.rate_down),
        ):
            return self.target - self.current

        if self.target > self.current:
            return self.rate_up

        return self.rate_down

    def inrange(self) -> bool:
        return self.validrange[0] < self.current < self.validrange[1]

    @property
    def rate_up(self) -> float:
        if isinstance(self._rate_up, Callable):
            return self._rate_up(self.current, self.target)

        return self._rate_up

    @rate_up.setter
    def rate_up(self, value: RateType) -> None:
        match value:
            case float() | Callable():
                self._rate_up = value
            case str():
                self._rate_up = resolve_name(value)
            case _:
                raise ValueError(f"Invalid rate: {value!r} (type={type(value).__name__})")

    @property
    def rate_down(self) -> float:
        if isinstance(self._rate_down, Callable):
            return self._rate_down(self.current, self.target)

        return self._rate_down

    @rate_down.setter
    def rate_down(self, value: RateType) -> None:
        match value:
            case float() | Callable():
                self._rate_down = value
            case str():
                self._rate_down = resolve_name(value)
            case _:
                raise ValueError(f"Invalid rate: {value!r} (type={type(value).__name__})")

    @property
    def rate(self) -> float:
        return self.current_rate

    @rate.setter
    def rate(self, value: RateType | tuple[RateType, RateType]) -> None:
        if isinstance(value, tuple):
            self.rate_up, self.rate_down = value
        else:
            self.rate_up = abs(value)
            self.rate_down = -self.rate_up

    # def time_to_target(self) -> float:
    #     ...

    def advance(self, steps: int = 1) -> None:
        self.current += self.current_rate * steps
        self.data.append(self.current)

    def __repr__(self) -> str:
        return f"{self.name}({self.current=}, {self.target=}, {self.rate=})"


class Check:
    """Define a checking function.

    Parameters:
        prop (Property): Property whose value is to be checked.
        validrange (tuple[float | None, float | None] | float): Valid range or value for property.
    """

    def __init__(
        self,
        prop: Property,
        valid: tuple[float | None, float | None] | float,
    ) -> None:
        self.prop = prop
        self.valid = valid

    def _check(self) -> bool:
        """Ensure property is in range.

        Returns
        -------
        bool
            Property in valid range.
        """
        match self.valid:
            case (None, None):
                return True
            case (None, maxi):
                return self.prop.current <= maxi
            case (mini, None):
                return self.prop.current >= mini
            case (mini, maxi):
                return mini <= self.prop.current <= maxi
            case valid:
                return math.isclose(self.prop.current, valid)

    def __call__(self) -> bool:
        return self._check()

    def __bool__(self) -> bool:
        return self._check()


@dataclass
class CurrentState:
    properties: dict[str, Property]
    counts: list[tuple[float, float]]
    records: list[tuple[float, float]]
    run_variables: dict
    counting: float | None = None

    @classmethod
    def empty(cls) -> CurrentState:
        return cls(properties={}, counts=[], records=[], run_variables={})
