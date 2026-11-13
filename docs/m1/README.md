# M1：TC69 実機計測の手順書（Windows、一人で全部やる版）

2026-11-13 作成。対象は TC69（XIAO RP2040 の静電容量キーボード）。目的と各計測の意味は `measurement-plan.md`、診断ファームの中身は qmk_firmware（sadao-master）の `keyboards/tc69/adc_diag_impl.h`。

> **未検証の注意**：診断ファームはビルドと、PC 上のシミュレーション（`sim/`）でしか動かしていない。TC69 の実機では一度も動かしていない。解析スクリプトも合成ログでしか試していない。おかしな挙動があれば、その場で止めて §8 の手順で元のファームに戻せばよい（§2 の吸い出しさえ済んでいれば、いつでも戻せる）。

所要時間の目安：準備 30 分（初回のドライバ設定を含む）、吸い出し 5 分、計測 40 分（任意の 30 分待ちを除く）、戻し 5 分。

---

## 0. 全体の流れ

1. 準備（§1）：QMK MSYS、picotool、必要なら Zadig。この一式を `C:\m1` に置く。
2. **最初に必ず、今のファームを吸い出す（§2）。**
3. 診断ファーム（A 版＝今の走査のまま）を書く（§3）。
4. ログを取りながら 01〜07 を測る（§4、§5）。任意で 10（30 分後）。
5. 実験ファーム（B 版＝パージ順序を変えたもの）を書いて 08〜09 を測る（§6）。
6. 解析する（§7）。
7. 吸い出したファームを書き戻す（§8）。
8. 持ち帰る（§9）。

ファイル名の番号（`m1-01-…`〜`m1-10-…`）は解析スクリプトがステップを見分けるのに使う。`m1-log.sh` を使えば自動でそうなる。

---

## 1. 準備

### 1.1 QMK MSYS（導入済みのはず）

- スタートメニューの「QMK MSYS」を開く。黒い画面（以下「MSYS」）が出る。
- `qmk --version` と打って Enter。バージョン番号が出れば OK。
- 入っていなければ https://msys.qmk.fm/ からインストーラを入れる（最初の起動時に `qmk setup` を聞かれたら、今回は飛ばしてよい。ファームのビルドはしない）。
- `python3 --version` も確かめる（解析スクリプトに使う。QMK MSYS には入っている）。

### 1.2 Arduino（今回は使わない）

この手順では Arduino IDE は使わない。診断ファーム（QMK）が動かなかったときの予備手段として design-spec M1-2 の Arduino 版テスターがあるが、それは別の手順になる。

### 1.3 作業フォルダとツールキット

1. エクスプローラで `C:\m1` を作る。
2. ブラウザで次を開き、ZIP をダウンロードする（ts52k リポジトリの tc52 ブランチ一式）：
   https://github.com/sadaoikebe/ts52k/archive/refs/heads/tc52.zip
3. ZIP を展開し、中の `docs\m1` フォルダの**中身**を `C:\m1` にコピーする。次のようになれば OK：
   ```
   C:\m1\README.md            （この手順書）
   C:\m1\m1-log.sh            （ログ取りの補助）
   C:\m1\m1_analyze.py        （解析）
   C:\m1\firmware\tc69-m1-diag.uf2
   C:\m1\firmware\tc69-m1-diag-purgeB-EXPERIMENTAL.uf2
   C:\m1\firmware\tc69-normal-rebuild.uf2   （非常用。§8.3）
   C:\m1\firmware\SHA256SUMS.txt
   ```
4. MSYS で確かめる：
   ```sh
   cd /c/m1/firmware
   sha256sum -c SHA256SUMS.txt
   cd /c/m1
   ```
   3 行とも `OK` なら、ファームのファイルは壊れていない。

### 1.4 picotool（Raspberry Pi 公式）

1. ブラウザで https://github.com/raspberrypi/pico-sdk-tools/releases を開く。
2. 最新のリリース（2026-11-13 時点で `v2.3.1-0`）の Assets から **`picotool-2.3.1-x64-win.zip`** をダウンロードする（名前に `picotool` と `x64-win` が入っているもの）。
   - picotool 本体のリポジトリ（github.com/raspberrypi/picotool）の README も「Windows 用のビルド済みはここ」としてこのページを案内している。
3. ZIP を `C:\m1` に展開する。`C:\m1\picotool\picotool.exe` ができるはず（違う場所にできたら、以下の `/c/m1/picotool` をその場所に読み替える）。
4. MSYS で：
   ```sh
   export PATH="/c/m1/picotool:$PATH"
   picotool version
   ```
   `picotool v2.3.1 (…)` のように出れば OK。**MSYS を開き直したら `export` の行をもう一度打つ。**

### 1.5 Zadig（picotool が TC69 を見つけられないときだけ）

RP2040 を Windows の picotool から触るには、ブート用の USB インターフェースに WinUSB ドライバが要る（picotool の README の「Zadig」の節）。§2 で picotool が次のどちらかを言ったら、ここをやる：

- `No accessible RP-series devices in BOOTSEL mode were found.`
- `... appears to be in BOOTSEL mode, but picotool was unable to connect. You may need to install a driver via Zadig.`

手順（TC69 を BOOTSEL モードでつないだ状態で。§2 の 1〜3）：

1. https://zadig.akeo.ie から Zadig をダウンロードして起動。
2. メニュー「Options」→「List All Devices」にチェック。
3. 上のドロップダウンから **`RP2 Boot (Interface 1)`** を選ぶ。**`Interface 0` は選ばない**（そちらは RPI-RP2 ドライブで、変えるとドライブが出なくなる）。
4. 右側のドライバ欄が **WinUSB** になっていることを確かめて「Install Driver」（または「Replace Driver」）。数分かかることがある。
5. 終わったら picotool のコマンドをやり直す。

### 1.6 その他

- **メモ帳**を開いておく。計測中のキー入力はメモ帳に流す（MSYS の画面にキーを打ち込まないため。特に Ctrl と C を同時に押すとログ取りが止まる）。
- 日本語入力（IME）は**オフ**にしておく。
- TC69 の XIAO RP2040 の **B（BOOT）ボタン**に指が届くか確かめる。XIAO の基板の USB 端子の横に、小さな「B」と「R」のボタンがある。ケースで隠れていて押せないなら、ケースを開ける必要がある（このキーマップには「ブートローダへ入るキー」が無いので、ボタン以外の入り方が無い）。
- スマホのストップウォッチ（秒数を数えるため）。

---

## 2. 最初に必ず：今のファームを吸い出す

**ここは飛ばさない。** 理由：

- TC69 の中に入っている QMK のファームは、ビルドした成果物がどこにも残っていない（firmware-audit.md §5。どの版が入っているかも分かっていない）。
- 診断ファームを書くと、今のファームは消える。
- `firmware\tc69-normal-rebuild.uf2` は「今の QMK で作り直したもの」で、2026-11 の NICOLA の修正も入っている。**今の TC69 の中身と同じではない**。今の打鍵感・挙動に確実に戻せるのは、ここで吸い出すファイルだけ。
- **吸い出しと検証が済むまで、§3 以降に進まない。** うまくいかなければ、何も書かずに終わりにする（TC69 はそのまま使える）。

手順：

1. TC69 の USB ケーブルを PC から抜く。
2. XIAO の **B ボタンを押したまま** USB ケーブルを挿し、挿してから 1 秒ほどしてボタンを離す。
   （挿したままでやるなら：B を押したまま R を 1 回押して離し、それから B を離す）
3. エクスプローラに **`RPI-RP2`** というドライブが出る（中身は `INDEX.HTM` と `INFO_UF2.TXT` の 2 つ）。これが BOOTSEL モード。キーボードとしては動いていない状態。
   - このドライブには、ファームを読み出したファイルは**無い**（RP2040 のブートローダは書き込み専用）。だから picotool で吸い出す。
4. MSYS で：
   ```sh
   cd /c/m1
   export PATH="/c/m1/picotool:$PATH"
   picotool info -a
   ```
   デバイスの情報が出れば、picotool が TC69 を見つけている（QMK のファームは picotool 向けの情報を持っていないので、「Program Information」がほとんど空でも問題ない）。見つからないと言われたら §1.5 の Zadig へ。
5. 吸い出す（`-a` ＝フラッシュ全体、`-v` ＝読み出した後に照合）：
   ```sh
   picotool save -a -v tc69-backup.uf2
   ```
   - `-a` を付けないと「Cannot determine the binary size」で失敗する（QMK のファームには大きさの情報が無いため）。
   - 1 分ほどかかる。XIAO RP2040 のフラッシュは 2 MB なので、ファイルは約 4 MB（4,194,304 バイト）になるはず。大きさが違っても、次の検証が通れば問題ない。
6. 検証する（TC69 の中身とファイルを突き合わせる）：
   ```sh
   picotool verify tc69-backup.uf2
   ls -l tc69-backup.uf2
   sha256sum tc69-backup.uf2 | tee tc69-backup.sha256
   ```
   `verify` の最後が **`OK`** なら吸い出し完了（`First mismatch at …` と出たら不一致。もう一度 5 からやり直す）。`save -v` でも同じ照合が走り、最後に `OK` が出る。
7. **`tc69-backup.uf2` と `tc69-backup.sha256` を、PC 以外にもう 1 か所コピーする**（USB メモリか Google ドライブ）。
8. ここではまだ何も書き込まない。そのまま §3 へ（BOOTSEL モードのままでよい）。

---

## 3. 診断ファーム（A 版）を書く

BOOTSEL モード（`RPI-RP2` ドライブが出ている状態）で、次のどちらか一方。

**方法 1：ドラッグ＆ドロップ**
`C:\m1\firmware\tc69-m1-diag.uf2` を `RPI-RP2` ドライブにコピーする。コピーが終わると TC69 が自動で再起動し、ドライブは消える（Windows が「ドライブが正しく取り外されなかった」と言うことがあるが、問題ない）。

**方法 2：picotool**
```sh
picotool load -v -x firmware/tc69-m1-diag.uf2
```
（`-v` は書き込み後の照合、`-x` は書き終えたら起動）

書いた後：

- 再起動の直後に、全キーの基準値（校正）を 1 回だけ取る。**挿す瞬間・再起動の瞬間はキーに触らない。** 校正の後で触る分には問題ない。もし触ってしまったら、USB を抜いて挿し直す（挿し直すと校正し直す）。
- メモ帳で何文字か打って、普通にキーボードとして動くことを確かめる。打鍵の判定は今までと同じ（診断ファームは値を読むだけで、判定には触らない）。
- **診断ファームの癖**：1 秒に 1 回、統計を PC に送る間（約 0.1 秒）と、キーを 1 回押して離した後に記録を送る間（離してキーが元の位置に戻ってから約 1 秒）、キーが反応しない。計測用なので、普段使いにはしない。

---

## 4. ログの取り方

1. MSYS をもう 1 つ開き（吸い出しに使ったものでもよい）、
   ```sh
   cd /c/m1
   ./m1-log.sh 00-check
   ```
   1 秒ごとに `#ADC seq=…` で始まる 40 行ほどのかたまりが流れれば OK。`Ctrl+C` で止める。`logs\m1-00-check-<日時>.log` ができる（確認用。解析には使わない）。
   - 何も出ない → §10 のトラブルシューティング。
   - `Permission denied` と言われたら `bash m1-log.sh 00-check`。
2. 各ステップは「`./m1-log.sh <ステップ名>` で記録開始 → 手を離して 5 秒待つ → 決まった操作 → 手を離して 5 秒待つ → MSYS をクリックして `Ctrl+C`」。1 ステップ 1 ファイル。
3. **操作中はメモ帳をクリックしておく**（キー入力をメモ帳へ流す）。MSYS の画面は流れっぱなしでよい（見なくてよい）。
4. ステップ 01〜07（と任意の 10）は、**途中で USB を抜かない**（挿し直すと校正が変わる。解析は各ログの中の無操作区間を基準にするので致命的ではないが、ノイズの比較がずれる）。
5. 失敗したら（別のキーに触った、数え間違えた等）、そのステップを `Ctrl+C` で止めて**同じステップ名で最初からやり直す**。古いファイルは `logs` から別のフォルダへ移すか、消す（同じ番号のファイルが 2 つあると、解析は両方を使う）。
6. 気づいたこと（「A に小指を載せたら a が打たれた」など）は紙かメモ帳の別ファイルに書いておく。

### キーの呼び方

TC69 の配列（`keyboard.json`）で、キーキャップの英字・数字で呼ぶ。最下段は左から：**Fn、Win、Alt、左親指（長いキー）、右親指（長いキー）、Alt、Win、Menu、←、↓、→**。

---

## 5. 計測（A 版）

各ステップの「目的」は `measurement-plan.md` の番号に対応する。

### 01 無操作（60 秒）— 計測 1

```sh
./m1-log.sh 01-idle
```
- 手をキーボードから 30 cm 以上離し、**60 秒**何もしない。机も揺らさない、ケーブルにも触らない。
- 60 秒たったら `Ctrl+C`（MSYS をマウスでクリックしてから）。

### 02 全キー押下（約 7 分）— 計測 2、3、4

```sh
./m1-log.sh 02-press
```
- 全 69 キーを、1 個ずつ、次の順で：**上の段から、左から右へ**（` 1 2 … BS Home、Tab Q … \ PgUp、Ctrl A … Enter PgDn、Shift Z … ↑ End、最下段 Fn … →）。
- 1 キーにつき：**底までしっかり押す → そのまま 3 秒 → 離す → 3 秒待つ。** 他のキーには触らない。押す指以外はキーボードから離す。
- 長押しでメモ帳に文字が連打されるのは問題ない。
- Win キー：離すとスタートメニューが開く。マウスでメモ帳をクリックして閉じ、3 秒待ってから次へ。Menu キー：右クリックメニューが出たら同様。Alt：メモ帳のメニューに移るだけ。
- 疲れたら途中で区切ってよい：`Ctrl+C` で止めて、続きを `./m1-log.sh 02-press-b` のように別名で取る（`02-` で始まっていれば全部まとめて解析される）。
- 時間が無いときの最低限：各段の左端・中央・右端の 3 キー、左右の親指、A。

### 03 最下段キーの漏れ込み（約 2 分 10 秒）— 計測 4、5

```sh
./m1-log.sh 03-leak
```
- 次の 8 キーを、この順に：**左親指、右親指、左 Alt、右 Alt、Fn、←、↓、→**。
- 1 キーにつき：**底まで押して 5 秒 → 離す → 3 秒待つ。**
- 8 キーを**2 周**する。
- （Win と Menu は、画面が変わるので外してある。）
- 09 で同じことを B 版でやる。押し方をそろえる。

### 04 A キーに小指を載せる（約 1 分 30 秒）— 計測 7

```sh
./m1-log.sh 04-pinky
```
1. 手を離して **10 秒**。
2. いつもの打鍵の姿勢で、**左手の小指を A キーに軽く載せる**（押し込まない。普段の「置いている」感じ）。そのまま **30 秒**。他の指はキーに触れないよう浮かせる。
3. 手を離して **10 秒**。
4. もう一度、小指を載せて **30 秒**。
5. 手を離して 5 秒待って `Ctrl+C`。
- メモ帳に `a` が打たれたかどうかをメモしておく（打たれたなら、載せただけで押下の判定が出たということで、それ自体が記録すべき結果）。

### 05 普通の速さの押下・解放（約 2 分 30 秒）— 計測 6

```sh
./m1-log.sh 05-normal
```
- **F を 10 回**：普段の文章を打つときの強さと速さで 1 回打つ → **3 秒待つ** → 次。
- 続けて **J を 10 回、A を 10 回、左親指を 10 回**、同じように。
- 3 秒待つのは、1 回ごとに記録の書き出し（約 1 秒、画面が勢いよく流れる）が入るため。流れている間に次を打つと、その 1 回は記録されないことがある。

### 06 ゆっくりの押下・解放（約 1 分 30 秒）— 計測 6

```sh
./m1-log.sh 06-slow
```
- **F を 5 回**：**約 2 秒かけてゆっくり底まで押す → 1 秒保持 → 約 2 秒かけてゆっくり離す → 5 秒待つ。**
- 続けて **A を 3 回**、同じように。
- 「ゆっくり」の途中で判定が出たり消えたり（メモ帳に文字が出たり出なかったり）しても、そのまま続ける。それが測りたいこと。

### 07 速い打鍵（約 40 秒）— 計測 6

```sh
./m1-log.sh 07-fast
```
- **F を 10 回**：できるだけ素早く、短く 1 回たたく → **3 秒待つ** → 次。

### 10（任意）30 分後の無操作 — 計測 9

- 01 を始めてから 30 分たつまで、TC69 を挿したまま触らずに置く（USB は抜かない）。
- `./m1-log.sh 10-idle-30min` で、01 と同じく**60 秒**無操作。
- やるなら、§6 の B 版に進む**前**に（B 版を書くと再起動で校正し直すため）。

---

## 6. 計測（B 版＝パージ順序の実験版）

B 版は、走査の順番を Arduino 時代の `sense.ino` の形（読んでからパージ、パージ 6 µs）に変えた**実験用**のファーム。ログの全ダンプに `purge=after` と `#WARN EXPERIMENTAL ...` が出る。キーボードとしても一応動くが、普段使いはしない。

1. §2 の 1〜3 と同じ手順で BOOTSEL モードにする（B ボタンを押しながら挿す）。
2. 書き込む（どちらか）：
   - `C:\m1\firmware\tc69-m1-diag-purgeB-EXPERIMENTAL.uf2` を `RPI-RP2` にコピー、または
   - `picotool load -v -x firmware/tc69-m1-diag-purgeB-EXPERIMENTAL.uf2`
3. 挿し直し・再起動の瞬間はキーに触らない。

### 08 B 版の無操作（30 秒）

```sh
./m1-log.sh 08-B-idle
```
手を離して **30 秒**。流れてくる行に `#WARN EXPERIMENTAL` が混ざっていることを確かめる（混ざっていなければ A 版のまま。書き込みをやり直す）。

### 09 B 版の最下段キーの漏れ込み（約 2 分 10 秒）

```sh
./m1-log.sh 09-B-leak
```
**03 とまったく同じ**：左親指、右親指、左 Alt、右 Alt、Fn、←、↓、→ を、5 秒押して 3 秒待つ、2 周。

---

## 7. 解析（その場で数字を見る）

MSYS で：
```sh
cd /c/m1
python3 m1_analyze.py all logs --out logs/m1-out
```
- `logs\m1-out\summary.md` に日本語の要約、同じフォルダに CSV（Excel で開ける）が出る。要約はメモ帳で読める。
- 画面に「step 01 (idle): …」と、各ステップに使ったファイルが出る。`— none —` のステップは、そのファイルが無い（名前を確かめる）。
- 個別に見るとき（例）：`python3 m1_analyze.py press logs/m1-02-press-*.log --baseline logs/m1-01-idle-*.log --out logs/m1-out`
- `python3` が無いと言われたら、Windows に入っている Python で `py m1_analyze.py all logs --out logs\m1-out`（PowerShell から。追加ライブラリは要らない）。

### 主な CSV の列（単位は 10 bit・1 サンプルのカウント）

| ファイル | 列 | 意味 |
|---|---|---|
| `baseline.csv` | `mean`, `sigma`, `pp_total`, `drift_last_minus_first` | 無操作時の平均、標準偏差、全区間の最大−最小、ログの最初と最後の平均の差 |
| `press.csv` | `delta_mean` | 全押下 Δ（押している 1 秒区間の平均 − 無操作時の平均） |
| | `full_pct_of_1023` | 押したときの値が ADC 上限の何 % か（§9 は 85% 以下） |
| | `margin_over_thr` | Δ − 押下閾値（120、A は 220） |
| | `snr_delta_over_sigma`, `snr_delta_over_pp` | Δ ÷ σ、Δ ÷ p-p（01 の無操作から） |
| | `tc52_est_*` | Δ に tc52-sim.md のモデル比を掛けた TC52 の推定（測定ではない） |
| `press_leak.csv`, `bottomrow_leak.csv` | `shift_mean`, `frame_min`, `frame_max`, `categories` | あるキーを押している間の、別のキーの平均の動きと 1 フレームの最小・最大（Δ）、位置関係の分類 |
| `*_leak_summary.csv` | | 押したキーごと・分類ごとの最悪値 |
| `ab_focus.csv` | `B_minus_A` | 最下段キーを押したときの、同じ列の行 0 の動き（B 版 − A 版）。報告書の推定は −18〜−6 |
| `pinky_r2c7_summary.csv` | `avg_delta_p50` など | 小指を載せた A の Δ の分布、120／220 を超えた割合 |
| `trace_*_summary.csv` | `press_band_ms` | 押すときに Δ が 30 から閾値まで上がるのにかかった時間 |
| | `release_band_ms` | 離すときに Δ が閾値から 30 まで下がるのにかかった時間 |
| | `rise_10_90_ms`, `plateau_delta` | 立ち上がり時間、底まで押したときの Δ |
| | `chatter_extra_transitions` | 押下・解放の 2 回以外に判定が反転した回数（チャタリング） |
| `trace_*_curves.csv` | `dt_ms`, `delta`, `d3_per_sample`, `judged` | カーブ本体（グラフにするならこれ）。`d3_per_sample` は判定に使う 3 フレーム平均 |
| `trace_*_envelope_episodes.csv` | | 50 ms ごとの包絡から見た、ゆっくり押しの各区間の時間 |
| `scan_summary.csv` | `scan_rate_hz`, `period_*_us`, `acquire_per_crosspoint_us` | 走査の速さとばらつき、1 交点あたりの時間 |

---

## 8. 元のファームに戻す

### 8.1 picotool で（推奨）

1. BOOTSEL モードにする（§2 の 1〜3）。
2. MSYS で：
   ```sh
   cd /c/m1
   export PATH="/c/m1/picotool:$PATH"
   sha256sum -c tc69-backup.sha256          # 吸い出したファイルが壊れていないこと
   picotool load -v tc69-backup.uf2         # 書き戻し＋照合（4 MB なので 1 分ほど）
   picotool verify tc69-backup.uf2          # 念のためもう一度突き合わせ
   picotool reboot
   ```
3. 挿し直し・再起動の瞬間はキーに触らない。メモ帳で打って、いつもの打鍵感・NICOLA の動きに戻っていることを確かめる。
4. `qmk console` を起動しても `#ADC` の行は流れないはず（元のファームには診断出力が無い）。流れたら、まだ診断ファームのまま。

### 8.2 ドラッグ＆ドロップで

`tc69-backup.uf2` を `RPI-RP2` ドライブにコピーしても戻せる（picotool が作る UF2 は普通の UF2）。ただし照合ができないので、できれば 8.1。

### 8.3 吸い出しを失くしたとき（最後の手段）

`firmware\tc69-normal-rebuild.uf2` を書く。今の QMK で作り直した通常版で、判定の仕組みと閾値は同じだが、元の中身と同一ではない（NICOLA に 2026-11 の修正が入っている、QMK 本体が新しい）。

---

## 9. 持ち帰るもの

`C:\m1` で次をまとめる：

- `logs` フォルダ（`m1-01-…` から `m1-10-…` のログと、`m1-out` の解析結果）
- `tc69-backup.uf2` と `tc69-backup.sha256`
- 気づいたことのメモ

MSYS で 1 つにまとめるなら：
```sh
cd /c/m1
zip -r m1-results-$(date +%Y%m%d).zip logs tc69-backup.uf2 tc69-backup.sha256 memo.txt
```
（`zip` が無いと言われたら、エクスプローラで右クリック →「送る」→「圧縮 (zip 形式) フォルダー」）

USB メモリか Google ドライブで持ち帰る。VM 側では `~/workspace/ts52k-ec/measurements/<日付>-tc69-m1/` に置き、同じ `m1_analyze.py all` で再解析できる。

---

## 10. トラブルシューティング

**BOOTSEL のドライブ（RPI-RP2）が出ない**
- B ボタンを押したまま挿しているか（挿してから押しても入らない）。R を使う方法も試す：挿したまま B を押し続け、R を 1 回押して離し、B を離す。
- ケーブルが充電専用でないか。いつもキーボードとして使えているケーブルなら問題ない。
- USB ハブを外し、PC 本体の端子に直接挿す。別の端子も試す。
- エクスプローラの「PC」を開き直す。数秒かかることがある。

**RPI-RP2 は出るのに picotool が見つけない／つながらない**
- §1.5 の Zadig。選ぶのは `RP2 Boot (Interface 1)`。
- Zadig で `Interface 0` を変えてしまい、RPI-RP2 ドライブが出なくなったら：デバイスマネージャーで該当デバイスを右クリック →「デバイスのアンインストール」（ドライバも削除）→ 挿し直す。
- `Cannot determine the binary size` → `save` に `-a` を付け忘れている。

**診断ファームを書いたのに `qmk console` に何も出ない**
- `Looking for devices...` のまま → TC69 がコンソールを持つファームで動いていない。`qmk console -l` で一覧に TC69（Shobon TC69 Oyayubi Shift）が出るか見る。出なければ書き込みをやり直す（元のファームにはコンソールが無いので、元のままだと何も出ない）。
- 一覧に出るのに行が流れない → 1〜2 秒待つ（1 秒に 1 回出る）。QMK Toolbox を開いているなら閉じる。USB を挿し直す。
- PC 側でコンソールを開いていない間の出力は捨てられる（ファームは止まらない）。ログ取りは `m1-log.sh` を始めてから操作する。

**ログの途中が欠けている、行が化けている**
- USB の都合でまれに起きる。解析は壊れたかたまりを飛ばす。大量なら、そのステップをやり直す。

**キーを離した後、1 秒ほどキーが効かない**
- 仕様（遷移の記録を送っている）。次の操作まで 3 秒待つ。

**解析で `no complete diagnostic dump found`**
- そのファイルに診断の出力が入っていない（ファイル違い、元のファームのまま、記録開始が遅れた）。

**解析のステップが `— none —`**
- ファイル名が `m1-<番号>-…log` になっていない。`m1-log.sh` を使うか、名前を直す。

**元に戻したのに様子がおかしい**
- BOOTSEL モードで `picotool verify tc69-backup.uf2` を実行し、最後が `OK` なら、フラッシュの中身は計測前とビット単位で同じ。

---

## 付録 A：ログの形式（fmt=2）

QMK コンソールに出る行（`qmk console` は先頭に `Shobon:TC69 Oyayubi Shift:1: ` を付ける）。詳しくは `keyboards/tc69/adc_diag_impl.h` の先頭。

```
#ADC seq=<n> t=<ms> scans=<n> scan_hz=<n>       1 秒ごとのかたまりの先頭（ここから下は従来どおり）
CAL r<行>: 16 値   校正値（基準値）
RAW r<行>: 16 値   最新 1 フレーム
MIN r<行>: 16 値   区間内の 1 フレーム最小
MAX r<行>: 16 値   区間内の 1 フレーム最大
D3  r<行>: 16 値   最新の 3 フレーム合計 − 校正合計（360 超で押下。A は 660）
PRS r<行>: XXXX    判定後のマトリクス（ビット＝列）
AVG r<行>: 16 値   区間平均 ×10                         （fmt=2 で追加）
SDV r<行>: 16 値   区間の標準偏差 ×10                   （fmt=2）
#SCN n=… per_min=… per_avg=… per_max=… acq_min=… acq_avg=… acq_max=…   走査周期と acquire_adc の時間（µs）
#HST bin_us=250 <16 個>                                 走査周期のヒストグラム
#CFG fmt=2 kb=tc69 purge=before|after ...              ビルドの設定
#WARN EXPERIMENTAL purge order ...                      B 版だけ
ENV t=<ms> n=<走査数> r2c7=<最小>,<最大>,<最新> ...      50 ms ごと。基準から ±20 以上動いたキーだけ
#TRC begin id=… seg=P|R key=r2c2 cal=… thr3=… rel3=… pre=… post=… other=… t0_us=…
T <P|R> <i> <dt_us> <生値> <D3> <判定>                   押下（P）・解放（R）の前後、1 行 1 走査
#TRC end id=… seg=P|R
```

並びは列 0〜15（4051 のアドレス順）、行 0〜4（ストローブ順）。キーとの対応は `keyboard.json` の `matrix`（解析の CSV では `r2c7` とキー名 `A` を併記）。

## 付録 B：診断ファームの作り方（VM 側の記録）

- ソース：sadaoikebe/qmk_firmware の sadao-master、`keyboards/tc69/`（コミット c22ba5c9 と a54896da）。
- ビルド：`make tc69:nicola TC69_ADC_DIAG=yes`（A 版）、`make tc69:nicola TC69_ADC_DIAG=yes TC69_DIAG_PURGE=after`（B 版）、`make tc69:nicola`（通常版）。
- 通常版（診断なし）は、この変更の前後でバイト単位で同一（`SHA256SUMS.txt` の `tc69-normal-rebuild.uf2` の値は変更前のビルドと一致）。
- `sim/`：本物の `matrix.c` を PC 上でコンパイルし、おもちゃの電気モデルにつないだシミュレータと、手順どおりの合成ログを作るスクリプト。`./sim/build_sim.sh <qmk_firmware> before|after` → `python3 sim/gen_logs.py sim/sim-before sim/sim-after <出力先>`。数値に意味は無い（パイプラインの動作確認用）。
