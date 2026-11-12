# TS52K の NICOLA 修正（nicola-fixes）は TC69 に入っているか — 確認結果

2026-11-12。確認だけの作業で、コードは変えていない。作業中のクローン（`firmware-rebuild/qmk_firmware`）は `git show` / `git log` / `git ls-tree` / `git ls-remote` だけで読んだ。checkout も fetch もしていない。

## 結論

| 修正 | TS52K のコミット | TC69（78105002）の状態 | 判定 |
|---|---|---|---|
| F-A：再生できるキーコードだけをバッファに積む | `a76fe62` | TC69 の旧エンジンには追い越し防止バッファ自体が無い | **TC69 には該当しない** |
| F-C：モード切替とホストへの切替コード送信の前に、保留中の入力を確定する | `362001f` | コード上は入っていない。ただし TS52K で直した仕組み（clear が保留を出力する／`is_nicola` を見て Shift を反転する）が TC69 には無い。TC69 では別の形の問題がある（保留中の文字が捨てられる） | **未取り込み。ただし機械的に移植しても何も変わらない**（下の §3） |
| F-B：かなモードに入るとき、押されている modifier を数え直す | `b7d0ccf` | 入っていない。直した不具合と同じ数え方のコードが TC69 にそのまま残っている。TC69 には数がマイナス方向に回り込む（アンダーフロー）経路まである | **未取り込み。不具合は TC69 でも起きる（コードを読んだ範囲で）。移植はほぼ機械的にできる** |

## 0. 前提として確認できたこと（依頼文の想定と違う点）

- **修正が入っているのは qmk_firmware フォークではなく、qmk_userspace のほう。** 修正は `sadaoikebe/qmk_userspace` にある。ローカルは `~/workspace/qmk_userspace`。`git ls-remote` で見ると、リモートの `master` と `nicola-fixes-2026-11-10` はどちらも `b7d0ccf` を指していて、マージも push も済んでいる。修正は次の 3 コミットで、親はすべて `64bf032`。
  - `a76fe62` nicola: buffer only replayable keycodes (F-A) — `users/nicola/nicola.c`
  - `362001f` nicola: clear old input before mode and host switch (F-C) — `users/nicola/nicola.c` と `keyboards/ts52k/keymaps/nicola/keymap.c`
  - `b7d0ccf` nicola: reseed held modifiers after clear on ON (F-B) — `users/nicola/nicola.c`
- **フォーク側の sadao-master（`78105002`）に TS52K の NICOLA は入っていない。** あるのは `keyboards/ts52k/` のボード定義（config.h、keyboard.json、matrix.c、rules.mk）だけで、`users/nicola` も ts52k の keymap も無い（`git ls-tree 78105002` で確認）。つまりフォーク側に、TS52K 向けの NICOLA 修正を入れる場所はもともと無い。
- このクローンは shallow clone で、手元にある履歴は `e3ef3b89`（ts52k のボード定義）と `78105002`（tc69）だけ。それより前のフォーク履歴は見ていないが、上のとおり修正は userspace にあるので、今回の判断には影響しない。
- 修正の意図と根拠は計画書 `~/workspace/nicola-projects/ts52k-qmk-fix-plan.md` による（C1〜C9 は不具合の連鎖、F-A/B/C は修正の名前）。
- **TC69 の nicola は TS52K の nicola と別物。** TC69 のものは、2020 年の旧エンジン（`users/nicola@b3ac8db961`）を keymap ディレクトリにそのまま入れたもの。`firmware-rebuild/notes/legacy-users-nicola-b3ac8db961/` の nicola.c / nicola.h と `78105002` の中身を diff し、バイト単位で一致することを確かめた。現行の users/nicola は使っていない（rules.mk の `USER_NAME := tc69_legacy_nicola` で読み込まれないようにしてある）。状態機械（S1〜S5）、出力（`send_string` によるローマ字出力）、バッファの有無、clear の動作がどれも違う。そのため、差分をそのまま当てられる関係にはない。修正ごとに「同じ仕組みの不具合が TC69 にあるか」を判断した。

以下、行番号の表記は次のとおり。
- `T69:`：`78105002:keyboards/tc69/keymaps/nicola/nicola.c`
- `T69K:`：同じく keymap.c
- `N:`：`qmk_userspace@b7d0ccf:users/nicola/nicola.c`
- `N0:`：修正前の `64bf032` の同じファイル

## 1. F-A（a76fe62）— TC69 には該当しない

**TS52K で直した不具合**：かな入力が保留中（状態が S_INIT 以外）のとき、NICOLA 以外のキーは押下も解放もすべて追い越し防止バッファに積まれていた（N0 の `nicola_on_other`）。積んだキーは後で `register_code16` を使って再生される。この方式では `MO(2)` のようなレイヤー操作が下位 8 ビットに切り詰められて KC_5 として押され、レイヤーの ON/OFF も実行されなかった。修正では `process_nicola` の入口に判定を入れ、NG キーでも basic / QK_MODS でもないキーは押下・解放とも素通しにした（N:173 `is_replayable_key`、N:613-616）。

**TC69 の実物**：
- バッファはまったく無い。押下時、NG 以外のキーは「その他のキー」の分岐（T69:396-417）に入る。保留中の M／O／MO／OM をその場で出力して S1_INIT に戻し、`return true` で QMK に処理を渡す。
- 解放時、NG 以外のキーは T69:418-477 のどの分岐にも入らず、`cont_process = true` のまま QMK に渡る。
- 再生も無いので、キーコードが切り詰められることもない。

**手で追った例**（TS52K で症状 2 を起こした操作「キー押下 → Fn 押下 → キー解放 → Fn 解放」）：
1. かなモードで W を押す → S2_M。
2. Fn（`MO(_FUNC)`、T69K:58）を押す → 「その他のキー」の分岐で W を出力し、INIT に戻り、MO は QMK に渡って FUNC レイヤーが ON になる。
3. W を離す → 解放は押したときのレイヤー（キャッシュ）で解決されて NG_W になる。INIT なので何もしない。
4. Fn を離す → MO の解放が QMK に渡って FUNC が OFF になる。

KC_5 が混入することも、FUNC が残ることもない。

**取り込みは不要。** F-A の判定（`IS_QK_BASIC || IS_QK_MODS`）は、バッファがあって初めて意味を持つ。TC69 に移しても何も変わらない。

（参考までに、TC69 では NG 以外のキーを押した瞬間に保留を確定させるので、TS52K の F-A 後の挙動「Fn で保留を割らない」とは違う。これは旧エンジンの元からの方針で、今回の修正とは関係がない。）

## 2. F-B（b7d0ccf）— 未取り込み。不具合は TC69 にもある

**TS52K で直した不具合**：`nicola_mode` は、かなモード中に押された modifier だけを数える（`n_modifier`）。最初の押下で NICOLA レイヤーを外し、最後の解放で戻す。英数モード中の modifier は数えない。そのため、OFF をまたいで離した modifier の分だけ数が残る。また、英数モードで押した modifier はそもそも数えられない。さらに ON のときに数を合わせ直さず、無条件に `layer_on` していた。修正では、`nicola_on` で保留を確定させたあと、`n_modifier = bitpop(get_mods())` で数え直す。数が 0 ならレイヤーを ON、0 でなければ明示的に OFF にする（N:697-706）。

**TC69 の実物**：
- `nicola_mode`（T69:85-112）は、修正前の TS52K と同じ数え方（`!is_nicola` なら即 return、押下で増やし解放で減らす）。
- `nicola_on`（T69:55-62）は数え直さず、無条件に `layer_on` する。
- keymap は `if (nicola_state()) { nicola_mode(); process_nicola(); }` となっている（T69K:101-106）。計画書のいう「TS69 型のガード」がそのまま入っていて、英数モード中の modifier は数えられない。
- TS52K の修正前版にもあった、解放時の下限チェック `else if (n_modifier > 0)`（N0 にあり、N:661 にもある）が TC69 には無い。T69:103-104 は、0 から引くと `uint8_t` が 255 に回り込む。

**コードを手で追って確かめたこと（実機では試していない）**：
- **OFF をまたいで離した場合**：かなモードで Ctrl を押す（n=1、レイヤー OFF）→ Fn＋左親指で `KC_EISU`（`nicola_off`）→ Ctrl を離す（英数なので数えず、n=1 のまま）→ Fn＋右親指で `KC_KANA2`（`nicola_on`、`layer_on`、n=1 のまま）。この後、Ctrl を押しても n≠0 なのでレイヤーが外れず（n=2）、離しても n=1 で止まる。数の食い違いはずっと残る。
- **英数で押してかなで離した場合（TC69 だけの悪化）**：英数モードで Shift を押す（数えない）→ ON（n=0、レイヤー ON）→ Shift を離す → n-- で 255。以後、押すと 255→0（レイヤーは外れない）、離すと 0→255 を繰り返す。かなモード中の modifier は二度と NICOLA レイヤーを外さない。TS52K の修正前版は下限チェックがあるので、こうはならなかった。
- 上のどちらの状態でも、Ctrl を押したまま NG キーを打つと、NICOLA の判定を通ってしまう。その結果、`send_string` でローマ字列（例：NG_C なら "su"）が Ctrl を押したまま送られる。Ctrl+S、Ctrl+U がホストに届く計算になる。これはコードから導いた予想で、実機では確認していない。
- 元に戻る経路は、偶然「かなで押して英数で離す」ことか、電源の入れ直し（static 変数が 0 に戻る）しかない。

**取り込むなら**：TC69 の `nicola_on`（T69:55-62）を次のようにすればよい。実質 F-B の差分そのままで、ほぼ機械的にできる。
```c
void nicola_on(void) {
  nicola_clear();
  n_modifier = bitpop(get_mods());
  is_nicola = true;
  if (n_modifier == 0) layer_on(nicola_layer); else layer_off(nicola_layer);
}
```
TC69 に固有の事情として確認したこと：
- `bitpop()` は、このツリー（78105002）の `quantum/bitwise.h:26` と `bitwise.c:21` にある。`get_mods()` も `quantum/action_util.c:350` にある。
- 計画書の F-B は「保留を全部確定させた後に数え直す」ことを前提にしている。TC69 には保留中の modifier の押下・解放が無い（modifier は「その他のキー」として即座に QMK に渡る）ので、`nicola_on` が呼ばれる時点の `get_mods()` は、すでに実際の状態を表している。旧エンジンの `nicola_clear` は何も出力しない（§3）ので、順序を気にする必要もない。
- 計画書の前提「modifier は素のキーだけ。mod-tap や、modifier を押しっぱなしにする出力は無い」は、TC69 の keymap でも成り立つ。modifier はすべて素の KC_LCTL / KC_LSFT / KC_LALT / KC_LGUI / KC_RSFT / KC_RALT / KC_RGUI で、mod-tap は無い。`LT(_FUNC, KC_APP)` は modifier ではない。出力の `SS_LSFT()` は send_string の中で押して離すので、押しっぱなしにはならない。
- 下限チェック `else if (n_modifier > 0)` は F-B のコミットには含まれない（TS52K には修正前からあった）。F-B を入れると、英数で押してから ON にした場合も 1 と数えられるので、上で書いたアンダーフローの経路はふさがる。それでも、TC69 にこの下限チェックを足すかどうかは別に判断すること（足すのは 1 行）。
- 注意点：TC69 は「原版そのまま」の方針で再構成されている。移植すれば旧エンジンの挙動を変えることになるので、入れるかどうかは Sadao の判断が要る。ビルドと実機での確認もまだしていない。

## 3. F-C（362001f）— 未取り込み。ただし TC69 では問題の形が違う

**TS52K で直した不具合**には 2 つの部分があった。
1. keymap が、ホストへの切替コード（INT5/LNG2、INT4/LNG1）を `nicola_off/on` より前に送っていた。修正前の TS52K の `nicola_clear` は保留中の打鍵を出力する（N0 の `nicola_clear` → `nicola_m_release` など）ので、古い文字がホストの切替要求の後に届いていた。
2. `nicola_on/off` が、`is_nicola` を書き換えてから `nicola_clear` を呼んでいた。TS52K の同時打鍵の出力は `is_nicola` を見て Shift を反転するので、新しいモードの解釈で出力されていた。

修正では、`nicola_clear` を先に呼ぶ順序にした（N:697-712）。keymap も、`nicola_off/on` の後に切替コードを register する順序に変えた（keymap.c:66-84）。

**TC69 の実物**：
- keymap は、TS52K の修正前と同じく、切替コードを先に送っている（T69K:78-97。`send_string(SS_TAP(X_INT5/LNG2))` の後に `nicola_off()`、`SS_TAP(X_INT4/LNG1)` の後に `nicola_on()`）。
- `nicola_on/off` も、`is_nicola` を書き換えてから `nicola_clear` を呼ぶ（T69:55-71）。
- **ただし、TC69 の `nicola_clear`（T69:79-82）は、状態を S1_INIT に戻して `key_process_guard` を 0 にするだけで、何も出力しない。** 出力関数（`nicola_m_type` / `nicola_o_type` / `nicola_om_type`）は `is_nicola` を一切読まない（T69:116-282）。

そのため、TS52K で起きていた 2 つの現象（古い文字が切替要求より後に届く、新しいモードの Shift 解釈で出力される）は、TC69 では仕組み上起きない。順序を入れ替えるだけの移植をしても、出力は何も変わらない。

**TC69 で代わりに起きること（コードを手で追った結果、実機では試していない）**：切替の時点で保留中だった打鍵は、出力されずに捨てられる。
- 起こる操作：かなモードで Fn を押す → W を押す（FUNC レイヤーの W は KC_TRNS なので NG_W に落ち、S2_M で保留）→ W を押したまま左親指を押す（FUNC レイヤーでは `KC_EISU`。T69K:66）。
- `KC_EISU` は `process_nicola` より前に処理されて `return false` する（T69K:78-87）ので、「その他のキー」として保留を確定させる経路を通らない。`nicola_off` → `nicola_clear` で S2_M が捨てられる。
- その後 W を離しても、`nicola_state()` が false なので `process_nicola` は呼ばれず、何も出ない。
- 一方で、W を先に押して Fn を後に押す順序では、Fn の押下で保留が確定する（§1）ので、捨てられない。つまり、捨てられるのは「Fn → 文字キー → 親指」をすばやく重ねて押したときだけ。
- 英数から ON にする方向では、英数モード中に `process_nicola` が呼ばれないので、保留ができること自体がない。

**取り込むなら**（F-C の目的「切替の前に古い入力を古いモードのまま確定させる」を TC69 で実現する場合）、機械的な移植では済まない。旧エンジンの挙動を変える設計判断になる。
1. TC69 の `nicola_clear` に、状態ごとの確定出力を足す。S2_M なら `nicola_m_type()`、S3_O なら `nicola_o_type()`、S4_MO / S5_OM なら `nicola_om_type()`（TS52K と同じく、clear のときは同時打鍵として確定する方針）。これは「clear は保留を捨てる」という原版の方針を変えることになる。
2. 1 を入れた場合に限り、keymap の順序も TS52K と同じく「`nicola_off/on` の後に `send_string(SS_TAP(...))`」へ入れ替える必要がある。入れ替えないと、TS52K の修正前と同じく、古い文字が切替要求の後に届く。
3. `nicola_on/off` の中の `is_nicola` の順序は、TC69 の出力が `is_nicola` を見ないので、どちらでも結果は変わらない（揃えるなら TS52K と同じ順にしてよい）。
4. TC69 の切替コードは `SS_TAP` で押して即離す。TS52K の「押下で register、解放で unregister」とは違うが、これは F-C の範囲外。

1 を入れるかどうか（捨てるか確定するか）は Sadao の判断事項。入れない場合は、TC69 を今のまま（該当する不具合なし、保留は捨てる仕様）としておけばよい。

## 確認できたこと／できなかったこと

確認できたこと（実物を読んだ）：
- 3 つの修正コミットの差分全体、修正前の `64bf032` の該当部分、TC69 の nicola.c / nicola.h / keymap.c / rules.mk の全文（`78105002`）。
- TC69 の nicola.c / nicola.h が、サルベージした控えとバイト単位で一致すること（diff の終了コード 0）。
- `qmk_userspace` のリモート master と nicola-fixes ブランチがどちらも `b7d0ccf` であること（ls-remote）。フォーク側の sadao-master が `78105002` で、そこに users/nicola も ts52k の keymap も無いこと。
- `bitpop()` と `get_mods()` が、このツリーにあること。

確認できなかったこと／していないこと：
- 実機（TC69、TS52K）での動作は確かめていない。§2 と §3 の「起きる」は、すべてコードを手で追った結果。
- TS52K の修正そのものが実機で効いたかどうか（メモ上は「Sadao が実機で確認」が次の手順になっていた）は、このタスクでは確かめていない。
- フォークの shallow clone より前の履歴（e3ef3b89 以前）。§0 のとおり、修正は userspace にあるので判断には影響しない。
- 移植案のビルドはしていない（コードを変えない約束のため）。
