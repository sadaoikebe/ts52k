# 2026-11-13 J2西端移設の作業スクリプト

KiCad 10.0.8の `pcbnew` で実行する（描画だけ `~/.venv-tc52w` のmatplotlibを使う）。

| スクリプト | 内容 |
| --- | --- |
| `search_j2_sites.py` | 候補地の探索。各スイッチの15.6 mm正方形から2 mm以上離れる位置を、仮のクリップ外形（12.7×9.906 / 9.906×7.239 / 9.906×6.096 mm）とコートヤード（7×4 mm）で比較する。移設前の基板に対して実行した。スタビライザーの範囲は穴から推定した概略値 |
| `move_j2_west.py` | J2を (−0.6, 86.5)・−90°へ移し、SWD配線を引き直す。wireless 4cbad9fの基板に1回だけ実行する前提 |
| `measure_j2.py` | `../j2-west-2026-11-13/j2-check.json` を作る |
| `render_j2.py` | `../j2-west-2026-11-13/j2-area.png` を描く |

```sh
python3 move_j2_west.py ../../ts52k.kicad_pcb          # 1回だけ
python3 measure_j2.py ../../ts52k.kicad_pcb ../j2-west-2026-11-13/j2-check.json
~/.venv-tc52w/bin/python render_j2.py ../../ts52k.kicad_pcb ../j2-west-2026-11-13/j2-area.png
```
