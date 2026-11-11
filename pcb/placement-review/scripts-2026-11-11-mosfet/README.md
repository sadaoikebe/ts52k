# 2026-11-11 逆接続保護Q1の作業スクリプト

起点は `wireless` b730700。どちらも1回だけ実行する前提（実行済み）。KiCad 10.0.8。

- `add_q1_schematic.py <リポジトリ> 90 y`：KiCad標準の `Package_TO_SOT_SMD:SOT-23` を `pcb/ts52k.pretty` へ複写し、
  `Transistor_FET:AO3401A`（`TP0610T` を継承）を独立シンボル `ts52k:AO3401A` として登録する。
  回路図ではJ3を右下へ移し、BAT → Q1ソース、Q1ドレイン → `BAT_CONN` → J3の1番、Q1ゲート → GND を結線する。
- `place_q1_pcb.py <pcb>`：Q1を裏面 (24.97, 68.73) に置き、BAT・`/BAT_CONN`・ゲートのGND・Net-(D3-A) を引き、
  D−・D+・nRESET・col1 をQ1の下だけ0.15 mm南へ寄せて、ベタを再充填して保存する。
  回路図の Q1 のUUID（`10b01f4d-…`）を埋め込んでいるので、回路図を作り直した場合は書き換える。
- `reverse_insert_transient.py`：USB給電中に逆向きの電池を挿した瞬間のBAT端子電圧の見積もり。
  2乗則の簡易MOSFETモデルと仮定した配線定数による計算で、検証されたモデルではない。結果は `../README.md` の冒頭の節。

検査結果は `../mosfet-2026-11-11/`（DRC、ERC、Q1周辺の測定値、確認用の図）。
