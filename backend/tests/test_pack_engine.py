from app.services.pack_engine import (
    OPEN_CAPACITY,
    OPEN_FIRST,
    OPEN_ISOLATION,
    REJECT_OVERSIZE,
    StopItem,
    pack_route,
)


def test_packs_in_route_order_splitting_bags():
    stops = [
        StopItem(1, 1, 2.0, 3.0),
        StopItem(2, 2, 2.5, 3.0),
        StopItem(3, 3, 1.0, 1.0),
    ]
    result = pack_route(stops, max_weight=4.0, max_volume=10.0)
    assert len(result.bags) == 2
    assert [i.stop_id for i in result.bags[0].items] == [1]
    assert [i.stop_id for i in result.bags[1].items] == [2, 3]
    assert not result.rejects


def test_reject_oversized_stop():
    stops = [StopItem(1, 1, 9.0, 1.0, "大件"), StopItem(2, 2, 1.0, 1.0)]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0)
    assert len(result.rejects) == 1
    assert result.rejects[0][0].stop_id == 1
    assert len(result.bags) == 1
    assert result.bags[0].items[0].stop_id == 2


def test_volume_cap_triggers_new_bag():
    stops = [StopItem(1, 1, 1.0, 4.0), StopItem(2, 2, 1.0, 4.0)]
    result = pack_route(stops, max_weight=10.0, max_volume=5.0)
    assert len(result.bags) == 2


def test_fragile_and_normal_never_share_a_bag_even_when_capacity_remains():
    # 两站合计 3kg / 3L，远低于 8kg / 18L；仅因易碎隔离必须分袋。
    stops = [
        StopItem(1, 1, 1.5, 1.5, "普通站", fragile=False),
        StopItem(2, 2, 1.5, 1.5, "易碎站", fragile=True),
        StopItem(3, 3, 1.5, 1.5, "普通站", fragile=False),
        StopItem(4, 4, 1.5, 1.5, "易碎站", fragile=True),
    ]
    result = pack_route(stops, max_weight=8.0, max_volume=18.0)

    assert len(result.bags) == 4
    for bag in result.bags:
        kinds = {it.fragile for it in bag.items}
        assert len(kinds) == 1  # 每袋只含一种类型
    assert [b.fragile for b in result.bags] == [False, True, False, True]
    assert [[it.stop_id for it in b.items] for b in result.bags] == [[1], [2], [3], [4]]
    # 首袋 + 三次易碎隔离开袋
    assert [b.opened_reason for b in result.bags] == [
        OPEN_FIRST,
        OPEN_ISOLATION,
        OPEN_ISOLATION,
        OPEN_ISOLATION,
    ]
    assert not result.rejects


def test_consecutive_fragile_stops_share_until_capacity():
    # 同类易碎站可同袋；装满后触发 capacity 而非 isolation。
    stops = [
        StopItem(1, 1, 2.0, 2.0, "易碎甲", fragile=True),
        StopItem(2, 2, 2.0, 2.0, "易碎乙", fragile=True),
        StopItem(3, 3, 2.0, 2.0, "易碎丙", fragile=True),
    ]
    result = pack_route(stops, max_weight=5.0, max_volume=10.0)
    assert len(result.bags) == 2
    assert all(b.fragile for b in result.bags)
    assert [it.stop_id for it in result.bags[0].items] == [1, 2]
    assert [it.stop_id for it in result.bags[1].items] == [3]
    assert result.bags[0].opened_reason == OPEN_FIRST
    assert result.bags[1].opened_reason == OPEN_CAPACITY


def test_oversized_fragile_stop_still_rejected_not_isolated_into_bag():
    # 易碎站自身超重（9 > 8），即使前一袋是易碎袋且完全空，也不能借隔离规则装入。
    stops = [
        StopItem(1, 1, 2.0, 2.0, "易碎甲", fragile=True),
        StopItem(2, 2, 9.0, 2.0, "易碎超大件", fragile=True),
        StopItem(3, 3, 1.0, 1.0, "易碎乙", fragile=True),
    ]
    result = pack_route(stops, max_weight=8.0, max_volume=18.0)

    assert len(result.rejects) == 1
    item, reason, kind = result.rejects[0]
    assert item.stop_id == 2
    assert kind == REJECT_OVERSIZE
    assert "超重" in reason

    # 站 3 与站 1 同为易碎且站 1 所在袋还装得下，应合并，拒收站不打断隔离规则。
    assert len(result.bags) == 1
    assert [it.stop_id for it in result.bags[0].items] == [1, 3]
    assert all(it.fragile for it in result.bags[0].items)


def test_ordering_strictly_follows_seq_regardless_of_input_order():
    # 输入故意打乱，装袋顺序必须按 seq；碎/非交错产生 3 袋。
    stops = [
        StopItem(3, 3, 1.0, 1.0, "非易碎3", fragile=False),
        StopItem(1, 1, 1.0, 1.0, "非易碎1", fragile=False),
        StopItem(2, 2, 1.0, 1.0, "易碎2", fragile=True),
    ]
    result = pack_route(stops, max_weight=8.0, max_volume=18.0)
    flat = [it.seq for b in result.bags for it in b.items]
    assert flat == [1, 2, 3]
    assert [b.fragile for b in result.bags] == [False, True, False]
    assert result.bags[1].opened_reason == OPEN_ISOLATION
    assert result.bags[2].opened_reason == OPEN_ISOLATION


def test_seed_style_interleaved_route_with_overweight_stop():
    # 锁住种子场景：非易碎→易碎→非易碎→(超重拒)→易碎→易碎→非易碎→非易碎(满额)
    stops = [
        StopItem(1, 1, 2.2, 4.0, "松林里", fragile=False),
        StopItem(2, 2, 3.5, 5.5, "梧桐苑", fragile=True),
        StopItem(3, 3, 1.8, 3.0, "快递柜", fragile=False),
        StopItem(4, 4, 9.5, 6.0, "超大件", fragile=False),
        StopItem(5, 5, 2.0, 4.5, "咖啡店", fragile=True),
        StopItem(6, 6, 1.5, 3.0, "花房", fragile=True),
        StopItem(7, 7, 3.0, 5.0, "菜店", fragile=False),
        StopItem(8, 8, 5.5, 8.0, "水站", fragile=False),
    ]
    result = pack_route(stops, max_weight=8.0, max_volume=18.0)

    # 拒收：仅 seq=4
    assert [it.stop_id for it, _, kind in result.rejects if kind == REJECT_OVERSIZE] == [4]

    # 每袋类型纯净，且 seq 顺序保持
    for bag in result.bags:
        assert len({it.fragile for it in bag.items}) == 1
        seqs = [it.seq for it in bag.items]
        assert seqs == sorted(seqs)
    flat = [it.stop_id for b in result.bags for it in b.items]
    assert flat == sorted(flat)
    assert 4 not in flat

    kinds = [b.fragile for b in result.bags]
    assert kinds == [False, True, False, True, False, False]
    # 最后一袋为满额开新袋（菜店 3.0 + 水站 5.5 = 8.5 > 8.0）
    assert result.bags[-1].opened_reason == OPEN_CAPACITY
    assert [it.stop_id for it in result.bags[-1].items] == [8]
