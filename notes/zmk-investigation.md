# ZMK調査メモ（保留・未検証）

記録日: 2026-11-02

この文書はNICOLA移植について確認した情報の退避先で、方式は未決・未実装。このメモ作成後、別リポジトリ`C:\Users\marur\zmk-config`でハードウェア起動用の最小ZMKをビルド済み。[現在の起動条件](zmk-hardware-bringup.md)を参照。NICOLA移植とUSB/BLE実機検証は未実施。

## 今回の検討範囲

ts52kはハードウェアのリポジトリ。今回はZMKとブートローダが動作するために基板側で必要な電源、クロック、GPIO、USB、SWD、リセットなどを検討する。

NICOLAの内部実装、イベント処理、テスト基盤など、ハードウェア設計に影響しない事項は将来のZMK開発時に検討する。これらの実装完了をハードウェア設計開始の条件にしない。

## 確認した現行実装

- QMK本体: `C:/Users/marur/qmk_firmware`
- ユーザー実装: `C:/Users/marur/qmk_userspace`
- 判定本体: `users/nicola/nicola.c`、`nicola.h`
- 出力表: `users/nicola/nicola_table.c`、`nicola_table.h`
- キーマップ: `keyboards/ts52k/keymaps/nicola/keymap.c`
- 仕様: `docs/NICOLA-SPEC.md`（旧実装に関する記述も含む）

上記は調査時のローカルファイルを参照した。コミットや未コミット差分は固定していないため、将来の互換性基準にはその時点で対象版を確定する必要がある。

キーボード側で親指シフトを判定し、ホストへローマ字のキー出力を送る。RP2040へのQMK移植の検討は今回の対象外。

判定本体は5状態（S_INIT/S_M/S_O/S_MO/S_OM）。期限80 ms、重なり下限20 ms、逐次判定の比係数1。3キーの前後関係判定、通常キーの追い越し防止用8イベントバッファがある。英数入力も親指シフト判定を通す。

重要: 現行出力は文字ごとのタップ列ではない。たとえば「な」はN、Aを順次押下し、保持後に解放する。出力済みのコードをheld_m/o/omに記録し、解放時は表を引き直さない。仕様書はtap_code/send_stringへの置換を禁止し、長押しで「なあああ…」になることを意図した挙動としている。会話中の「ローマ字をタップ列として出力する」という初期提案は不適切であり撤回。

## ZMKについて確認した拡張点

- Cで独自behaviorを外部モジュールとして追加できる。
- キー押下・解放をイベントとしてHID処理へ送る経路がある。
- behaviorの押下・解放を待ち時間付きで処理するキューがある。ただし現在のNICOLA仕様にそのまま適用できるとは判断していない。

参考:
- https://zmk.dev/docs/development/new-behavior
- https://zmk.dev/docs/features/modules
- https://zmk.dev/docs/development/events
- https://github.com/zmkfirmware/zmk/blob/main/app/src/behaviors/behavior_key_press.c
- https://github.com/zmkfirmware/zmk/blob/main/app/src/hid_listener.c
- https://github.com/zmkfirmware/zmk/blob/main/app/src/behavior_queue.c

参照URLのmainは変動する。採用版で再確認すること。

## 将来のファームウェア開発へ保留する事項

独自behaviorから共通の判定エンジンへ入力を渡す方式は候補であり、未決定。

- 判定ロジックとQMK依存APIの分離、キーコード表現とPROGMEM読み出しの置換。
- 通常キーの追い越し防止。NICOLAキーだけを独自behaviorにしても現行動作は再現できない。
- 修飾キー中のレイヤー切替、出力時だけのShift反転、モード切替。
- QMKのdefer_execと入力処理の直列性を、ZMK/Zephyr上でどう再現するか。
- 処理時刻とイベント時刻の差、期限境界、古いタイマの取消。
- 出力保持とUSB/BLEでのレポート順序、長押し、同一キー再入力。
- 現行実装を基準とする入力トレース比較、USB/BLE実機試験。

これらを確認せず「互換移植できた」とは言えないが、現時点で基板変更が必要だという証拠もない。

## ハードウェア検討に残す項目

以下は確認対象であり、全項目の適合を確認済みという意味ではない。

- VDDH/VDD/VBUSの結線、動作電圧範囲、必要な外付けコンデンサ。
- DC/DC各段の外付け部品と設定の対応。現在はREG0インダクタを実装し、ZMKで両DC/DC有効と決定済み。
- 32.768 kHz水晶を実装。ブートローダはRC、ZMKはXTAL/50 ppmで、それぞれが回路と対応する構成を採用済み。
- REGOUT0、nRESET設定、初回SWD書き込みと復旧手段、デバッグ電圧。
- GPIO割当、特殊機能ピンとの競合、マトリクス極性、スリープ復帰。
- エンコーダの停止時接点状態とプルアップ電流、休止時の扱い。
- BQ24072 OUTを読むVDDH残量測定の限界。充電中はセル電圧そのものではない。

無線通信の成立には別途、アンテナ周辺の金属・電池・基板銅箔・ケースを含めた配置検討が必要。
