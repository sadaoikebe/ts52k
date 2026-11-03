# 電源コンデンサの採用部品

2026-11-03更新。[現行決定事項](wireless-decisions.md)に対応する初版構成。選定した12個を無線版回路図へ反映し、[BOMと電源ネットを照合済み](../pcb/schematic-review/validation.json)。試作確認を理由に選定停止へ戻さない。

## 採用構成

**VDD外付けは4.7 µF＋1 µF＋100 nF×3を全て実装する。** [nice!nano v2公開回路](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/)のVDD_NRFと[NordicのVDDデカップリング例](https://docs.nordicsemi.com/r/bundle/nwp_030/page/wp/nwp_030/nrf52840_vdd.html)を基準にした初版の判断。裸のnRF52840とMDBT50Qの差を理由に、根拠なく4.7 µF単体へ簡略化しない。

| 用途 | 型番 / JLC番号 | 仕様 | 数量 |
| --- | --- | --- | ---: |
| BQ24072 IN、VDD | CL10A105KB8NNNC / C15849 | 1 µF、50 V、X5R、±10%、0603 | 各1、計2 |
| VDD、VBUS、BQ OUT、BAT | CL10A475KO8NNNC / C19666 | 4.7 µF、16 V、X5R、±10%、0603 | 各1、計4 |
| VDD | CC0603KRX7R9BB104 / C14663 | 100 nF、50 V、X7R、±10%、0603 | 3 |
| VDDH | CL21A106KAYNNNE / C15850 | 10 µF、25 V、X5R、±10%、0805 | 1 |
| LF水晶負荷 | 0402CG120J500NT / C1547 | 12 pF、50 V、C0G、±5%、0402 | 2 |

**計12個、全てBasic。** 型番・数量・サイズは[仮BOM](wireless-bom-draft.csv)と[ライブラリ登録表](../pcb/wireless-library.csv)に反映済み。電源用へX7Rを一律に要求しない。耐圧50 V/25 Vは安いBasic品にある仕様を選んだ結果で、追加の高耐圧要件ではない。

分類は2026-11-03のJLC個別ページで確認した記録。[C15849](https://jlcpcb.com/partdetail/C15849)、[C19666](https://jlcpcb.com/partdetail/C19666)、[C14663](https://jlcpcb.com/partdetail/C14663)、[C15850](https://jlcpcb.com/partdetail/C15850)、[C1547](https://jlcpcb.com/partdetail/C1547)。発注時の見積確認とは区別する。

## 先行回路との対応

- nice!nanoのC11=4.7 µF、C14=1 µF、C6/C12/C13=100 nFが今回のVDD構成の根拠。C15=4.7 µFはDEC4用なので、この5個へ含めない。
- Raytac [Version K p38](https://cdn.sparkfun.com/assets/4/7/4/3/8/_nRF52840__MDBT50Q-1MV2___MDBT50Q-P1MV2_Ver.K_spec.pdf)、[Version L](https://www.raytac.com/download/index.php?index_id=43) p36のVDD参考値は10 µF。今回はnice!nano/Nordicの5個構成を採用した差分として記録する。
- 上表の完全型番は安いBasic品から選んだもので、先行基板の非公開BOMと同一だとは説明しない。

## 回路図に反映した条件とPCBへの引継ぎ

VDDの5個はモジュール28番とGNDの間に実装し、短い配線と帰路を確保する。OUTとVDDHは同じネットだが、IC直近・モジュール直近へそれぞれ容量を設ける。モジュールVBUSの4.7 µFは2.2 Ωの後に置く。USBへつながる外付け容量は1＋4.7=5.7 µF。[電源の結線](wireless-power-input.md)を参照。

Nordicの[REG0出力の実効容量条件](https://docs.nordicsemi.com/r/bundle/nwp_030/page/wp/nwp_030/nrf52840_effective_capa.html)は2.7〜5.5 µF。公称値の和や単体部品の代表グラフだけで、モジュール内部込みの適合を実証したとは扱わない。電源立上りと動作は試作時に確認する。この未実証を、採用部品の保留や内部容量調査の反復へ戻す理由にはしない。

以前の4.7 µF単体案、不要なX7R一律条件、旧型番候補、選定停止の記述は撤回した。旧単体案の容量推算を現行5個構成の検証結果として使わない。
