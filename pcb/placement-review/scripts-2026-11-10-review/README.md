# 2026-11-10 自己レビューのスクリプト（記録）

`../scripts-2026-11-10/lib.py` の編集ヘルパーを使う。`r1`→`r2`→`r3`→`r4`→`r5` の順に、コミット `85376c9` の基板へ適用した編集の記録である。各スクリプトは適用前の座標を前提にしており、現在の基板へ再実行するものではない。

| ファイル | 内容 |
| --- | --- |
| `r1_swd_corner.py` | SWD・nRESET・VTrefの引き直し |
| `r2_island_stitch.py` | ビア1個のGND島へ2個目のビアを追加 |
| `r3_silk_refs.py` | 参照名シルクの整理。引数は直前のDRCのJSON |
| `r4_merge_overlaps.py` | 重なり線分の統合とBATスタブの除去 |
| `r5_antenna_fill_keepout.py` | `ANT_NO_FILL` の追加 |

外径0.5 mmのGNDビアを0.6 mmへ広げた変更と、`ts52k.kicad_pro` のネットクラス更新は、スクリプトを残していない。

次の3本は編集を行わない検査・描画用で、現在の基板にも使える。

- `check_return_path.py <pcb>`：USB・DCCH・水晶配線直下のF.Cu GND欠損を数える。
- `check_gnd_islands.py <pcb>`：GNDベタの島ごとの面積と接続ビア数。
- `render_region.py <pcb> x0 y0 x1 y1 out.png [scale=40] [layers=FB]`：指定範囲をmatplotlibで描く。
