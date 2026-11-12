# 無線 TS52K（nRF52840 / ZMK）への親指シフト（NICOLA）実装

2026-11-12。**ビルド成功・QMK 版との差分テスト一致まで。実機では一切動かしていない。**
同じ内容を zmk-config のブランチ `nicola-zmk` の `docs/ts52k-nicola-zmk.md` にも置いた（Sadao の PC から読めるように）。

## 0. 結論

- QMK の現行 NICOLA（qmk_userspace master `b7d0ccf`、F-A/F-B/F-C 修正込み）を、ZMK のモジュールとして移植した。判定エンジンは QMK の `nicola.c` をほぼそのまま写し、QMK の API を呼ぶ箇所だけ差し替えた。出力表とキーマップは QMK のソースからスクリプトで機械生成した（手で書き写していない）。
- 全キーがエンジンを通る。NICOLA キーは独自 behavior、それ以外のキーは ZMK のキーコードイベントを `hid_listener` の手前で受けるリスナで処理し、保留中はイベントごと飲み込んで後で流す（QMK の追い越し防止バッファに当たる）。
- 出力は QMK と同じく「押下を保持し、物理キーの解放で解放する」。タップ列にはしていない。
- ファームのビルドは成功（.uf2 あり）。QMK の本物のソース（nicola.c / nicola_table.c / keymap.c）をホストでコンパイルした参照と、ZMK 側の本物のソース（エンジン＋ZMK グルー＋生成キーマップ）を同じ入力列で動かし、**20,034 シナリオ・674,564 回の HID 操作で完全一致**。ZMK 側のタイマ処理を最大 40 ms 遅らせても一致する。
- 未決・要判断は §8（主に NKRO、エンコーダの押し込みキー、実機での BLE 試験）。

## 1. 対象と版

| 対象 | 版・場所 |
|---|---|
| zmk-config | `~/workspace/zmk-config-wireless`（`https://github.com/sadaoikebe/zmk-config.git` を clone）。作業ブランチ **`nicola-zmk`**。分岐元は `pin-sync-2026-11-11`（`a6613ee`、2026-11-11 に Sadao の PC で 18 ピン同期・クリーンビルド確認済みの状態）。main は触っていない |
| 基板定義 | `verification/main/boards/ts52k/ts52k_mdbt50q`（pin-sync のまま無変更） |
| ZMK / Zephyr | ZMK `4dd95d7840eb3d5a3f59bb29fbf1ab054715ef85`、Zephyr `10ba6d0cb38bc3d258775d27982f707599320085`（4.1.0）。PC の記録と同じ版。VM では既存の west ワークスペース `~/workspace/ts52k-ec/zmk-work` を流用 |
| 意味論の正 | `~/workspace/qmk_userspace` master `b7d0ccf604ddc0418781cc729344882b261b2474`（作業ツリーの変更なし）。`users/nicola/*`、`keyboards/ts52k/keymaps/nicola/keymap.c`、`docs/NICOLA-SPEC.md` |
| QMK のキーコード定義（テスト用ヘッダのみ） | `~/workspace/ts52k-ec/firmware-rebuild/qmk_firmware`（`81e679ac`）の `quantum/keycodes.h` 等 |

## 2. ベースライン（現状確認）

- `config/west.yml` と GitHub Actions はまだ ZMK v0.3（旧 1 キー bring-up 用）。現行の基板定義は ZMK main 4dd95d78 を `-DBOARD_ROOT=verification/main` で指してローカルビルドする方式（`docs/ts52k-main-bringup.md`）。今回もそれに従った。Actions と west.yml は触っていない。
- VM には Zephyr SDK が無いので、QMK 用に入れてある arm-none-eabi-gcc 15.2 を `ZEPHYR_TOOLCHAIN_VARIANT=gnuarmemb` で使った（TC69/TC52 の ZMK と同じ方法。nRF52840 でもそのまま通った）。
- pin-sync 版（素の QWERTY）を VM で再ビルドした結果:
  - 生成 `zephyr.dts` は、PC の記録 `docs/baseline/main-ts52k-pinsync/zephyr.dts` と **完全一致**（コメント行以外）。
  - `.config` の差は、ツールチェインと libc の選択（gnuarmemb＋picolibc モジュール vs Zephyr SDK 0.16.3）に由来する項目だけ。両 DC/DC、XTAL/50ppm、USB/BLE、EXT_POWER 無効などは同じ。
  - FLASH 197,044 B（PC は 198,024 B。コンパイラが gcc 15.2 と 12 で違うため）。UF2 のハッシュは PC の `86232bd5…` とは当然一致しない。
  - VM の zmk-work ワークスペースには TC69/TC52 用のモジュール `tc-ec` がマニフェストとして入っており、`.config` に `CONFIG_ZEPHYR_TC_EC_MODULE=y` が出る。中身は対応する DT ノードが無いと何もコンパイルしない（生成 dts が PC と一致することで確認）。

## 3. 設計

### 3.1 全体構成

```
kscan → physical_layouts(msgq, システムワークキュー) → position_state_changed
   ├─ [nicola_position リスナ]  期限切れのタイムアウトを先に発火 (ng_advance)
   └─ keymap: キーを behavior に解決（押下時のレイヤー状態を位置ごとに記憶）
        ├─ &ng NG_*        → ng_zmk_key()  → エンジン (M / O キー)
        ├─ &ng_mode …      → ng_zmk_mode() → かな/英数切替＋ホストへの切替コード
        ├─ &mo 2           → レイヤー (エンジンを通らない。QMK の MO と同じ)
        └─ &kp X           → keycode_state_changed
                               ├─ [nicola リスナ]  modifier を数える (ゲート2)、
                               │     保留中ならイベントをコピーして CAPTURED
                               └─ hid_listener → HID レポート
エンジンの出力: keycode_state_changed を raise（nicola リスナは素通し）→ hid_listener
保留の確定時: 捕まえたイベントを ZMK_EVENT_RELEASE で hid_listener へ（積んだ順）
タイムアウト: k_work_delayable（システムワークキュー）→ ng_timer_expired()
```

### 3.2 エンジン本体と ZMK 依存の分離

| ファイル（`nicola/` 以下） | 中身 |
|---|---|
| `src/core/ng_engine.c/.h` | 判定エンジン。QMK `nicola.c` を機械的に写し、QMK API の呼び出しを「ポート関数」に置換した箇所だけ `[ZMK]` と書いてある。5 状態の遷移（`nicola_on_m_press` / `nicola_on_o_press` / `nicola_on_release`）は QMK 版と 1 行も違わない（`diff` で確認）。Zephyr/ZMK のヘッダを一切 include しない |
| `src/core/ng_table.c/.h`、`ng_kc.h` | 出力表。`tools/gen_ng_table.py` が QMK の `nicola_table.c` から生成（表の行はそのまま、include と PROGMEM だけ置換）。`KC_*` の値は QMK の `keycodes.h` から引く（QMK の基本キーコード＝HID usage） |
| `include/dt-bindings/zmk/nicola.h` | `NG_*` の番号。`tools/gen_ng_codes.py` が QMK `nicola.h` の enum から生成。範囲比較で分類するので順序が意味を持つ。値は SAFE_RANGE からのオフセット（NG_TOP=0） |
| `src/zmk/ng_zmk.c` | ポート関数の実装、キーコード／position リスナ、タイマ、`ng_zmk_key` / `ng_zmk_mode` |
| `src/zmk/behavior_nicola_{key,mode}.c` | 薄い behavior（引数をそのまま ng_zmk.c へ渡すだけ） |
| `dts/`、`Kconfig`、`CMakeLists.txt`、`zephyr/module.yml` | ZMK モジュールとしての登録。`CONFIG_ZMK_NICOLA` は `&ng` ノードがあれば自動で有効。`CONFIG_ZMK_NICOLA_LAYER`（既定 1） |
| `keymap/ts52k_mdbt50q_nicola.keymap` | `tools/gen_keymap.py` が QMK の `keymaps/nicola/keymap.c` から生成。53 位置の順は基板の default_transform（＝QMK の LAYOUT 順、pin-sync で照合済み） |
| `tests/` | 差分テスト（§5） |
| `build.sh` | VM 用ビルド（plain と nicola の 2 本）。リスナの並び順を ELF で検査する |

ポート関数（`ng_engine.h` 末尾）: `ng_port_key(usage, pressed, shift)`、`ng_port_replay(slot)`、`ng_port_layer(layer, on)`、`ng_port_get_mods()`、`ng_port_timer_start(deadline)` / `ng_port_timer_cancel()`。ZMK 実装とホストテストの両方がこれを実装する。

### 3.3 全キーがエンジンを通る仕組み（追い越し防止）

- 調査メモの懸念どおり、NICOLA キーだけ behavior にしても通常キーの追い越しは防げない。そこで **キーコードイベント（`zmk_keycode_state_changed`）のリスナ**を `hid_listener` より前に置いた。`&kp` に限らず、キーコードを出す全 behavior の出力がここを通る。
- 保留中（S_INIT 以外）は、エンジンが枠番号（0〜7）を返し、リスナはイベントを `copy_raised_…` でコピーして `CAPTURED` を返す。エンジンが保留を確定したときに `ng_port_replay(枠)` → `ZMK_EVENT_RELEASE` で、捕まえたリスナの次（`hid_listener`）から処理を再開する。hold-tap が使っているのと同じ ZMK の仕組み。
- 8 枠が満杯のとき、9 個目は「保留を吐き出してから通す」（QMK と同じ）。
- **リスナの並び順はリンク順で決まる。** モジュールのソースは ZMK 本体より先に `app` に追加されるので前に来る。`build.sh` が ELF のシンボル順で確認し（結果: keycode は `nicola → hid_listener`、position は `nicola_position → activity → keymap`）、起動時にも `check_listener_order()` が確かめてログに出す。
- エンジン自身が raise したイベントと、かな/英数キーのホスト用コードは、`emitting` フラグで素通しする（QMK でも `register_code` 直呼びで `process_nicola` を通らない）。
- QMK の「再生可能なキー」（basic と QK_MODS）に当たるのは、ZMK ではキーコードイベントになるもの全部。`&mo`（QMK の `MO()`）はイベントを出さないので素通り＝QMK と同じ。

### 3.4 時刻とタイマの直列性

- **直列性**: ZMK では、走査結果の処理（`physical_layouts` の msgq を k_work で処理 → keymap → behavior）、キーコードリスナ、エンジンのタイマ（`k_work_delayable` を `k_work_reschedule` でシステムワークキューへ）がすべて **システムワークキュー（協調スレッド）** で動く。エンコーダ（EC11 の GLOBAL_THREAD → sensors → behavior_queue）も同じキュー。互いに割り込まないので、QMK の「defer_exec のコールバックは process_record_user と同じ文脈」と同じ前提が成り立つ。排他フラグは要らない。ZMK 4dd95d78 のソース（physical_layouts.c、sensors.c、behavior_queue.c、ec11_trigger.c）で確認した。
- **時刻**: イベントのタイムスタンプを使う。ZMK の position イベントの timestamp は msgq を処理した時点の `k_uptime_get()` で、QMK の `timer_read()`（走査処理時点）と同じ意味。間隔 t1/t2 は QMK と同じく 16 bit で計算する（`now` を `uint16_t` に落とす）。
- **期限の持ち方**: 期限（deadline = 最後の M/O 押下 + 80 ms）をエンジン自身が持ち、OS のタイマは「起こすだけ」にした。
  - `ng_timer_expired(now)`: `now >= deadline` のときだけ発火。取消や延長の後に古いタイマが届いても期限が合わなければ何もしない（古いタイマの取消漏れに強い）。早すぎたら掛け直す。
  - `ng_advance(now)`: 各入口（position リスナ、`&ng`/`&ng_mode`、キーコードリスナ）で、イベントを処理する前に呼ぶ。期限を過ぎていればそのイベントより先にタイムアウトを発火させる。システムワークキューが混んでタイマのワークが遅れても、結果はイベント時刻だけで決まる（差分テストで 40 ms 遅らせても一致）。
  - position リスナを keymap より前に置いたのは、`&mo` のようにエンジンを通らないキーでも、レイヤーが変わる前に保留中の打鍵を確定させるため（QMK のメインループで defer_exec が次の走査より先に回るのと同じ順序）。これが無いとタイマ遅延時に「レイヤー変更」と「タイムアウト出力」の順がログ上で入れ替わる（HID 出力自体は同じ。§5 の対照）。
- **期限ちょうどのイベント**（押下からちょうど 80 ms）: タイムアウトを先に発火させる、に固定した。QMK は 1 ms 内のループの位相（同じ ms の最初の走査で拾ったイベントだけがタイマより先）で変わりうる境界なので、決定的な側に寄せた。**意図的に QMK から変えた（というより、QMK で不定な境界を固定した）点**。参照ハーネスも同じ規則で比較している。

### 3.5 出力（押下保持＋解放）と Shift 反転

- `held_m` / `held_o` / `held_om` の記録、解放時に表を引き直さないこと、`held_release_stale()`、全出力の末尾でのバッファ吐き出しは QMK のまま。`ng_port_key` は 1 キーずつ press/release の keycode イベントを raise する。タップ列・`send_string` 相当は使っていない。「なあああ」になる長押しも QMK と同じ。
- QMK の同時打鍵での Shift 反転は `set_mods(反転) → register → set_mods(元)` で、反転が効くのはその瞬間のレポートだけだった。ZMK では:
  - Shift を足す側: キーイベントの `implicit_modifiers = LSFT`。ZMK の implicit modifier は次に別のキーが押される/離されるときに外れるので、次のレポートから元に戻る QMK と同じ。
  - Shift を外す側: `zmk_hid_masked_modifiers_set(LSFT|RSFT)` → press を raise（このレポートだけ Shift が消える）→ 直後に `…_clear()`。
  - 差分テストは各レポートの modifier バイトまで比べて一致。
- 押下中のキーをもう一度押す出力（「ん」= N,N など）: QMK の `register_code` も ZMK の `hid_listener` も「一度離してから押す」ので、ホストから見て同じ（QMK `quantum/action.c` の "Force a new key press if the key is already pressed"）。テストでは両側で 1,819 回ずつ発生し一致。

### 3.6 modifier 中の扱い、モード切替

- [ゲート2]（QMK `nicola_mode`）: キーコードリスナで、modifier（キーボードページ 0xE0〜0xE7）の押下/解放を、バッファに積むかどうかの判断より前に数える。かなモード中、1 個目で NICOLA 層を外し、全部離したら戻す。解放の数え過ぎ防止（`n_modifier > 0`）も QMK のまま。
- `&ng_mode NG_MODE_KANA` / `NG_MODE_EISU`（QMK の `KANA_ON` / `KANA_OFF`）: 押下で **先に `ng_on()`/`ng_off()`（保留を確定してクリア、F-C）**、次に Windows 用（変換 INT4 / 無変換 INT5）、Mac 用（かな LANG1 / 英数 LANG2）を押す。解放は Mac 用 → Windows 用。QMK の keymap.c と同じ順序。
- `ng_on()` は QMK どおり、クリア後に押されている modifier の数を `zmk_hid_get_explicit_mods()` から数え直す（F-B）。0 個なら NICOLA 層を入れ、そうでなければ外したままにする。
- 英数モードでも全キーが判定を通る（TS52K 方式、ゲート1 なし）。

### 3.7 キーマップ

- 層は QMK と同じ番号: 0 = 英数（全文字キーが `&ng NG_E_*`）、1 = かな（`&ng NG_*`、それ以外は `&trans`）、2 = FUNC（ナビ、PrtSc/Pause/Ins/Del、親指 2 つがかな/英数切替）。
- QMK の keycode → ZMK の対応は `tools/gen_keymap.py` の表にあり、未知の keycode があれば生成が止まる。
- エンコーダの回転は QMK の `encoder_update_user` と同じく全層で PgDn/PgUp（`&inc_dec_kp`）。押し込み（15 番目）は QMK の `KC_NO` → `&none`。

### 3.8 QMK から意図的に変えた点・違いが残る点

| 項目 | 内容 | 理由 |
|---|---|---|
| 期限ちょうど | タイムアウト優先に固定（§3.4） | QMK では不定な 1 ms 境界。決定的にした |
| エンコーダの回転 | ZMK ではキーコードイベントになるので、保留中はバッファに積まれ、保留中の打鍵の後に出る | QMK は `tap_code` で `process_nicola` を通らず即出力（追い越し得る）。ZMK では区別できないので、順序が保たれる側になった。1 回転＝2 イベントで 8 枠を使う |
| 押し込み（`KC_NO` / `&none`） | QMK の `KC_NO` は「再生可能なキー」としてバッファの枠を 1 つ使う（出力は無し）。ZMK の `&none` はイベントを出さないので枠を使わない | バッファ溢れ（8 枠）の境界だけが変わる。実用上の差は無い。差分テストでは押し込みを除外した |
| 時刻の型 | 間隔は QMK と同じく 16 bit。期限は 32 bit | 65.5 秒を超える押しっぱなしの後の間隔計算まで QMK と同じになる |

## 4. ビルド結果

VM（`nicola/build.sh all`）。ZMK 4dd95d78 / Zephyr 10ba6d0 / arm-none-eabi-gcc 15.2.0（QMK toolchain、gnuarmemb）/ west 1.5.0 / CMake 3.28.3。

| 版 | FLASH / RAM | UF2 | SHA-256 |
|---|---|---|---|
| plain（pin-sync の素 QWERTY、比較用） | 197,044 / 48,100 B | `~/workspace/zmk-config-wireless/nicola/out/ts52k_plain.uf2` 394,240 B、770 ブロック | `0664f1eb378c7ec6f758d930cf398617008d982f2650850719893a91e6301889` |
| **nicola** | 201,392 / 48,476 B | `~/workspace/zmk-config-wireless/nicola/out/ts52k_nicola.uf2` 402,944 B、787 ブロック | **`380dea6f4114de07aec7ebcba659b99469924e0bb2d6424cde122e8f8084707f`** |

- 両方 family ID `0xada52840`、書き込み範囲 plain `[0x26000, 0x56200)`、nicola `[0x26000, 0x57300)`。アプリ領域 `[0x26000, 0xec000)` 内。
- plain は同じ VM で 2 回ビルドして同じハッシュ（再現性あり）。
- NICOLA 由来の警告は 0。残る警告は pin-sync と同じ KSCAN の deprecated、dtc の unique_unit_address、picolibc 内部のもの。
- plain との差: `.config` は `CONFIG_ZMK_NICOLA=y`、`CONFIG_ZMK_NICOLA_LAYER=1`、モジュール有効化、`DT_HAS_TS52K_BEHAVIOR_NICOLA(_MODE)_ENABLED` の 5 行だけ。`zephyr.dts` は behavior 2 ノードとキーマップだけ。kscan・エンコーダ・電源・水晶・フラッシュ配置は不変。
- リスナ順（ELF）: `zmk_keycode_state_changed`: nicola → hid_listener。`zmk_position_state_changed`: nicola_position → activity → keymap。

## 5. 差分テスト（QMK 版との突き合わせ）

`nicola/tests/run.sh`（VM で 10 秒弱）。

- **QMK 参照**（`tests/qmk_ref.c`）: qmk_userspace の `nicola.c`、`nicola_table.c`、`keymaps/nicola/keymap.c` を**無改変で**ホストコンパイルし、QMK 本体の必要部分だけを模擬した上で動かす: レイヤーによるキーコード解決（押下時のレイヤーを解放でも使う source-layer cache）、`process_record_user` が true のとき basic キーを register・`MO` をレイヤー操作、`defer_exec`（期限が次のイベント時刻以下なら先に実行＝メインループの順序）、`timer_read()` ＝イベント時刻。
- **ZMK 側**（`tests/zmk_sim.c`）: `ng_engine.c`、`ng_table.c`、**`ng_zmk.c`（ZMK グルー本体）**を `-DNG_HOST_TEST` でコンパイルし、ZMK の該当部分を模擬: keymap（押下時のレイヤー状態を位置ごとに記憶、`&trans`/`&none`）、behavior（`&kp` は ZMK 本物の `zmk_keycode_state_changed_from_encoded`、`dt-bindings/zmk/keys.h` も本物）、イベントマネージャ（BUBBLE/CAPTURED、RELEASE は次のリスナから）、hid（explicit 数え・implicit・masked、`hid_listener` の再押下前解放）、遅延ワーク。キーマップは生成した `.keymap` そのものを `keymap_to_c.py` で読み込む（キーマップの移植も同時に検査される）。
- 比べるもの: HID レベルの操作列（押す/離す usage と、そのレポートの modifier バイト）、レイヤー状態の変化、シナリオ終了時のかな/英数・レイヤー・押下中キー。
- シナリオ（`tests/gen_scenarios.py`）: 名前付き 34 本（仕様の例、3 キー判定 t1<t2 / t1≥t2、長押し、タイムアウト後の親指、追い越し防止の順序、バッファ溢れ、Ctrl+C / Ctrl+Shift+X、保留中の modifier、小指シフト＋親指シフト同側/クロス、英数のクロスシフト、カーソルキー、`_`、「ん」「っ」、F-B/F-C の回帰、親指単独、期限ちょうど/1 ms 前）＋ランダム 20,000 本（かな/英数、文字・親指・矢印・通常キー・modifier・Fn の混在、間隔 0〜900 ms、同時押し最大 5、Fn 経由のモード切替を含む。時刻は通算で 16 bit を何度もまたぐ）。

結果（2026-11-12、qmk_userspace b7d0ccf、作業ツリー変更なし）:

| ZMK 側の条件 | シナリオ | HID 操作 | 不一致 |
|---|---|---|---|
| タイマ遅れ 0 ms、position リスナあり | 20,034 | 674,564 | **0** |
| タイマ遅れ 0〜3 ms（乱数） | 20,034 | 674,564 | **0** |
| タイマ遅れ 0〜15 ms | 20,034 | 674,564 | **0** |
| タイマ遅れ 0〜40 ms | 20,034 | 674,564 | **0** |
| タイマ遅れ 0 ms、position リスナなし | 20,034 | 674,564 | **0** |
| 対照: 遅れ 0〜40 ms、position リスナなし | 20,034 | — | レイヤー変更の行の順だけ 25 本で異なる。レイヤー行を除いた HID 列は 0 不一致 |

- 全シナリオで、終了時に押されたままのキー・modifier は 0（QMK 側も ZMK 側も）。
- **変異テスト**（テストが壊れを見つけられるかの確認。3,000 シナリオ）: T_abs 20→21 で 2 本、期限 80→81 で 57 本、キーコードリスナが積まない で 1,858 本、modifier を数えない で 942 本、Shift 反転を常に「足す」で 50 本、期限ちょうどの規則を `>` にすると（タイマ遅れありで）45〜57 本の不一致。すべて検出できた。
- 参考: QMK 版の挙動として、`kana_timeout_then_thumb_late_release`（M をタイムアウトさせた後に親指を押し、さらにタイムアウトさせてから M を離す）は「か・え・か・空白」と出る。これは QMK の現行実装どおりで、ZMK 版も同じに再現している（移植の問題ではない。QMK 側で意図した挙動かは未確認）。

## 6. 再現・引き継ぎ手順

### VM

```sh
cd ~/workspace/zmk-config-wireless          # ブランチ nicola-zmk
nicola/build.sh all                          # plain と nicola の UF2 → nicola/out/
nicola/tests/run.sh                          # 差分テスト（N_RANDOM=… で本数を変更）
# QMK 側を直したら生成物を作り直す（3 本とも決定的な機械生成）
python3 nicola/tools/gen_ng_codes.py ~/workspace/qmk_userspace/users/nicola/nicola.h nicola/include/dt-bindings/zmk/nicola.h
python3 nicola/tools/gen_ng_table.py ~/workspace/qmk_userspace ~/workspace/ts52k-ec/firmware-rebuild/qmk_firmware
python3 nicola/tools/gen_keymap.py ~/workspace/qmk_userspace/keyboards/ts52k/keymaps/nicola/keymap.c
```

`nicola.c` 本体（状態機械）を QMK 側で変えた場合は、`ng_engine.c` に手で反映する（`[ZMK]` の印の箇所以外は QMK と同じ行なので、`diff` で対応が取れる）。その後 `tests/run.sh` で一致を確かめる。

### Sadao の PC（PowerShell、pin-sync と同じ環境）

```powershell
Set-Location C:\Users\marur\zmk-config
git fetch origin
git checkout nicola-zmk
Set-Location C:\Users\marur\zmk
$env:PATH = 'C:\Program Files\CMake\bin;C:\Users\marur\zmk\.venv\Scripts;' + $env:PATH
$env:ZEPHYR_SDK_INSTALL_DIR = 'C:/Users/marur/zephyr-sdk-0.16.3'
$env:ZEPHYR_TOOLCHAIN_VARIANT = 'zephyr'
west build -p always -s app -d app/build-ts52k-nicola -b ts52k_mdbt50q/nrf52840 -- '-DBOARD_ROOT=C:/Users/marur/zmk-config/verification/main' '-DZMK_CONFIG=C:/Users/marur/zmk-config/config' '-DZMK_EXTRA_MODULES=C:/Users/marur/zmk-config/nicola' '-DKEYMAP_FILE=C:/Users/marur/zmk-config/nicola/keymap/ts52k_mdbt50q_nicola.keymap'
```

- 未実施（PC 側の SDK 0.16.3 / gcc 12 でのビルドは試していない）。UF2 のハッシュは VM のものとは一致しない（コンパイラが違う）。
- ビルド後、ELF のリスナ順は `arm-none-eabi-nm -n app/build-ts52k-nicola/zephyr/zmk.elf | Select-String zmk_event_sub_` で、`nicola…keycode` が `hid_listener…keycode` より前、`nicola_position…` が `keymap…position` より前であることを確かめる（起動時のログにも異常なら ERR/WRN が出る）。
- `-DZMK_EXTRA_MODULES` と `-DKEYMAP_FILE` を付けなければ、従来どおりの素の QWERTY（pin-sync 版）になる。

## 7. Git

- ブランチ `nicola-zmk`（`pin-sync-2026-11-11` の `a6613ee` から）に実装を `db974a7` としてコミットし、`origin/nicola-zmk` へ push（force なし）。この記録の SHA 追記は次のコミット。main への push・マージはしていない。
- push で既存の Actions（`config/west.yml` = v0.3、REVIUNG41 と旧 1 キー bring-up のビルド）が走る。`nicola/` はそのビルドから参照されないので影響しない。run 43210207978（`db974a7`）は全ジョブ success（REVIUNG41、ts52k-bringup-1key）。
- 生成物（`nicola/out/`、`nicola/tests/build/`）は `.gitignore`。UF2 は上表のパスとハッシュで記録。

## 8. 未検証・残作業・要判断

**実機では一切動かしていない。** 基板は試作発注前。以下はすべて未確認。

1. 実機（USB / BLE）での打鍵: 同時打鍵の判定、長押しのリピート、Shift 反転の見え方（特に implicit modifier を使う「足す」側が、OS / IME で QMK と同じに見えるか）、かな/英数切替（Windows 変換・無変換、Mac かな・英数）。
2. BLE での連続レポート: 保留の確定時に最大でおよそ 1 + 3 + 8 個のレポートが続けて出る。`CONFIG_ZMK_BLE_KEYBOARD_REPORT_QUEUE_SIZE=20`（既定）で収まる計算だが、接続間隔の長い BLE で取りこぼし・遅延が無いかは実機で見る。
3. **要判断: キーロールオーバー。** QMK 版 TS52K は NKRO（`keyboard.json` の `"nkro": true`）。ZMK の基板設定は既定の HKRO 6 キー（pin-sync のまま、今回は変えていない）。かな出力は最大 3 キーを保持するので、通常キーを押しながらの打鍵で 6 キーを超えると ZMK では取りこぼす。合わせるなら `CONFIG_ZMK_HID_REPORT_TYPE_NKRO=y`（BIOS 等のブートプロトコル対応を要確認）。
4. 要判断: エンコーダの回転が、保留中は NICOLA の確定を待って出る（§3.8）。QMK と同じ「即出力」にしたいなら、回転専用の behavior を作ってエンジンを迂回させる。
5. ZMK の deep sleep / BLE プロファイル切替 / USB-BLE の出力先切替を、キーを押したまま・保留中に行ったときの挙動は見ていない（QMK 側に対応する経路がない）。
6. Actions（`config/west.yml` が v0.3）でのビルドは未対応。現行基板定義と同じく、ローカルビルド前提。
7. PC 側（SDK 0.16.3）でのビルド未実施（§6）。
8. テストの範囲外: 65.5 秒を超える押しっぱなし、9 個以上を同時に保留させる極端な入力の網羅、エンコーダ・押し込みの入力（シナリオに含めていない）。
