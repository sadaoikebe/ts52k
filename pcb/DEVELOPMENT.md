# KiCad開発環境の記録

2026-11-09に、この作業環境の設定とローカルファイルを確認した記録。設計の決定事項は[無線版の決定事項](../notes/wireless-decisions.md)、現在の配置・配線と検査結果は[配置・配線記録](placement-review/README.md)を参照する。

## KiCad MCP

- MCPサーバーは Brian Wong 氏の [blwfish/kicad-mcp](https://github.com/blwfish/kicad-mcp)（MITライセンス）。Codex上の接続名は `kicad`。
- 確認時のローカルコピーは `C:\Users\marur\kicad-mcp`、`main` のコミット [`fc143f9fe6b16ae64f1dbc0a6ef3df233db96634`](https://github.com/blwfish/kicad-mcp/commit/fc143f9fe6b16ae64f1dbc0a6ef3df233db96634)。パッケージのバージョンは `0.18.1`。
- このコピーは仮想環境にeditableインストールされており、`C:\Users\marur\kicad-mcp\.venv\Scripts\python.exe -m kicad_mcp.server` で起動する設定。KiCadは10.0.5、`KICAD_CLI_PATH` は `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`。`PYTHONUTF8=1` と、同じKiCadインストール内のシンボル・フットプリントディレクトリも設定されている。
- 上記コミットからの**ローカル未コミット変更**が `src/kicad_mcp/utils/pcbnew_bridge.py` と `tests/test_pcbnew_bridge.py` にある。前者は、Windowsで `KICAD_CLI_PATH` と同じディレクトリのKiCad付属Pythonを探す変更と、一時PythonスクリプトをUTF-8で書く変更。後者はそのテストを追加している。これらの差分はTS52Kリポジトリに含まれないため、上記コミットだけでは確認時の環境を完全には再現できない。

導入方法や操作の詳細は、MCP本体の [README](https://github.com/blwfish/kicad-mcp/blob/fc143f9fe6b16ae64f1dbc0a6ef3df233db96634/README.md) と [AGENT-INSTALL.md](https://github.com/blwfish/kicad-mcp/blob/fc143f9fe6b16ae64f1dbc0a6ef3df233db96634/AGENT-INSTALL.md) を参照する。上記のパスはこのPCの実例であり、他の環境では異なる。

## このリポジトリでの作業

KiCad MCPは回路図・PCBの調査や操作に利用できる。直近のマトリクス配線作業では、KiCad付属の `pcbnew` Pythonと `kicad-cli` も直接使い、配線・ベタ再充填・DRC・画像出力を行った。MCPがすべての変更を行ったという意味ではない。作業ごとの具体的な内容と検査結果は[配置・配線記録](placement-review/README.md)に記載する。

複数のMCPサーバープロセスやKiCad GUIから同じPCBを同時編集しない。編集前に現状を確認し、編集後は回路図との整合、DRC、必要な画像とGNDなどを確認する。MCPやDRCの成功だけで、実機の動作や信号品質が確認できたことにはならない。
