# TC69（静電容量・NICOLA）QMK ファームウェア更新 — 2026-11-12

入力：`nicola-diff-check.md`（F-A/F-B/F-C の切り分け）、TC69 現行コード `78105002:keyboards/tc69`、`qmk_userspace` の `64bf032..b7d0ccf`（users/nicola）。
対象ファイル：`keyboards/tc69/keymaps/nicola/nicola.c`、`keymap.c`。matrix.c、nicola.h、rules.mk は変えていない。

## 結果の要約

| 項目 | 内容 |
|---|---|
| コミット | `352bf72c` tc69: nicola: flush pending input on mode switch, reseed modifiers on ON（親 `78105002`） |
| ブランチ | `tc69-nicola-update`（一時クローン `~/workspace/ts52k-ec/work-tc69-nicola`） |
| sadao-master | `git ls-remote` で GitHub 側の tip が `78105002` と確認 → fast-forward で `352bf72c` を push 済み（`78105002..352bf72c`）。force なし |
| 正本コピー | `firmware-rebuild/keyboards/tc69` を同期済み（clone 側コミットと `diff -r` で一致） |
| 作業クローン | `firmware-rebuild/qmk_firmware` は `tc52-ec-port` のまま、変更なし（`git status` クリーン） |
| ビルド | 通常版・診断版とも成功、警告 0 |
| 実機 | **未検証** |

## 1. F-B：ON のときに modifier を数え直す（移植済み）

`nicola_on` を次の順にした（現行 users/nicola と同じ）。

```c
nicola_clear();                       // 保留を確定（§2）
n_modifier = bitpop(get_mods());      // 実際に押されている modifier を数え直す
is_nicola = true;
if (n_modifier == 0) layer_on(nicola_layer); else layer_off(nicola_layer);
```

- `bitpop()`（`quantum/bitwise.h`）と `get_mods()` はこのツリーにある。
- TC69 では modifier を保留しない（「その他のキー」として即座に QMK に渡る）。そのため `nicola_on` を呼ぶ時点の `get_mods()` は物理的な状態と一致する。keymap の modifier はすべて素の `KC_LCTL/LSFT/LALT/LGUI/RSFT/RALT/RGUI` で、1 つの modifier ビットを 2 つのキーが共有することもないので、ビット数＝押しているキーの数になる。

**下限チェック `else if (n_modifier > 0)` も入れた。** 理由：
- F-B で ON のたびに数え直すので、今の keymap で分かっているアンダーフローの経路（英数で押してかなで離す）はふさがる。
- ただし、数え直しが正しいのは「modifier ビット 1 個＝物理キー 1 個」のときだけ。将来 keymap で同じ modifier を 2 つのキーに割り当てる（例：FUNC レイヤーにもう 1 つ LSFT を置く）と、英数で 2 つ押してから ON にした場合、数え直しは 1 なのに解放は 2 回来る。2 回目の解放で 0→255 に回り込む。そうなると、それ以後かなモード中の modifier で NICOLA レイヤーが外れなくなり（Ctrl+S が "su" になる類）、電源を入れ直すまで直らない。
- 0 のときの解放で何もしなくても、失うものは無い（0 ならレイヤーはすでに ON）。TS52K（現行 users/nicola）も修正前からこの形。1 行で済み、通常の経路での挙動は変わらない。

## 2. F-C：切替時は保留を旧モードのまま確定してから切り替える（再設計して移植）

### clear の意味を「捨てる」から「確定して初期化」に変えた
- `nicola_clear()` は保留を、状態に応じて出力してから S1_INIT に戻すようにした。S2_M → `nicola_m_type()`、S3_O → `nicola_o_type()`、S4_MO / S5_OM → `nicola_om_type()`（同時打鍵として確定）。
- この規則は、旧エンジンの「その他のキーが押された」分岐（保留を即座に確定）と同じもの。新しい規則を作ったのではなく、旧エンジンにすでにあった確定規則を切替の経路にも当てはめた。重複をなくすため、その他キーの分岐も `nicola_clear()` を呼ぶ形にした。その分岐の挙動はまったく変わらない（状態ごとの出力も、S1_INIT と `key_process_guard = 0` も同じ）。

### 影響範囲（呼び出し元の洗い出し）
`grep` で調べた、`nicola_clear` の呼び出し元は次のとおり。
- `nicola_on()` と `nicola_off()`（nicola.c）。
- （今回追加）`process_nicola` の「その他のキー」分岐。前述のとおり同じ動作。
- keymap.c と matrix.c、ほかのファイルからは呼ばれていない。`nicola.h` で公開はされているが、外部の利用者はいない。

捨てる動作が必要な呼び出し元が無いので、clear と flush を別の関数に分けなかった。切替以外で clear が呼ばれる経路は無いので、実害が出ることはない。

### 順序
- `nicola_on/off`：`nicola_clear()` を先に、`is_nicola` の書き換えを後にした（現行 users/nicola と同じ）。TC69 の出力関数は `is_nicola` を読まないので、出力は変わらない。揃えたのは、将来の差分を読みやすくするため。
- keymap.c：`KC_EISU` は `nicola_off()` の後で `SS_TAP(X_INT5)`、`SS_TAP(X_LNG2)` を送る。`KC_KANA2` は `nicola_on()` の後で `SS_TAP(X_INT4)`、`SS_TAP(X_LNG1)` を送る。確定した文字は、IME の切替要求より前にホストに届く。
- 確定した文字が modifier と一緒に送られることはない。modifier が押されている間は NICOLA レイヤーが外れているので、保留が生まれない。F-B の後は、ON の直後もそうなる。

### 直る操作
- かなモードで「Fn → W → 左親指（FUNC レイヤーでは KC_EISU）」をすばやく重ねて押す。修正前は「か」が捨てられていた。修正後は「ka」を出してから無変換/英数を送る。
- かなモードで「Fn → W → 右親指（KC_KANA2）」と押した場合（かなのまま ON し直す）も、同じく捨てられていた。修正後は「ka」の後に変換/かなを送る。

## 3. F-A と同種の穴の洗い出し（2020 年エンジンを読んだ結果）

方法：`process_record_user` → `nicola_mode` → `process_nicola` の全分岐と、QMK 側で関係する経路を読んで追った。QMK 側の経路は、process_record_quantum での呼ばれる順序、action_tapping の waiting_buffer、レイヤーキャッシュ、send_string。各状態（S1〜S5）と、他キーの押下と解放、modifier、レイヤーキー（MO / LT）、親指キー、モード切替の組み合わせを確かめた。

前提として確認したこと：保留状態（S2〜S5）は、必ず保留中のキーが物理的に押されている間だけ続く。どの遷移でも、保留中の m_key / o_key は押されたままになっている。解放か他キーの押下で必ず確定する。タイマーで確定する仕組みは無い（`keypress_timer_expired` は宣言だけで、`key_process_guard` は書かれるだけで読まれない）。

### 実害あり（今回直したもの）

| # | 経路 | 根拠 | 対応 |
|---|---|---|---|
| A1 | 保留中に **`process_nicola` より前で `return false` するキー**（KC_EISU / KC_KANA2）を押す | keymap.c の switch が `process_nicola` より前にあるので、「その他のキー」として確定する経路を通らない。`nicola_clear` は保留を捨てていた。F-A の「素通しにすべきでないキーが別扱いされて化ける」穴と同じ種類で、TC69 では文字が落ちる | F-C（§2） |
| A2 | **英数中の modifier の変化**が数えられない／0 からの解放で回り込む | §1 | F-B と下限チェック |
| A3 | **QMK の遅延再生（LT の判定待ち）**の中で起きた打鍵の時刻 | TC69 の右下の `LT(_FUNC, KC_APP)` は action_tapping が判定するまで、後続のイベントを waiting_buffer に溜める。判定後に元の `event.time` を保ったまま、まとめて再生する。旧エンジンは処理した時点の `timer_read()` で同時打鍵か時間切れかを判定していた。そのため、溜められた打鍵の間隔がほぼ 0 に潰れていた。例：APP を押したまま W、170 ms 後に親指を押し、APP を 200 ms 以内に離す（タップと判定される）。本来は「か」＋空白だが、「が」系の同時打鍵になる。もう一つの例：Fn として LT を押したまま W を押す。W の時刻が判定の時刻（遅い方）として記録されるので、その後の親指が同時打鍵と判定されやすくなる。「TC69 にも遅延再生がある」という Sadao の見立ては、エンジンの外（QMK 本体）で当たっていた | `curr_time = record->event.time` に変更。通常の経路では、イベントはスキャンの直後に処理されるので `timer_read()` との差は 1 ms 未満で、挙動は変わらない。QMK の `MAKE_EVENT` は `.time = timer_read()`、action_tapping は再生のときに `event.time` を保つことをソースで確認した |

A3 は起きる場面が狭い（APP キーを押したまま、またはそこから転がすようにかなを打つ）。それでも直したのは、イベントの時刻を使うのが判定の本来の意図に沿っていて、通常の経路への影響が無いことをコードで確かめられたから。順序のほうは QMK が保つので崩れない（溜めた押下は順番どおりに再生される。LT より前に押したキーの解放は即座に処理されるが、それは時系列でも先）。

### 実害なしと判断した経路（根拠つき）

1. **保留中に他キー（Enter・BS・矢印・ESC・Tab など）を押す**：その場で保留を確定してから、そのキーを QMK に渡す。順序は保たれる。
2. **保留中に他キーを離す**（押したのは保留より前）：解放はすぐ QMK に渡る。そのキーは保留より前に押したキーなので、ホストに届く順序は物理的な順序と矛盾しない。
3. **保留中に modifier を押す**：`nicola_mode` の layer_off が先に来るが、`send_string` はレイヤーを通らない。確定出力は `process_record_user` の中、つまり modifier の register より前に送られる。出力に含まれる `SS_LSFT` も、物理の Shift とぶつからない。
4. **modifier を押している間に NG キーを押す**：NICOLA レイヤーが外れているので QWERTY のキーとして素通しになり、保留は生まれない。そのため、確定出力が modifier つきで送られる経路は無い（F-B の後は、ON の直後も含めて）。
5. **NG キーを押したまま modifier や Fn を押し、離す**：解放はレイヤーキャッシュで NG キーとして解決される。S1_INIT なので何もしない。キーが押されたまま残ることもない。
6. **MO(_FUNC) を押す／離す**：押下は「その他のキー」として保留を確定させる。解放はホストに何も出さない。FUNC レイヤーで KC_TRNS のキーは NICOLA レイヤーに落ちて、かなになる（設計どおり）。F-A で TS52K に起きた KC_5 化けは、再生バッファが無いので起きない（`nicola-diff-check.md` §1）。
7. **LT(_FUNC, KC_APP) の判定待ちのときの順序**：保留の後に LT を押すと、LT の押下は判定まで `process_record_user` に来ない。その間に保留中のキーを離すと、「LT より前に押したキーの解放」として即座に処理されて確定する。あるいは、判定の後に LT の押下で確定する。どちらでも「保留中の文字 → APP / FUNC」の順序になる（時刻の問題は A3）。
8. **英数中に押した QWERTY のキーを、かなにしてから離す**（またはその逆）：解放はレイヤーキャッシュで押下のときのキーコードになる。素の KC は「その他のキー」の解放として QMK に渡る。NG のキーコードは、英数中は `process_nicola` を通らず、未定義のカスタムキーコードとして何もしない。キーが押されたまま残ることはない。
9. **保留中でない NG キーを押したまま OFF にする**：解放は何もしないで終わる（8 と同じ）。
10. **3 打鍵の判定（S4/S5 の後で、もう一方の親指や文字キーを押す）**：保留中のキーと関係ないキーの解放は無視される。それ以外の解放は確定する。追ったところ、どの分岐でも出力が落ちたり二重になったりしない。
11. **NG キーの解放で、m_key / o_key のどちらとも違うキーが来る場合**：`cont_process = false` で捨てるだけ。そのキーの出力はすでに済んでいる（状態遷移のときに確定済み）。
12. **UG_*（RGB）など、`process_record_user` の後で処理されるキー**：「その他のキー」として確定してから QMK に渡る。
13. **16 ビットのタイマーの回り込み**：保留を 65.5 秒以上押し続けてから次のキーを押すと、時間切れの判定が誤ることがありうる。静電容量スイッチは指を載せただけでは作動しないので、実際には起きないと判断した。直していない。
14. **NG キーのキーリピートが無い**（離したときに 1 回だけ出力）、**親指単独の空白が離したときに出る**：旧エンジンの設計どおり。不具合ではない。

## 4. その他（nicola / matrix まわり）

- matrix.c は変えていない。`curr_matrix` を毎回 0 にしているため解放の閾値が効かない点（ファイル冒頭の NOTE と `firmware-audit.md` §3.3）は、「TC69 が実際にこう動いていた」ので意図して残してある。実機のデータなしに変えるべきではないと判断した。
- nicola.h は `nicola_type()` を宣言しているが、定義が無い（使われていない）。挙動に関係しないので触っていない。
- `nicola_m_type/o_type/om_type` は、clear が前方から呼ぶようになったので、nicola.c の先頭で前方宣言した（公開範囲は元のまま）。

## 5. 検証

### ビルド
一時クローン（サブモジュールは共有クローンの `.git/modules` からローカルで取得）で、build.sh と同じ手順を実行した。PATH にツールチェインと qmk-venv、`QMK_USERSPACE` は unset、`make tc69:nicola`／`make tc69:nicola TC69_ADC_DIAG=yes`。
build.sh そのものは使っていない。build.sh は `firmware-rebuild/qmk_firmware/keyboards/tc69` を上書きするので、`tc52-ec-port` のチェックアウトが変わってしまうため。正本コピーは clone のコミットと一致させてあるので、後で build.sh を回しても同じソースになる。

| ファイル | sha256 |
|---|---|
| `firmware-rebuild/out/tc69_nicola.uf2`（68,096 B） | `d28d73929088ff32fe721c74e5ba07f7e2e4088585412be4d037219f71feb539` |
| `firmware-rebuild/out/tc69_nicola_diag.uf2`（69,632 B） | `40d04d00c457d04ff09df102abdf2ff0b27f93844fa6f454487a3c4238133937` |

ログ：`firmware-rebuild/out/build-nicola.log`、`build-nicola-diag.log`（警告 0、エラー 0）。
修正前の 78105002 の成果物とログは `firmware-rebuild/out/prev-78105002/` に退避した（nicola `0dd9a41d…`、diag `3072cab1…`）。

### ホストでのテスト
`~/workspace/ts52k-ec/tc69-nicola-test/`：実物の `nicola.c` と、keymap.c から取り出した `process_record_user` をホストの gcc でビルドする。send_string、レイヤー、get_mods、タイマーはスタブにしてある。12 の場面を流す。
- 通常の打鍵の回帰：単独打鍵、同時打鍵、時間切れ、他キーでの確定、modifier の押下での確定。
- F-C：Fn, W, EISU → `ka<X_INT5><X_LNG2>`。Fn, W, KANA2 → `ka<X_INT4><X_LNG1>`。
- F-B：英数で Shift を押して ON → レイヤーは OFF のまま、離すと ON、Ctrl でまた外れる。OFF をまたいで Ctrl を押していた場合。
- 下限チェック：押下が数えられていない解放が来ても、回り込まない。
- A3：再生されたイベント（処理した時刻は同じで、event.time は 170 ms 離れている）が、順次打鍵と判定される。

結果：新コードは **12 件すべて合格**。同じハーネスを 78105002 の旧コードで回すと 5 件失敗する（F-C 2 件、F-B 2 件、event.time 1 件）。テストが修正点を実際に見分けていることを確かめた。限界：ハーネスはキーコードを直接与えているので、レイヤーの解決とマトリクスは通らない。

## 6. Git

- 一時クローン：`~/workspace/ts52k-ec/work-tc69-nicola`（`firmware-rebuild/qmk_firmware` をローカルで clone したもの。remote `github` = https://github.com/sadaoikebe/qmk_firmware.git）。
- ブランチ `tc69-nicola-update` = `352bf72c`（親 `78105002`）。作者は既存のコミットと同じ `sadaoikebe <…noreply>`、Co-Authored-By つき。
- push の前に `git ls-remote` で GitHub の `sadao-master` = `78105002` を確認。祖先関係も確認して fast-forward で push し、`78105002..352bf72c` で成功した。push の後、ls-remote で `352bf72c` になっていることを確認した。一時クローンのローカル `sadao-master` も同じ位置。
- `tc69-nicola-update` ブランチ自体は GitHub に push していない（sadao-master と同じコミットなので不要）。
- `firmware-rebuild/qmk_firmware`（共有クローン）は触っていない：`tc52-ec-port` のまま、作業ツリーはクリーン。共有クローン内のローカル `sadao-master` と `origin/sadao-master` の追跡ブランチは古いまま（`78105002`）。必要なら、次にそのクローンで fetch したときに追いつく。
- 注意：GitHub の `tc52-ec-port` は今回扱っていない。共有クローンの `tc52-ec-port`（`81e679ac`）は `78105002` から分かれているので、今回の sadao-master とは分岐した状態になる。TC52 側に同じ修正を入れるかどうかは別の判断。

## 7. 未検証・残っていること

- **実機（TC69）での動作確認は一切していない。** 確かめてほしい操作は次のとおり。(1) Fn → 文字 → 左親指をすばやく押して文字が残るか。(2) 英数で Shift を押したまま Fn＋右親指で ON にし、Shift を離した後に Ctrl+S などが効くか。(3) 普段の打鍵の感触（同時打鍵の判定）が変わっていないか。(3) は event.time への変更のためで、理屈の上では 1 ms 未満の差。
- F-C で clear を「捨てる」から「確定」に変えたのは、旧エンジンの挙動の変更にあたる（`nicola-diff-check.md` で「Sadao の判断事項」とされていた点）。今回の依頼の指示に従って入れた。
- Mac / Windows の IME が、確定した文字の直後に届く切替コードを期待どおりに扱うかどうかは、ホスト側で確かめていない。
