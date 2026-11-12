# ZMK 4 機種の zmk-config 統合

2026-11-12（Opus 5.5）。**結論：`sadaoikebe/zmk-config` の main（`30e0f6e`）に 4 機種（TS52K 無線、TS52K Rev 0.2 有線＝新規、TC69、TC52）がそろい、ビルドマトリクスの 8 本すべてが VM でビルドできた。** GitHub Actions でも 8 本すべて成功した（§5）。**実機ではどの機種も一切動かしていない。**

## 0. 要点

- リポジトリ全体を 1 つの Zephyr モジュールにした（`zephyr/module.yml`：board_root・dts_root ともに `.`）。ボード、EC ドライバ、NICOLA がすべて `-DZMK_EXTRA_MODULES=<リポジトリ>` だけで読まれる。Actions の標準ワークフローもこの形を前提にしている。
- EC ドライバ（`shobon,kscan-ec-mux-adc`）は 1 つのまま（`drivers/kscan/kscan_ec_mux_adc.c`、移動前とバイト単位で同一、SHA-256 `670aab6f…`）。差分テストもリポジトリへ移して再実行し、TC69・TC52 とも不一致 0（数値も前回記録と同一、§4）。
- NICOLA は全機種共用のモジュールとして直下に置いた。使うかどうかはキーマップ次第（`<behaviors/nicola.dtsi>` を include したときだけ `CONFIG_ZMK_NICOLA` が有効になる）。
- 無線版の未決定事項（6KRO のまま、保留中のエンコーダ回転は確定待ち）は変えていない。無線版の UF2 は、統合前の nicola-zmk から作ったものと **バイト単位で一致**（§3）。
- 新規の有線 TS52K（`ts52k_rp2040`）は、無線版と同じ 53 位置の transform にしたので、素の QWERTY と NICOLA のキーマップをそのまま共用している。
- ts52k リポジトリの KiCad ファイルと `firmware-rebuild/` の QMK クローンには触れていない（KiCad は `git show origin/rp2040:…` で /tmp に出して読んだだけ、QMK も `git show` で読んだだけ）。

## 1. リポジトリの形（main `30e0f6e`）

| 機種 | ボード / シールド | キーマップ | build.yaml の成果物 |
|---|---|---|---|
| TS52K 無線（nRF52840 / MDBT50Q） | `ts52k_mdbt50q/nrf52840`（`boards/ts52k/ts52k_mdbt50q`） | 既定＝`boards/ts52k/ts52k_plain.keymap`、NICOLA＝`nicola/keymap/ts52k_nicola.keymap`（`-DKEYMAP_FILE`） | `ts52k_wireless_nicola`、`ts52k_wireless_plain` |
| TS52K Rev 0.2 有線（RP2040 オンボード） | `ts52k_rp2040`（`boards/ts52k/ts52k_rp2040`、新規） | 無線版と同じ 2 つを共用 | `ts52k_rp2040_nicola`、`ts52k_rp2040_plain` |
| TC69（XIAO RP2040） | `xiao_rp2040//zmk` ＋ シールド `tc69` | `boards/shields/tc69/tc69.keymap`（変更なし） | `tc69`、`tc69_diag` |
| TC52（TS52K 静電容量版） | `tc52`（`boards/shobon/tc52`）＋ シールド `tc52` | `boards/shields/tc52/tc52.keymap`（変更なし） | `tc52`、`tc52_diag` |

主な移動と変更：

| 統合前 | 統合後 | 備考 |
|---|---|---|
| `verification/main/boards/ts52k/ts52k_mdbt50q` | `boards/ts52k/ts52k_mdbt50q` | 中身は無変更。ただし keymap 本体を `boards/ts52k/ts52k_plain.keymap` へ移し、ボードの keymap はそれを include するだけにした |
| `nicola/keymap/ts52k_mdbt50q_nicola.keymap` | `nicola/keymap/ts52k_nicola.keymap` | 生成スクリプト `gen_keymap.py` の出力名と見出しコメントを変更。再生成してバインド部分は差分なし（コメント 2 行のみ） |
| `nicola/dts/`、`nicola/include/` | `dts/`、`include/` | Zephyr の module.yml は dts_root を 1 つしか持てないため、EC の binding と同じ dts_root に寄せた。`gen_ng_codes.py` を再生成して `nicola.h` は差分なし |
| `nicola/zephyr/module.yml`、`nicola/build.sh` | 廃止 → 直下の `CMakeLists.txt`／`Kconfig` から `add_subdirectory(nicola)`／`rsource`、`scripts/build.sh` | NICOLA のリスナ順の ELF 検査は `scripts/build.sh` に移した |
| zmk-work の `zmk-config/`（tc69・tc52・ドライバ・binding・tools）、`test/` | 直下の `boards/`、`drivers/`、`dts/bindings/kscan/`、`config/tc*.conf`、`tools/`、`tests/ec-kscan/` | 内容は無変更（テストのみ include パスを書き換え） |
| `boards/arm/ts52k_bringup`、`config/reviung41.*` | `legacy/` | ZMK v0.3（HWMv1）時代のもの。main 4dd95d78 ではビルドできないので、マトリクスから外して board_root の外へ |
| `config/west.yml`＝ZMK v0.3、Actions＝`@v0.3` | ZMK `4dd95d7840eb…`（Zephyr v4.1.0+zmk-fixes）に固定、Actions の workflow も同じ SHA | zmk-work と同じ版 |

ほかに `README.md`（機種・置き場・ビルド・テストの手順）、`build.yaml`（8 本）、`scripts/build.sh`（build.yaml をそのまま読んでローカルでビルド）を足した。`docs/` の既存 3 文書は、冒頭に「統合後のパス対応」の追記だけを入れ、本文（経緯）は変えていない。

### zmk-work 側

- 旧 `zmk-config/` は west のマニフェストリポジトリだったので、zephyr/module.yml がモジュールとして自動で読まれていた（無線版の `.config` にも `CONFIG_ZEPHYR_TC_EC_MODULE=y` が出ていた）。統合版と同じボード名・binding が二重に読まれるのを避けるため、マニフェストを **`manifest/west.yml`（モジュールなし）** へ移した（`.west/config` の `manifest.path`）。`west list` のプロジェクト・版は切り替え前後で同一（57 行）。再取得は不要だった。
- 旧 `zmk-config/`、`test/`、古い `out/*.uf2` は zmk-work のローカル git から削除（`397a4b0`。中身は `d0b979a` に残る）。`zmk-work/build.sh` は統合版の `scripts/build.sh` を呼ぶ入口にした（`./build.sh tc52` などは従来どおり使える。成果物は zmk-config 側の `out/`、ビルドディレクトリは `zmk-work/build/zc-<名前>`）。
- 統合版の置き場は従来どおり `~/workspace/zmk-config-wireless`（名前は無線版の頃のまま）。

## 2. 有線 TS52K Rev 0.2（`ts52k_rp2040`）の根拠

**正本の食い違い（要確認）**：指定の正本 QMK `keyboards/ts52k`（sadao-master `65726d75`）は **ATmega32U4 版**で、5 本の行ピンにダイオードを逆向き 2 個ずつ付けた duplex マトリクス（論理 10 行 × 6 列）、ピン名は AVR（D2 など）。RP2040 の GPIO 番号は QMK のどこにも無い。そこで：

- **マトリクスの論理位置と LAYOUT の順**は QMK の `keyboard.json` を正とした。
- **GPIO 番号とダイオードの向き**は ts52k リポジトリの `rp2040` ブランチ（`origin/rp2040` `0413811`）の `pcb/ts52k.kicad_pcb` から読んだ。U5（RP2040）のパッドのネット名と、スイッチ・ダイオードのネットから。Rev 0.2 は duplex をやめて 10 本の行ネット（row1〜row10）に分けてあり、ダイオードは全 53 個とも陰極が行側（＝col2row）。
- **照合**：基板上の 53 個のスイッチ（エンコーダの押し込み SW2 を含む）を座標で並べ、行ネット・列ネットから得た [行-1, 列-1] を QMK の LAYOUT と 1 つずつ突き合わせて **53/53 一致**。つまり QMK の論理 [r][c] ＝ 基板の row(r+1)／col(c+1)。無線版の基板定義と同じ対応で、transform は無線版と文字単位で同一（スクリプトで比較）。

| ネット | GPIO | ネット | GPIO |
|---|---|---|---|
| col1 | 22 | row1 / row6 | 2 / 3 |
| col2 | 12 | row2 / row7 | 4 / 5 |
| col3 | 6 | row3 / row8 | 16 / 17 |
| col4 | 13 | row4 / row9 | 18 / 19 |
| col5 | 14 | row5 / row10 | 20 / 21 |
| col6 | 15 | エンコーダ A / B（rpg1 / rpg2） | 0 / 1（基板に 10 kΩ プルアップ R15/R16 と 0.1 µF あり、確認済み） |

- 注意：ts52k の rp2040 ブランチの `pcb/PLACEMENT.md` の「GPIO 割り当て（確定）」の表は、行が row1〜row5 だけの duplex 時代のまま古い（例：col1＝GPIO17）。基板そのもの（と同ブランチ `README.md` の「6 列 × 10 行で配線済み」）が新しい。今回は基板の値を使った。KiCad リポジトリの文書は直していない（触らない約束のため）。
- MCU 周り（12 MHz 発振器、W25Q128JVS 16 MB、BOOTSEL、Tag-Connect）は tc52 ボードと同じ「デジタル島」なので、tc52 のボード定義（boot2 W25Q080、16 MB のパーティション、末尾 512 KB を設定領域、RETENTION_BOOT_MODE、xosc の起動待ち）をそのまま写した。
- キーボード一式（マトリクス、エンコーダ）は 1 枚の基板なので、tc52 のようなシールドには分けず、無線版と同じくボードに置いた。
- 走査：`zmk,kscan-gpio-matrix`、列を出力（active high）、行を入力プルダウン。デバウンス 5 ms（QMK `"debounce": 5`）。
- エンコーダ：QMK の resolution 4 に合わせて tc52 と同じ steps 80 / triggers-per-rotation 20。回転方向は実機で要確認。押し込みはマトリクスの [5][5]（QMK と同じ）。
- **自分で決めた点（見直し可）**：HID は **NKRO**（QMK `keyboard.json` の `"nkro": true` と、tc52/tc69 の先例に合わせた）。無線版の NKRO/6KRO 問題（BLE とブートプロトコル）は有線には当たらないと判断したが、気になるなら `ts52k_rp2040_defconfig` の 1 行を消せば 6KRO になる。キーボード名は QMK と同じ "TS52K"（USB の製品名にも出る）。

## 3. 「挙動を変えていない」ことの確認

統合前の状態（nicola-zmk ブランチのスナップショットと、旧 zmk-work）で 6 本を作り直して基準にし、統合後の同じ機種と比べた。基準の UF2 は過去の記録（`ts52k-nicola-zmk.md`、`tc52-zmk.md`、`tc69-zmk.md`）のハッシュと全部一致したので、基準そのものは正しい。

| 機種 | 統合前（基準） | 統合後 | 比較 |
|---|---|---|---|
| TS52K 無線 NICOLA | `380dea6f…` | `380dea6f…` | **UF2 一致**。`zephyr.dts` 一致、`.config` はモジュール名の行のみ |
| TS52K 無線 plain | `0664f1eb…` | `0664f1eb…` | **UF2 一致**。同上 |
| TC69 / TC69 診断 | `3bb49277…` / `ac552bca…` | `5ed6025b…` / `0d6d4250…` | `zephyr.dts` 一致、`.config` の値はモジュール名以外一致。ELF のシンボル名とサイズの集合が完全一致し、UF2 の大きさも同じ。違いはモジュールの読み込み順が変わったことによる配置（リンク順）だけ |
| TC52 / TC52 診断 | `dcf4b513…` / `dde1ae01…` | `4f748520…` / `baf25c9e…` | 同上 |

## 4. テスト（ホスト）

統合後の置き場で 3 本とも実行した。参照側の QMK は `qmk_userspace` `b7d0ccf`（変更なし）と `firmware-rebuild/qmk_firmware` の `tc52-ec-port` `81e679ac`（`git show` で読むだけ）。

| テスト | 結果 |
|---|---|
| `tests/ec-kscan/run.sh`（EC ドライバ vs QMK tc69 matrix.c、200×400 走査） | **不一致 0**。押下の立ち上がり 153,637、コールバック 306,242（前回と同じ数） |
| `tests/ec-kscan/tc52/run.sh`（EC ドライバ vs QMK tc52 matrix.c） | **不一致 0**。立ち上がり 107,469、ホームキー 2,097（前回と同じ数） |
| `nicola/tests/run.sh`（NICOLA vs QMK users/nicola） | 20,034 シナリオ・674,564 HID 操作で、タイマ遅れ 0/3/15/40 ms、position リスナあり・なしの全条件で **不一致 0**（前回と同じ） |

ドライバのソースはバイト単位で同一（移動のみ）だが、指示どおり EC の差分テストを再実行した。

## 5. ビルド結果

### VM（`scripts/build.sh`、ZMK 4dd95d78 / Zephyr 4.1.0 / arm-none-eabi-gcc 15.2 gnuarmemb、2026-11-12）

8 本すべて成功。成果物は `~/workspace/zmk-config-wireless/out/`（git 管理外）。

| 成果物 | FLASH / RAM（B） | UF2（B） | SHA-256 |
|---|---|---|---|
| ts52k_wireless_nicola | 201,392 / 48,476 | 402,944 | `380dea6f4114de07aec7ebcba659b99469924e0bb2d6424cde122e8f8084707f` |
| ts52k_wireless_plain | 197,044 / 48,100 | 394,240 | `0664f1eb378c7ec6f758d930cf398617008d982f2650850719893a91e6301889` |
| ts52k_rp2040_nicola | 42,952 / 14,484 | 86,528 | `9b5aa8c3ef0a9c02d0f096913f650c4386e6ff3cbaeea5ef77e390430561cb4f` |
| ts52k_rp2040_plain | 38,652 / 14,108 | 77,824 | `adf7e1d1c7361cfaf4cbf6f8d104b855246966bf2157f233defeabfcf09eac3e` |
| tc69 | 42,388 / 19,132 | 85,504 | `5ed6025b60422b8b57afb578c60e38fa8c9fb2a84ead861a00768d412077d505` |
| tc69_diag | 67,236 / 56,724 | 135,168 | `0d6d4250b882d17df8b3e49485d228382bd238d78c3ffa4ee614b814da3b515b` |
| tc52 | 43,148 / 16,220 | 87,040 | `4f74852068618ddef1110af69365dac808086749419bca3e46615ba3ab45d496` |
| tc52_diag | 67,352 / 53,724 | 135,680 | `baf25c9e7abb44896fad6f533907539abec25eb59286aa78040bd1fc26fb9c88` |

- NICOLA を含む 2 本は、ELF のリスナ順（nicola → hid_listener、nicola_position → keymap）を自動検査して OK。
- `ts52k_rp2040_*` の UF2：family `0xE48BFF56`（RP2040）、書き込み範囲 `0x10000000`〜。`.config` で `CONFIG_ZMK_NICOLA=y`（nicola 版のみ）、`NKRO=y`、`EC11=y`、`RP2_FLASH_W25Q080=y` を確認。
- 警告：自前コード由来は 0。残るのは picolibc 内部、`Deprecated symbol KSCAN`（ZMK 本体）、`SETTINGS_NVS` の choice の警告（tc52 の統合前ビルドでも同じものが出ている。ボード defconfig の作法由来）。

### GitHub Actions

run `43225653755`（main `30e0f6e` の push、ZMK の `build-user-config.yml`@4dd95d78、Zephyr SDK のコンテナ）：**全 10 ジョブ success**（マトリクス 8 本＋取得・統合）。2026-11-12 13:16〜13:21 UTC。artifact `firmware` に 8 本の .uf2 がそろっていることをダウンロードして確認（例：tc52.uf2 87,040 B、ts52k_rp2040_nicola.uf2 86,528 B、ts52k_wireless_nicola.uf2 404,992 B）。コンパイラが VM と違うので大きさ・ハッシュは VM の値と一部異なる（§7-5）。

## 6. 再現手順

```sh
cd ~/workspace/zmk-config-wireless          # = sadaoikebe/zmk-config（main）
scripts/build.sh                             # 8 本 → out/（約 20 分）
scripts/build.sh ts52k_rp2040_nicola tc52    # 名前を指定して一部だけ
tests/ec-kscan/run.sh && tests/ec-kscan/tc52/run.sh && nicola/tests/run.sh
```

Sadao の Windows PC：`-DBOARD_ROOT=…/verification/main` と `-DZMK_EXTRA_MODULES=…/nicola` は不要になった。`-DZMK_EXTRA_MODULES=C:/Users/marur/zmk-config` と `-DZMK_CONFIG=…/config`、NICOLA なら `-DKEYMAP_FILE=…/nicola/keymap/ts52k_nicola.keymap`（README.md に例あり）。PC 側の west ワークスペースは ZMK 4dd95d78 のままでよい。PC でのビルドは試していない。

## 7. 未検証・残課題

**実機検証は対象外で、4 機種とも一切動かしていない。** 以下はすべて未確認。

1. **全機種**：実機での打鍵、USB 列挙、設定の保存、`&bootloader`。
2. **ts52k_rp2040（新規）**：基板未製造。マトリクスの全キー、ダイオードの向き（col2row の判断は基板データから）、エンコーダの回転方向、行入力のプルダウンでの読み取り。GPIO の出所が QMK ではなく KiCad の rp2040 ブランチである点（§2）を Sadao に確認してほしい。rp2040 ブランチの `PLACEMENT.md` の GPIO 表が古い件も、KiCad 側で直すかどうか判断が要る。
3. **無線版の未決定事項（変えていない）**：NKRO／6KRO（今も ZMK 既定の 6KRO）、NICOLA 保留中のエンコーダ回転（確定を待って出る）。`docs/ts52k-nicola-zmk.md` §8 のほかの項目（BLE の連続レポートなど）もそのまま。キーボード名も "TS52K Bringup" のまま。
4. **NICOLA を TC69/TC52 で使うか**：モジュールは全機種で読み込まれるが、TC69/TC52 のキーマップは QWERTY のまま。TC52 は TS52K と同じ 53 位置なので `nicola/keymap/ts52k_nicola.keymap` をそのまま当てられる見込み（transform の並びが QMK の LAYOUT 順で同じ）。TC69 は配列が違うので別のキーマップ生成が要る。
5. **Actions の成果物の再現性**：Actions は Zephyr SDK（VM とは別の gcc）でビルドするので、UF2 のハッシュは VM と一致しない。
6. `legacy/` の 1 キー bring-up と REVIUNG41 はビルド対象から外した（ZMK v0.3 前提のため）。要らなければ消してよい。
7. 旧文書（`tc52-zmk.md`、`tc69-zmk.md`、`ts52k-wireless-nicola.md` など）に書かれた `zmk-work/zmk-config/…`、`zmk-work/test/…`、`zmk-work/out/…` のパスは古くなった。対応は §1 の表。
