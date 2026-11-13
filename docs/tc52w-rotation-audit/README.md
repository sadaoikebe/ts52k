# TC52 wireless：CPL 回転の全数照合（2026-11-14）

対象：ブランチ `tc52-wireless`（監査開始 3fa54e7）の BOM 31 行・LCSC 31 種・CPL 67 点（全点 Bottom）。
基板・回路図は変更していない。変更は `pcb/jlcpcb/export.py` の `ROTATION_CORRECTIONS` と再生成した製造データだけ。

**ランドの出典：JLCEDA/EasyEDA Official Library（嘉立创EDA/EasyEDA官方库）** — [JLCEDA](https://lceda.cn/) / [EasyEDA](https://easyeda.com/)。

## 結論

| 区分 | LCSC 種類 | 実装点 |
| --- | ---: | ---: |
| 補正あり：C15127 AO3401A（Q1）+180°（既存、再確認） | 1 | 1 |
| **補正を追加：C41249 AD8601（U6）+180°** | 1 | 1 |
| **補正を追加：C21379 CD4051（U7, U8）+90°** | 1 | 2 |
| 補正不要（向きが意味を持ち、一致を確認） | 6 | 8 |
| 向き無関係（無極性 2 端子。0°/180° が等価、90° 違いはないことも確認） | 22 | 55 |
| 合計 | 31 | 67 |

変更前後（CPL の Rotation）：U6 −90 → 90、U7 0 → 90、U8 0 → 90。その他 64 点は変更なし。

## 方法

1. `extract_board.py`：pcbnew で基板の 67 点を読み、Bottom 反転と配置角をメモリ上で戻して表面 0° のパッド（番号・座標・寸法）を取り出す。
   使っているライブラリのフットプリントとも全パッドを比較（67 点すべて一致）。結果は `board-extract.json`。
2. `raw/<C>-components.json`：`GET https://easyeda.com/api/products/<C>/components`（31 種すべて HTTP 200。途中でレート制限の 403 が出たものは間隔を空けて再取得）。
   `raw/<C>-svgs.json`（JLCPCB の部品ページのビューアが使う `/svgs`）も全種取得し、両者のランド座標が 0.0012 mm 以内で一致することを確認。
   `raw/<C>-lcsc.json`：`GET https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=<C>`（型番・メーカー・パッケージ・データシート URL）。取得記録は `fetch-log.json`（URL・SHA-256）。
3. `audit.py`：番号付きランドを 0/90/180/270° と平行移動で最小二乗比較（`audit.json`, `audit-summary.txt`）。
   EasyEDA の回路記号のピン名と、基板のネット名（例：U6 の 2=GND, 5=+3V3A）を突き合わせ、番号の意味が同じことを確認。
   U6・U7/U8 はメーカー資料（ADI AD8601 図1 の 5 ピン SOT-23、TI SCHS047H の Pin Functions）でもピン配置を確認。
4. `required_angles.py`：CPL の 67 点それぞれについて、JLCPCB のランドが基板の銅に重なる CPL 角度を計算（`required-angles.json/.txt`）。補正を入れた後、モデル A では 67 点すべて一致。

## 未解決：JLCPCB が Bottom の角度をどう読むか（発注前に要確認）

JLCPCB の公開資料（[Pick & Place File](https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly)）は「正の値は反時計回り」としか書いておらず、**Bottom 面の角度の約束事は定義されていない**。EasyEDA のランドデータからも決められない。公開されている報告は次のとおりで、互いに食い違う。

| モデル | 式（KiCad 角 φ、補正 c） | 根拠 |
| --- | --- | --- |
| A | φ + c（KiCad の値そのまま。現在の export.py） | これを支持する公開報告は見つからなかった |
| B | 180 − φ + c | [kicad-jlcpcb-tools #159](https://github.com/Bouni/kicad-jlcpcb-tools/issues/159)（2022、JLCPCB 注文画面で 0°/180° の Bottom 部品が反転した実例、`f753e6e` で修正）、[KiBot の位置ファイル説明](https://kibot.readthedocs.io/en/latest/notes_position.html)（2023-11「KiCad は Bottom を鏡映するが JLCPCB はしない」）。2025 年の報告でもアップロード時のプレビューはこれで正しく見える |
| C | φ + 180 + c | [kicad-jlcpcb-tools #636](https://github.com/Bouni/kicad-jlcpcb-tools/issues/636)（2025-07/08、JLCPCB の技術者がこの値で機械を設定し、正しく実装されたという報告。プレビューの表示とは食い違った） |

さらに [KiBot #510](https://github.com/INTI-CMNB/KiBot/issues/510) では「JLCPCB は少なくとも 3 回 Bottom 角の扱いを変えた」と書かれている。この基板（2023 年の ATmega32U4 版）を最初に発注したときも kicad-jlcpcb-tools（`jlcpcb/project.db`、モデル B）を使っていた。

**向きが意味を持つ部品の要求 CPL 角（補正込み）**

| 部品 | KiCad φ | 現 CPL（A） | B | C |
| --- | ---: | ---: | ---: | ---: |
| D89 H5VU10U | 180 | 180 | 0 | 0 |
| D90, D91 H5VU10U | 0 | 0 | 180 | 180 |
| J1 USB-C | 0 | 0 | 180 | 180 |
| J3 JST PH | 180 | 180 | 0 | 0 |
| Q1 AO3401A | 0 | 180 | 0 | 0 |
| SW1（180° 等価） | 0 | 0 | 180 | 180 |
| U5 MDBT50Q | 270 | 270 | 270 | 90 |
| U6 AD8601 | 270 | 90 | 90 | 270 |
| U7, U8 CD4051 | 0 | 90 | 90 | 270 |
| U9 BQ24072 | 180 | 180 | 0 | 0 |

0°/180° に置いた部品は、B と C がそろって現 CPL と 180° 違う。±90° に置いた部品は B が現 CPL と一致し、C だけが 180° 違う。
推測で全体の約束事を書き換えることはしていない。発注画面のプレビューで上の表のどの列で正しく見えるかを確かめ、必要なら JLCPCB に Bottom の角度の解釈を問い合わせてから、`export.py` の Bottom の基本の式を決めること。

## 再実行

```sh
/usr/bin/python3 -I docs/tc52w-rotation-audit/extract_board.py ~/ts52k docs/tc52w-rotation-audit/board-extract.json
python3 -I docs/tc52w-rotation-audit/audit.py docs/tc52w-rotation-audit/board-extract.json
/usr/bin/python3 -I docs/tc52w-rotation-audit/required_angles.py
```
