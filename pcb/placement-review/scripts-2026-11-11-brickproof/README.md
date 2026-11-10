# 2026-11-11 文鎮化対策の作業スクリプト

- `move_j2_mark_j3.py <pcb>`：J2の移設・引き直しとJ3の極性シルク。`wireless` 43c3f08 の基板に対して1回だけ実行する前提（実行済み）。
- `hexinfo.py <hex>`：Intel HEXの領域とUICRの語を表示する。
- `disscan.py <hex> F4000 FBFC4`：ブートローダ領域を逆アセンブルし、UICR・POWER・NVMCレジスタへの読み書きを列挙する（capstoneが必要。定数の追跡は直線的なコードに限る簡易なもの）。
- `thumbdis.py <hex> <開始> <終了>`：指定範囲の逆アセンブル。

対象HEXは `nice_nano_bootloader-0.11.0_s140_6.1.1.hex`（SHA-256 `1b72d4cd…441f7e`）。HEX自体はリポジトリに入れていない。
検査結果は `../brickproof-2026-11-11/`（DRC・ERC）と `notes/zmk-hardware-bringup.md`。
