# TS52Kの部品ライブラリ

2026-11-03。無線版の採用部品を登録済み。[現行決定事項](../notes/wireless-decisions.md)に従い、KiCad 10.0.5の公式ライブラリを基準に使用分を同梱した。回路図は無線版へ移行・検査済み、PCBには無線部品を仮置きした。メーカー図や既存回路図に合わせた図形の変更は以下に記載する。

## 回路図で選ぶもの

- `ts52k`：選定済み20品種（2026-11-11にAO3401Aを追加）のシンボルと既存のMXスイッチ。20品種には`MPN`、`Manufacturer`、`LCSC`、`JLCClass`と`ts52k:`のフットプリントを設定済み。抵抗・容量・インダクタ・水晶の`Value`には値を表示し、完全型番は`MPN`で保持する。
- `tag-connect:TC2030_IDC_NL`：SWD接点。部品実装がないためBOM・実装座標出力から除外。既存IDを維持し、ライブラリの既定ランドを`ts52k:`に変更した。1=VTref、2=SWDIO、3=nRESET、4=SWCLK、5=GND、6=NC。
- `MX_Only`：現在使用している7種類のMXキー用フットプリント。

[部品対応表](wireless-library.csv)に20品種・82点のシンボルIDとフットプリントIDを記載した。[仮BOM](../notes/wireless-bom-draft.csv)と対応する。SWDは実装部品でないため19品種の外にある。キースイッチと既存エンコーダもPCBA用の仮BOMには含めない。

`sym-lib-table`と`fp-lib-table`は`${KIPRJMOD}`を使い、他のPCでも同じファイルを参照する。プロジェクトのピン留めには`ts52k`、`MX_Only`、`tag-connect`を設定した。KiCad全体の標準ライブラリ設定には変更を加えていない。

## 公式ライブラリからの採用

| 対象 | 元のシンボル／フットプリント | 登録時の扱い |
| --- | --- | --- |
| MDBT50Q-1MV2 | `RF_Module:MDBT50Q-1MV2` / `RF_Module:Raytac_MDBT50Q` | 61端子の公式定義を採用。全層アンテナ禁止領域の長さを3.75から3.8 mmへ変更 |
| BQ24072RGTR | `Battery_Management:BQ24072RGT` / `Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm` | シンボルの旧1.6 mm EPランド既定値を、採用済みの1.68 mm EPランドへ変更。EPは17番 |
| 抵抗・容量・コイル | `Device:R`、`R_Small`、`C`、`L` / 各標準Metricランド | CC抵抗は既存の配置・端点を維持するため公式R_Small図形。他はR/C/L。0603、0402、0805を選定表どおりに割当て |
| FC-12M | `Device:Crystal` / `Crystal:Crystal_SMD_2012-2Pin_2.0x1.2mm` | 下記のEpson専用ランドへ変更 |
| 電池コネクタ | `Connector_Generic:Conn_01x02` / `Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal` | 1=BAT+、2=GNDをシンボルの説明に記載。MPは固定金具 |
| USB-C | 既存`ts52k:USB_C_Receptacle_USB2.0` / `Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12` | 既存部品を継続し、標準ランドを同梱 |
| H5VU10U | 既存`ts52k:H5VU10U` / `Diode_SMD:D_SOD-882D` | 下記のメーカー推奨ランドへ変更 |
| リセットスイッチ | `Switch:SW_Push` / 既存`rp2040:SW_Tactile_XKB_TS-1187A_5.1x5.1mm` | 既存採用ランドを`ts52k`へコピー。1・2各2パッドの定義を継続 |
| 1N4148W | `Device:D_Small` / `Diode_SMD:D_SOD-123` | 既存マトリクスの配置・端点を維持するため公式D_Small図形を採用。1=K、2=A |
| AO3401A（Q1、2026-11-11追加） | `Transistor_FET:AO3401A`（`TP0610T` の図形・ピンを継承する定義）／ `Package_TO_SOT_SMD:SOT-23` | KiCad 10.0.8の公式定義から、継承をほどいた独立シンボルとして登録。1=G、2=S、3=D。ランドは無変更で同梱 |
| SWD | 既存`tag-connect:TC2030_IDC_NL` / `Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical` | 標準ランドを同梱。6接点にペースト無し、位置決め穴3個。回路図のピン名文字を1 mmへ縮小して重なりを解消 |

コピー元のライブラリIDとSHA-256を[library-sources.json](library-sources.json)に保存した。シンボルのハッシュは元の公式`.kicad_sym`ファイル全体、フットプリントは元の`.kicad_mod`のもの。独立したシンボルとして同梱しているため、他のローカルシンボルへの継承依存はない。

公式ライブラリの著作者はKiCad community。[公式シンボル](https://gitlab.com/kicad/libraries/kicad-symbols)、[公式フットプリント](https://gitlab.com/kicad/libraries/kicad-footprints)を出典とし、同梱・改変した公式ライブラリ部分には[KiCadライブラリのライセンス](KICAD-LIBRARY-LICENSE.md)を適用する。

## メーカー図に合わせた変更

- **Raytac**：[Version L](https://www.raytac.com/download/index.php?index_id=43) p9・11に合わせ、アンテナの禁止領域をx=−6.2〜6.2、y=−7.75〜−3.95 mmにした。全銅箔層で配線・ビア・パッド・ベタを禁止。標準の実装面局所禁止領域1.6×1.2 mmも維持する。基板配置時は横方向の拡張と基板端への配置を確認する。
- **Epson**：[FC-12M推奨図](https://download.epsondevice.com/td/pdf/brief/FC-12M_en.pdf)に従い、`Crystal_Epson_FC-12M_2.05x1.2mm`を作成。各ランド0.7×1.4 mm、中心間1.5 mm。端子間0.8×1.4 mmを実装面の銅箔禁止領域にした。Fab外形は2.05×1.2 mm。近似の汎用3Dモデルは付けない。
- **hongjiacheng**：[H5VU10U Rev.2.0](https://datasheet.lcsc.com/lcsc/2504101957_hongjiacheng-H5VU10U_C22395519.pdf)に従い、`H5VU10U_DFN1006-2L`を作成。各0.55×0.60 mm、中心間0.85 mm、端子間隙0.30 mm。1=カソード／信号、2=アノード／GND。ペーストもこのランドに合わせ、元の分割ペーストパッドと汎用3Dモデルは取り除いた。

BQ24072は[TIの現行RGT0016C図](https://www.ti.com/lit/ds/symlink/bq24072.pdf)と照合した1.68 mm EPの標準ランドを使う。周辺ランドはメーカー図の完全な複製ではなく、標準ライブラリの外側へ長い形状を採用する。中央ペーストの分割は標準定義を維持し、EP17はGNDに接続する。

水晶・モジュールの禁止領域はF.Cuを実装面として定義する。裏面実装ではKiCadの面反転を使う。手作業でピンを鏡像に変更しない。SWDの他信号に対する0.508 mm離隔など、基板全体で適用する条件は[配置条件](../notes/wireless-layout-check.md)を参照する。

## 削除したもの

- 不採用の`TPD4E1U06DCKR`、`ESD321DPYR`、`ESD441DPYR`を`ts52k.kicad_sym`から削除。
- 未使用のRP2040ランド候補`IC57_RP2040-L`、`IC57_RP2040-M`を削除。
- 参照されていなかった`tag-connect.pretty`の重複ランドと、そのライブラリ登録を削除。SWDの採用ランドは`ts52k.pretty`に一本化。

- `rp2040.kicad_sym`、`rp2040.pretty`全体と両ライブラリテーブルの登録を削除。リセットスイッチの採用ランドは`ts52k.pretty`へ移したものを使う。
- 旧LDOの`ts52k:TPS7A2433DBVR`を削除。

ライブラリは無線版で使用するものに整理した。無線版回路図への移行で旧RP2040子シートと未使用の埋め込みシンボルも除去済み。PCBの旧部品と旧ライブラリIDも仮配置時に取り除いた。

## 確認結果

2026-11-11にKiCad 10.0.8で `check_libraries.py` を再実行し、21個の`ts52k`シンボルと15個のフットプリント、20品種・82点でPASS（[結果](library-validation.json)）。以下は当初の確認記録。

KiCad 10.0.5で20個の`ts52k`シンボルと14個のフットプリントをSVG出力し、全フットプリントをKiCad APIでも読み込んだ。19品種の型番・数量・LCSC番号と仮BOMの一致、全シンボルのピン番号と対応ランドのパッド番号の一致、モジュールの主要電源・USB・SWD端子番号、水晶とESDのランド寸法、SWDのペースト無しを確認済み。固定金具MP、穴、ペーストだけのパッドは電気端子として数えない。

両ライブラリテーブルの登録先と採用部品の参照先に欠落なし。ライブラリ検査と別に、[無線版回路図の検査](schematic-review/validation.json)でERCエラー・警告とも0件、BOMと全主要ネットを照合済み。PCBは仮配置段階で、[parityは0件、DRCには未解消事項あり](placement-review/README.md)。実機起動は未検証。

検査は[check_libraries.py](check_libraries.py)で再実行できる。[library-validation.json](library-validation.json)に合格した検査項目、KiCad版、対象ファイルのSHA-256を保存した。回路図・PCBを変更する処理はない。

```powershell
& 'C:/Program Files/KiCad/10.0/bin/python.exe' pcb/check_libraries.py --report pcb/library-validation.json
```

KiCad Pythonで実行する。スクリプトは未採用ライブラリの不存在、BOMの型番・分類・数量、ピンとパッド、専用ランド、全層アンテナ禁止領域、SWDの実装除外を検査し、KiCad CLIで全登録シンボルと採用ランドをSVG出力する。JSONのハッシュは今回の対象を識別するもので、後からファイルを変更した場合の合格を保証しない。
