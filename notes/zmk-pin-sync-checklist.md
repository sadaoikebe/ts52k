# 西端移設後のzmk-config同期チェックリスト

2026-11-10作成。対象はSadaoのPC上の `C:\Users\marur\zmk-config`。
このVMから実ファイルを参照・編集できないため、以下は未実施の引き継ぎ手順。
実在を記録で確認できるファイル名は `docs/ts52k-main-bringup.md` のみ。
基板定義の正確なパス・ノード名はWindows側で特定し、作業記録へ追記する。
本リポジトリの[GPIO表](wireless-pin-assignment.md)と回路図・PCBを接続の基準にする。

## 対象ファイルを特定する

- [ ] `zmk-config` のブランチ・先端・未コミット差分を記録する。
- [ ] リポジトリのルートで次の検索を実行し、TS52Kが実際に読み込む定義を特定する。
  `boards/`、`config/` 等の場所やZephyrの世代による階層を決め打ちしない。

```powershell
Set-Location C:\Users\marur\zmk-config
git status --short
git rev-parse HEAD
git ls-files '*ts52k*' '*.dts' '*.dtsi' '*.overlay' '*.keymap' '*defconfig' '*.conf' 'build.yaml'
git grep -n -E 'col-gpios|row-gpios|a-gpios|b-gpios|gpio-qdec|alps,ec11|EXT_POWER|ext-power|kscan|matrix-transform|sensors'
git grep -n -E 'ts52k|ZMK_CONFIG|BOARD_ROOT|SHIELD|board:|shield:'
```

| 対象ファイル | 変更・照合する対応 |
| --- | --- |
| TS52Kの `*.dts` / 共通 `*.dtsi` と、上書きする `*.overlay` / `*.keymap` | 有効なkscanノードの `col-gpios` / `row-gpios` を下表へ同期。共通定義だけ直してoverlayに旧値を残さない |
| TS52Kのエンコーダを定義する上記ファイル | `a-gpios` / `b-gpios` をrpg1/rpg2へ同期。別のbindingなら、そのA/B入力プロパティを対応させる |
| TS52Kの `*_defconfig` / `*.conf`、上記Devicetree | P0.13を外部電源制御に使うノード・設定が有効になっていないか確認。P0.13はrow3として入力専用 |
| TS52Kの `*.keymap` / マトリクス変換定義 | 列・行の配列順と変換の添字を照合。既存の6列×10行の論理位置・53接点・押し込みのcol6を維持する。旧1×1のままなら本番走査用へ拡張する |
| `build.yaml` / ローカルビルド手順 | 上で特定したTS52Kの定義・overlayが選択されることを確認する |
| `docs/ts52k-main-bringup.md` | 旧1×1ビルドの記録を履歴として残し、新割当て表、実際に変更したパス、ビルド条件、生成物ハッシュ、未検証範囲を追記する |

## 18信号の新旧対照

旧列は2026-11-07のハードウェア表。Windows側でこの旧設定が実装済みかは未確認。
`gpios` の数値はGPIO番号を使い、MDBT50Qの物理パッド番号を渡さない。
配列中の順番はcol1→6、row1→10。GPIO番号の大小で並べ替えない。

| 設定・信号 | 旧GPIO / パッド | 新GPIO / パッド | 新Devicetreeのコントローラ・番号 |
| --- | --- | --- | --- |
| col-gpios / col1 | P0.20 / 44 | P0.25 / 49 | `&gpio0 25` |
| col-gpios / col2 | P0.19 / 42 | P1.09 / 26 | `&gpio1 9` |
| col-gpios / col3 | P0.17 / 41 | P0.08 / 24 | `&gpio0 8` |
| col-gpios / col4 | P0.22 / 46 | P0.06 / 22 | `&gpio0 6` |
| col-gpios / col5 | P0.24 / 48 | P0.04 / 20 | `&gpio0 4` |
| col-gpios / col6 | P0.25 / 49 | P0.27 / 16 | `&gpio0 27` |
| row-gpios / row1 | P1.11 / 4 | P1.15 / 8 | `&gpio1 15` |
| row-gpios / row2 | P0.29 / 10 | P0.31 / 12 | `&gpio0 31` |
| row-gpios / row3 | P0.31 / 12 | P0.13 / 37 | `&gpio0 13` |
| row-gpios / row4 | P0.28 / 13 | P0.21 / 43 | `&gpio0 21` |
| row-gpios / row5 | P0.03 / 9 | P0.22 / 46 | `&gpio0 22` |
| row-gpios / row6 | P1.13 / 6 | P0.29 / 10 | `&gpio0 29` |
| row-gpios / row7 | P1.15 / 8 | P0.30 / 14 | `&gpio0 30` |
| row-gpios / row8 | P0.30 / 14 | P0.17 / 41 | `&gpio0 17` |
| row-gpios / row9 | P0.02 / 11 | P0.20 / 44 | `&gpio0 20` |
| row-gpios / row10 | P1.14 / 7 | P0.24 / 48 | `&gpio0 24` |
| エンコーダA / rpg1 | P1.10 / 3 | P1.11 / 4 | `&gpio1 11` |
| エンコーダB / rpg2 | P1.12 / 5 | P1.13 / 6 | `&gpio1 13` |

## 設定と検証

- [ ] 列6本に `NRF_GPIO_DRIVE_H0H1` を明示し、採用版の
  `dt-bindings/gpio/nordic-nrf-gpio.h` をincludeする。既存の走査極性と組み合わせる。
- [ ] `diode-direction = "col2row"`、行の内部プルダウン、A/Bの内部プルアップを維持する。
  北側の低周波専用端子は入力にのみ使い、高駆動フラグを入力へ複写しない。
- [ ] P0.00/P0.01はLF水晶、P0.18はリセット、P0.15はブートローダLED予約（基板NC）、
  P0.09/P0.10は未使用のまま。nice!nanoの外部電源制御やQSPIのpinctrlで競合させない。
- [ ] **既存UF2のP0.06列・P0.08行の1×1設定も置き換える。** 現PCBではcol4とcol3に当たり、
  新しい行入力へつながらない。全18本を反映したビルドを別の生成物として記録する。
- [ ] クリーンビルド後の `zephyr.dts` で、最終的なGPIO配列の順序、6列・10行、
  エンコーダA/B、プル設定、高駆動フラグ、競合する有効ノードがないことを照合する。
  `.config` では従来の両DC/DC、XTAL/50 ppm、USB/BLE、リセット条件を照合する。
- [ ] ビルドコマンド、ZMK/Zephyr/zmk-configのコミット、変更ファイル、UF2のSHA-256を
  `docs/ts52k-main-bringup.md` に記録する。旧UF2のハッシュを新ビルドの値として使わない。
- [ ] 実機で全キー・同時押し・押し込み・回転方向・休止復帰・USB/BLEを確認する。
  ビルド成功、Devicetree照合、実機試験の結果は分けて記録する。

配置の取り込み判断とWindows側の同期作業は未了。このチェックリストの作成は、
新割当てのファームウェアへの反映・動作確認を意味しない。
