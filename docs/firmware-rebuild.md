# TC69（静電容量版）ファームの現行 QMK への再構成

作成: 2026-11-12（Opus 5.5）。TS52K 静電容量版（TC52）の先行実施。
**結論：ビルドは成功した（`qmk compile` と `make` の両方で確認）。通常版と ADC 診断版の .uf2 ができている。実機にはまだ書き込んでいない。**

| 生成物 | サイズ | SHA-256 |
|---|---|---|
| `firmware-rebuild/out/tc69_nicola.uf2`（通常版） | 68,096 B（133 ブロック） | `0dd9a41d2d8057770d75885e7a6624d3917a57351762e618cd406293e6000ca7` |
| `firmware-rebuild/out/tc69_nicola_diag.uf2`（生 ADC ダンプ付き） | 69,632 B（136 ブロック） | `3072cab14d05fae7fab5dc083096dd760fc07a4ca6cea2b5ddaf691a3d8dbef3` |

- どちらも UF2 の family ID は `0xE48BFF56`（RP2040）、書き込み先は `0x10000000`（XIP フラッシュ）。
- 同じ入力から 2 回ビルドしても、`make` と `qmk compile` のどちらでビルドしても、SHA-256 は一致した（再現性あり）。
- 警告は 0 件（ビルドログ：`out/build-nicola.log`、`out/build-nicola-diag.log`）。

---

## 1. 置き場と構成

```
~/workspace/ts52k-ec/firmware-rebuild/
  keyboards/tc69/            ← キーボード定義の正本（ここを編集する）
    keyboard.json            info.json + tc69.h の LAYOUT マクロから生成（tools/gen_keyboard_json.py）
    rules.mk  mcuconf.h  matrix.c  readme.md
    keymaps/nicola/          keymap.c、旧 nicola.c / nicola.h（TC69 当時のもの）、rules.mk
  build.sh                   正本を clone へコピーし、通常版と診断版をビルドして out/ へ置く
  out/                       *.uf2 とビルドログ
  tools/gen_keyboard_json.py keyboard.json 生成器（マトリクス位置の照合つき）
  tools/adc_summary.py       診断ログの集計（§6）
  notes/                     原本との差分（matrix.c.diff、keymap.c.diff）と、
                             旧 users/nicola 一式（b3ac8db961 の diff から復元した控え）
  qmk_firmware/              QMK の clone（846 MB、サブモジュール込み）
```

- **QMK の clone**：`firmware-rebuild/qmk_firmware`。既存の `~/workspace/qmk_firmware`（sadao-master、0.33.13 ベース＋ts52k、変更なし・サブモジュール未取得）から `--depth 1` で clone した。既存の clone を汚さず、TS52K と同じベースに載せるため。必要なサブモジュール（chibios、chibios-contrib、pico-sdk、printf）だけを shallow で取得した。tc69 はローカルブランチ **`tc69-ec-rebuild`**（コミット `78105002`）にコミット済み。**push はしていない。** origin の URL は GitHub の sadaoikebe/qmk_firmware に向け直してある。
- **ツールチェイン**：QMK 公式の `qmk_toolchains` v15.2.0-1（arm-none-eabi-gcc 15.2.0）を `~/workspace/qmk-toolchain/qmk_toolchains_linuxX64/` に展開した。home 配下なので VM を入れ替えても残る。apt は使っていない。VM に zstd が無かったため、展開は Python の zstandard で行った。
- **qmk CLI**：`~/workspace/qmk-venv`（qmk 1.2.0 と、QMK の requirements.txt）。
- **ref/ 配下は一切変更していない。**

## 2. ビルド手順と結果

```sh
cd ~/workspace/ts52k-ec/firmware-rebuild
./build.sh        # out/tc69_nicola.uf2 と out/tc69_nicola_diag.uf2 を作る
```

qmk CLI で直接ビルドする場合：

```sh
export PATH=$HOME/workspace/qmk-toolchain/qmk_toolchains_linuxX64/bin:$HOME/workspace/qmk-venv/bin:$PATH
export QMK_HOME=$HOME/workspace/ts52k-ec/firmware-rebuild/qmk_firmware
unset QMK_USERSPACE            # 外部 userspace の users/nicola を混ぜないため
cd $QMK_HOME
qmk compile -c -kb tc69 -km nicola                         # 通常版
qmk compile -c -kb tc69 -km nicola -e TC69_ADC_DIAG=yes    # 診断版
```

実行結果（2026-11-12）：

- `make tc69:nicola` → 成功。`tc69_nicola.uf2` 68,096 B
- `make tc69:nicola TC69_ADC_DIAG=yes` → 成功。69,632 B
- `qmk compile -c -kb tc69 -km nicola` → 成功。SHA-256 は make 版と同じ
- `qmk compile ... -e TC69_ADC_DIAG=yes` → 成功。SHA-256 は make 版と同じ
- `arm-none-eabi-size`（診断版）：text 34,708 / bss 265,680（ChibiOS のスタックとヒープの確保を含む）
- `qmk lint -kb tc69 -km nicola` → 指摘 1 件：「nicola.h にライセンスヘッダが無い」。実際はヘッダが `#pragma once` の後にあるだけ。原本どおりにするため直していない。ビルドには影響しない。

途中で 1 回だけ失敗した：`RGB_MOD` などの旧キーコードが現行 QMK に無かった（§4 で置き換え）。

## 3. 原コードのまま残した部分（挙動は TC69 が正）

`notes/matrix.c.diff` で確認できる。判定ロジックの差分はゼロ。

- **走査手順**（交点ごと）：PURGE を出力 LOW → `wait_us(20)` → 入力（Hi-Z）に戻す → 行 HIGH → `wait_us(1)` → `analogReadPin(GP29)` → 行 LOW。列アドレス（GP3/GP6/GP27/GP26）は外側のループで 16 回切り替え、内側で 5 行を回す。80 交点すべてを読む。
- **ピン**：行 `GP2, GP4, GP1, GP0, GP7`、列アドレス `GP3, GP6, GP27, GP26`、PURGE `GP28`、SENSE `GP29`（ADC3）。
- **閾値**：押下 120×3、解放 30×3。A キー（col=7, row=2、`is_home_position`）は 220×3 と 80×3。
- **起動時校正**：3 回読み捨ててから、3 回分の合計を基準値にする。
- **判定**：3 フレームのリングバッファの合計と基準値を比べる。
- **ヒステリシスの実際の挙動（監査 §3.3）も原コードのまま。** `curr_matrix` を毎回ゼロで初期化するので、解放閾値の分岐は効かない。**実質は「押下閾値 1 本＋3 フレーム移動加算」で判定している。** 直していない。コード先頭のコメントに、意図して残したことを書いてある。
- **`CUSTOM_MATRIX = yes`（フル置き換え）のまま。** `lite` にすると QMK の `debounce()` が後段に入って挙動が変わるので、移行していない。原本と同じく、デバウンスは入らない。
- `matrix_init_kb` / `matrix_scan_kb` / `*_user` の weak 定義も残した。`CUSTOM_MATRIX = yes` のときは `quantum/matrix_common.c` がビルドに入らないため、原本と同じく自前で持つ必要がある。
- USB の VID/PID（0xFEED / 0x6363）、製品名、NKRO、レイアウト（69 キー）。
- **ADC の分解能**：現行 QMK でも 10 bit で返る（12 bit で変換して `>> 2`）。`analog.o` の `adc_read` を逆アセンブルして `lsrs r0, r0, #2` を確認した。閾値の単位は当時と同じ。
- **`wait_us` は RP2040 ではビジーウェイト**（`chSysPolledDelayX`、1 MHz のリアルタイムカウンタ）。スレッドのスリープではないので、20 µs と 1 µs の待ちは原コードの意図どおりに入る。matrix.o が `chSysPolledDelayX` を参照していることを `nm` で確認した。

## 4. 現行化のために変えた部分（機械的な変更のみ）

| 箇所 | 原本 | 現行版 | 理由 |
|---|---|---|---|
| GPIO API | `setPinOutput` / `setPinInput` / `writePin` / `writePinHigh` / `writePinLow` | `gpio_set_pin_output` / `gpio_set_pin_input` / `gpio_write_pin` / `gpio_write_pin_high` / `gpio_write_pin_low` | 旧名は現行ツリーで定義が消えている |
| 寸法 | `16`、`5`、`int [][5]`、`curr_matrix[5] = {0,0,0,0,0}` | `MATRIX_COLS` / `MATRIX_ROWS`。`_Static_assert` で 16 と 5 を固定 | 値は同じ。TC52（16×4）へ移すときの書き換え箇所を減らす |
| ピン配列の型 | `const int` | `const pin_t` | 型を合わせただけで、値は同じ |
| ADC | `ANALOG_ENABLE = yes` ＋ `SRC += analog.c` | `ANALOG_DRIVER_REQUIRED = yes` | 現行 QMK の書き方。これで `-DHAL_USE_ADC=TRUE` も付く |
| halconf.h | `HAL_USE_ADC TRUE` | **削除** | 上の `ANALOG_DRIVER_REQUIRED` が同じ定義を付けるので不要（監査 §5 の未確認事項への答え） |
| mcuconf.h | `RP_ADC_USE_ADC1 TRUE` | **そのまま残した** | 現行の GENERIC_RP_RP2040 の mcuconf.h が FALSE なので、今も必要（同じく §5 への答え） |
| info.json + tc69.h | `LAYOUT_oyayubi_shift` マクロ | `keyboard.json` の `"matrix": [row, col]` | 現行 QMK のデータ駆動の形式。生成器がマクロの本体（行列の並び）と引数を照合してから書き出す。69 キー全部の対応を検証済み（A キー＝[2, 7]） |
| MCU / BOOTLOADER / NKRO | rules.mk | keyboard.json の `processor` / `bootloader` / `features.nkro` | 同上 |
| keymap の FUNC レイヤ | `RGB_RMOD, RGB_MOD, RGB_VAI, RGB_VAD` | `UG_PREV, UG_NEXT, UG_VALU, UG_VALD` | 旧キーコードは現行 QMK で消えている。RGB は元から無効なので、どちらでも押しても何も起きない |
| 診断コード | なし | `#ifdef TC69_ADC_DIAG` の中だけに追加（§6） | 既定 OFF。通常版のバイナリには含まれない（通常版の .uf2 に `#ADC` の文字列が無いことを確認済み） |

## 5. NICOLA（親指シフト）の扱いと経緯

- final/ には `nicola.c` だけがあり、`nicola.h` が無かった。そこで、capacitive ブランチのコミット `b3ac8db961`（"compile error"）の diff から `users/nicola/` 一式（nicola.c、nicola.h、jtu.c、jtu.h、rules.mk など）を復元した。**復元した nicola.c は final/nicola.c とバイト単位で一致した。** 控えは `notes/legacy-users-nicola-b3ac8db961/`。
- **判断：TC69 当時の旧 NICOLA を、keymap ディレクトリの中にそのまま入れて使う。** 現行の `qmk_userspace/users/nicola` は使わない。理由は次のとおり。
  - 「挙動は TC69 そのまま」が前提。現行の userspace 版（NICOLA-SPEC.md に基づく作り直し。defer_exec と F-A〜F-C の修正を含む）は API もキーコード体系も違い、使うと keymap を書き直すことになって挙動が変わる。
  - `users/nicola` という名前のまま置くと、外部 userspace の overlay を使ったビルドで現行版とぶつかる。そこで keymap の rules.mk に `USER_NAME := tc69_legacy_nicola`（存在しない名前）を設定し、どの `users/nicola` も自動では読み込まれないようにした。
- `jtu.c` はビルドに入れていない。唯一の入口である `process_jtu()` の呼び出しが、keymap.c でコメントアウトされているため。リンクしても挙動は変わらない。
- 旧 rules.mk の `BACKLIGHT_ENABLE = no`（AVR の TIMER1 対策）は、既定値が no なので書いていない。
- nicola.c と nicola.h は無改変（どちらも原本と diff で一致を確認済み）。
- **TC52（TS52K 静電容量版）に向けて**：監査 §4.2 のとおり、TC52 では現行の userspace 版 NICOLA を使うのが自然。今回の TC69 再構成は「当時の挙動を再現する基準器」として旧版を固定した。

## 6. ADC 診断手段（M1：TC69 実機での基準値採り用）

- **有効にする方法**：ビルド時に `TC69_ADC_DIAG=yes` を付ける（既定は no）。付けると `CONSOLE_ENABLE = yes` と `-DTC69_ADC_DIAG` が入る。同梱の `out/tc69_nicola_diag.uf2` がこのビルド。
- **判定ロジックには触れない。** 判定が終わった後に、リングバッファと基準値を読むだけ。押下の判定、閾値、マトリクスの状態は変えない。
- **出力**（既定で 1 秒ごと。`TC69_ADC_DIAG_INTERVAL_MS` で変更可）：

```
#ADC seq=<n> t=<ms> scans=<前回ダンプ以降の走査回数> scan_hz=<走査/秒>
CAL r<行>: 16 値   基準値（校正の合計 ÷ 3、10 bit のカウント）
RAW r<行>: 16 値   最新 1 フレームの生値
MIN r<行>: 16 値   前回ダンプ以降の 1 フレーム最小値
MAX r<行>: 16 値   同、最大値
D3  r<行>: 16 値   最新の（3 フレーム合計 − 校正合計）。360 を超えると押下扱い（A キー [r2,c7] は 660）
PRS r<行>: XXXX    判定後のマトリクス行（ビット = 列）
```

  並びは列 0〜15（4051 のアドレス順）。行 0〜4 はストローブの順。キーとの対応は `keyboard.json` の `matrix` を見る。
- `scan_hz` から**走査周期の実測値**も得られる（監査 §3.5 で「実測なし」とされていた点）。診断版は 1 秒に 1 回、出力のために走査が止まる（ダンプの直後の 1 回）。周期の値は、出力時間を除いた区間の平均と考えてよい。

### 手順（M1）

1. `out/tc69_nicola_diag.uf2` を TC69 に書き込む（§7）。
2. PC で `qmk console` を起動する（または hid_listen）。ログはファイルに残す：
   ```sh
   qmk console | tee tc69-adc-$(date +%Y%m%d-%H%M).log
   ```
   Windows の QMK MSYS や QMK Toolbox の HID Console でも読める。
3. **起動時の校正は 1 回だけ。** 挿す瞬間はキーに触れないこと。
4. まず無操作で 30 秒以上置く（ベースラインと揺れを見る）。次にキーを 1 個ずつゆっくり底まで押し、1 秒以上保持してから離す。A キーには小指を軽く置いた状態も採る。
5. 集計：
   ```sh
   python3 -I ~/workspace/ts52k-ec/firmware-rebuild/tools/adc_summary.py tc69-adc-XXXX.log --csv tc69-m1.csv
   ```
   キーごとに、基準値（cal）、無操作時の揺れ（idle_noise ＝ 押されていない区間の MAX − MIN）、押下時のピーク（peak − cal）、D3 のピークを閾値と並べて出す。
6. 終わったら通常版 `out/tc69_nicola.uf2` に書き戻す。

**注意**：ホストがコンソールを開いていない間は、QMK のコンソール出力がタイムアウトしたあと捨てられるので、走査が長く止まり続けることはない。ただし診断版は計測専用で、普段使いは通常版にする。

## 7. 書き込み手順（XIAO RP2040）

1. XIAO RP2040 の **BOOT ボタンを押したまま USB を挿す**（または挿した状態で BOOT を押しながら RESET を押す）。`RPI-RP2` というドライブが現れる。
2. `.uf2` をそのドライブにコピーする。自動で再起動する。
3. 再起動の直後（約 3 走査分）で校正が終わる。その間はキーに触らない。
   - bootmagic は原本と同じく無効。keymap にも `QK_BOOT` は無い。ブートローダへは BOOT ボタンで入る。

**実機に書き込む前にしておくこと（推奨）**：今の TC69 の flash を `picotool save -a tc69-flash-backup.bin` で吸い出して保全する（HARDWARE-REFERENCE.md の推奨。監査 §5 のとおり、実機の中身がどの版かは分かっていない）。

## 8. 未確認のこと・残課題

- **実機では未検証。** ビルドが通ったところまで。TC69 で打鍵と診断出力を確かめるのは M1 の作業。
- 2023 年当時の QMK と今の QMK で、`analogReadPin()` の内部処理（ドライバ起動の管理など）や `wait_us` の実装が同じかは、比べていない。手順と待ち時間は同じだが、ストローブから ADC がサンプルするまでの実時間は、ソフトのオーバーヘッドの分だけ当時と違う可能性がある（監査 §3.5 の「固定されていない」問題は、原本のまま残っている）。M1 の `scan_hz` と、必要ならオシロで確かめる。
- 列アドレスを切り替えた直後に待ちが無いのも原本どおり（直後の PURGE 20 µs が実質的な整定時間になっている）。
- 監査 §4.4 の 3（タイミングの固定化：RAM 実行、割り込み禁止、ADC の直接操作）、5（座標の直書き）、6（起動時校正の弱点）は、TC69 の挙動を保つ方針により手を付けていない。TC52 側で扱う。
- `qmk lint` の nicola.h のライセンスヘッダの指摘は、原本どおりにするため残した。
