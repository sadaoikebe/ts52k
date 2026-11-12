# TC52（TS52K 静電容量版）の QMK ファーム

> **2026-11-13 追記：ピンと MUX の割当ては基板の確定値に変更済み（QMK sadao-master 366b376d／ZMK zmk-config 97be08b）。本文のピン表（design-spec.md §6.1 の旧ピン）は古い。現行の値は `tc52-firmware-pinsync.md` を見ること。**

作成: 2026-11-12（Opus 5.5）。土台は再構成済みの TC69 ファーム（`firmware-rebuild.md`）。
**結論：ビルドは通った（`make` と `qmk compile` の両方で確認、警告 0 件、`qmk lint` も合格）。通常版と診断版の .uf2 ができている。実機（TC52 基板）はまだ無いので、動作は一切検証していない。**

| 生成物 | サイズ | SHA-256 |
|---|---|---|
| `firmware-rebuild/out/tc52_nicola.uf2`（通常版、NICOLA） | 70,656 B（138 ブロック） | `274e17a10bd711d80925a40d28eefdb66a677612557b6ff509cb496b9b7d1e36` |
| `firmware-rebuild/out/tc52_nicola_diag.uf2`（生 ADC ダンプ付き） | 72,192 B（141 ブロック） | `a2a2244c2665acb9c9f1d4d428f0418ba7d2e97301e51844fabc5ef3aa3e0f8d` |
| `firmware-rebuild/out/tc52_default.uf2`（NICOLA なしの素の QWERTY。配線の切り分け用） | 62,976 B（123 ブロック） | `0d9dbcea362fbdfc498433ee58bea1ee779be775990fb2af3dc4ce442accf11a` |

- 3 本とも UF2 の family ID は `0xE48BFF56`（RP2040）、書き込み先は `0x10000000` から。
- 通常版に診断の文字列（`#ADC seq`、`CHK lo=`）が入っていないこと、診断版には入っていることを確認した。
- `make` と `qmk compile` のどちらでビルドしても SHA-256 は一致する。生成器を再実行（`--regen`）しても同じ。
- TC69 側には手を入れていない（`keyboards/tc69`、`build.sh`、`out/tc69_*.uf2` は変化なし。uf2 の SHA-256 は `firmware-rebuild.md` の値のまま）。`ref/` も読んだだけ。

---

## 1. 置き場と構成

```
firmware-rebuild/
  keyboards/tc52/            ← TC52 定義の正本（ここを編集する）
    keyboard.json            生成物（tools/gen_tc52.py）。手で直さない
    tc52_matrix.h            生成物。列 → MUX 入力の表、走査順、ホームキーの位置
    matrix.c                 TC69 再構成版の matrix.c をコピーして、ボード固有の部分だけ変更
    rules.mk  mcuconf.h  readme.md
    keymaps/nicola/          TS52K の NICOLA keymap と users/nicola 一式（現行版、無改変のコピー）
    keymaps/default/         TS52K の default keymap（無改変のコピー）
  build-tc52.sh              正本を clone へコピーし、3 本をビルドして out/ へ置く（--regen で先に生成器を実行）
  tools/gen_tc52.py          keyboard.json と tc52_matrix.h の生成器（3 つの資料を全位置で照合）
  tools/adc_summary_tc52.py  診断ログの集計（adc_summary.py の TC52 版。4 行 × 14 列、キー名つき）
  notes/tc52-matrix.py       電気的な割当ての控え（~/workspace/tc52/pcb/tc52-build/matrix.py のコピー）
  notes/tc52-matrix.c.diff   TC69 版 matrix.c / rules.mk との差分
```

- QMK の clone（`firmware-rebuild/qmk_firmware`）に、ローカルブランチ **`tc52-ec-port`**（`tc69-ec-rebuild` から分岐、コミット `81e679ac`）で `keyboards/tc52` をコミットした。**push はしていない。** コミットの作者は tc69 のコミットと同じ名義にした。
- 前回の試行の `tools/ts52k_keys.py` と `notes/ts52k-rev02-keys.tsv`（Rev 0.2 のキー抽出）はそのまま入力に使った（下記 §2）。

### ビルド手順

```sh
cd ~/workspace/ts52k-ec/firmware-rebuild
./build-tc52.sh            # out/tc52_nicola.uf2, tc52_nicola_diag.uf2, tc52_default.uf2
./build-tc52.sh --regen    # 割当てや配列の元資料が変わったとき（先に生成器を実行）
```

qmk CLI で直接ビルドする場合（TC69 と同じく、外部 userspace を混ぜないため `QMK_USERSPACE` を外す）：

```sh
export PATH=$HOME/workspace/qmk-toolchain/qmk_toolchains_linuxX64/bin:$HOME/workspace/qmk-venv/bin:$PATH
export QMK_HOME=$HOME/workspace/ts52k-ec/firmware-rebuild/qmk_firmware
unset QMK_USERSPACE
cd $QMK_HOME
qmk compile -c -kb tc52 -km nicola                         # 通常版
qmk compile -c -kb tc52 -km nicola -e TC52_ADC_DIAG=yes    # 診断版
```

`build-tc52.sh` は、同梱した keymap / NICOLA のコピーが qmk_userspace とずれたとき、また `notes/tc52-matrix.py` が tc52 作業ツリーの `matrix.py` とずれたときに **WARNING を出す**（止めはしない）。

## 2. キーボード定義の作り方（生成器 `gen_tc52.py`）

入力は 4 つ。どれか 1 つでも食い違えば assert で止まり、何も書き出さない。

| 資料 | 使ったもの |
|---|---|
| TS52K の `keyboard.json`（clone の `keyboards/ts52k`） | LAYOUT の 53 引数の順番と x/y/w、encoder の resolution、`qmk.locking` |
| `notes/ts52k-rev02-keys.tsv` | Rev 0.2 の各キー（MX 番号）の座標と行・列ネット。TS52K の `[r, c]` ＝ Rev 0.2 の `row(r+1) × col(c+1)` |
| `notes/tc52-matrix.py`（design-spec.md §3 ＋ 列ごとの MUX 入力） | TC52 の電気的な行・列 |
| TS52K の NICOLA keymap（qmk_userspace） | `NG_E_A` の位置 ＝ ホームキー（TC69 の A キーに当たる） |

確認したこと：
- TS52K の 53 位置すべてが Rev 0.2 のキー（MX 52 個＋エンコーダの押しボタン SW2）にちょうど 1 対 1 で対応する。
- LAYOUT の各行の中で、論理の x の順と基板上の x の順が一致し、物理的に同じ段に並んでいる（例外は右端の MX74 と SW2 だけ。どちらも段から外れた位置にある）。
- design-spec.md §3 の 52 キーの集合が Rev 0.2 の MX の集合と一致し、各キーの行（ROW1〜4）が基板上の段と一致する（MX74 は仕様書どおり行 2）。
- MUX 入力は 14 列で重複なし。
- ホームキー：TS52K で `NG_E_A` の位置は **MX8**（Rev 0.2 の row7×col1 ＝ 論理 `[6, 0]`）。TC52 では **c2 × ROW2 ＝ `[1, 1]`**。

TC52 の論理行列は「行 0〜3 ＝ ROW1〜4、列 0〜13 ＝ c1〜c14」。これに 5 行目（行 4）を足して、エンコーダの押しボタンを置いた（§4-3）。LAYOUT の引数は TS52K と同じ 53 個・同じ順番なので、**TS52K の keymap.c が 1 文字も変えずにそのまま入る。**

`tc52_matrix.h` の表（生成物から抜粋）：

```
  col : ROW1  ROW2  ROW3  ROW4   MUX/X
  c1  : MX2   MX3   MX4   MX5    A/X4
  c2  : MX7   MX8   MX13  MX9    A/X6      ← MX8 がホームキー（220/80）
  c3  : MX11  MX12  MX18  MX14   A/X7
  c4  : MX16  MX17  MX22  MX23   A/X5
  c5  : MX20  MX21  MX27  --     A/X3
  c6  : MX25  MX26  MX31  --     A/X0
  c7  : MX29  MX30  MX35  MX60   B/X4
  c8  : MX33  MX34  MX39  --     B/X6
  c9  : MX37  MX38  MX44  MX81   B/X7
  c10 : MX42  MX43  MX48  MX82   B/X5
  c11 : MX46  MX47  MX52  MX58   B/X3
  c12 : MX51  MX56  MX75  MX61   B/X0
  c13 : MX55  MX65  MX66  MX67   B/X1
  c14 : MX64  MX74  --    MX71   B/X2
走査順（論理列）: c6 c5 c1 c4 c2 c3 | c12 c13 c14 c11 c7 c10 c8 c9   （= MUX A の X0→X7、続いて MUX B の X0→X7）
```

## 3. TC69 から引き継いだもの（センシングは TC69 再構成版そのまま）

`notes/tc52-matrix.c.diff` で確認できる。判定ロジックの行は変えていない。

- **交点ごとの手順**：PURGE を出力 LOW → `wait_us(20)` → 入力（Hi-Z）に戻す → 行 HIGH → `wait_us(1)` → `analogReadPin(SENSE)` → 行 LOW。外側で列アドレスを切り替え、内側で行（ROW1→ROW4）を回す。**毎回ストローブの前にパージ**（仕様書の成立条件と同じ）。
- **走査順**：TC69 は 4 bit の列アドレスを 0→15 の順に回していた。TC69 の回路（`ref/out/tc69.net`）と matrix.c を突き合わせると、アドレスの bit0〜2 が S1〜S3（MUX の入力番号）、bit3 が S0（MUX の選択）。つまり TC69 の順は「MUX A の X0→X7、続いて MUX B の X0→X7」。TC52 も同じ順にした（使っていない MUX A の X1・X2 は飛ばす）。アドレスピンを書く順番も TC69 と同じ（S1、S2、S3、S0）。
- **全交点を読む**：TC69 は行列の全交点を読んでいた。TC52 も 14×4＝56 交点すべてを読む（電極の無い 4 交点を含む。keymap 上は位置が無いので押下にはならない）。
- **閾値**：押下 120×3、解放 30×3。ホームキー（MX8）は 220×3、80×3。
- **起動時校正**：3 回読み捨ててから 3 回分の合計を基準値にする。
- **判定**：3 フレームのリングバッファの合計と基準値を比べる。
- **ヒステリシスの実挙動も TC69 のまま**：`curr_matrix` を毎回ゼロで作るので、解放閾値の分岐は効かない（実質「押下閾値 1 本＋3 フレーム移動加算」）。
- `CUSTOM_MATRIX = yes`（デバウンスなし）、`ANALOG_DRIVER_REQUIRED = yes`、`mcuconf.h`（`RP_ADC_USE_ADC1 TRUE`）、ADC は 10 bit（`analogReadPin` の内部で 12 bit を `>> 2`）。`matrix.o` が `chSysPolledDelayX`（ビジーウェイト）と `analogReadPin` を参照していることを `nm` で確認した。
- 生 ADC 診断（§6）も TC69 版と同じ形式で移植した。

## 4. TC52 のために変えたもの（ボード固有の部分だけ）

| 箇所 | TC69 | TC52 | 出典 |
|---|---|---|---|
| 行ピン | GP2, GP4, GP1, GP0, GP7（5 行） | GP18, GP19, GP20, GP21（ROW1〜4） | design-spec.md §6.1 |
| 列アドレス | S1=GP3, S2=GP6, S3=GP27, S0=GP26 | S1=GP23, S2=GP24, S3=GP25, S0=GP22 | 同上 |
| PURGE / SENSE(ADC) | GP28 / GP29（ADC3） | GP26 / GP28（ADC2） | 同上 |
| 列 | アドレス 0〜15 がそのまま列番号 | 14 列。列ごとの MUX と入力番号を表で持つ | §3、§2.1「ファームは表で持つ」 |
| ホームキー | 列 7・行 2（A） | 列 1・行 1（MX8 ＝ TS52K の A） | 下記 §5-4 |
| 追加ピン | — | GP27・GP29 を出力 LOW に固定、GP2（ENC_SW）を入力プルアップ | §6.1 |
| エンコーダ | なし | GP0/GP1、resolution 4（TS52K と同じ） | §2.1、TS52K |
| 押しボタン | なし | 行 4・列 0 に GP2 の生の値を入れる（§4-3） | §2.1 |
| USB | 0xFEED / 0x6363 | 0xFEED / **0x1952**（仮。TS52K は 0x1969） | 新規 |
| 診断のスイッチ | `TC69_ADC_DIAG` | `TC52_ADC_DIAG` | — |
| keymap / NICOLA | TC69 当時の旧 NICOLA | TS52K の現行 NICOLA（qmk_userspace `b7d0ccf6`） | ご指示（TS52K が正） |

補足：

1. **NICOLA**：TS52K の keymap は clone の `keyboards/ts52k` には無く（clone にあるのはキーボード定義だけ）、`~/workspace/qmk_userspace/keyboards/ts52k/keymaps/{nicola,default}` にある。これと `users/nicola`（nicola.c、nicola.h、nicola_table.c、nicola_table.h）を keymap ディレクトリへ無改変でコピーした。TC69 と同じく `USER_NAME` を存在しない名前にして、どの `users/nicola` も自動では読み込まれないようにした。`DEFERRED_EXEC_ENABLE = yes` は users/nicola/rules.mk から写した。
2. **TS52K 定義から持ち込まなかったもの**：bootmagic（TS52K は有効、TC69 と仕様書 §6.3 は無効 → 無効）、`debounce: 5`（TC69 はデバウンスなし → 入れない）、ws2812 / rgblight（ATmega 版の設定。TC52 のピン計画に LED が無い）。
3. **エンコーダの押しボタン**：TS52K では行列の 1 位置（`[5, 5]`、全レイヤーで `KC_NO`）だが、TC52 では GPIO2 直結（仕様書 §2.1）。keymap をそのまま使えるように、行列に 5 行目を足してそこへ入れた。**デバウンスは無い**（`CUSTOM_MATRIX = yes` なので QMK のデバウンスが通らない）。今は `KC_NO` なので害は無いが、キーを割り当てるならデバウンスを足すこと。読むのは静電容量の判定が終わった後で、走査のタイミングには入らない。
4. フラッシュは Rev 0.2 と同じ W25Q128JVS。QMK の既定（GENERIC_RP_RP2040、boot2 は W25Q080 用）のままにした。W25Q 系は同じ命令で動くはずだが、実機で起動するかは未確認。

## 5. 食い違い（潰さずに残したもの）

### 5-1 割当ての元資料について

- **MUX の入力の割当ては暫定。** 仕様書 §2.1 は「列と MUX 入力の対応は配線の都合で自由に決めてよい」としており、仕様書自体には表が無い。今回の表は、作業中の tc52 ブランチ（`~/workspace/tc52/pcb/tc52-build/matrix.py`、06:02 更新、コミット `4db1912` は WIP）から取った。同ファイルのコメントは「配線から決めた」とあるが、`tc52-build-log.md` には配線の記録がまだ無い。**基板の配線が確定したら、matrix.py を `notes/tc52-matrix.py` へコピーし直して `./build-tc52.sh --regen` を実行すること。** ずれていれば build-tc52.sh が WARNING を出す。
- ピン（GPIO0/1/2、18〜26、28）は、tc52 ブランチの回路図生成スクリプト（`gen_sch.py` の `GPIO_NETS`）とも一致していた。GPIO27・29 は回路図では未接続で、ファームが LOW 出力に固定する（仕様書どおり）。

### 5-2 電気（design-spec.md）と論理（TS52K）の間

- **52 キーについては食い違いなし**（§2 の照合がすべて通った）。
- **エンコーダの押しボタンだけが食い違う**：TS52K の論理配列では行列の 1 位置、仕様書では行列の外の GPIO。上の §4-3 のように 5 行目で受けて、論理配列（53 位置）を保った。

### 5-3 仕様書 §6（ファームウェア仕様）と「センシングは TC69 のまま」の間

今回のご指示（TC69 再構成版そのまま）を優先し、仕様書 §6 の次の項目は**入れていない**。どれも打鍵の判定や読み取りのタイミングを変えるので、実機の M1〜M6 の結果を見て Sadao が判断する事項として残す。

| 仕様書 | 内容 | 今回 |
|---|---|---|
| §6.2 | アドレスの bit0 を S0（MUX 選択）とする | TC69 の実配線は bit3 が S0。**TC69 の並び**にした（§3）。電気的な割当て（どのピンが S0 か）は仕様書どおりで、違うのはファーム内部の数え方と走査順だけ |
| §6.2 | 空の交点 4 つは走査しない | TC69 どおり**全交点を読む**。1 走査あたり 4 交点（約 4×22 µs ≒ 0.1 ms）余計にかかる |
| §6.2 | ②〜④を RAM に置く、割り込み禁止、`t_cap` は空ループで固定 | 入れていない。TC69 と同じ `wait_us(1)`＋`analogReadPin()`（仕様書でいう第 1 段そのもの） |
| §6.2 | ADC を 12 bit で読み、判定は `>> 2`、診断は 12 bit で出す | 判定は同じ 10 bit 単位（`analogReadPin` が内部で `>> 2`）。診断の出力も 10 bit |
| §6.3 | ホームの特例は「キーごとの閾値表、**初期値は全キー同じ**」 | ご指示どおり **MX8 に 220/80 を引き継いだ**（TC69 の `is_home_position` の形のまま）。仕様書の初期値とは逆になる |
| §6.3 | 解放 +30 のヒステリシスを効かせる版をビルドオプションで | 入れていない（既定＝TC69 の実挙動、だけ） |
| §6.3 | 校正のベースラインが範囲外（5 未満／600 超）のキーを報告 | **診断版にだけ入れた**（`CHK` 行。報告だけで判定には触れない） |
| §6.4 | 診断：1 交点の連続測定、`t_cap`／`t_purge` を実行中に変える | 入れていない。全交点のダンプと走査周期（`scan_hz`）は TC69 版の形式で出る |
| §6.1 | PURGE と ADC のデジタル入力バッファを切る | TC69 どおり PURGE は普通の入力（Hi-Z）。ADC ピンは `analogReadPin` がアナログモードにする |
| §6.3 | ブートローダへは BOOTSEL か `QK_BOOT` | TS52K の keymap に `QK_BOOT` が無いので BOOTSEL だけ |

## 6. 生 ADC 診断（既定 OFF）

- **有効にする方法**：`TC52_ADC_DIAG=yes` を付けてビルド（`CONSOLE_ENABLE = yes` と `-DTC52_ADC_DIAG` が入る）。同梱の `out/tc52_nicola_diag.uf2` がこれ。判定の後に読むだけで、閾値・行列の状態は変えない。
- **出力**（既定で 1 秒ごと。`TC52_ADC_DIAG_INTERVAL_MS` で変更可）。並びは論理列 0〜13（＝ c1〜c14）、行 0〜3（＝ ROW1〜4）。TC69 版と同じ形式で、最後に `CHK` 行が付く：

```
#ADC seq=<n> t=<ms> scans=<前回以降の走査回数> scan_hz=<走査/秒>
CAL r<行>: 14 値   基準値（校正の合計 ÷ 3、10 bit）
RAW r<行>: 14 値   最新 1 フレーム
MIN r<行>: 14 値   前回ダンプ以降の最小
MAX r<行>: 14 値   同、最大
D3  r<行>: 14 値   最新の（3 フレーム合計 − 校正合計）。360 超で押下（ホームキー r1c1 は 660）
PRS r<行>: XXXX    判定後の行（ビット = 列）
CHK lo=<n> hi=<n>: r<行>c<列>=<基準値> ...   基準値が 5 未満／600 超の交点（報告だけ）
```

- **集計**：`python3 -I ~/workspace/ts52k-ec/firmware-rebuild/tools/adc_summary_tc52.py tc52-adc-XXXX.log --csv out.csv` で、交点ごとに MX 番号つきで基準値・無操作時の揺れ・押下ピーク・D3 のピークを閾値と並べる（偽のログで動作だけ確認済み）。
- 手順は `firmware-rebuild.md` §6 の TC69 と同じ（`qmk console | tee ...`、挿す瞬間はキーに触れない、まず無操作 30 秒、次に 1 キーずつ）。

## 7. 書き込み（基板が届いたら）

1. BOOTSEL を押したまま USB を挿す → `RPI-RP2` ドライブへ .uf2 をコピー。
2. 挿した直後の校正（約 6 走査分）の間はキーに触らない。
3. 立ち上げの順の提案：まず `tc52_default.uf2`（素の QWERTY）で全キーが正しい位置に出るかを見る → 診断版で生値を採る → 通常版。

## 8. 未検証のこと・残課題

- **実機では何も確かめていない。** TC52 基板はまだ無い（基板は tc52 ブランチで作業中）。打鍵、閾値の妥当性、校正、エンコーダの向き、押しボタン、USB の列挙、フラッシュからの起動、すべて未確認。
- **閾値は TC69 の値をそのまま使っている。** 仕様書 §7 の推定では TC52 の感度は 88〜94 カウント/pF（TC69 は 96）で、同じ閾値でも容量換算でわずかに鈍くなる。合わせ込みは M6。
- MUX 入力の表は暫定（§5-1）。配線確定後に再生成が要る。
- 仕様書 §6 の未導入項目（§5-3 の表）は、TC69 の挙動を基準にした今回の方針で保留にしたもの。
- USB の PID 0x1952 は仮に決めた値。
- `qmk lint` は合格（TC69 のような nicola.h のヘッダの指摘も無い）。
