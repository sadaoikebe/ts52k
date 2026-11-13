# 2026-11-13 J2下段移設の作業スクリプト

KiCad 10.0.8の `pcbnew` で実行する（描画だけ `~/.venv-tc52w` のmatplotlibを使う）。

| スクリプト | 内容 |
| --- | --- |
| `obstacles.py` | 表面側の障害物モデル。スイッチ本体15.6 mm正方形、Cherryスタビライザー本体（Keymodule MX資料の寸法、x±4.2 mm・2穴の外縁まで、+0.2 mm）、ワイヤー、エンコーダSW2のコートヤード |
| `search_sites.py` | 基板全体の候補探索。yを0.1 mm刻み、向き0°／90°ごとに、2 mm条件を満たすJ2中心のx区間を厳密に求める。裏面部品コートヤードとの距離も出す。移設前の基板（5f83906）に対して実行し、結果は `../j2-bottom-2026-11-13/site-search.json` |
| `move_j2_bottom.py` | J2を (19.05, 115.0)・+90°へ移し、SWD配線を引き直す。wireless 5f83906の基板に1回だけ実行する前提 |
| `measure_j2.py` | `../j2-bottom-2026-11-13/j2-check.json` を作る |
| `render_j2.py` | `../j2-bottom-2026-11-13/j2-area.png` を描く |

```sh
python3 search_sites.py ../../ts52k.kicad_pcb ../j2-bottom-2026-11-13/site-search.json   # 移設前
python3 move_j2_bottom.py ../../ts52k.kicad_pcb                                         # 1回だけ
python3 measure_j2.py ../../ts52k.kicad_pcb ../j2-bottom-2026-11-13/j2-check.json
~/.venv-tc52w/bin/python render_j2.py ../../ts52k.kicad_pcb ../j2-bottom-2026-11-13/j2-area.png
```
