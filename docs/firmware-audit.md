# TS52K EC 版：QMK capacitive ブランチのファームウェア監査

作成: 2026-11-12（Opus 5.5、読み取り専用の監査。リポジトリへの変更なし）

## 0. 結論（先に）

- **capacitive ブランチは現存しない。** 2026-08-10 14:36 UTC、フォーク整理のときに `tc69` などと一緒に削除されている（GitHub の activity API で確認）。ただし**コミットは今も SHA を指定すれば GitHub から読める**。今回はそこから原本を回収し、`ref/qmk-capacitive/` に控えた（下の §1）。
- **MCU は RP2040**（Seeed XIAO RP2040、`MCU = RP2040`）。QMK 版は**通常の打鍵まで到達していた**と判断する。根拠は、コミット「keys working」（2023-03-28 04:52 UTC）と、同じ日に打ち癖に合わせて閾値を調整していること、tc69 リポジトリの README が正式ファームとしてこのブランチを指していること。ただし**ビルド成果物は残っておらず、最終状態（upstream マージ後）をビルドして実機で確かめた記録はない**。
- **センシング実装はキーボード側の `keyboards/tc69/matrix.c` 1 ファイル（137 行）だけ**。quantum 側にドライバはない。ADC は QMK 標準の `analogReadPin()` を使う。アルゴリズムは Arduino の `sense.ino` をほぼそのまま移したもので、違いは PURGE の順序と時間だけ（§3.4）。
- **既存コードに不具合がある：ヒステリシスが効いていない**（`sense.ino` にも同じ不具合がある）。押下・解放の 2 つの閾値のうち解放側は死にコードで、実際は「押下閾値 1 本で判定」になっている（§3.3）。TC69 はこの状態で快調だった。
- **TS52K への流用はコード量としては小さい。** マトリクスの大きさを 16 列 × 5 行から 16 列 × 4 行へ変えるだけで済む。TS52K の各行のキー数（15/14/13/11）はすべて 16 以下。現行 QMK の API に合わせる書き換えも機械的な作業で済む。**重いのはコードではなく実機での立ち上げ**：閾値の測り直し、生 ADC 値を見る診断手段（QMK 側には無い）、走査タイミングの固定化（Fable のアナログ報告の要件）の 3 つ。

---

## 1. 原本の所在と回収

| 項目 | 内容 |
|---|---|
| ブランチ `capacitive` の最終 head | `690c285d83dd33b2143bcb818d480e462d238cbc`（2023-04-10、"Merge branch 'qmk:master' into capacitive"） |
| ブランチ `tc69`（旧・先行版）の head | `729ab3c894e023fac8b8f8273d2e7f382c385888`（2022-05-26、"add tc69 keyboard"） |
| 削除日時 | `capacitive` 2026-08-10T14:36:47Z、`tc69` 2026-08-10T14:37:16Z |
| 今回の取得方法 | `gh api repos/sadaoikebe/qmk_firmware/commits/<SHA>` と `contents/...?ref=<SHA>`（どちらも成功） |
| 手元の控え | `~/workspace/ts52k-ec/ref/qmk-capacitive/`：`final/`（capacitive の最終状態の tc69 一式と nicola.c）、`tc69branch/`（2022 版）、`diffs/`（Sadao の 4 コミットの差分） |

**注意（保全の問題）**：ブランチから参照されなくなったコミットは、GitHub 側のガベージコレクションでいずれ読めなくなる可能性がある。いつ消えるかは分からない。`qmk_userspace/docs/HARDWARE-REFERENCE.md` §8 は「ソースは bundle の中にしか無い」としているが、現時点では GitHub からも直接読める。ブランチやタグを打ち直して保全するかは Sadao の判断（この監査は読み取り専用なので何もしていない）。

### capacitive ブランチ上の Sadao のコミット

| SHA | 日時 (UTC) | メッセージ | 内容 |
|---|---|---|---|
| 4ea7efbc8d | 2023-03-26 | not yet passed compiler | `keyboards/tc69/` 新規 6 ファイル。2022 年の `tc69` ブランチの matrix.c と**同一内容** |
| b3ac8db961 | 2023-03-27 | compile error | `users/nicola/` 一式を追加、keymap 修正 |
| 317df36698 | 2023-03-28 04:52 | **keys working** | matrix.c の PURGE 手順を変更、`mcuconf.h` 追加、`ANALOG_ENABLE`、`NKRO` |
| 0c6e358fc5 | 2023-03-28 10:28 | adjust threshold and different threshold for home position | 押下閾値を 200 から 120 へ、A キーだけ別閾値 |
| 690c285d83 | 2023-04-10 | Merge branch 'qmk:master' into capacitive | upstream の取り込み（300 ファイル）。tc69 のファイルは変更なし |

ベースは upstream の `d6ce42ae5b`（2023-03-24）。2022-05 の `tc69` ブランチは KarlK90 の RP2040 対応 PR の上に作られていたが、コミットメッセージどおりビルドが通る前で止まっていた。2023-03 に新しい upstream の上で作り直し、2 日で動かしている。

### Arduino 版との時系列（tc69 リポジトリのコミットから）

- 2022-01-11：Arduino スケッチで「working as normal keyboard」。同じ日に「made xiao rp2040 compatible」
- 2022-01-12：「debounce to ADC hysteresis」「purge time tuning with oscilloscope」（PURGE 6 µs）
- 2023-01-02：`sense.ino` にホームポジション用の閾値を追加。**同じコミットでピン定義を SAMD21 用に切り替えている**（RP2040 用はコメントアウト）。理由はコミットからは分からない
- 2023-03-28：QMK（RP2040）で「keys working」。tc69 の README が QMK capacitive ブランチを指すように更新された

つまり、XIAO SAMD21 で動かしていた時期を挟んで、最終的に RP2040＋QMK に戻ったと読める。tc69 リポジトリのスケッチの現行ピンが SAMD21 なのは、この中間状態が残っているため。

---

## 2. ブランチの構成

```
keyboards/tc69/
  info.json      … processor RP2040, bootloader rp2040, matrix 16 cols × 5 rows, LAYOUT_oyayubi_shift
  rules.mk       … MCU=RP2040, CUSTOM_MATRIX=yes, ANALOG_ENABLE=yes, NKRO_ENABLE=yes, SRC+=matrix.c analog.c
  halconf.h      … HAL_USE_ADC TRUE
  mcuconf.h      … RP_ADC_USE_ADC1 TRUE
  tc69.h         … LAYOUT マクロ（論理 5×16、69 キー、未使用位置は KC_NO）
  matrix.c       … EC センシングのすべて（137 行）
  keymaps/nicola/keymap.c … QWERTY / NICOLA / FUNC の 3 レイヤ
users/nicola/    … 親指シフトの処理（timer_read ベース、TIMER1 は使っていないので RP2040 でも動く）
```

- **quantum 側の改変はない。** EC 専用のドライバも共通コードも作っていない。`CUSTOM_MATRIX = yes`（matrix 処理を丸ごと置き換える方式）で、`matrix_init()`、`matrix_scan()`、`matrix_get_row()` をキーボード側で自前実装している。
- ADC は QMK の `platforms/chibios/drivers/analog.c` の `analogReadPin()` をそのまま使う。
- `tc69.h` の冒頭コメントにある「9 rows 8 cols」は、流用元（TS69 系）のコメントが残っただけ。実際は 5×16。

---

## 3. センシング実装の要点

### 3.1 ピンと走査方式

```
CAP_ROW_PINS { GP2, GP4, GP1, GP0, GP7 }   … 行ストローブ（1 本ずつ HIGH）
CAP_COL_PINS { GP3, GP6, GP27, GP26 }      … 4 bit の列アドレス → 4051 ×2 で 16 列から 1 列を選ぶ
CAP_PURGE    GP28                          … 測定前に LOW を出力して放電、その後入力（Hi-Z）へ戻す
CAP_SENSE    GP29 (ADC3)                   … アンプ出力を ADC で読む
```

`acquire_adc()` の 1 キー分の手順（最終版）：

1. PURGE を出力 LOW にする → `wait_us(20)` → 入力に戻す（放電を解除）
2. 対象の行を HIGH にする → `wait_us(1)`
3. `analogReadPin(CAP_SENSE)` で 1 回変換する
4. 行を LOW に戻す

列アドレスは外側のループで 16 回切り替え、内側で 5 行を回す。**1 回の走査で 80 交点すべてを読む**（69 キーしか無い位置も読む）。

### 3.2 校正

- `matrix_init()` で、まず走査を 3 回して読み捨て、続く 3 回分を合計してキーごとの基準値 `calibration_val[col][row]` にする（単位は「3 サンプルの合計」）。
- **校正は起動時の 1 回だけ**。動作中の再校正、温度ドリフトの追従、EEPROM への保存はない。
- 起動時にキーが押されていると、そのキーは押された状態が基準値になる。その場合は抜き差しするまで反応しないはず（コードからの推論で、実機では確かめていない）。

### 3.3 判定と閾値、および不具合

- 毎回の走査で 1 フレームを 3 段のリングバッファに書き込み、直近 3 フレームの合計 `adc_total` を基準値と比べる（移動加算による簡易ローパス）。
- 閾値（単位は 10 bit ADC のカウント × 3）

| | 押下 | 解放 |
|---|---|---|
| 通常キー | 基準 + 120×3 | 基準 + 30×3 |
| A キー（col 7, row 2。左小指を置く癖への対策） | 基準 + 220×3 | 基準 + 80×3 |

  押下閾値の推移：150（Arduino 初期）→ 200（QMK「keys working」）→ 120（同じ日の調整後）

- `debounce()` は呼ばない（`CUSTOM_MATRIX = yes` なので QMK のデバウンス処理は通らない）。

**不具合：ヒステリシスが機能していない。** `matrix_scan()` の冒頭で `curr_matrix[5] = {0}` と毎回ゼロにしてから判定している。そのため、押下閾値と解放閾値の間の値は「前の状態を維持」ではなく「離した」扱いになる。`else if (< release) clear` の分岐は、ゼロのビットを消しているだけで何もしていない。

- 実際の動作：**`adc_total > 基準 + 押下閾値` のときだけ押下**。閾値は 1 本で、ヒステリシスはない。チャタリングを抑えているのは、3 フレーム移動加算による平滑化だけ。
- `sense.ino` も同じ書き方なので、TC69 は Arduino 時代から一貫して「閾値 1 本＋3 フレーム平均」で快調に動いていたことになる。
- `HARDWARE-REFERENCE.md` §8 は「どちらでもない＝前の状態を維持」「チャタリングが原理的に発生しない」と説明しているが、**実際のコードの動作とは合っていない**。同じ節が載せている閾値（150×3）とスタブの手順（読んでから PURGE）も、最終版ではなく古い版のもの。

TS52K で直すかどうかは、打鍵感に関わる判断になる。直すと解放が「基準 + 30」まで遅れる。現状は 120 を割った時点で解放される。TC69 で慣れた感触は「直していない版」の方。

### 3.4 ADC の使い方

- QMK の analog ドライバ（ChibiOS）は、RP2040 でも 12 bit で変換し、`>> (12 - ADC_RESOLUTION)` で **10 bit に落として返す**（`ADC_RESOLUTION` の既定値が 10 bit）。閾値の 120 や 30 は 10 bit の単位。Arduino 版も `analogRead()` の既定値で 10 bit なので、閾値はそのまま移植できた。brief にある「10-bit ADC でも良好だった」はこの事情による。`config.h` で `ADC_RESOLUTION` を 12 bit にすれば分解能は 4 倍になるが、試していない。
- `analogReadPin()` は呼ぶたびに `palSetLineMode(pin, ANALOG)` を実行し、ChibiOS の `adcConvert()` で 1 回変換して完了を待つ（同期的に待つが、完了通知は割り込み経由）。

### 3.5 タイミング

- **走査周期は実測値がない**（コードにもコミットにも計測の痕跡はない）。待ち時間だけで 1 交点 21 µs、80 交点で 1.7 ms。これに ADC 変換（RP2040 は 1 回約 2 µs）と ChibiOS の呼び出しのオーバーヘッドが加わる。オーバーヘッドの大きさは分からない。
- **行を HIGH にしてから ADC がサンプルするまでの時間は固定されていない。** `wait_us(1)` のあとに `analogReadPin()` のソフト処理（ピンモード設定、ドライバ起動）が入り、割り込みも止めていない。コードはフラッシュ（XIP）上で動く。Fable のアナログ報告（`fable-analog-report.md` §5）は「走査ループを RAM に置く」「測定窓の間は割り込みを止める」「遅延をサイクル数で固定する」を求めているが、**今のコードはそのどれも満たしていない**。TC69 では満たさなくても動いていた、というのが現時点で分かっていること。

### 3.6 Arduino `sense.ino` との差分

| 項目 | sense.ino（tc69 リポジトリの現行版） | QMK matrix.c（最終版） |
|---|---|---|
| 手順 | 行 HIGH → 読む → 行 LOW → PURGE LOW 6 µs → 解除 | PURGE LOW **20 µs** → 解除 → 行 HIGH → **1 µs** → 読む → 行 LOW |
| PURGE の位置 | 読んだ**後**に放電 | 読む**前**に放電（どの交点も直前に必ず放電される） |
| 閾値・ホームキー | 120/30、220/80 | 同じ |
| 校正・リングバッファ | 同じ | 同じ |
| ヒステリシスの不具合 | あり | あり（同じ） |
| ピン | SAMD21 用が有効、RP2040 用はコメント | RP2040（GP 番号は旧 RP2040 用と同じ） |

`sketch_tester/sketch_jan11a.ino`（キャリブレーション差分をシリアルに出す診断用スケッチ）は「PURGE 10 µs → 行 HIGH → 読む」の順で、QMK 版と同じく先に放電している。QMK 版の手順はこのテスター寄りの順序を採ったと読める。

---

## 4. TS52K EC 版へ流用する場合

前提：TS52K は 52 キー（現行 `keyboards/ts52k/keyboard.json` のレイアウトは 53 ポジションで、行ごとに 15 / 14 / 13 / 11）。オンボード RP2040、QMK を想定する。

### 4.1 マトリクス寸法：数字の変更で済む

- TC69 方式（4051 ×2 で 16 列、行ストローブ）をそのまま使えば、**16 列 × 4 行 = 64 交点**に TS52K の全キーが物理行どおりに収まる（各行 15 キー以下）。ファーム側の変更は行数 5 → 4 と LAYOUT の書き直しだけ。
- GPIO は 4 行 + 4 アドレス + PURGE + SENSE = 10 本。**SENSE は GP26〜29（ADC ピン）のどれかが必須**。TC69 は GP26/27 を列アドレスというデジタル用途に使っていた。オンボード RP2040 なら、ADC ピンを SENSE に回し、アドレス線はほかの GPIO へ逃がす割り当てが自然。最終的な割り当ては基板側で決める。
- duplex マトリクスは EC には関係ない（現行 TS52K の duplex スキャンは流用しない）。
- 交点が 80 から 64 に減るので、走査周期は同じ方式のまま約 2 割短くなる。

### 4.2 そのまま使える部分

- アルゴリズム全体：起動時校正、3 フレームの移動加算、基準値との差による閾値判定、PURGE → ストローブ → ADC の順序。
- `users/nicola` は現行の qmk_userspace 版を使う（capacitive 版の nicola は古いが、もともとプラットフォームに依存していない）。

### 4.3 機械的な書き換え（現行 QMK、ローカルの `~/workspace/qmk_firmware` sadao-master で確認）

- GPIO の旧名（`setPinOutput`、`writePin`、`writePinHigh` など）は現行ツリーに**定義が残っていない**。`gpio_set_pin_output()`、`gpio_write_pin()` などへ改名する。
- `ANALOG_ENABLE = yes` と `SRC += analog.c` を **`ANALOG_DRIVER_REQUIRED = yes`** に置き換える（現行 docs/drivers/adc.md の書き方）。
- `info.json` を `keyboard.json` にする。
- `CUSTOM_MATRIX = yes` から `lite`（`matrix_scan_custom()`）へ寄せるかを決める。TS52K の現行定義が lite なので揃えやすい。ただし lite にすると QMK の `debounce()` が後段に入るので、`DEBOUNCE_TYPE` の扱いを決める必要がある。
- コード中に直書きされた `16` と `5`（`acquire_adc` のループ、`int [][5]` の型、`curr_matrix[5]`）を `MATRIX_COLS` と `MATRIX_ROWS` に置き換える。
- 置き場所：`HARDWARE-REFERENCE.md` のとおり、キーボード定義は External Userspace には置けない。sadao-master の `keyboards/` に新しい定義を足すことになる（現行の `keyboards/ts52k/` とは別のキーボード名かリビジョンにする）。
- `mcuconf.h`（`RP_ADC_USE_ADC1`）と `halconf.h`（`HAL_USE_ADC`）が現行 QMK でも必要かは**未確認**。

### 4.4 作り直し・追加が必要な部分（ここが本体）

1. **閾値の測り直し**：閾値はアンプのゲイン、電極パッドの形、基板（層構成や GND）で決まる値なので、TC69 の 120 / 30 は目安にしかならない。TS52K の実機で、全キーの基準値・押下時の値・無操作時のばらつきを採ってから決める。
2. **生 ADC 値の診断手段**：QMK 版には生値を出力する仕組みがない（Arduino 時代のシリアル出力はコメントアウトのまま、QMK に来たときに削除された）。QMK の console（`CONSOLE_ENABLE` と `uprintf`）か raw HID で、生値や基準値との差を出すデバッグ用ビルドを用意する必要がある。tc69 リポジトリの Arduino テスター（`sketch_jan11a.ino`、RP2040 用のピン定義あり）を arduino-pico で使い回す手もある。ただし QMK 側と変換条件がずれる。
3. **タイミングの固定化**（Fable 報告の要件を満たす場合）：`analogReadPin()` の経路では、ストローブから変換開始までの時間がソフトの処理次第で揺れる。走査ループを RAM に置き、割り込みを止め、ADC をレジスタで直接叩く（ChibiOS ドライバを通さない）書き換えが要る。QMK の RP2040 環境から pico-sdk の `hardware_adc` を直接使えるかは**未検証**。TC69 はこれ無しで快調だったので、「最初から必須」か「S/N が足りなかった時の手段」かは、試作の実測で決めるのが妥当。
4. **ヒステリシスの不具合の扱い**（§3.3）：直すか、TC69 の感触を保つため「閾値 1 本」を仕様として明記するか。
5. **ホームポジションの特例**：`is_home_position()` は TC69 の A キーの座標を直書きしている。TS52K では座標を置き換えるか、キーごとの閾値テーブルにする。
6. **起動時校正の弱点**：
   - 押したまま起動するとそのキーが反応しない（推論）。
   - リングバッファが 0 から始まるため、起動直後の 2 フレームは押下を検出できない。そのため、**bootmagic（押しながら挿してブートローダに入る機能）はこのままでは動かない**と考えられる（推論、未確認）。現行 TS52K は bootmagic を有効にしているので、EC 版では RP2040 の BOOTSEL / 物理リセットに頼るか、別の入り方を用意する。
7. **エンコーダ**：現行 TS52K にはロータリーエンコーダがある。EC 版でも残すなら、ストローブやアドレスの GPIO と干渉しない割り当てにし、エンコーダの読み取りが測定窓の割り込み禁止とぶつからないかも確かめる。

### 4.5 作業量の見立て

- コード：matrix.c は約 140 行で、§4.3 の改名と寸法変更は小さい。診断ビルド（§4.4-2）を足しても、**ファームの机上作業は小規模**。
- 実機での立ち上げ：閾値決め、タイミングの固定化を入れるかどうかの判断、校正まわりの手当ては、**試作基板が来てからの反復作業になる**。期間は基板の S/N 次第で、今は見積もれない。
- ブロッカーになりうるもの：基板側で SENSE を ADC ピンに割り当てること、AFE（オペアンプのゲインと基準容量）を決めること。これらはファームではなく回路の論点で、Fable の担当範囲。

---

## 5. 分からないこと（推測で埋めていない）

- capacitive の最終状態（upstream マージ後の 690c285d）を当時ビルドして焼いたのか。TC69 実機の flash の中身が「keys working + 閾値調整」版か、マージ後の版か、どちらでもないのか。（HARDWARE-REFERENCE は実機の吸い出し `picotool save` を推奨しているが、実施記録は見当たらない）
- 実際の走査周期と、ストローブから ADC サンプルまでの実時間。計測の痕跡がない。
- 2023-01 にいったん SAMD21 へ切り替えた理由。
- TC69 で長期的なドリフトや誤爆が実際にあったか。コードと履歴からは読み取れない。Sadao 本人の「快調だった」という証言だけが根拠。
- 現行 QMK で `mcuconf.h` や `halconf.h` の上書きが要るか、RP2040 の ADC を pico-sdk で直接叩けるか。いずれも未検証。
- 現行 QMK でこのコードがビルドできるかは試していない（§4.3 の改名などが必要なことはソースから確認済み）。
