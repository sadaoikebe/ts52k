> **このブランチ（tc52-wireless）の製造データは TC52 wireless（MDBT50Q＋BQ24072、4 層）のものです。** ガーバー zip・BOM 31 行・CPL 67 点は `export.py` で再生成済み。**発注時は 4 層・1.6 mm・スタック JLC04161H-7628（L1–L2／L3–L4 が 7628 プリプレグ 0.2104 mm）を明示する**（`assembly/export-status.txt` にも出力される）。発注時の指定と確認事項は [docs/tc52w-build-log.md](../../docs/tc52w-build-log.md) の「製造データ」を参照。以下の本文は Rev 0.2（RP2040 版）の記述のままです。

# Revision 0.2 — JLCPCB 向け出力

**Revision 0.2 のガーバー・ドリル・BOM・実装座標を同梱しています。**

## 電源・USB ESD保護

- U3 は **TPS7A2433DBVR / C2866134**。SOT-23-5 の 1=+5V、2=GND、3=+5V（EN と IN を直結）、4=GND（NC端子を放熱用に接続）、5=+3V3。[TI データシート](https://www.ti.com/lit/gpn/TPS7A24)
- C3 は **CL10A475KA8NQNC / C69335、4.7 µF、25 V、0603**。入力側の C4 は1 µFのまま、位置を調整。U3出力側のC5は従来の **CL05A475MP5NRNC / C23733、4.7 µF、10 V、0402** のままです。メーカーの典型DCバイアスデータでは、C3は5 Vで約2.43 µF、C5は3.3 Vで約2.43 µFです。これは典型値であり、温度・個体差を含む保証値ではありません。[C3](https://product.samsungsem.com/mlcc/CL10A475KA8NQN.do) / [C5](https://product.samsungsem.com/mlcc/CL05A475MP5NRN.do)
- D−のD89、D+のD90、VBUSのD91に **H5VU10U / C22395519** を使用しています。各素子の1番は保護する線、2番はGNDです。[JLCPCB 部品情報](https://jlcpcb.com/partdetail/C22395519)
- 3個ともKiCad標準の `Diode_SMD:D_SOD-882D` を使用し、Bottomに実装します。現在の位置と向きは基板データと実装座標を参照してください。
- J1はKiCad標準の `Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12`、C13は `Capacitor_SMD:C_0402_1005Metric`、J2は `Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical` です。J1のシールド端子 `SH` はGNDに接続しています。J2は標準のベタ銅箔とビアの禁止領域を含みます。
- C3・C4はU3入力とGNDの間、C5・C21は3.3V出力とGNDの間に接続しています。U3の2番・4番はGNDに接続しています。回路・ESD波形の実測は未実施です。
- USB付近の配線と保護素子の位置は基板データを参照してください。USB信号品質は未測定です。



## 基板と検査

- 銅箔と基板外周の設計ルールを **0.25 mm** にし、表裏の GND ゾーンを再充填して基板に保存しました。JLCPCB の通常のルーター外形では銅箔まで 0.2 mm 以上が必要です。[JLCPCB 基板製造能力](https://jlcpcb.com/capabilities/pcb-capabilities)
- BOOTSEL の SW1 は、上押し式 **XKB TS-1187A-B-A-B / C318884** に変更。JLCPCB の掲載上は Basic です。高さは基板から約 1.5 mm、実装面は Bottom。裏面側から押します。[部品情報](https://jlcpcb.com/partdetail/C318884) / [メーカー図面](https://www.helloxkb.com/uploads/qingchukaiguan/TS-1187A-X-X-X.pdf)
- SW1 は裏面の (47.6, 76.2) mm、90°に配置しています。メーカー図面の推奨ランドと A–B／C–D の接点構成に合わせています。ケースは既存版と共通です。底板を取り付けた状態での BOOTSEL の押下方法は組み立て時に確認してください。
- KiCad 10.0.5 のDRCは **エラー0、未接続0、回路図との不一致0、フットプリント差異0、警告25件**。残る警告はシルク関連で、ERCはエラー・警告とも0件です。プロジェクト設定で無効なチェックもあるため、これだけで機構干渉や実装品質を保証するものではありません。
- USB の R7/R8 は **22Ω・C25092** のままです。同じ Basic 部品を QSPI 側 R9–R13 と共通化し、部品種と PCBA の段取り費を抑える設計判断です。Raspberry Pi の[設計資料](https://datasheets.raspberrypi.com/rp2040/hardware-design-with-rp2040.pdf)で指定される 27Ω とは異なり、USB 波形の測定・シミュレーションは行っていません。

## データの再生成

KiCad 10 と Python 3 を用意し、KiCad 上の変更を保存したうえで、リポジトリ直下から実行します。

```powershell
python pcb/jlcpcb/export.py
```

`kicad-cli` が PATH にない場合、Windows の標準 KiCad 10 インストール先を探します。それ以外では `--kicad-cli` に実行ファイルのパスを渡します。

スクリプトは現在の回路図・基板から DRC / ERC、ガーバー、PTH・NPTH ドリル、BOM、実装座標を作成します。外周クリアランスが 0.2 mm 未満の場合、DRC エラー・未接続・回路図との不一致・ERC エラーがある場合、部品番号や実装座標が欠けている場合は停止します。作成時のソースと出力の SHA-256 は `assembly/manifest.json` に記録します。ガーバーZIP、BOM、実装座標、manifestはGitに保存し、基板編集後は再生成してください。その他の生成物は `.gitignore` の対象です。

次の表は現在の基板から生成した出力先です。

| JLCPCB に渡すもの | ファイル |
| :--- | :--- |
| ガーバーとドリル | `gerber/ts52k-gerbers.zip` |
| PCBA 部品表 | `assembly/ts52k-bom.csv` |
| PCBA 配置座標 | `assembly/ts52k-cpl.csv` |

正常終了したら `assembly/export-status.txt` が `EXPORT COMPLETED` になります。失敗時には以前の出力が残ることがあるため、利用しないでください。基板・回路図・設定を変更したら再生成します。

実装面は **Bottom のみ、96 点 / 部品番号16種、BOM 16行**です。C13は同じ標準フットプリントと部品番号を使うコンデンサと同じ行です。USB コネクタ J1 と BOOTSEL の SW1 は JLCPCB に実装してもらいます。キースイッチ 52 個とロータリーエンコーダ SW2 は手付け、Tag-Connect J2 は接点と穴だけで部品実装なしです。J1は固定脚にPTHがあるため、スクリプトはSMDのみに限定せず座標を出力し、J1を含むBOMと配置座標の参照番号を照合します。

## RP2040 のパッドと JLCPCB の製造実例

**結論：この基板の RP2040 のパッドと中央パッド内ビアは、JLCPCB の2層・1 ozで製造・実装できる設計と判断しています。パッド幅や中央パッド内ビアを理由にガーバー出力を止める必要はありません。**

この基板の U5（RP2040）は、端子パッドの幅が **0.20 mm** です。中央の GND パッドには、ペースト開口と重なる **穴径 0.30 mm の貫通ビアが4個**あります。

参考となる実例として、[RP2040 Advanced Breakout Board の発注手順](https://github.com/OpenStickCommunity/Hardware/blob/main/Boards/GP2040-CE%20Official%20Boards/RP2040%20Advanced%20Breakout%20Board/RP2040%20Advanced%20Breakout%20Board/README.md)では、JLCPCB に発注した基板について、2層・1.6 mm厚・1 oz・Tented ビアが指定されています。[公開 BOM・実装座標・ガーバー](https://github.com/OpenStickCommunity/Hardware/tree/main/Boards/GP2040-CE%20Official%20Boards/RP2040%20Advanced%20Breakout%20Board/RP2040%20Advanced%20Breakout%20Board/Hardware%20files/RP2040%20Advanced%20Breakout%20Board%20-%20USB-C)を確認すると、RP2040 は C2040、端子パッド幅は 0.20 mm、中央パッド内にはペースト開口と重なる穴径 0.305 mm のビアが9個あります。

この実例は、同様のパッド幅と中央パッド内ビアを持つ基板が JLCPCB に発注されている根拠です。中央パッド内ビアの実装については、[JLCPCB のビア・イン・パッド資料](https://jlcpcb.com/help/article/via-in-pad-pofv-guide)も参照できます。

## 発注画面で確認すること

1. 2 層、板厚 1.6 mm、銅厚 **1 oz** を選ぶ。基板外形は約 307.23 × 80.41 mm。最小配線幅 0.15 mm は JLCPCB の 2 層 1 oz の公表能力内ですが、2 oz の公表最小値 0.16 mm は満たしません。
2. BOM をアップロードし、各部品の実装在庫と見積額を確認する。
3. JLCPCB の配置プレビューで Bottom 側の J1・SW1、U3/U4/U5 の向き、D89/D90/D91を含むダイオードの極性を確認する。配置データの角度は KiCad の値であり、部品ライブラリごとの回転補正はプレビューで確認が必要です。
4. U5 のパッドとビアについては、上記の製造実例を参照する。
5. 実機では SW1 の押下方法と Tag-Connect の挿入性、全キー、同時押し、USB の両向き、繰り返し起動を確認する。Revision 0.2 の動作には RP2040 対応ファームウェアが必要です。
