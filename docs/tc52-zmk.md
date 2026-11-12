# TC52（TS52K 静電容量版）の ZMK 構成

> **2026-11-13 追記：ピンと MUX の割当ては基板の確定値に変更済み（QMK sadao-master 366b376d／ZMK zmk-config 97be08b）。本文のピン表（design-spec.md §6.1 の旧ピン）は古い。現行の値は `tc52-firmware-pinsync.md` を見ること。**

作成：2026-11-12（Opus 5.5）。前段は TC69 の ZMK 移植（`tc69-zmk.md`）。正本は design-spec.md §6 と、QMK 移植版 `firmware-rebuild/qmk_firmware` のブランチ `tc52-ec-port`（`81e679ac`）の `keyboards/tc52/`。QMK 側は `git show` で読んだだけで、チェックアウトもコミットもしていない。

**結論：TC52 専用のボード `tc52`（RP2040 オンボード）とシールド `tc52` を作り、通常版と診断版の .uf2 をビルドできた。** 静電容量の走査は TC69 と同じドライバを使う。TC52 の 14 列（MUX アドレス表と走査順）に対応するため、ドライバに任意プロパティを 3 つ足した。プロパティを書かなければ TC69 の動作は変わらない（§5 で確認）。QMK tc52 の matrix.c と ZMK ドライバを同じ疑似 TC52 で並べて動かす差分テストも作り、不一致は 0 件だった。**実機（TC52 基板）はまだ無いので、実機での動作は一切確かめていない。**

| 生成物 | サイズ | SHA-256 |
|---|---|---|
| `zmk-work/out/tc52_zmk.uf2`（通常版） | 87,040 B（170 ブロック） | `dcf4b513f24df506a3afdbe72fc0ae8b0de0ab2bfaef9e83c9ed85d584a03781` |
| `zmk-work/out/tc52_zmk_diag.uf2`（生値ダンプ版） | 135,680 B（265 ブロック） | `dde1ae01e5ef721d1b7e30ed3f1fd22228a649f9cb4ad8b53fd295cd04a922e9` |
| `zmk-work/out/tc69_zmk.uf2`（TC69 通常版、作り直し） | 85,504 B | `3bb49277a8760b73a5d52033598dd73a0b240df9dc5b08eb4dc3bf1301b732bf` |
| `zmk-work/out/tc69_zmk_diag.uf2`（TC69 診断版、作り直し） | 135,168 B | `ac552bca31e62e90eed50ab99dbb880e4e8965513d7d8397ef2fef87e5b894f0` |

- TC52 の 2 本：UF2 の family ID は `0xE48BFF56`（RP2040）、先頭アドレスは `0x10000000`。通常版には診断の文字列（`#ADC seq`、`CHK lo=`）が無く、診断版にはある。
- TC52 通常版は、別のディレクトリでもう一度ビルドしても SHA-256 が一致した（再現性あり）。
- TC69 の .uf2 はドライバのコードが増えたので変わった（`tc69-zmk.md` の値から更新）。動作が変わっていないことは §5 で確かめた。
- コミット：`zmk-work` のローカル git に `d0b979a`。push はしていない。

---

## 1. 置き場

```
zmk-work/
  build.sh                        ./build.sh [tc69|tc52|all]。既定は all（4 本、約 6 分）
  out/tc52_zmk.uf2, tc52_zmk_diag.uf2, build-tc52*.log
  test/run.sh                     TC69 の差分テスト（変更なし）
  test/tc52/run.sh                TC52 の差分テスト（新規、§6）
  zmk-config/
    boards/shobon/tc52/           ボード tc52（新規、§2）
    boards/shields/tc52/          シールド tc52（新規、§3）
    config/tc52.conf              利用者側の設定（空）
    config/tc52_diag.conf         診断版の追加設定
    drivers/kscan/kscan_ec_mux_adc.c        プロパティを 3 つ追加（§4）
    dts/bindings/kscan/shobon,kscan-ec-mux-adc.yaml
    tools/gen_tc52_layout.py      QMK の keyboard.json から tc52-layouts.dtsi を生成
```

ビルドのコマンド（build.sh の中身）：

```sh
west build -p always -s zmk/app -d build/tc52 -b tc52 -- \
  -DSHIELD=tc52 -DZMK_CONFIG=$PWD/zmk-config/config -DZMK_EXTRA_MODULES=$PWD/zmk-config
west build -p always -s zmk/app -d build/tc52_diag -b tc52 -S zmk-usb-logging -- \
  ... -DEXTRA_CONF_FILE=$PWD/zmk-config/config/tc52_diag.conf
```

## 2. ボード定義 `tc52`（方式と判断）

**zmk-config のモジュールの中に、Zephyr の新しいボード形式（HWMv2）でカスタムボードを定義した。** モジュールの `board_root: .` は TC69 のときから設定済みなので、`boards/shobon/tc52/` に置くだけで `-b tc52` が通る。手本は ZMK 本体にある RP2040 オンボードのキーボード（`zmk/app/boards/kbdfans/tofu65`）と、ZMK 用の `rpi_pico//zmk` の設定。素の `rpi_pico` を流用する案は使わなかった（工数が膨らまなかったため）。

| 項目 | 設定 | 出典・理由 |
|---|---|---|
| SoC | RP2040（`select SOC_RP2040`） | — |
| フラッシュ | 16 MB（`DT_SIZE_M(16)`）。boot2 は `RP2_FLASH_W25Q080` | U4 は W25Q128JVS（Rev 0.2 と同じ。tc52-firmware.md §4-4）。W25Q080 用の boot2 は Winbond の QSPI 共通で、QMK の GENERIC_RP_RP2040 と Pico も同じものを使う |
| パーティション | boot2 256 B、コード 15.5 MB、ZMK 設定保存 512 KB（`0xF80000`〜、末尾） | ZMK の `rpi_pico//zmk` と同じ割り方を 16 MB に広げた |
| クロック | 12 MHz の XOSC（rp2040.dtsi の既定）、`startup-delay-multiplier = 64` | X2 12 MHz が XIN、XOUT は未接続（board-inventory.md）。起動待ちは Zephyr の xiao_rp2040 と同じ多め（起動が約 1 ms 遅れるだけ） |
| USB | `zephyr_udc0: &usbd`、`CONFIG_ZMK_USB=y` | J1（USB-C） |
| ブートローダへ入る | `rp2040-boot-mode-retention.dtsi`、`RETENTION_BOOT_MODE` | ZMK の `&bootloader` で BOOTSEL モードに入れる（今のキーマップには割り当てていない）。SW1（裏面の BOOTSEL）でも入れる |
| UART・I2C・SPI・LED | 定義しない | このボードには無い。GPIO0〜2 はエンコーダ、GPIO18〜28 は静電容量の回路 |
| ZMK 対応の印 | `select ZMK_BOARD_COMPAT` | ZMK の「ZMK 用に整えたボード」の印。付けないと警告が出る |
| 書き込みの runner | uf2（`RPI-RP2`）、openocd・pyocd（SWD） | J2 の Tag-Connect は SWD |

キーボードとしての中身（kscan、ピン、エンコーダ）はすべてシールドに置き、ボードには MCU まわりだけを書いた。ボードとシールドが同じ名前 `tc52` なので、ZMK は `config/tc52.conf` を 3 回読み込む（ビルドログに出る）。中身は空なので影響は無い。

## 3. シールド `tc52`

`boards/shields/tc52/`：`tc52.overlay`、`tc52.keymap`、`tc52.conf`、`tc52-layouts.dtsi`（生成物）、`Kconfig.shield`、`Kconfig.defconfig`、`tc52.zmk.yml`。

### 3.1 ピン（design-spec §6.1 と QMK tc52 matrix.c は一致）

| 信号 | GPIO | ZMK での設定 |
|---|---|---|
| ROW1〜4 | 18〜21 | `strobe-gpios`（行 0〜3） |
| S1, S2, S3, S0 | 23, 24, 25, 22 | `mux-gpios`（アドレスの bit 0〜3。QMK の `CAP_COL_PINS` と同じ順で書く） |
| PURGE | 26 | `purge-gpios` |
| ADC（SENSE） | 28 | `io-channels = <&adc 2>`。pinctrl で ADC 機能にするのは GPIO28 だけ（`ADC_CH2_P28`、input-enable なし） |
| 固定 LOW | 27、29 | `&gpio0` の gpio-hog（`output-low`） |
| ENC_A／B | 0／1 | `alps,ec11`、内部プルアップ、`steps = 80`・`triggers-per-rotation = 20`（QMK の resolution 4 ＝ 1 イベントあたり 4 遷移に合わせた） |
| ENC_SW | 2 | `zmk,kscan-gpio-direct`（アクティブ LOW、内部プルアップ）。下記 3.2 |

ストローブ・アドレス・パージの出力は TC69 と同じく 2 mA・低速スルー（`drive-strength-ma = <2>`。QMK/ChibiOS の出力設定に合わせたもの、tc69-zmk.md §4）。

### 3.2 行列

- `zmk,kscan-composite` で 2 つの kscan をまとめて 5 行 × 14 列にした。行 0〜3 が静電容量（`shobon,kscan-ec-mux-adc`）、行 4 がエンコーダの押しボタン（列 0）。QMK tc52 と同じ位置 `[4, 0]` なので、LAYOUT の 53 キーの並びがそのまま使える。
- 列 0〜13 ＝ design-spec の c1〜c14。各列の MUX アドレスと走査順は §4 のプロパティで渡す：
  - `column-addresses = <4 6 7 5 3 0 12 14 15 13 11 8 9 10>`（QMK の `TC52_COL_X | TC52_COL_MUX_B << 3`）
  - `scan-order = <5 4 0 3 1 2 11 12 13 10 6 9 7 8>`（QMK の `TC52_SCAN_ORDER`。MUX A の X0→X7、続いて MUX B の X0→X7）
- 電極の無い 4 交点（r3c4、r3c5、r3c7、r2c13）も QMK と同じく読む（56 交点）。キーマップに位置が無いので、押下と判定されても何も起きない。
- 閾値：押下 120、解放 30、3 フレーム、t_purge 20 µs。ホームキーの特例は `threshold-overrides = <1 1 220 80>`（MX8 ＝ 論理 [1, 1]）。
- t_cap（ストローブ HIGH → ADC）：QMK tc52 の `wait_us(1)` をそのまま採り、`strobe-settle-us = <1>`。

### 3.3 物理レイアウトとキーマップ

- `tools/gen_tc52_layout.py` が QMK の keyboard.json（`git show tc52-ec-port:keyboards/tc52/keyboard.json`）から `tc52-layouts.dtsi`（マトリクス変換と物理レイアウト）を作る。検査：53 キー、5×14、位置の重複なし、MX が 52 個で全部行 0〜3、SW2 ＝ [4, 0]、MX8 ＝ [1, 1]、空の 4 交点は未使用。
- キーマップ `tc52.keymap` は QMK tc52 の `keymaps/default`（TS52K の素の QWERTY）をそのまま移した。QWERTY 層と FUNC 層。SW2 は QMK と同じく何も割り当てない（`&none`）。エンコーダは両方の層で時計回り PgDn、反時計回り PgUp（`&inc_dec_kp PG_DN PG_UP`）。**NICOLA は入れていない（範囲外）。**
- `tc52.conf`：NKRO、`CONFIG_EC11=y`、`CONFIG_EC11_TRIGGER_GLOBAL_THREAD=y`。キーボード名は "TC52"。

## 4. ドライバの拡張

TC52 の列は「アドレス 0〜15 がそのまま列」ではない（14 列、MUX A の X1・X2 は空き、論理列の順とアドレスの順が違う）。overlay だけでは表せないので、`shobon,kscan-ec-mux-adc` に任意プロパティを足した。binding（yaml）にも説明を書いた。

| プロパティ | 意味 | 無いとき（TC69） |
|---|---|---|
| `column-addresses` | 論理列ごとの MUX アドレス。要素数が列数になる | 列数 ＝ 2^（`mux-gpios` の数）、列 c のアドレス ＝ c |
| `scan-order` | 論理列を回る順番 | 0, 1, 2, … の順 |
| `diag-baseline-range` | 診断版だけ。`<下限 上限>` を外れた基準値を `CHK lo=.. hi=..: r<行>c<列>=<値> …` の行で報告する（QMK tc52 の診断と同じ書式・順番） | CHK 行を出さない |

- 走査の中身：`for s in 走査順: c = scan_order[s]; addr = column_addresses[c]; アドレスの全ビットを mux-gpios の順に書く; for 行 …` 。QMK tc52 の `acquire_adc()` と同じ形。
- 起動時に、アドレスが重複していないか・MUX のビット数に収まるか・走査順が全列を 1 回ずつ並べているかを検査し、だめなら初期化を失敗させる。`scan-order` の要素数はビルド時に検査。
- 判定、閾値、校正、リングバッファ、パージ・ストローブの手順には触れていない。
- 診断の出力は論理列の順（c1〜c14）で 14 個ずつ。QMK tc52 の診断と同じなので、**集計は `firmware-rebuild/tools/adc_summary_tc52.py` がそのまま使える**（書式は照合した。実機ログでは未確認）。

## 5. 回帰確認（TC69）

| 確認 | 結果 |
|---|---|
| `test/run.sh`（TC69 の差分テスト、200 通り × 400 走査） | **不一致 0 件**。手順も完全一致。数字は前回と同じ（押下の立ち上がり 153,637 回、コールバック 306,242 回） |
| TC69 通常版・診断版のビルド（`./build.sh all`） | 両方成功 |
| 拡張前のドライバ（コミット `a4ea58d`）で TC69 通常版を組み直して比較 | 旧版は記録どおりの SHA-256 `ba72be23…` を再現した。新旧で **`.config` と `zephyr.dts` は完全一致**。ELF のシンボルで違うのはドライバの `ec_acquire`、`ec_thread_main`（校正が中に展開される）、`kscan_ec_init`、`kscan_ec_config_0` だけ（ほか、コンパイラが付ける表の名前の番号 1 つ） |

TC69 の .uf2 は作り直したので、`tc69-zmk.md` の SHA-256 は古い値になった（上の表が新しい値）。

## 6. TC52 の差分テスト（実機の代わり）

`test/tc52/run.sh`。TC69 のテストと同じ仕組みで、QMK tc52 の `matrix.c` と `tc52_matrix.h`（`git show` で `test/tc52/qmk-src/` に取り出す。git 管理外）と ZMK ドライバを PC 用にコンパイルし、同じ疑似 TC52 の上で動かす。

- 疑似ハードは、HIGH になっている行と S0〜S3 の実際のレベルから「いま読んでいる交点」を割り出して値を返す。列と MUX 入力の対応はテスト側に別に書いた（design-spec §3 ＋ tc52_matrix.h の表）。MUX A の空き入力（X1・X2）を読むと小さい値を返す。値は TC69 のテストと同じく、閾値の上下と**ちょうど等しい値**を多く含む。ホームキー MX8 は 220/80 の上下。
- 比べるもの：(1) 校正から最後までのピン操作・待ち・ADC 読み出しの全手順、(2) 走査ごとの行 0〜3。QMK の行 4（押しボタン）は、ボタンを離した状態で 0 のままであることだけ確かめる。GPIO27・29 の LOW 固定と GPIO2 は、ZMK ではドライバの外（gpio-hog と別の kscan）なので比較から外した。
- 結果（200 通り × 400 走査）：**手順は完全一致、不一致 0 件**（押下の立ち上がり 107,469 回、ホームキーの押下 2,097 走査分を含む）。
- 感度：わざと壊した 4 通り（ドライバが `scan-order` を無視する、`column-addresses` の c7 と c8 を入れ替える、ホームキーの特例を [1, 2] にずらす、t_cap を 2 µs にする）は、4 つとも不一致として検出された。
- **このテストで分かるのは論理（順序・アドレス・判定・単位）の一致まで。** 実時間、ピンの電気的なふるまい、Zephyr のドライバの実際の動きは確かめていない（TC69 と同じ限界、tc69-zmk.md §5）。

## 7. ビルドの警告

4 本とも同じ内訳で、**ドライバ・ボード・シールド由来の警告は 0 件**。

| 警告 | 件数（1 ビルドあたり） | 出どころ |
|---|---|---|
| `-Wunterminated-string-initialization`（picolibc の `chacha_private.h`、`asctime_r.c`） | 21 | 上流（GCC 15 と picolibc の組み合わせ） |
| Kconfig：`SETTINGS_NVS` が選ばれたが choice が決まらない | 1 | 上流。ZMK の RP2040 ボード定義と同じ設定から出る（TC69 の XIAO でも同じ）。ZMK の設定保存（`CONFIG_SETTINGS`）はどちらのビルドでも無効のまま |
| Kconfig：`KSCAN` は非推奨 | 1 | 上流（ZMK が KSCAN を使う） |
| CMake：`drivers__kscan` に SOURCES が無い | TC69 のみ 1 | 上流。TC52 は ZMK の kscan ドライバ（gpio-direct、composite）を使うので出ない |

## 8. design-spec と QMK 移植版の食い違い、どちらを採ったか

ピン（§6.1）と行列の割当て（§3、52 キーと MUX A／B）は一致している。違うのは次の点。**いずれも QMK 移植版（＝TC69 の実績のある動作）を採った。**

| 点 | design-spec | QMK tc52 | ZMK |
|---|---|---|---|
| 電極の無い交点 | §3・§6.2：走査しない（52 交点） | 読む（56 交点。TC69 と同じ） | QMK（指示どおり）。読まない形にするなら、ドライバに「列ごとの行」のプロパティを足す必要がある |
| アドレスのビットの呼び方 | §6.2：bit0 ＝ S0（MUX の選択）、bit1〜3 ＝ MUX 入力 | bit0〜2 ＝ S1〜S3（MUX 入力）、bit3 ＝ S0。ピンを書く順も S1、S2、S3、S0 | QMK。電気的な対応（どのピンがどの MUX 端子か）は同じで、違うのは番号の付け方とピンを書く順だけ |
| 列の走査順 | 表で持つ（順は指定なし） | TC69 と同じ「MUX A の X0→X7、続いて MUX B」 | QMK（`scan-order`） |
| ②〜⑤の割り込み禁止、RAM 上の関数、固定回数の空ループ | §6.2 で指定 | どれも無い（`wait_us`、割り込み許可のまま） | QMK と同じく無い。ZMK では USB 割り込みや優先度の高いスレッドが、ストローブから ADC までの間に入りうる（QMK でも割り込みは入りえた） |
| t_cap | 実機で決める（モデルではピークは約 3.5 µs） | `wait_us(1)` | QMK（1 µs。M3 で見直す） |
| ホームキーの閾値 | §6.3：キーごとの表にし、初期値は全キー同じ | MX8 だけ 220/80（TC69 の A キーの特例） | QMK（ご指示どおり MX8） |
| ヒステリシスを効かせる版 | §6.3：ビルドオプションにする | 無い | 無い（TC69 と同じ「閾値 1 本」） |
| 診断出力 | §6.4：生値は 12 bit、1 交点の連続測定、t_cap・t_purge を実行中に変える手段、走査時間 | 10 bit の値、走査回数／秒、CHK 行 | QMK と同じ（10 bit、`scan_hz`、CHK 行）。§6.4 の 2・3 番目はどちらにも無い |
| エンコーダの押しボタン | §2.1：行列の外の GPIO | 行列の 5 行目に入れる。**デバウンスなし** | 5 行目に入れる（kscan-composite）。**ZMK の gpio-direct の既定デバウンス（押下・解放とも 5 ms）が入る**。キーを割り当てていないので今は影響なし |

QMK 移植版から引き継ぐ「暫定」：

- **MUX 入力の割当て（列 → X0〜X7）は暫定**（tc52-firmware.md §5-1。tc52 作業ブランチの `matrix.py` から取ったもので、基板の配線は未確定）。配線が確定して QMK 側の `tc52_matrix.h` が変わったら、`tc52.overlay` の `column-addresses` と `scan-order`、`test/tc52/zmk52_side.c` と `sim52.c` の表を直して、`test/tc52/run.sh` を流すこと（QMK 側の表を自動で読む仕組みにはしていない）。

ZMK 版だけの違い（QMK tc52 と比べて）：

| 項目 | QMK tc52 | ZMK |
|---|---|---|
| USB VID/PID | 0xFEED / 0x1952 | ZMK の既定 0x1D50 / 0x615E（TC69 の ZMK 版と同じ方針） |
| GPIO27・29 の LOW 固定 | `matrix_init()` の中 | GPIO ドライバの初期化時（gpio-hog）。少し早い |
| フラッシュの大きさ | 既定の 2 MB として扱う（W25Q128 でも動く） | 16 MB と宣言。設定保存の領域は末尾 512 KB。ZMK の設定保存は今は無効なので、実際には書き込まない |
| XOSC の起動待ち | ChibiOS の既定 | ×64（多め） |
| ADC の読み方、待ちの実時間、走査の回し方 | — | TC69 の ZMK 版と同じ違い（tc69-zmk.md §4） |

## 9. 書き込みと診断版の使い方（基板が届いたら）

1. BOOTSEL（SW1、裏面）を押したまま USB を挿す → `RPI-RP2` ドライブが出る → `out/tc52_zmk.uf2`（または `_diag`）をコピー。SWD（J2）なら openocd・pyocd も使える。
2. 起動直後に 1 回だけ校正が走る。挿す瞬間はキーに触らない。
3. 診断版は USB の仮想シリアルに、1 秒ごとに `#ADC` ブロック（CAL／RAW／MIN／MAX／D3／PRS を 4 行分、最後に CHK 行）を出す。開き方は tc69-zmk.md §6 と同じ。集計：`python3 -I ~/workspace/ts52k-ec/firmware-rebuild/tools/adc_summary_tc52.py tc52-zmk-adc.log --csv tc52-zmk-m2.csv`。
4. QMK 版（`firmware-rebuild/out/tc52_default.uf2` など）と入れ替えて比べられる。ZMK の設定保存領域は QMK 版では使われない。

## 10. 未検証のこと・残課題

- **実機では一切動かしていない**（TC52 基板が無い）。起動、USB の認識、校正、打鍵、エンコーダの向き、押しボタン、生値ダンプは、どれも基板が届いてから確かめる。
- **ボード定義は実機で起動を確かめていない。** 特にフラッシュ（W25Q128JVS を W25Q080 用の boot2 で起動する点。QMK も同じ前提で、こちらも未確認）と、12 MHz の XOSC の起動。起動しなければ、まず SWD で止まっている場所を見る。
- エンコーダの回転方向（時計回り ＝ PgDn）は、A／B の配線と ZMK の EC11 ドライバの向きの定義に依存する。QMK と逆になる可能性がある。逆なら keymap の `&inc_dec_kp` の 2 つを入れ替える。
- 1 イベントあたりの遷移数（`steps` ÷ `triggers-per-rotation` ＝ 4）は QMK の resolution 4 に合わせたが、実際のエンコーダのクリック数とは照合していない。
- タイミングの実測（ストローブから ADC までの実時間、走査周期）は TC69 と同じく無い。閾値 120/30・220/80 が TC52 の基板でそのまま合うかは M1〜M6 で決まる。
- 電極の無い交点を読まない形（design-spec §6.2）にするかは未決。読む形でも、keymap に位置が無いので誤入力にはならない。
- ZMK の設定保存（キーマップの書き換えの保存など）は有効にしていない（TC69 と同じ）。
