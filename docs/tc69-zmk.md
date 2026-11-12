# TC69 静電容量センシングの ZMK 移植

作成：2026-11-12（Opus 5.5）。正本は QMK 版 `firmware-rebuild/qmk_firmware/keyboards/tc69/matrix.c`（ブランチ `tc69-ec-rebuild`。経緯は `firmware-rebuild.md`）。

**結論：ビルドは通った。通常版と生値ダンプ版の .uf2 ができている。実機には書き込んでおらず、実機での動作は未検証。** 実機の代わりに、PC 上で QMK の matrix.c と ZMK ドライバを同じ疑似ハードで並べて動かす差分テストを作った。ピン操作・待ち時間・ADC 読み出しの順序と、走査ごとのマトリクスが完全に一致した（§5）。

| 生成物 | サイズ | SHA-256 |
|---|---|---|
| `zmk-work/out/tc69_zmk.uf2`（通常版） | 84,992 B（166 ブロック） | `ba72be230893543b6741775ee853152191e6d6abe1c983f0b5b242db45dc5cab` |
| `zmk-work/out/tc69_zmk_diag.uf2`（生値ダンプ版） | 134,144 B（262 ブロック） | `4f789fef9cbb465ea7bd96c285651d79cb432ba14aafba314963b83eba103ffa` |

- どちらも UF2 の family ID は `0xE48BFF56`（RP2040）、先頭アドレスは `0x10000000`。
- 同じソースから 2 回ビルドして SHA-256 が一致した（再現性あり）。
- ドライバ・シールド由来の警告は 0 件。ログに残る警告は上流のものだけ（picolibc の `-Wunterminated-string-initialization`、ZMK の XIAO RP2040 ボード定義が出す `SETTINGS_NVS` の choice 警告、`KSCAN` シンボルの非推奨警告、Zephyr 本体の空ライブラリ `drivers__kscan` の CMake 警告）。
- 作業内容は `zmk-work/` の git（ローカルのみ、push なし）にコミット済み：`a4ea58d`。
- **追記（2026-11-12、TC52 対応）**：ドライバに任意プロパティ（`column-addresses`、`scan-order`、`diag-baseline-range`）を足したため、TC69 の .uf2 を作り直した。新しい SHA-256 は通常版 `3bb49277…`（85,504 B）、診断版 `ac552bca…`（135,168 B）。TC69 の overlay は変えておらず、差分テストは不一致 0 件のまま、`.config` と `zephyr.dts` も旧版と完全一致（詳細は `tc52-zmk.md` §5）。コミット `d0b979a`。

---

## 1. 置き場と構成

```
~/workspace/ts52k-ec/zmk-work/
  build.sh                       通常版と診断版をビルドして out/ へ置く
  out/                           *.uf2 とビルドログ
  test/                          PC 上の差分テスト（§5）。test/run.sh で実行
  zmk-config/                    ← 自前のファイルはすべてここ（west の manifest 兼 Zephyr モジュール）
    west.yml                     ZMK を main @ 4dd95d78（2026-11-12）に固定。Zephyr は v4.1.0+zmk-fixes
    zephyr/module.yml            モジュール名 tc-ec（board_root / dts_root はここ）
    Kconfig, CMakeLists.txt
    drivers/kscan/kscan_ec_mux_adc.c          kscan ドライバ本体
    dts/bindings/kscan/shobon,kscan-ec-mux-adc.yaml
    boards/shields/tc69/         シールド（overlay、keymap、conf、生成した layouts.dtsi）
    config/tc69.conf             利用者側の設定（空）
    config/tc69_diag.conf        診断版の追加設定
    tools/gen_tc69_layout.py     QMK の keyboard.json から tc69-layouts.dtsi を生成
  zmk/ zephyr/ modules/ optional/  west が取得したもの（git 管理外）
  .venv/                         west、ninja、Zephyr の Python 依存
```

- **QMK のクローン（firmware-rebuild/）と ref/ には一切手を入れていない。** keyboard.json と matrix.c は読み出しだけ（レイアウト生成と差分テストの入力）。
- ツールチェーンは QMK 用に展開済みの arm-none-eabi-gcc 15.2（`~/workspace/qmk-toolchain/qmk_toolchains_linuxX64`）を、Zephyr の `gnuarmemb` で使っている。Zephyr SDK は入れていない。libc は picolibc をモジュールからソースビルド。
- `west zephyr-export`（`~/.cmake` への登録）は使わず、build.sh の中で `CMAKE_PREFIX_PATH` を設定している。zmk-work の外は汚していない。

## 2. ビルド手順

```sh
cd ~/workspace/ts52k-ec/zmk-work
./build.sh          # 約 3.5 分。out/tc69_zmk.uf2 と out/tc69_zmk_diag.uf2
```

中身は次の 2 回の `west build`（ボードは ZMK 既存の `xiao_rp2040//zmk`）：

```sh
west build -p always -s zmk/app -d build/tc69 -b xiao_rp2040//zmk -- \
  -DSHIELD=tc69 -DZMK_CONFIG=$PWD/zmk-config/config -DZMK_EXTRA_MODULES=$PWD/zmk-config
west build -p always -s zmk/app -d build/tc69_diag -b xiao_rp2040//zmk -S zmk-usb-logging -- \
  ... -DEXTRA_CONF_FILE=$PWD/zmk-config/config/tc69_diag.conf
```

取り直すとき（VM の入れ替え後など。zmk-work は home 配下なので通常は残る）：`.venv/bin/west update --narrow -o=--depth=1`。

## 3. ドライバの設計

compatible は `shobon,kscan-ec-mux-adc`（ベンダ名は QMK の keyboard.json の manufacturer から）。**寸法・ピン・ADC チャンネル・閾値はすべて devicetree から読む**ので、TC52 は overlay を書くだけで同じドライバを使える。

| プロパティ | TC69 の値 | 意味 |
|---|---|---|
| `strobe-gpios` | GP2, GP4, GP1, GP0, GP7 | 行（ストローブ）。並び = 行番号。行数はこの要素数 |
| `mux-gpios` | GP3, GP6, GP27, GP26 | 列アドレス（ビット 0 から）。列数 = 2^要素数（TC69 は 16） |
| `purge-gpios` | GP28 | パージ。出力 LOW → 入力（Hi-Z、プルなし）に戻す |
| `io-channels` | `<&adc 3>`（GP29） | センス（オペアンプ出力）。12 bit で読む |
| `frames` | 3 | リングバッファの深さ |
| `press-threshold` / `release-threshold` | 120 / 30 | 1 フレームあたり（判定時に ×frames） |
| `threshold-overrides` | `<2 7 220 80>` | `<行 列 押下 解放>` の組。A キー |
| `purge-us` / `strobe-settle-us` | 20 / 1 | ビジーウェイト（`k_busy_wait`） |
| `adc-bits` | 10 | 12 bit の結果を 10 bit に落として判定（QMK と同じ単位） |
| `drive-strength-ma` | 2 | RP2040 のみ。出力ピンの駆動電流（§4） |
| `scan-interval-us` | 0 | 0 = 走査を連続で回す（QMK のメインループと同じ） |

- **走査スレッド**：ZMK が kscan を有効にした時点で専用スレッド（優先度 14＝アプリケーションの最低。プリエンプティブ）を起こし、ADC チャンネルの設定 → 起動時校正 → 走査の連続ループ、の順に進む。1 回の走査ごとに `k_yield()` するだけで、待ちは入れない（`scan-interval-us` で入れられる）。より高い優先度のスレッド（USB、ZMK のワークキュー）は割り込める。
- **キーイベント**：変化した交点ごとに `callback(dev, 行, 列, 押下/解放)` を呼ぶ。順番は行 0→4、各行の中で列 0→15。デバウンスは入れない（QMK もフル置き換えの `CUSTOM_MATRIX` でデバウンスなし）。ZMK の kscan には後段のデバウンスが無いので、QMK と同じく判定結果がそのままイベントになる。
- **XIAO の既定ペリフェラルとの衝突を外した**：SPI0（GP2/3/4）と I2C1（GP6/7）を無効化。UART0（GP0/1）は ZMK のボード定義が元から無効。ADC のピン設定はボード既定だと GP26〜29 を全部アナログにする（列アドレスとパージを奪う）ので、GP29 だけに絞った。
- **キーマップ**：`tc69-layouts.dtsi`（マトリクス変換と物理レイアウト）は QMK の keyboard.json から生成した。生成時に 69 キー、位置の重複なし、A キー＝[2,7] を検査している。

## 4. QMK 版との対応と差分

### そのまま移したもの（差分テストで一致を確認、§5）

- **走査順序**：外側で列アドレス 0〜15 を切り替え、内側で行 0〜4。交点ごとに、PURGE を出力 LOW → 20 µs → 入力に戻す → 行 HIGH → 1 µs → ADC → 行 LOW。列アドレスを切り替えた直後の待ちは無い（原本どおり）。
- **閾値**：押下 120×3、解放 30×3。A キー（行 2・列 7）は 220×3 と 80×3。
- **起動時校正**：3 回読み捨ててから、3 回分の合計を基準値にする。リングバッファは 0 から始まるので、校正直後の 2 走査は押下を出さない（原本と同じ）。
- **判定**：3 フレーム合計 > 基準合計 ＋ 押下閾値×3。
- **ヒステリシスの実挙動**：走査ごとの状態を毎回 0 から作るので、解放閾値の分岐は効かない。**実質は「押下閾値 1 本＋3 フレーム移動加算」。** QMK と同じ構造のまま残し、コメントで意図を書いた。直していない。
- **ADC の単位**：12 bit 変換を 2 bit 右シフトして 10 bit。読み出しに失敗したら 0（QMK の `analogReadPin` と同じ）。

### 変わったもの・変えたもの

| 項目 | QMK 版 | ZMK 版 | 影響と理由 |
|---|---|---|---|
| ADC の読み方 | ChibiOS の `adcConvert`（チャンネル選択 → START_ONCE → 割り込みで完了待ち）。毎回 `palSetLineMode(GP29, ANALOG)` | Zephyr の `adc_read_dt`（チャンネル選択 → START_ONCE → 割り込み → セマフォ） | 手順の形は同じだが、**行 HIGH から ADC が実際に取り込むまでの時間はソフトのオーバーヘッドの分だけ違う**。QMK 版でも固定されていなかった点（監査 §3.5）。未測定 |
| パージの切り替え | `palSetLineMode` でレジスタを直接書く | `gpio_pin_configure_dt` を毎回呼ぶ | パージ解放から行 HIGH までの間隔（センス節点が浮いている時間）が少し長くなる可能性。未測定 |
| 出力ピンの駆動電流 | ChibiOS の `PAL_MODE_OUTPUT_PUSHPULL` は pad を IE のみで設定＝**2 mA、スルー低速、シュミットなし** | Zephyr の GPIO ドライバは pad の駆動電流に触らない（リセット値 4 mA） | ストローブの立ち上がりがキー電極を通ってセンスアンプに乗るので、**駆動電流を QMK と同じ 2 mA・低速スルーに合わせた**（`drive-strength-ma`）。ChibiOS のソースで確認した。入力のシュミットは電気的に影響しないので合わせていない |
| ADC ピン（GP29）の pad | `PAL_MODE_INPUT_ANALOG`＝pad ビットすべて 0（IE なし） | pinctrl で ADC 機能、`input-enable` なし | 合わせた |
| 1 µs の待ち | `wait_us(1)`：1 MHz のタイマでのビジーウェイト（実際は 1〜2 µs） | `k_busy_wait(1)`：CPU サイクルで数えるビジーウェイト（1 µs ちょうどに近い） | **実効の待ちが短くなる可能性**。ADC オーバーヘッドの差と合わせて実機で確かめる |
| 走査の回し方 | メインループで `matrix_scan()` → キーボード処理 → USB → 次の走査 | 専用スレッドで連続走査。キー処理と USB は別スレッド・割り込み | 走査周期は未測定（診断版の `scan_hz` で測れる）。3 フレーム加算なので、周期が変わると押下から報告までの時間が変わる |
| 校正のタイミング | `matrix_init()`（起動処理の中） | ZMK が kscan を有効にした直後（スレッドの先頭） | どちらも起動直後。**挿す瞬間はキーに触らない**のは同じ |
| USB VID/PID・名前 | 0xFEED / 0x6363、"TC69 Oyayubi Shift" | ZMK の既定 0x1D50 / 0x615E、名前は "TC69 Oyayubi Shift" | QMK 版と同時に PC につないでも区別できるよう、VID/PID は ZMK 既定のまま |
| NKRO | 有効 | 有効（`CONFIG_ZMK_HID_REPORT_TYPE_NKRO=y`） | — |
| Menu キーの `LT(_FUNC, KC_APP)` | QMK のタップ判定 | ZMK の `&lt FUNC K_APP`（既定のホールドタップ設定） | 判定のタイミングが少し違う可能性 |

## 5. PC 上の差分テスト（実機の代わり）

`zmk-work/test/run.sh`。QMK の `keyboards/tc69/matrix.c`（正本をそのまま、読み出しのみ）と、ZMK ドライバの .c を、それぞれ GPIO・待ち・ADC だけをスタブにして PC 用にコンパイルし、同じ疑似 TC69 の上で動かす。

- 疑似ハードは、どの行が HIGH か・列アドレスのピンがどうなっているかから、いま読まれている交点を割り出して値を返す（走査順序がずれたら値も合わなくなる）。値はキーごとの基準値＋雑音＋押下量で、押下量は両方の閾値の上下と**ちょうど等しい値**（29/30/31、119/120/121、A キーは 79/80/81、219/220/221）を多く含むようにした。ZMK 側には 12 bit（10 bit 値×4＋下位 2 bit の乱数）を渡し、シフトも確かめている。
- 比べるもの：(1) 校正から最後の走査までの**ピン操作・待ち時間・ADC 読み出しの全手順**（文字列で完全一致）、(2) **走査ごとの 5×16 マトリクス**。
- 結果（200 通り × 400 走査）：**手順は完全一致、マトリクスの不一致 0 件**（押下の立ち上がり 153,637 回を含む）。
- テストの感度も確かめた。ドライバをわざと壊した版（判定を `>` → `>=`、ヒステリシスを「本当に効く」ように変更、パージを 21 µs に変更）は、3 つとも不一致として検出された。
- **このテストで分かるのは論理（順序・判定・単位）の一致まで。** 実時間（ADC が取り込む時刻、走査周期）、ピンの電気的なふるまい、Zephyr のドライバの実際の動きは確かめていない。

## 6. 生値の読み出し（M1 実測用）

- **診断版** `out/tc69_zmk_diag.uf2` は、ZMK の `zmk-usb-logging` スニペットで USB に CDC-ACM シリアルを追加し、そこへ 1 秒ごと（`CONFIG_ZMK_KSCAN_EC_MUX_ADC_DIAG_INTERVAL_MS`）に生値を出す。キーボードとしても普通に動く。
- **出力形式は QMK の診断版（`TC69_ADC_DIAG`）と同じ**なので、集計は既存の `firmware-rebuild/tools/adc_summary.py` がそのまま使える：

```
#ADC seq=<n> t=<ms> scans=<前回以降の走査回数> scan_hz=<走査/秒>
CAL r<行>: 16 値   基準値（校正合計 ÷ 3、10 bit）
RAW r<行>: 16 値   最新 1 フレーム
MIN r<行>: 16 値   前回ダンプ以降の最小
MAX r<行>: 16 値   同、最大
D3  r<行>: 16 値   最新の 3 フレーム合計 − 校正合計（> 360 で押下、A キー [r2,c7] は > 660）
PRS r<行>: XXXX    判定後のマトリクス行（ビット = 列）
```

  起動時に 1 回 `#EC calibrated: rows=5 cols=16 frames=3 press=120 release=30 adc_shift=2` も出る。
- 判定には触れない（判定の後で読むだけ）。ZMK 自身のデバッグログ（キーイベントなど）も同じポートに混ざるが、集計スクリプトは該当行だけを拾う。

### 手順

1. `out/tc69_zmk_diag.uf2` を書き込む（§7）。
2. PC でシリアルポートを開いてログに残す。Linux：`python3 -m serial.tools.miniterm /dev/ttyACM0 115200 | tee tc69-zmk-adc.log`（`screen`、`tio` でもよい）。Windows：デバイスマネージャで COM 番号を見て Tera Term や PuTTY で開き、ログを保存。ボーレートは何でもよい（USB 仮想シリアル）。
3. 挿す瞬間はキーに触らない（起動時の校正は 1 回だけ）。ログ処理スレッドは起動後 1 秒待ってから出力を始める。
4. 測り方は `firmware-rebuild.md` §6 と同じ（無操作 30 秒以上 → 1 キーずつ底まで押して 1 秒保持 → A キーに小指を置いた状態）。
5. 集計：`python3 -I ~/workspace/ts52k-ec/firmware-rebuild/tools/adc_summary.py tc69-zmk-adc.log --csv tc69-zmk-m1.csv`
6. **QMK 版の診断ログと並べると、ZMK 版で基準値・押下量・走査周期がどれだけ変わったかが分かる**（§4 の未測定項目はここで埋まる）。

## 7. 書き込み手順（XIAO RP2040）

1. **書き込む前に、今の TC69 の flash を吸い出して保全する**（`picotool save -a tc69-flash-backup.bin`。`firmware-rebuild.md` §7 と同じ）。
2. BOOT ボタンを押したまま USB を挿す → `RPI-RP2` ドライブが出る → .uf2 をコピー。
3. 再起動直後に校正が走る。その間はキーに触らない。
4. 戻すときは同じ手順で QMK 版の `firmware-rebuild/out/tc69_nicola.uf2` を書く。ZMK 版の設定保存領域（flash 末尾 512 KB）は QMK 版では使われないので、そのままでよい。

## 8. 範囲外

- **親指シフト（NICOLA）の ZMK 実装はこのタスクの範囲外。** キーマップは通常キーだけの最小構成（QMK 版の QWERTY 層と FUNC 層）。`_NICOLA` 層は入れていない。
- FUNC 層の英数・かなキー（QMK の `KC_EISU` / `KC_KANA2`）は、送るキーだけ移した（英数＝INT5 → LANG2、かな＝INT4 → LANG1 のマクロ）。QMK 版でこれらが行っていた `nicola_off()` / `nicola_on()` は無い。
- FUNC 層の RGB キー（`UG_*`）は、QMK 版でも RGB 無効で何もしないので `&none`。

## 9. 未検証のこと・残課題

- **実機では一切動かしていない。** ビルドと PC 上の差分テストまで。打鍵、校正、生値ダンプ、USB の認識は M1 で確かめる。
- **タイミングの実測が無い。** 行 HIGH から ADC 取り込みまでの実時間、パージ解放から行 HIGH までの間隔、走査周期は、QMK 版とも ZMK 版とも測っていない。§4 のとおり ZMK 版はソフトの経路が違うので、**閾値 120/30・220/80 がそのまま合うとは限らない**。診断版で両者の CAL と D3 を比べ、必要ならオシロで行の立ち上がりと ADC の時刻を見る（design-spec §8 M3）。
- 駆動電流を 2 mA に合わせた処理（pico-sdk の `gpio_set_drive_strength`）は、Zephyr がピンを設定し直しても残る前提にしている（Zephyr の RP2040 GPIO ドライバのソースで、pad の駆動電流に触らないことは確認した）。レジスタの実際の値は実機で見ていない。
- 走査スレッドが休みなく回るので、アイドルスレッドは動かない（USB 給電なので電力は問題にしていない）。ZMK のスリープは RP2040 では使っていない。
- 診断版のログは deferred モード（バッファ 16 KB、CDC のリングバッファ 8 KB）。PC がポートを開いていない間や、出力が詰まったときに行が欠ける可能性はある（集計は行単位なので、欠けたブロックは落ちるだけ）。
- ZMK の XIAO RP2040 ボード定義が出す `SETTINGS_NVS` の Kconfig 警告は上流のもので、触っていない。
- TC52 向けには、行 4 本・ピン・ADC チャンネル（GPIO28＝ch2）・パージ（GPIO26）を overlay に書けばよい想定。TC52 の基板では未確認。
