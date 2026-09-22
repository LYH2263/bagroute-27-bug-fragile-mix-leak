# BagRoute

投递装袋：按路线订户顺序装袋，重量与体积双约束，超限拒收；易碎站点隔离装袋。

## 装袋规则

1. 严格按路线 `seq` 顺序装袋。
2. 重量与体积双约束，任一超出路线限额即新开袋（开袋原因记为「满额开新袋」）。
3. 易碎站点与非易碎站点绝不混装：类型切换时即使当前袋重量、体积都仍够，也必须新开袋（开袋原因记为「易碎隔离」）。
4. 单站自身重量或体积超过路线限额时直接拒收（类别「超限拒收」），不能借隔离规则装入。

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4300 |
| API | http://localhost:9300 |
| API 文档 | http://localhost:9300/docs |
| Postgres | localhost:5444 |

健康检查：`GET http://localhost:9300/api/health`

## 页面

- `/routes` — 路线
- `/stops` — 订户点
- `/pack` — 装袋
- `/bags` — 袋明细
- `/rejects` — 拒收
- `/weights` — 袋重

## 使用说明

1. 查看路线与订户点顺序。
2. 在装袋页选择路线执行双约束装袋。
3. 袋明细与袋重查看结果，拒收页查看超限订户。

## 开发与测试

```bash
docker compose exec api pytest -q
```
