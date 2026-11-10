# 西端移設後の軽作業・再検査

ブランチ `claude-followup-2026-11-11`、起点 `e2a60ac`。
実行日は2026-11-10 UTC、KiCad 10.0.8。Fableの以前の検査を転記した結果ではなく、
この作業で再実行した結果。実機・ファームウェアの動作検証は行っていない。

## 変更と結果

- GPIOの旧説明を修正し、[Windows側の同期チェックリスト](../../../notes/zmk-pin-sync-checklist.md)を追加。
- PCBは `ANT_EDGE` の `pads allowed` を `pads not_allowed` に変更。
  配置・配線・基板外形・フットプリントは変更していない。
- [check.json](check.json)：GPIO表18信号のGPIO名・物理パッド・回路図ネットリスト・PCB・
  同期表の対応が一致。文書25ファイルを検索し、20ファイルの全ヒット行を保存した。
  文書の意味の照合は手作業で行い、旧GPIO新旧対照表、旧UF2の履歴、RP2040版の記録、
  他製品のGPIO説明を現PCBの指定と区別した。
- モジュール内のアンテナ禁止領域は x=−3.3〜0.5、y=57.2〜69.6 mm、
  `ANT_EDGE` は x=−3.8〜0.23、y=45〜82 mm（PCBから読んだ座標）。
  両領域のF.Cu/B.Cuで配線・ビア・パッドの侵入0、再充填後のベタとの重複0 mm²。
  銅箔の図形・文字も検索対象に含めたが、現基板には該当する銅箔描画はなかった。
- `grep -c ANT_NO_FILL pcb/ts52k.kicad_pcb` は0件。
- [drc.json](drc.json)：未接続0、回路図との不一致0、エラー0、警告9。
  内訳はD89/D90のシルク重なり7、J1のシルクと基板端2。
  作業開始後に測った修正前のDRCと、種類・重大度・対象UUIDが全件一致した。
- [erc.json](erc.json)：エラー・警告・除外とも0。

アンテナの基準は[Raytac Version K §2.3（印刷p13〜15）](https://cdn.sparkfun.com/assets/4/7/4/3/8/_nRF52840__MDBT50Q-1MV2___MDBT50Q-P1MV2_Ver.K_spec.pdf)。
全層の銅箔を抜き、基板端へ配置し、帯を横方向へ広げる図を再確認した。
スクリプトは実装済みの禁止領域と銅箔の幾何学的な交差を検査するもので、
ケース・真鍮プレートを含むRF性能や通信距離の検証ではない。

## 再実行

リポジトリのルートから実行する。`pcbnew` を読み込めるPythonを使う。
アンテナ検査はメモリ上でベタを再充填するが、PCBを保存しない。
配線幅・ビア径・パッド形状を最大誤差0.001 mmの外接ポリゴンへ変換し、
禁止領域との面積交差を求める。ベタは実際の充填ポリゴン（穴を含む）を使う。

```sh
kicad-cli sch export netlist --format kicadxml -o /tmp/ts52k-followup.net pcb/ts52k.kicad_sch
/usr/bin/python3 pcb/check_wireless_followup.py --netlist /tmp/ts52k-followup.net --output pcb/placement-review/followup-2026-11-11/check.json
kicad-cli pcb drc --refill-zones --severity-all --schematic-parity --format json -o pcb/placement-review/followup-2026-11-11/drc.json pcb/ts52k.kicad_pcb
kicad-cli sch erc --severity-all --format json -o pcb/placement-review/followup-2026-11-11/erc.json pcb/ts52k.kicad_sch
```

製造データは今回の範囲外。旧RP2040版の出力を再生成していない。
Fable報告の取り込み判断、LF精度・USB品質、J3挿抜、基板端実装条件、
金属と通信距離、SWD実機書き込みは引き続き未確認。
