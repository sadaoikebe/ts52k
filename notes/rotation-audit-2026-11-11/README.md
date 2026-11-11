# CPL回転監査の根拠データ（2026-11-11）

全件の判定・最終検査は[監査報告書](report.md)、実装点ごとの角度は[全82点CSV](instance-audit.csv)を参照。

対象：wireless `6e3c3ec` のBOM 21行・20 LCSC種類・82実装点。基板・回路図は変更しない。

**ランド図の出典：JLCEDA/EasyEDA Official Library（嘉立创EDA/EasyEDA官方库）**。
[JLCEDA](https://lceda.cn/) / [EasyEDA](https://easyeda.com/)。SVG内の出典属性を保持している。

- `raw/C*-svgs.json`：JLCPCBの公開部品ページ内のフットプリントビューアが使うGET
  `https://easyeda.com/api/products/<C番号>/svgs` の実応答。全20種類、各1組の回路記号・番号付きランド。
- `jlc-metadata.json`：JLCPCB公開HTML埋め込みデータから取得したLCSC番号・MPN・メーカー・資料リンク。
- `fetch-*-log.json`、`fetch-log.json`：取得URL・HTTP結果・原文SHA-256。公開ページとSVGは全種類取得済み。
  LCSC詳細APIは403。EasyEDA `/components?version=6.4.19.6` はQ1単独取得に成功したが、全種類取得時の最初のC140288で403となり停止した。
  `/svgs` はJLCPCB公開ビューアのJavaScriptに記載された別のGETエンドポイントで、全件200。
  KiCad MCP `lcsc(resolve, C5118826)` は `lcsc_tos_acceptance_required`。同意操作・注文APIは使用していない。
- `geometry.json`：基板全実装点、KiCadライブラリ、EasyEDAランドの番号・座標・寸法・角度・形状。
  座標はmm、右が+x・下が+y。比較のためKiCadのBottom反転と配置回転をメモリ内で戻す。基板は保存しない。
- `comparison.json`：番号対応を固定し、0/90/180/270°と平行移動の最小二乗を比較。
  J1の重複パッド・シールド、J3の固定金具、SW1の同一接点にはコードに明示した対応を使う。
  ランド長の違いがあるため残差ゼロは要求しない。形状・長軸とメーカー図も併せて人が判定する。
  **最小二乗の平行移動はCPL座標補正ではない**。とくにQ1の非対称なパッド分布による0.071 mmの値を原点差と解釈しない。
- `board-library-check.json`：82点全てBottom。基板とライブラリの番号・形状・サイズ・角度は一致。
  D91の45°配置に伴う座標丸めの差のみ最大0.000001 mm。

`raw/` のHTML・PDF・PDF抽出テキストはこのワークツリー内に保持するが、Gitには大容量の資料本文や期限付きURLを含むHTMLを追加しない。
PDF取得はLCSCのHTML資料ページを経由し、ページ内の実PDFリンクを追跡。`fetch-datasheet-log.json`の `pdf: false` はこのHTMLラッパーを指し、`fetch-pdf-log.json`の全8件は `pdf: true`。

ローカルで再抽出・再照合する場合：

```sh
bash ~/workspace/ensure-kicad.sh
/usr/bin/python3 notes/rotation-audit-2026-11-11/extract.py
/usr/bin/python3 notes/rotation-audit-2026-11-11/compare.py
```

取得スクリプトは経路の記録用。403だった経路をむやみに再実行しない。
