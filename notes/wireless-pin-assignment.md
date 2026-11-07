# 無線版GPIO割当て

2026-11-07。MCU周辺の配線開始に合わせ、以下を回路図・PCBへ反映した。続く北側への延長で、交差を避けてMX7へ接続するため41と44のcol1／col3を交換した。ZMK側への反映はまだ行っていない。信号の対応順は、今後の配線に合わせて変更できる。

## 採用した引き出し方針

- 列6本は北側の高駆動可能なパッド41・44・46・48・49と42／43の一方から選ぶ。今回は42を採用、43は未接続。
- 37はUSBに隣接し離れているため避ける。39は採用候補ブートローダーのLED出力。50は標準駆動・低周波限定なので列には使わない。
- 行10本とエンコーダA/Bの12入力は、南側パッド3〜14を使う。
- ダイオードの向きは変えない。列High出力、行内部プルダウン入力の `col2row`。列はZMKで `NRF_GPIO_DRIVE_H0H1` を明示する。
- 南側入力端子に現れる走査信号は10 kHz以下の条件を守る。エンコーダは内部プルアップ。
- 以前の西側列ピン割当ては維持しない。具体的な配線は[現状](../pcb/placement-review/README.md)を参照。

## 現在の回路図・PCBの接続

「パッド」はMDBT50Qの物理端子番号で、GPIO番号とは異なる。

| ネット | GPIO | パッド |
| --- | --- | ---: |
| col1 | P0.20 | 44 |
| col2 | P0.19 | 42 |
| col3 | P0.17 | 41 |
| col4 | P0.22 | 46 |
| col5 | P0.24 | 48 |
| col6 | P0.25 | 49 |
| row1 | P1.11 | 4 |
| row2 | P0.29 | 10 |
| row3 | P0.31 | 12 |
| row4 | P0.28 | 13 |
| row5 | P0.03 | 9 |
| row6 | P1.13 | 6 |
| row7 | P1.15 | 8 |
| row8 | P0.30 | 14 |
| row9 | P0.02 | 11 |
| row10 | P1.14 | 7 |
| rpg1（A） | P1.10 | 3 |
| rpg2（B） | P1.12 | 5 |

SW2のCはGND。押し込み接点はcol6を含む既存マトリクス内に維持し、専用GPIOは追加しない。

## 予約端子・書き込み

| 用途 | GPIO／信号 | パッド |
| --- | --- | --- |
| LF水晶 | P0.00 / XL1、P0.01 / XL2 | 17、18 |
| リセット、SWDのnRESET | P0.18 | 40 |
| ブートローダーLED、基板は未接続 | P0.15 | 39 |
| SWDデータ、クロック | SWDIO、SWDCLK | 51、53 |
| SWDのVTref | nRF_VDD | 28のネットから分岐 |
| USBデータ | D−、D+ | 34、35 |

nRESET・SWDIO・SWCLKは南へ引き出す案を実装中。必要な交差には短いF.Cuとビアを使う。VTrefは近傍のVDDコンデンサから分岐する。

## 電気条件・根拠

[Raytac Version K](https://cdn.sparkfun.com/assets/4/7/4/3/8/_nRF52840__MDBT50Q-1MV2___MDBT50Q-P1MV2_Ver.K_spec.pdf) §2.5–2.6を基準とする。入力用3〜14には「standard drive, low frequency I/O only」の制限がある。列用41・42・44・46・48・49にはこの指定がない。

列の最大9接点同時押し負荷を考慮して高駆動を使う。標準駆動では絶対に動かないと判定したという意味ではない。内部プルダウン以外の抵抗は追加しない。

採用候補のAdafruit nRF52 Bootloader 0.11.0 / nice_nanoは[board.h](https://github.com/adafruit/Adafruit_nRF52_Bootloader/blob/c67f0bcf0fa8e841426335b1bbde91cda6ca1f50/src/boards/nice_nano/board.h)でP0.15をLEDに使う。別ブートローダーを使う場合は、そのピン使用を照合する。秋月の書き込み済みモジュールの詳細は未確認。SWD機材の選定は後日。

## ファームウェアへの引き継ぎ

- `col-gpios`、`row-gpios`をそれぞれcol1〜6、row1〜10の順に設定する。今回の対応は回路図ネットリストとPCBで照合済み。
- 列の高駆動指定には[ZephyrのNordic GPIO定義](https://github.com/zephyrproject-rtos/zephyr/blob/main/include/zephyr/dt-bindings/gpio/nordic-nrf-gpio.h)を使う。
- QSPI等の周辺機能として使わず通常のGPIOとする。nice!nanoの外部電源制御も追加しない。
- エンコーダの回転方向は実機で設定順を確認する。
- 現在の検証UF2は以前の1×1最小構成。新しい18信号の割当て・高駆動設定・走査条件を反映したビルドや実機試験は未実施。
