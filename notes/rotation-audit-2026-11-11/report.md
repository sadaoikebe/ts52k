# TS52K 無線版：全実装部品のCPL回転監査（2026-11-11）

BOM **21行・LCSC 20種類・82実装点を全件照合**した。追加の回転補正は不要。`C15127: +180°` の既存補正を実データで再確認し、そのまま維持した。

| 判定 | LCSC種類 | BOM行 | 実装点 |
| --- | ---: | ---: | ---: |
| 補正あり（既存Q1の+180°） | 1 | 1 | 1 |
| 補正不要（確認済み） | 7 | 7 | 61 |
| 回転無意味（無極性2端子の180°反転） | 12 | 13 | 20 |
| 未確認（公開ライブラリの回転定義） | 0 | 0 | 0 |
| 合計 | 20 | 21 | 82 |

無極性の「回転無意味」は0°と180°が電気的に等価という意味。90°はランドに合わないため許容しない。SW1も180°は等価だが、4端子の接点対応を確認して「補正不要」に分類した。

## 作業範囲と根拠

- 元：`~/workspace/ts52k`、`wireless` の `6e3c3ec`。
- 作業先：`~/workspace/ts52k-rotation-audit`、`codex-rotation-audit-2026-11-11`。
- 基板・回路図は編集・保存していない。マージ・pushなし。
- `ensure-kicad.sh` 実行後、KiCad **10.0.8**で基板の全82実装点を読み取った。Bottom反転と配置回転をメモリ内で戻し、使用ライブラリと番号・形状・寸法・角度を全パッドで比較。最大差はD91の45°配置に伴う0.000001 mmの丸めだけ。
- JLCPCB公開部品ページを20種類すべてGETし、埋め込みデータのLCSC番号・メーカー・MPNを確認。ページ内iframe→公開JavaScriptが指定する `https://easyeda.com/api/products/<C番号>/svgs` を取得し、各LCSCにつながる回路記号とPCBランドの双方を解析した。
- **出典：JLCEDA/EasyEDA Official Library（嘉立创EDA/EasyEDA官方库）**。[JLCEDA](https://lceda.cn/) / [EasyEDA](https://easyeda.com/)。原文SVGの出典属性を保持した。
- 取得ログ、SHA-256、番号付きSVG、抽出データ、比較コードは[根拠データ](README.md)に保存。HTML/PDF原文も同じワークツリーの`raw/`にローカル保持するがGitには含めない。

表の座標は**各フットプリントを表面・0°に正規化した座標、mm、右が+x・下が+y**。基板Bottomの実配置とは区別する。EasyEDAの内部座標は1単位=0.254 mmとして換算した。パッド番号だけでなく、端子の辺・長軸・ランド寸法・固定金具・EPも確認した。角丸/矩形や推奨ランド長の差は回転差とは扱わない。

## 全BOM行の棚卸し

Kのリンクは使用KiCadフットプリント、EのリンクはLCSC番号に対応する取得元SVG API。原文は`raw/<LCSC>-svgs.json`にも保存。JはJLCPCB部品ページ。

| 部品名・全実装点 | LCSC | KiCad側の向きの事実 | JLCPCB公開ライブラリ側の向きの事実 | 判定 | 根拠の出典 |
| --- | --- | --- | --- | --- | --- |
| 1uF：C22,C28 | C15849 | 1=(-0.775,0)、2=(+0.775,0)。各0.90×0.95角丸矩形。 | 1=(-0.701,0)、2=(+0.701,0)。各0.80×0.90矩形。長軸・番号の並びは一致。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/C_0603_1608Metric.kicad_mod) / [E](https://easyeda.com/api/products/C15849/svgs) / [J](https://jlcpcb.com/partdetail/C15849) |
| 4.7uF：C23,C26,C27 | C19666 | 1=(-0.775,0)、2=(+0.775,0)。各0.90×0.95角丸矩形。 | 1=(-0.701,0)、2=(+0.701,0)。各0.80×0.90矩形。同方向。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/C_0603_1608Metric.kicad_mod) / [E](https://easyeda.com/api/products/C19666/svgs) / [J](https://jlcpcb.com/partdetail/C19666) |
| 4.7u：C24 | C19666 | 1=(-0.775,0)、2=(+0.775,0)。各0.90×0.95角丸矩形。 | 1=(-0.701,0)、2=(+0.701,0)。各0.80×0.90矩形。同方向。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/C_0603_1608Metric.kicad_mod) / [E](https://easyeda.com/api/products/C19666/svgs) / [J](https://jlcpcb.com/partdetail/C19666) |
| 10uF：C25 | C15850 | 1=(-0.950,0)、2=(+0.950,0)。各1.00×1.45角丸矩形。 | 1=(-1.001,0)、2=(+1.001,0)。各1.41×1.35矩形。同方向。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/C_0805_2012Metric.kicad_mod) / [E](https://easyeda.com/api/products/C15850/svgs) / [J](https://jlcpcb.com/partdetail/C15850) |
| 100nF：C29,C30,C31 | C14663 | 1=(-0.775,0)、2=(+0.775,0)。各0.90×0.95角丸矩形。 | 1=(-0.701,0)、2=(+0.701,0)。各0.80×0.90矩形。同方向。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/C_0603_1608Metric.kicad_mod) / [E](https://easyeda.com/api/products/C14663/svgs) / [J](https://jlcpcb.com/partdetail/C14663) |
| 12pF：C32,C33 | C1547 | 1=(-0.480,0)、2=(+0.480,0)。各0.56×0.62角丸矩形。 | 1=(-0.419,0)、2=(+0.419,0)。各0.50×0.54矩形。同方向。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/C_0402_1005Metric.kicad_mod) / [E](https://easyeda.com/api/products/C1547/svgs) / [J](https://jlcpcb.com/partdetail/C1547) |
| 1N4148W：D2,D3,D4,D5,D7,D8,D9,D11,D12,D13,D14,D16,D17,D18,D20,D21,D22,D23,D25,D26,D27,D29,D30,D31,D33,D34,D35,D37,D38,D39,D40,D42,D43,D44,D46,D47,D48,D49,D51,D52,D53,D55,D56,D58,D61,D63,D64,D65,D66,D68,D70,D87,D88 | C81598 | 1=Kが左(-1.650,0)、2=Aが右(+1.650,0)。各0.90×1.20角丸矩形。 | 1=Kが左(-1.735,0)、2=Aが右(+1.735,0)。各1.10×1.00矩形。帯側と番号が一致。メーカーも1=K、2=A。 | 補正不要（確認済み） | [K](../../pcb/ts52k.pretty/D_SOD-123.kicad_mod) / [E](https://easyeda.com/api/products/C81598/svgs) / [J](https://jlcpcb.com/partdetail/C81598) |
| H5VU10U：D89,D90,D91 | C22395519 | 1=Kが左(-0.425,0)、2=Aが右(+0.425,0)。各0.55×0.60矩形。 | 1=Kが左(-0.399,0)、2=Aが右(+0.399,0)。各0.50×0.60矩形。メーカーRev.2.0の極性とも一致。 | 補正不要（確認済み） | [K](../../pcb/ts52k.pretty/H5VU10U_DFN1006-2L.kicad_mod) / [E](https://easyeda.com/api/products/C22395519/svgs) / [J](https://jlcpcb.com/partdetail/C22395519) |
| TYPE-C-31-M-12：J1 | C165948 | 信号列y=-4.045、左端A1/B12、右端A12/B1。内側8端子は0.50ピッチ、0.30×1.45。外側電源/GNDは0.60×1.45。SH固定脚4本、穴2個。 | 信号列y=-2.473、左端A1B12、右端B1A12。8端子の番号列一致、0.50ピッチ、0.30×1.30。外側は0.60×1.30。SH相当=1〜4は四隅。開口方向一致。原点・ランド長の差は別記。 | 補正不要（確認済み） | [K](../../pcb/ts52k.pretty/USB_C_Receptacle_HRO_TYPE-C-31-M-12.kicad_mod) / [E](https://easyeda.com/api/products/C165948/svgs) / [J](https://jlcpcb.com/partdetail/C165948) |
| JST PH 2-pin：J3 | C295747 | 1=(-1,-2.85)、2=(+1,-2.85)、1.0×3.5角丸矩形。MPは(±3.35,+2.90)、1.5×3.4。 | 1=(-1.001,-2.924)、2=(+1.001,-2.924)、1.0×3.8矩形。固定金具3/4=(±3.350,+2.926)、1.5×3.4。端子側・開口側・番号一致。 | 補正不要（確認済み） | [K](../../pcb/ts52k.pretty/JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal.kicad_mod) / [E](https://easyeda.com/api/products/C295747/svgs) / [J](https://jlcpcb.com/partdetail/C295747) |
| 10uH：L1 | C713281 | 1=(-0.7875,0)、2=(+0.7875,0)。各0.875×0.95角丸矩形。 | 1=(-0.699,0)、2=(+0.700,0)。各0.80×0.864矩形。同方向（パッド自体の180°は同じ矩形）。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/L_0603_1608Metric.kicad_mod) / [E](https://easyeda.com/api/products/C713281/svgs) / [J](https://jlcpcb.com/partdetail/C713281) |
| AO3401A：Q1 | C15127 | 1=G=(-0.9375,-0.950)、2=S=(-0.9375,+0.950)、3=D=(+0.9375,0)。各1.475×0.600角丸矩形。 | 1=G=(+1.149,+0.950)、2=S=(+1.149,-0.950)、3=D=(-1.149,0)。各1.000×0.600矩形。2本辺/1本辺と1・2の上下がともに180°逆。 | 補正あり（既存+180°維持） | [K](../../pcb/ts52k.pretty/SOT-23.kicad_mod) / [E](https://easyeda.com/api/products/C15127/svgs) / [J](https://jlcpcb.com/partdetail/C15127) |
| 5.1k：R5,R6 | C23186 | 1=(-0.825,0)、2=(+0.825,0)。各0.80×0.95角丸矩形。 | 1=(-0.754,0)、2=(+0.754,0)。各0.806×0.864矩形。同方向、無極性抵抗。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/R_0603_1608Metric.kicad_mod) / [E](https://easyeda.com/api/products/C23186/svgs) / [J](https://jlcpcb.com/partdetail/C23186) |
| 8.2k：R17 | C25981 | 1=(-0.825,0)、2=(+0.825,0)。各0.80×0.95角丸矩形。 | 1=(-0.754,0)、2=(+0.754,0)。各0.806×0.864矩形。同方向、無極性抵抗。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/R_0603_1608Metric.kicad_mod) / [E](https://easyeda.com/api/products/C25981/svgs) / [J](https://jlcpcb.com/partdetail/C25981) |
| 1.5k：R18 | C22843 | 1=(-0.825,0)、2=(+0.825,0)。各0.80×0.95角丸矩形。 | 1=(-0.754,0)、2=(+0.754,0)。各0.806×0.864矩形。同方向、無極性抵抗。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/R_0603_1608Metric.kicad_mod) / [E](https://easyeda.com/api/products/C22843/svgs) / [J](https://jlcpcb.com/partdetail/C22843) |
| 10k：R19 | C25804 | 1=(-0.825,0)、2=(+0.825,0)。各0.80×0.95角丸矩形。 | 1=(-0.754,0)、2=(+0.754,0)。各0.806×0.864矩形。同方向、無極性抵抗。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/R_0603_1608Metric.kicad_mod) / [E](https://easyeda.com/api/products/C25804/svgs) / [J](https://jlcpcb.com/partdetail/C25804) |
| 2.2：R20 | C22939 | 1=(-0.825,0)、2=(+0.825,0)。各0.80×0.95角丸矩形。 | 1=(-0.754,0)、2=(+0.754,0)。各0.806×0.864矩形。同方向、無極性抵抗。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/R_0603_1608Metric.kicad_mod) / [E](https://easyeda.com/api/products/C22939/svgs) / [J](https://jlcpcb.com/partdetail/C22939) |
| RESET：SW1 | C318884 | 上行y=-1.875に番号1が2個、下行y=+1.875に番号2が2個。x=±3.0、各1.0×0.75矩形。 | 上行y=-1.849は1=A・2=B、下行y=+1.849は3=C・4=D。x=±3.0、各1.0×0.75矩形。メーカーA–B/C–D導通でKiCadの同番対と一致。 | 補正不要（確認済み） | [K](../../pcb/ts52k.pretty/SW_Tactile_XKB_TS-1187A_5.1x5.1mm.kicad_mod) / [E](https://easyeda.com/api/products/C318884/svgs) / [J](https://jlcpcb.com/partdetail/C318884) |
| MDBT50Q-1MV2：U5 | C5118826 | 61端子。1=(-4.65,-3.75)、55=(+4.65,-3.75)、15〜33は下辺、56〜61は内部列。側辺0.6×0.4・下辺/内部0.4×0.6矩形。アンテナは上。 | 同番号61端子の全配列と長軸が一致。1=(-4.650,-5.450)、55=(+4.649,-5.450)。yに+1.700移動すると全端子中心の最大差0.0017。アンテナは上。 | 補正不要（確認済み） | [K](../../pcb/ts52k.pretty/Raytac_MDBT50Q.kicad_mod) / [E](https://easyeda.com/api/products/C5118826/svgs) / [J](https://jlcpcb.com/partdetail/C5118826) |
| BQ24072RGTR：U6 | C140288 | 1=(-1.4625,-0.750)、1〜4左・5〜8下・9〜12右・13〜16上、17中央。端子0.825×0.250（辺に合わせ回転）、EP 1.68角。 | 1≈(-1.499,-0.749)、全16端子の番号順一致。端子0.800×0.280の長円（辺に合わせ回転）、17は1.60角。長軸・EP・番号一致。 | 補正不要（確認済み） | [K](../../pcb/ts52k.pretty/VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm.kicad_mod) / [E](https://easyeda.com/api/products/C140288/svgs) / [J](https://jlcpcb.com/partdetail/C140288) |
| 32.768kHz：X3 | C96341 | 1=(-0.750,0)、2=(+0.750,0)。各0.70×1.40矩形。 | 1=(-0.749,0)、2=(+0.749,0)。各0.70×1.30矩形。同じ2端子配置。無極性水晶。 | 回転無意味（180°） | [K](../../pcb/ts52k.pretty/Crystal_Epson_FC-12M_2.05x1.2mm.kicad_mod) / [E](https://easyeda.com/api/products/C96341/svgs) / [J](https://jlcpcb.com/partdetail/C96341) |

## 補正値とCPLの変更前後

| 対象 | KiCad生角度 | 監査開始時（6e3c3ec） | 監査後CPL | export.pyの補正 |
| --- | ---: | ---: | ---: | ---: |
| Q1 / C15127 | 0° | 180° | 180° | +180°を維持 |
| その他81点 | 各配置の生角度 | 生角度 | 同じ生角度 | なし |

Q1の「補正前→補正後」は0°→180°。ただしこれは既存コミット6e3c3ecで適用済みなので、**今回の監査前後は180°→180°、CPLの差分は0件**。角度を変える新たな証拠はなく、表の追加や推測補正は行っていない。180°はBottom反転で補正符号の曖昧さが生じない。

[全82実装点の角度一覧](instance-audit.csv)に、参照番号・LCSC・生角度・開始時CPL・最終CPL・判定を記録した。C24は4.7u表記のため同じC19666でもBOM別行になっており、棚卸しに含めている。53個のC81598も全参照番号を照合した。

## 番号の異なる表現とメーカーによる裏付け

- **Q1**：AO3401A資料p1のTop/Bottom Viewに示されたG/S/Dの位置を、EasyEDA回路記号・KiCadシンボルの1=G・2=S・3=Dという番号対応と合わせて確認。ランドの2本辺/1本辺と1・2の上下が両方180°逆なので補正が必要。
- **D2〜D88**：C81598のSemtech資料p1に1=カソード、2=アノード。EasyEDAのパッケージ名にSOD-123Fが含まれるが、メーカー資料の呼称はSOD-123。名前だけで不適合とは判断せず、端子間隔・ランド形状・帯側を確認した。
- **D89〜D91**：H5VU10U Rev.2.0 p1のFunction Diagramでも1=K、2=A。KiCadはメーカー推奨0.55×0.60 mmを採用しており、EasyEDAの0.50×0.60 mmとの差は回転ではない。
- **J1**：EasyEDAの`A1B12`等はKiCadの同位置の`A1`と`B12`に対応。シールド1〜4はKiCadの`SH`に対応。HRO資料p1の12ランドの端子順・CC/D+/D−と四隅の固定脚を確認した。
- **J3**：EasyEDAの3/4は信号端子ではなく固定金具で、KiCadの`MP`に対応。メーカーPH Connector資料p3のSMT side entryと照合。1/2の番号、2 mmピッチ、固定金具側が一致。
- **SW1**：メーカー図p1のA–BとC–Dは常時導通。EasyEDAの1=A・2=Bと3=C・4=Dを、KiCadは各行を同番1/同番2で表す。上行と下行の相対位置・ランド長軸が一致する。単純な1↔1、2↔2だけで比較しない。
- **U5**：Raytac資料p7のTop Viewにある全61端子の配列と、p9の推奨ランド方向に整合。1・55がアンテナ寄り、15〜33が反対側、56〜61が内部列。平行移動後に番号付き全61パッドが最大0.0017 mmで一致。
- **U6**：TI資料のPin Configuration/Terminal Functionsに整合。1〜16の辺と順序、17=GNDのEPを確認した。EP 1.68 mmと1.60 mm、外周ランドの角丸矩形と長円という設計差はあるが、回転は一致する。

メーカーPDFの取得URLとSHA-256は[PDF取得記録](fetch-pdf-log.json)にある。主要な資料リンク：

- [C140288 メーカー資料](https://datasheet.lcsc.com/datasheet/pdf/aa9babe75c8236efb01497d1ee9a88a2.pdf?productCode=C140288)
- [C15127 メーカー資料](https://datasheet.lcsc.com/datasheet/pdf/fee353dd1e9e0bc90b295f14f381aa4c.pdf?productCode=C15127)
- [C165948 メーカー資料](https://datasheet.lcsc.com/datasheet/pdf/9e56b777c022540fcce7c7f67825f55e.pdf?productCode=C165948)
- [C22395519 メーカー資料](https://datasheet.lcsc.com/datasheet/pdf/c39c364bc61f363e0e429e5dec391fd3.pdf?productCode=C22395519)
- [C295747 メーカー資料](https://datasheet.lcsc.com/datasheet/pdf/2474e9261ed7c5f86b55d373e724589d.pdf?productCode=C295747)
- [C318884 メーカー資料](https://datasheet.lcsc.com/datasheet/pdf/56c8799ae5193945a16a1ffbe378246a.pdf?productCode=C318884)
- [C5118826 メーカー資料](https://datasheet.lcsc.com/datasheet/pdf/cf7f2e1118bb72c312aab99b9b39e26c.pdf?productCode=C5118826)
- [C81598 メーカー資料](https://datasheet.lcsc.com/datasheet/pdf/8abd7fc00ebe41ffb03ad1383c10753b.pdf?productCode=C81598)

## 回転以外の所見（未修正）

**今回、部品と合わないフットプリントだと確定したものはない。** ただし原点の違いを2件記録する。公開SVGと実際の注文システムの中心座標の扱いは同じとは限らず、回転監査からXY補正を導いてはいない。

| 対象 | データで確認したこと | 扱い |
| --- | --- | --- |
| U5 | EasyEDAの全パッド座標に(約0,+1.700) mmを加えるとKiCadと一致する。KiCad原点は15.5 mm長のモジュール本体中心、EasyEDA原点はランド群の上下範囲の中心に近い。61端子の相対位置・長軸は一致。 | CPLのXYは変更しない。プレビューでアンテナ方向だけでなく61端子全体の重なりを確認。仮に公開SVG原点をそのまま使用する実装なら、現在の配置では約1.7 mmの左右ずれが生じうる。 |
| J1 | EasyEDAとKiCadで信号列のyが約1.572 mm、固定脚のyが約1.424 mm違う。ランド長が異なるため全体を単一の平行移動だけで完全一致させる比較にはならない。信号ピッチ・番号列・四隅の脚・開口方向は一致。 | CPLのXYは変更しない。12信号ランド・4脚・開口位置をプレビューで確認。原点差を角度補正で解消しない。 |

これらは、回転の未確認部品やフットプリント不適合の確定例とは区別する。メーカー推奨ランドとの差のDFM・はんだ品質の全面評価は本監査の対象外。

## 最終目視で残ること

公開ライブラリ同士の比較は全件完了したが、発注画面は操作していない。発注時はREADMEの表に従い、Bottomの反転表示に注意して、Q1の3=DがJ3側、全ダイオードのK/A、U5のアンテナ、U6の1番、コネクタの開口、SW1の接点行と全ランドの重なりを確認する。JLCPCB側の自動補正や原点処理による二重補正・平行ずれの最終目視を残す。

## 製造データと検査

`python3 pcb/jlcpcb/export.py` を実行し、DRC/ERCゲートを通過してBOM・CPL・ガーバー/ドリル・manifestを再生成した。

| 検査 | 最終結果 |
| --- | --- |
| DRC error | 0 |
| 未接続 | 0 |
| 回路図とのパリティ不一致 | 0 |
| DRC warning | 9（silk_overlap 7、silk_edge_clearance 2） |
| ERC error / warning | 0 / 0 |
| 製造BOM / CPL | 21行 / 82点、開始時のファイルとバイト単位で同一 |
| CPL角度・XY・面 | 全82点で基板座標と補正式に一致 |
| 基板・回路図などmanifestの全ソース | 6e3c3ecとバイト単位で同一 |
| ガーバーZIP内12ファイル | 生成日時を除き開始時と同一 |
| 最終manifestのsource/output SHA-256 | 全件実ファイルと一致 |

**別途見つけて修正した不整合：** 開始時のmanifestはCPLハッシュに `8d42bada…` を記録していたが、6e3c3ecの実CPLは `aed416db…` だった。今回の再生成で実CPLのSHA-256に更新した。CPL自体の回転値を変更したものではない。

検査原文：[DRC](drc.json)、[ERC](erc.json)。検証サマリー：[validation.json](validation.json)。[検証コード](verify-export.py)では、82点の角度、BOM/CPL不変、ソース不変、ガーバーの日時以外不変、manifest全ハッシュまで確認している。

`export.py`の補正表はC15127だけのまま、全件監査の結果と根拠への参照をコメントに反映した。`pcb/jlcpcb/README.md`の確認表には全対象を追加し、確認済み・既存補正・無極性を区別し、U5/J1の位置の最終目視も明記した。

## 未確認として残った部品と理由

**公開JLCPCB/EasyEDAライブラリとKiCadの回転定義について未確認の部品は0種類・0点。** 403だった経路の部品も、JLCPCB公開ビューアのSVG経路で全20種類の番号付きランドを取得できたため、未確認扱いにはしていない。

未実施なのは実際の注文画面での最終プレビューと実装後の実機確認。U5・J1の原点差が注文システムでどう処理されるかは公開データだけでは確定できず、上記の回転以外の所見として残す。
