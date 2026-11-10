# ZMKと対応するハードウェア起動条件

2026-11-10更新。[現行決定事項](wireless-decisions.md)と[部品BOM](wireless-bom-draft.csv)に従う。従来の最小ZMKのビルド・出力設定照合と、無線版回路図・PCBへの反映は別工程。PCBはU5を西端へ移した無線版で、18信号の新割当てを反映済み。ZMK側の同期・再ビルドと実機起動は未実施。[同期チェックリスト](zmk-pin-sync-checklist.md)を参照。

## 基準にする版と成果物

| 対象 | 固定した版・ファイル |
| --- | --- |
| ZMK | main `4dd95d7840eb3d5a3f59bb29fbf1ab054715ef85` |
| Zephyr | `10ba6d0cb38bc3d258775d27982f707599320085` / 4.1.0 |
| Adafruitブートローダ | 0.11.0、ソース`c67f0bcf0fa8e841426335b1bbde91cda6ca1f50` |
| 初回SWD候補HEX | `nice_nano_bootloader-0.11.0_s140_6.1.1.hex`、SoftDevice結合版 |
| 最小ZMK UF2 | `C:\Users\marur\zmk\app\build-ts52k-main-verified\zephyr\zmk.uf2` |

UF2 SHA-256は`fb828611ee074e82a9c90dda64dc1209e44b9cac1bbc338699ea9bfe5b71d467`。HEX SHA-256は`1b72d4cd163239dec96231b3549d541cbc96b7a64b3041b635482ca4d7441f7e`。

再現手順、最終.config、Devicetreeと領域照合は`C:\Users\marur\zmk-config\docs\ts52k-main-bringup.md`にある。実装コードは同リポジトリで管理し、ここへ複製しない。

## 回路との対応

| 項目 | 初版の採用内容・根拠 |
| --- | --- |
| VDDH給電 | BQ24072 OUT→モジュール30番。RaytacのVDDH参考構成 |
| REG0 | ZMKでDC/DC有効、DCCH(31)–VDD(28)へ外付け10 µH / C713281。REG0 LDOは以前の試験設定であり、固定設計条件ではない |
| REG1 | ZMKでDC/DC有効。32 MHz水晶とREG1用インダクタはモジュール内蔵 |
| VDD電圧 | ブートローダ初期化により3.3 V。UICR未設定・全消去直後は1.8 V |
| LFクロック | ZMKは外付け32.768 kHz、XTAL/50 ppm。C96341＋12 pF / C1547×2。ブートローダは内蔵RCで動作 |
| デカップリング | VDDは4.7 µF＋1 µF＋100 nF×3、VDDHは10 µF、VBUSは4.7 µF。他は[容量表](capacitor-selection.md) |
| USB | アプリ・ブートローダの既存申告設定を維持。USB100固定充電。USB状態連動の追加制御は初版で実施しない |
| リセット | P0.18 / モジュール40番。SW1でGNDへ。ブートローダ初期化にCONFIG_GPIO_AS_PINRESETの経路あり |
| 初回SWD | VTref=VDD(28)、SWDIO=51、SWCLK=53、nRESET=40、GND。6番NC。1.8 Vと3.3 Vへ対応 |
| 入力 | 既存UF2はP0.06列・P0.08行の旧1接点検証用。現PCBではそれぞれcol4・col3の出力側であり、このUF2を現PCBの走査確認に流用しない。本番18本は[GPIO表](wireless-pin-assignment.md)に従って同期する |
| 未使用機能 | P0.13のEXT_POWER制御を置かずrow3に使う。row6はP0.29。ブートローダのLED端子P0.15はNC |

電源回路をZMKの版ごとに変える要求ではない。実装回路に適合する基板定義を維持する。インダクタ実装回路でブートローダがLDO、アプリがDC/DCでも矛盾しない。ブートローダとアプリのLF源も同じである必要はなく、それぞれが実装回路に適合すればよい。

## 確認した起動経路

1. USBから基板給電。消去直後のVDD=1.8 VでもSWDへ接続できる端子構成を持つ。
2. 通常品はSWDからSoftDevice結合HEXを書き込み、検証・再起動する。更新用UF2だけを初回HEXの代用にしない。
3. 未設定のPSELRESETとREGOUT0をブートローダの初期化処理が設定する経路をソースで確認した。既に別の値が書かれたUICRを常に上書きするとは扱わない。
4. 初回基板でVDDとUICRを読戻し、USBブートローダを確認してからZMK UF2を導入する。
5. ZMKのUSB入力、BLE入力を確認する。全マトリクス・NICOLAの実装はその後のファームウェア開発で行う。

HEXのチェックサム・アドレス範囲と、ZMKアプリ開始0x26000、保存領域0xec000、ブート領域0xf4000との非重複を確認済み。配布バイナリの全初期化命令の逆アセンブル照合と実機でのUICR読戻しは未実施。

SWDランドは必須。機材の機種・購入時期・モジュール購入先は後日決める。[通常品と書き込み済み品の比較](swd-equipment.md)を参照し、機材購入を基板設計の条件にしない。

## 先行例と判断の根拠

- [Raytac資料 Version L](https://www.raytac.com/download/index.php?index_id=43)：モジュール内蔵部品、REG0外付け10 µH、電源・端子・アンテナ・USB参考図。旧Version Kとの参照ページ差を区別する。
- [nice!nano v2公開回路](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/)：10 µH、FC-12M＋12 pF×2、VDDの5個構成と固定充電の手本。公開図の充電IC表記はBQ24075で、TS52KのBQ24072と同一ではない。
- [Adafruit 0.11.0](https://github.com/adafruit/Adafruit_nRF52_Bootloader/releases/tag/0.11.0)と[固定ソース](https://github.com/adafruit/Adafruit_nRF52_Bootloader/tree/c67f0bcf0fa8e841426335b1bbde91cda6ca1f50/src)：REGOUT0、RCクロック、LED、フラッシュ領域。[nrfx初期化](https://github.com/NordicSemiconductor/nrfx/blob/7a4c9d946cf1801771fc180acdbf7b878f270093/mdk/system_nrf52840.c)：P0.18リセット設定。
- [Nordic UICR](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/uicr.html)、[デバッグ仕様](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/dif.html)：消去後電圧とCTRL-AP復旧。採用末尾は-1MV2で固定し、別末尾への自動置換をしない。

MDBTMicroの未製造・未試験版を動作実績として扱わない。独自の温度範囲や水晶省略を設計要件にしない。部品・GPIOを回路図へ反映し、[結線・ERCを確認済み](../pcb/schematic-review/validation.json)。電源波形、水晶精度、USB/BLEの動作は試作後に検証する。
