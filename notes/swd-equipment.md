# 初回SWD書き込み用の機材

2026-11-03。調達経路と機材の調査記録。機種未決・未購入・実機未検証。基板側は採用済みTC2030-NLランドを使い、部品は実装しない。[決定事項](wireless-decisions.md)に従い、機材購入を基板設計の条件にしない。

## 現在の決定事項

ユーザー判断により、**SWDランドは必須として残し、SWD機材の機種・購入時期は後で決める**。以下のJ-Link／Tag-Connect一式は調査記録であり、採用・購入決定ではない。

モジュールは通常品と秋月のブートローダー書き込み済み品のどちらも調達候補にできる。JLCPCB通常在庫品を実装する場合は、Adafruitブートローダーなしを想定して初回SWD書き込みを計画する。秋月品との比較や機材の決定は、現在の部品選定を止める条件にしない。電源・クロック・SWD配線は両方の調達経路に対応する構成として進める。

## 追記: 書き込み済みモジュールの購入で初回SWDを省く対案

機材選定後、ユーザーの指摘を受けて[秋月電子117928](https://akizukidenshi.com/catalog/g/g117928/)を確認した。商品名は「ブートローダー書込済Bluetoothモジュール MDBT50Q-1MV2」。**モジュール単体**で、Adafruit nRF52 Bootloader書き込み済みと明記される。2026-11-03確認時は税込1,430円・在庫あり。

従って「MDBT50Q-1MV2を使うには、自分で最初のブートローダーを書き込む機材を必ず買う必要がある」という前提は置かない。これまで照合したRaytac標準品の工場テストコードと、秋月が書き込み済みとして販売する商品は区別する。機材の購入は前節のとおり後で決める。

商品ページと秋月のAE-NRF52840関連資料では、書き込まれているブートローダーの版、ビルド対象、SoftDevice版、アプリ開始アドレス、VDDH給電時のREGOUT0初期化条件までは特定できなかった。既存のnice_nano用0.11.0 HEXと同一だとは扱わない。これらがTS52Kの構成と一致すれば、通常の初回導入をUSBから始め、SWDは復旧・デバッグ用という位置づけにできる。SWDランドは保持する。

秋月購入品をJLCPCB通常在庫のC5118826と同じ調達品として扱わない。持込実装などの製造手配は未決で、今回その手続きや購入はしていない。以下の機材一式は、標準品への初回書き込みまたは復旧が必要になった場合の候補として残す。

## 調査した機材一式（機種決定は後日）

| 項目 | 型番・条件 | 数量 | 確認内容 |
| --- | --- | ---: | --- |
| 書き込み器 | SEGGER J-Link EDU Mini **V2**、USB-C版、製品番号8.08.91 | 1 | 1.8 V／3.3 VのSWDに対応。非商用の個人・教育用途を前提とする |
| SWDケーブル | Tag-Connect **TC2030-CTX-NL**、**Normal Orientation** | 1 | Cortex 10ピン・1.27 mmピッチ側をEDU Miniへ直接接続し、6接点側を基板J2へ当てる |
| 保持具・任意 | **TC2030-CLIP-3PACK** | 1袋 | ケーブルを手で押さえず使うための3個入りクリップ。初回書き込みだけなら手押しでも接続可能 |
| PC用USBケーブル | データ通信対応USB-Cケーブル | 必要分 | 書き込み器用とTS52K給電用。手持ち品を使える |

このEDU Mini案ではJ-Link BASEや20ピン変換アダプタは不要。TC2030-IDC-NLはランド形状の名称として既存ファイルに現れるが、EDU Mini案に対応するケーブルは**CTX-NL**。脚付きTC2030-CTXは、現在の3位置決め穴だけのNLランド向けには選ばない。

根拠:

- [SEGGER V2仕様](https://kb.segger.com/J-Link_EDU_Mini_V2): 1.8 V／3.3 V、USB-C、0.05インチのCortexヘッダ、ターゲット給電なし。
- [Tag-ConnectのEDU Mini接続案内](https://www.tag-connect.com/debugger-cable-selection-installation-instructions/segger-j-link-edu-mini): TC2030-CTX-NLを直接接続する構成を掲載。
- [TC2030-CTX配線図](https://www.tag-connect.com/wp-content/uploads/bsk-pdf-manager/TC2030-CTX_1.pdf): 以下の信号対応を照合。

## 価格と利用条件

[SEGGER米国ショップ](https://shop-us.segger.com/product/j-link-edu-mini-8-08-91/)の参考価格は$76、[TC2030-CTX-NL](https://www.tag-connect.com/product/tc2030-ctx-nl-6-pin-no-legs-cable-with-10-pin-micro-connector-for-cortex-processors)は$42.95、[クリップ3個](https://www.tag-connect.com/product/tc2030-retaining-clip-board-3-pack)は$18。

本体とSWDケーブルで**$118.95**、任意のクリップを含めると**$136.95**。税・送料を除く参考額で、日本向け購入総額ではない。基板ごとのBOM費用ではなく、繰り返し使う開発機材の費用。

本体の型番8.08.91だけで旧版を区別できるとはしない。購入時は**V2・USB-C・1.8 V対応**を確認し、3.3 V専用の旧V1を取り違えない。[SEGGERの利用条件](https://www.segger.com/products/debug-probes/j-link/models/j-link-edu-mini/#licensing-and-support)は非商用の教育・個人用途に限定する。商用製品の開発や業務利用にはこの選定を流用しない。今回は個人の非商用開発という前提での機材候補で、購入操作はしていない。

## J2の信号対応

| 基板J2／TC2030側 | TS52K無線版の接続先 | Cortex 10ピン側 |
| ---: | --- | ---: |
| 1 | VTref。MDBT50QのVDD、パッド28 | 1 |
| 2 | SWDIO、モジュールパッド51 | 2 |
| 3 | nRESET。P0.18、モジュールパッド40 | 10 |
| 4 | SWCLK、モジュールパッド53 | 4 |
| 5 | GND | GND系。ケーブル図では3／5／9 |
| 6 | SWOは未接続 | 6 |

READMEで予定している無線版J2配列と一致。既存RP2040版PCBもCTX配列の6接点と3位置決め穴を使っていることを確認した。ただし既存PCBのJ2-1はRP2040用の+3V3ネットであり、無線版へ流用する際は必ずMDBT50QのVDDへ接続する。接点番号は基板実装面とメーカー図の向きを合わせ、改版時に再照合する。クリップを使う場合はJ2周辺の反対面にも保持具の空間を残す。

## 電源と初回起動の扱い

TS52KはUSBから給電する。J2-1のVTrefは基板が出しているVDDを読む端子で、書き込み器から3.3 Vを供給する端子ではない。EDU Mini V2にはターゲット給電機能がない。

消去直後のVDDは1.8 V。ブートローダ初期化後は3.3 Vになるため、将来選ぶ機材はその両方に対応させる。調査例のEDU Mini V2は対応するが、機種の採用決定ではない。SWD接続は当初100 kHz程度から試す。SWOの接続は初回書き込みや通常のSWDデバッグには必須ではない。

Windows側はSEGGER J-Link Software and Documentation Packを使い、対象を`nRF52840_xxAA`、インターフェースをSWDに指定する。[J-Link Commander](https://kb.segger.com/J-Link_Commander)はHEX書き込みと検証に対応する。保護解除を伴う全消去には[Nordic nRF Utilのdevice recover](https://docs.nordicsemi.com/bundle/nrfutil/page/nrfutil-device/guides/programming_recovery.html)を使う経路を予定する。機材選定のための確認で、今回インストールや消去コマンドの実行はしていない。

初回用ファイルは検査済みの`nice_nano_bootloader-0.11.0_s140_6.1.1.hex`。以後の最小ZMK UF2と領域の関係は`C:\Users\marur\zmk-config\docs\ts52k-main-bringup.md`に記録済み。実機では、給電とVDD測定、SWD接続、消去、HEX書き込み・検証、再起動後のVDD／UICR読戻し、USBブートローダ認識、ZMK UF2書き込みの順に確認する。
