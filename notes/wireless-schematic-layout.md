# 無線版回路図の配置元と確認

2026-11-03。回路図上の配置についての記録。PCB配置の検討ではない。[PDF](../pcb/schematic-review/ts52k-wireless.pdf)はA4横2枚で、[全体図](../pcb/schematic-review/overview.png)と[MCU詳細](../pcb/schematic-review/mcu.png)も出力した。

## 引き継いだ既存図

既存の`a82fe3d`時点の回路図をPDF化して確認し、親シートの「左にMCU子シート、右にキーマトリクス、左下にUSBと電源、上にSWD」を維持した。

| 対象 | 引き継ぎ内容 |
| --- | --- |
| 52個のMXと53個のダイオード | 全105個の座標・角度・UUIDと、マトリクスの全接続を維持。row/colの並びも維持 |
| MCU子シート枠 | 左上(55.88, 41.91) mm、50.8×62.23 mmを維持。右側の既存信号行の高さを維持して端子名を更新 |
| USB J1 | (29.21, 167.64) mmを維持。CC抵抗2個とESD3個の座標も維持 |
| SWD J2 | (180.34, 35.56) mmを維持。VTrefはnRF_VDDと明記 |
| RESET SW1 | (25.4, 133.35) mmを維持。旧1 kΩを除去してnRESET–GNDへ |
| エンコーダ SW2 | (255.27, 62.23) mmを維持。押し込みのマトリクス配線を維持し、A/Bの外付けRCだけ除去 |

既存部品114個の座標・角度・UUIDと、キー回路の接続を[検査スクリプト](../pcb/check_schematic.py)で旧図と照合した。文字の重なりは参照名・値の位置と寄せ方を調整し、部品を並べ替えて解消する方法は採っていない。

## 追加ブロックの配置元

[nice!nano v2公開回路](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/)の[回路画像](https://nicekeyboards.com/static/511ae101870d00c265b84f35d5f39eda/61100/schematic_nice_nano_v2.png)を確認し、以下の相対配置を踏襲した。

- **充電回路:** 入力をICの上、OUTとBATを右、設定抵抗とGNDを下へ置く。U6は既存LDOブロックと同じx=82.55 mm、y=138.43 mmに置き、ICの高さに応じた端子間隔を確保した。電池コネクタもBAT側の右に置き、キーマトリクスの領域へ入り込まないようにした。
- **MCU子シート:** MCUを中央、VDDの容量を上の横一列、VDDH/VBUS容量とREG0コイルも上、LF水晶を右上、信号を両側、GNDを下に置く。水晶はXL1/XL2の間に縦向き、12 pFを右に2個並べて共通GNDへ戻す。nice!nanoの同じまとまりを、MDBT50Qの公式シンボルの端子位置に合わせて使う。
- **USB:** 既存のレセプタクルとCC・ESDブロックを維持する。VBUSの直列2.2 Ωは、[Raytac Version L](https://www.raytac.com/download/index.php?index_id=43) p42の入力直列抵抗と同じ順序で、モジュールVBUSへの枝に描く。充電ICへの入力をこの抵抗へ通さない。

nice!nanoの裸のnRF52840、BQ24075、LED、外部VCC制御をそのまま移植したわけではない。電気的構成は[決定事項](wireless-decisions.md)を維持し、ここで先行例から引き継いだのは回路図のまとまりと読み順。公式シンボルの端子位置とサイズが違うため、画像の画素座標を直接転用したものではない。

## 読める図としての確認

電源・信号の流れが追えるよう、電源名をUSB_VBUS（入力）、MCU_VBUS（2.2 Ωの後）、VDDH（充電IC OUT）、nRF_VDD（モジュールREG0出力）、BATに分けた。nRF_VDDを固定3.3 Vという名前にはせず、SWD欄に消去直後1.8 V／初期化後3.3 Vを記載した。

未使用端子にNCを付け、必要な配線は水平・垂直で描いた。型番・JLC番号・説明は非表示フィールドに保持し、図には参照名と値を表示する。電池製品・容量・ケースは追加していない。

既存の密度を保つため、1N4148WとCC抵抗の図形は公式`Device:D_Small`、`Device:R_Small`へ合わせた。端子番号・型番・フットプリントは変えていない。SWDシンボルはピン名の文字サイズを1 mmへ縮め、VTref/SWDIO等が重ならないようにした。

PDFを画像化し、全体、MCUページ、電源とマトリクスの拡大図で確認した。入力容量と制御端子、電池コネクタと行ラベル、参照名と図形の重なりを修正した。視認確認とは別に、[検査結果](../pcb/schematic-review/validation.json)でERCエラー0・警告0、19品種81点、電源ネット・18 GPIO・旧マトリクスの一致を記録した。

コミット前の再検査では、KiCad保存後にUSB D−のB7接続が失われていることを検出した。重複線を使った接続をやめ、A7/B7を明示的な線分と接合点でまとめる配線へ修正。USBデータ4接点それぞれに線分の端点があることも検査へ追加し、ネットリストとERCを再確認した。

## 再実行と範囲

```powershell
& 'C:/Program Files/KiCad/10.0/bin/python.exe' pcb/check_schematic.py
& 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe' sch export pdf pcb/ts52k.kicad_sch -o pcb/schematic-review/ts52k-wireless.pdf
```

[参照番号付きBOM](../pcb/schematic-review/bom.csv)も回路図から照合して生成する。実装座標を持つ製造用BOMではない。PCBは旧RP2040版のまま変更しておらず、新回路図とのparityや無線版DRCを合格と報告しない。実機起動も未検証。
