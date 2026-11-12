# TC52 部品選定

調査日：2026-11-12。対象要件は [design-spec.md](design-spec.md) §2.2。以下は**電気仕様と JLCPCB 区分を確認した暫定選定**である。指定された LCSC 詳細 API と EasyEDA API は、各候補への GET がともに HTTP 403 となり、API 間の照合は未完了。発注前に両 API を再確認する。JLCPCB API への POST は使用していない。

| 記号 | 暫定選定 LCSC | メーカー・型番 | パッケージ | JLCPCB 区分 | 要件との照合 |
|---|---|---|---|---|---|
| C2 | [C52152](https://jlcpcb.com/partdetail/C52152) | FH（Guangdong Fenghua）0603CG301J500NT | 0603 | Extended | 300 pF、C0G、50 V、±5%。[JLCPCB 仕様表](https://jlcpcb.com/partdetail/53166-0603CG301J500NT/C52152)に記載。設計仕様に C2 の許容差の指定はない。 |
| R2 | [C881384](https://jlcpcb.com/partdetail/C881384) | EVER OHMS CR0402F43K0Q10Z | 0402 | Extended | 43 kΩ、±1%、定格 63 mW・50 V。[LCSC 製品仕様](https://www.lcsc.com/de/product-detail/C881384.html)に記載。3.3 V が全抵抗にかかる保守的な場合でも約 0.253 mW で定格以下。 |
| U_AMP | [C41249](https://jlcpcb.com/partdetail/C41249) | Analog Devices AD8601ARTZ-REEL7 | SOT-23-5 | Extended | [LCSC 製品情報](https://www.lcsc.com/product-detail/C41249.html)と [ADI データシート](https://www.analog.com/media/en/technical-documentation/data-sheets/AD8601_8602_8604.pdf)で型番・5 ピンを確認。単電源 2.7〜5.5 V は +3V3A に適合し、入出力レール・ツー・レール、GBW 8.2 MHz、スルーレート 5.2 V/µs。 |

JLCPCB 部品ページを GET し、それぞれ対象型番と `componentLibraryType: expand` を確認した。区分は確認時点のもの。C2 と R2 は Extended のため、実装費と発注可能数を注文画面で確認する。

C2 の代替として仕様書が許容する [C1664](https://jlcpcb.com/partdetail/C1664)（Samsung CL10C331JB8NNNC、330 pF、C0G、50 V、0603）は JLCPCB GET で `base`（Basic）を確認した。300 pF からの変更は設計仕様の許容する代替であり、感度が約 6% 下がるという見積もりを伴う。実機で感度を確認する。

TC69 の BOM の C89851 は、JLCPCB の GET で onsemi NCS2003SN2T1G と確認できたため、AD8601 の品番として使用しない。

## 未完了の照合

- LCSC 詳細 API `https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=<C番号>` と EasyEDA API `https://easyeda.com/api/products/<C番号>/components` は C52152、C881384、C41249 について GET を試し、いずれも HTTP 403。API の仕様値・データシート URL・EasyEDA ランドとピン配置は今回確認できていない。特に U_AMP のフットプリントのピン番号と実装向きは、KiCad 採用時にデータシートおよび EasyEDA の実データで照合する。
- C2・R2 のメーカーの個別データシートを API 経由で照合できていない。C2 の [JLCPCB 記載データシート](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2304140030_FH--Guangdong-Fenghua-Advanced-Tech-0603CG301J500NT_C52152.pdf)、R2 の [JLCPCB 記載データシート](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2304140030_Ever-Ohms-Tech-CR0402F43K0Q10Z_C881384.pdf) を再確認する。
- 在庫・価格・実装可能数は変動する。JLCPCB の発注画面で再確認する。+3V3A の実電圧も電源公差と R_F の電圧降下を含め、AD8601 の最低電源電圧 2.7 V を満たすことを実機で確認する。
