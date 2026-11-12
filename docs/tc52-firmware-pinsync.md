# TC52 ファームのピン同期（QMK・ZMK）

作成: 2026-11-13（Opus 5.5）。対象は、基板で確定した GPIO 配置（`tc52-build-log.md`「ファームウェアとの食い違い」、`~/workspace/tc52/pcb/tc52-build/matrix.py`）。
**結論：QMK・ZMK とも確定値に合わせ、ビルドが通り、差分テストの不一致は 0。QMK は sadao-master に、ZMK は zmk-config main に push 済み。実機は無いので、動作は検証していない。**

## 経緯
変更の本体は、2026-11-13 未明の Fable セッションがほぼ書き上げていた（中断）。
- QMK：ローカルブランチ `tc52-ec-port` のコミット `25420642`（未 push）
- ZMK：コミットされていない変更 7 ファイル

今回はその中身を確定値と 1 項目ずつ照合し、作り直し・ビルド・差分テストで検証してから、既存の流儀どおりに取り込んだ。中身には手を加えていない。

## 確定値との照合（全項目一致）
| 項目 | 確定値 | QMK（matrix.c／tc52_matrix.h／keyboard.json） | ZMK（tc52.overlay → ビルド後の zephyr.dts） |
|---|---|---|---|
| 行 ROW1〜4 | GP21／20／19／18 | `CAP_ROW_PINS = {GP21, GP20, GP19, GP18}` | `strobe-gpios` 21 20 19 18 |
| PURGE／ADC | GP28／GP26（ADC0） | `CAP_PURGE GP28`、`CAP_SENSE GP26` | `purge-gpios` 28、`io-channels <&adc 0>`、pinctrl `ADC_CH0_P26` |
| エンコーダ A／B | GP1／GP0 | `pin_a GP1`、`pin_b GP0` | `a-gpios` 1、`b-gpios` 0 |
| LOW 固定 | GP6、22〜25、27、29 | `TIE_LOW_PINS` | gpio-hog（output-low）× 7 |
| MUX A の S1／S2／S3／INH | GP10／9／8／11 | `CAP_SEL_PINS[0]`、`CAP_INH_PINS[0]` | `mux-gpios` の前半 3 本、`mux-enable-gpios` 11（ACTIVE_LOW） |
| MUX B の S1／S2／S3／INH | GP5／4／3／7 | `CAP_SEL_PINS[1]`、`CAP_INH_PINS[1]` | `mux-gpios` の後半 3 本、`mux-enable-gpios` 7（ACTIVE_LOW） |
| 切替の順序 | 旧側の INH を HIGH にしてから、新側を LOW | `select_column()`：他方の INH を HIGH → S1〜S3 → 自分の INH を LOW | ドライバ：他の MUX を無効化 → 選択線 → 有効化（同じ順序） |
| 起動時 | — | 出力にする前に INH を HIGH にしておく（両方無効で開始） | `GPIO_OUTPUT_INACTIVE`（ACTIVE_LOW なので HIGH） |
| 列 c1〜c6 | A の X4／6／7／0／1／2 | `TC52_COL_X` = 4 6 7 0 1 2 … | `column-addresses` = 4 6 7 0 1 2 … |
| 列 c7〜c14 | B の X4／6／7／5／3／0／1／2 | … 4 6 7 5 3 0 1 2、`MUX_B` = 1 | … 12 14 15 13 11 8 9 10（= 8 + X） |

- `tc52_matrix.h` と `keyboard.json` は生成器の出力のまま。`./build-tc52.sh --regen` で作り直しても、コミット済みの内容と 1 バイトも違わなかった。`notes/tc52-matrix.py` は基板側の `matrix.py` と同一。
- **センシングは TC69 のまま。** 判定ロジック・閾値（120／30、ホームキー 220／80）・校正・パージの手順はどれも変えていない。走査順の規則「MUX A の X0→X7、続いて MUX B の X0→X7」も同じ。ただし列の割当てが変わったので、規則から出てくる順番は変わった：`5 4 0 3 1 2 …` が `3 4 5 0 1 2 11 12 13 10 6 9 7 8` になる（後半の B 側は前と同じ）。
- 列アドレスの書き方は、TC69 の「S1、S2、S3、S0 の順」から「MUX ごとの S1〜S3 ＋ INH」に変えた。基板の構成が変わった（MUX ごとに別の選択線を持ち、インバータを廃止）ので、これはピンの変更に伴うもの。
- ZMK のドライバは TC69 と共用。`mux-enable-gpios` を省略可能なプロパティとして足し、それが無いとき（TC69）は従来のコードを通る。

## ビルド結果
### QMK（`firmware-rebuild/build-tc52.sh --regen`、make）— 警告 0
| 生成物 | サイズ | SHA-256 |
|---|---|---|
| `out/tc52_nicola.uf2`（通常版） | 70,656 B | `1d41d654253ba705516f3c4a1793f0c9bcbea5a0372722c5ed8bc8a97228bb9d` |
| `out/tc52_nicola_diag.uf2`（診断版） | 72,192 B | `76fddecd316ab6a89626f1d168f01f929c1e34e61d071d35d6c611227b3a4a68` |
| `out/tc52_default.uf2`（素の QWERTY） | 63,488 B | `db220b3fa28df931402928a502dfca7059bcffed26d539f77db6780881877a42` |

### ZMK（`scripts/build.sh tc52 tc52_diag tc69 tc69_diag`）
| 生成物 | FLASH / RAM | SHA-256 |
|---|---|---|
| `out/tc52.uf2` | 43,436 / 16,220 B | `97062134ed870bcae75fd8f4eb09327c7c10e85f8d3a666be96ea964ee939beb` |
| `out/tc52_diag.uf2` | 67,640 / 53,724 B | `21b3f6f6e347109b830d3d2c6671cd5f2a910f82d01d64006b475c16244fed78` |
| `out/tc69.uf2`（共用ドライバの回帰確認） | 42,604 / 19,132 B | `3470672333e8fbce79b5cb75bcc997e5e24c156b88c4925ae222655ae09b945c` |
| `out/tc69_diag.uf2` | 67,444 / 56,724 B | `2705a702ca1128b29076af083b0fe7b3969f229eac020f051d98ccd829054556` |

- 警告は各 23 件。どれも Zephyr の libc（asctime_r.c）と Kconfig のもので、従来から出ていた。ドライバ由来の警告は 0。
- ビルド後の `tc52.zephyr.dts` で、kscan_ec ノードのピン・アドレス・走査順が上の表どおりになっていることを確認した。
- GitHub Actions（push 時に全マトリクスをビルド）：run 43322387995 は **全 8 ジョブ成功**（TC52 の通常版と diag 版、TC69、TS52K の 4 種）。

## 差分テスト（QMK の matrix.c をホストでコンパイルし、ZMK ドライバと突き合わせる）
| テスト | 比較の対象 | 結果 |
|---|---|---|
| `tests/ec-kscan/tc52/run.sh` | QMK `tc52-ec-port`（25420642、sadao-master の 366b376d と同じ tc52 ツリー）の matrix.c ↔ tc52.overlay 構成のドライバ | 200 シード × 400 スキャン、**不一致 0**（押下エッジ 107,469） |
| `tests/ec-kscan/run.sh` | QMK tc69 の matrix.c ↔ TC69 構成のドライバ（共用ドライバの回帰確認） | 200 × 400、**不一致 0** |

- 模擬ハードの `sim52.c` は、列 → MUX／X の対応を基板側から独立に持っている（`matrix.py` と一致）。INHA と INHB が同時に LOW の状態で ADC を読むと、その場で異常終了する。
- **テストが間違いを検出できることの確認**：ZMK 側の列アドレスを旧表（c4〜c6 ＝ X5／3／0）に戻すと、ピン操作の記録が 30 バイト目で食い違って失敗した。

## 取り込み（既存の流儀どおり）
- **QMK**：`25420642` を origin/sadao-master（65726d75）の上へ cherry-pick した。共有クローンのチェックアウトは変えず、一時的な worktree で作業。tc52 のツリーが検証済みのコミットと同一であることを確かめてから、**`366b376d` を sadao-master へ fast-forward で push**。ローカルの sadao-master も追従させた。`tc52-ec-port` は差分テストの参照先なので、そのまま残してある。
- **ZMK**：**`97be08b` を zmk-config の main へ push**（名義は既存のコミットと同じ sadaoikebe）。

## 変更ファイル
QMK（`keyboards/tc52/`。正本 `firmware-rebuild/keyboards/tc52/` とクローンは同一）
- `matrix.c`：ピン定義、MUX ごとの選択線と INH、`select_column()`（先に切ってから入れる順序）、LOW 固定ピン、初期化
- `tc52_matrix.h`：`TC52_COL_X`・`TC52_SCAN_ORDER`、表のコメント（生成物）
- `keyboard.json`：エンコーダの A／B（生成物）

ZMK（`~/workspace/zmk-config-wireless`）
- `boards/shields/tc52/tc52.overlay`：行・選択線・`mux-enable-gpios`・列アドレス・走査順・PURGE・ADC0・エンコーダ・gpio-hog
- `drivers/kscan/kscan_ec_mux_adc.c`：省略可能な `mux-enable-gpios`（MUX ごとの選択線と有効化。無ければ TC69 の動作のまま）
- `dts/bindings/kscan/shobon,kscan-ec-mux-adc.yaml`：上のプロパティの説明と、TC52 の値の例
- `tests/ec-kscan/tc52/{sim52.c, zmk52_side.c, qmk52_side.c, qmkstub/qmk_stub.h}`：新しいピンと INH を模擬し、追跡する

触れていないもの：KiCad ファイル、`~/workspace/tc52`（matrix.py は読んだだけ）、TC69 の QMK 定義。

## 残っていること
- 実機での確認（基板待ち）。
- `tc52-firmware.md` §4 と `tc52-zmk.md` のピン表は旧ピン（§6.1）のまま。この文書が新しいピンの正となる旨を、両方の冒頭に書き足した。
