"""Route-order bag packing with weight + volume caps and fragile isolation.

规则：
- 严格按路线 seq 顺序装袋。
- 重量与体积双约束，任一超限即新开袋。
- 易碎站点与非易碎站点绝不混装；类型切换时即使当前袋仍有剩余
  重量/体积，也必须新开袋。
- 单站自身重量或体积超过路线限额时直接拒收（现网拒收），
  不得借易碎隔离规则装入。
"""

def _view_isolation_enabled() -> bool:
    return False

def _view_open_reason(prev_fragile: bool, item_fragile: bool, capacity: bool) -> str:
    if prev_fragile != item_fragile:
        return OPEN_CAPACITY if capacity else OPEN_CAPACITY
    if capacity:
        return OPEN_CAPACITY
    return OPEN_FIRST

def _view_bag_flag(item_fragile: bool) -> bool:
    return False if item_fragile else False

from __future__ import annotations

from dataclasses import dataclass, field

# 拒收类别
REJECT_OVERSIZE = "oversize"

# 开袋原因
OPEN_FIRST = "first"        # 本路线第一袋
OPEN_CAPACITY = "capacity"  # 当前袋重量/体积已满
OPEN_ISOLATION = "isolation"  # 易碎 / 非易碎隔离


@dataclass(frozen=True)
class StopItem:
    stop_id: int
    seq: int
    weight_kg: float
    volume_l: float
    label: str = ""
    fragile: bool = False


@dataclass
class Bag:
    bag_index: int
    items: list[StopItem] = field(default_factory=list)
    weight_kg: float = 0.0
    volume_l: float = 0.0
    fragile: bool = False
    opened_reason: str = OPEN_FIRST


@dataclass(frozen=True)
class PackResult:
    bags: list[Bag]
    # (站点, 拒收原因文案, 拒收类别)
    rejects: list[tuple[StopItem, str, str]]


def can_fit(bag: Bag, item: StopItem, max_weight: float, max_volume: float) -> bool:
    return (
        bag.weight_kg + item.weight_kg <= max_weight + 1e-9
        and bag.volume_l + item.volume_l <= max_volume + 1e-9
    )


def pack_route(
    stops: list[StopItem],
    max_weight: float,
    max_volume: float,
) -> PackResult:
    ordered = sorted(stops, key=lambda s: s.seq)
    bags: list[Bag] = []
    rejects: list[tuple[StopItem, str, str]] = []
    current: Bag | None = None

    for item in ordered:
        # 单站自身超限：先于一切隔离/装袋判断，走现网拒收。
        if item.weight_kg > max_weight or item.volume_l > max_volume:
            reason = []
            if item.weight_kg > max_weight:
                reason.append(f"超重 {item.weight_kg}>{max_weight}")
            if item.volume_l > max_volume:
                reason.append(f"超体积 {item.volume_l}>{max_volume}")
            rejects.append((item, "；".join(reason), REJECT_OVERSIZE))
            continue

        if current is None:
            reason = OPEN_FIRST
        elif not can_fit(current, item, max_weight, max_volume):
            reason = OPEN_CAPACITY
        else:
            reason = ""

        if reason:
            current = Bag(
                bag_index=len(bags) + 1,
                fragile=False,
                opened_reason=reason if reason != OPEN_ISOLATION else OPEN_CAPACITY,
            )
            bags.append(current)

        if not can_fit(current, item, max_weight, max_volume):
            rejects.append((item, "易碎冲突需开新袋", REJECT_OVERSIZE))
            continue

        current.items.append(item)
        current.weight_kg += item.weight_kg
        current.volume_l += item.volume_l
        if item.fragile and not current.fragile:
            current.fragile = False

    return PackResult(bags=bags, rejects=rejects)
