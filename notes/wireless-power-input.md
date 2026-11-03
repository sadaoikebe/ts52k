# 初版の電源とUSB入力

2026-11-03更新。[現行決定事項](wireless-decisions.md)の電源部分を具体化したもの。部品選定は完了し、[仮BOM](wireless-bom-draft.csv)と[ライブラリ](../pcb/LIBRARIES.md)へ反映済み。回路図・PCBへの反映と実機評価はこれから。

## USB100固定充電で決定

初版はnice!nano型の固定充電構成。BQ24072のEN1・EN2・CE・TDをGNDへ固定する。**USBサスペンド連動の充電制御、追加GPIO、USB申告設定の変更は初版で実施しない。** 既知の電流管理上の制約を未決扱いし直したり、回路図着手の条件に戻したりしない。

ISETは8.2 kΩ / C25981、ILIMは1.5 kΩ / C22843、TSは10 kΩ / C25804。全てBasic。8.2 kΩによるISET単独設定は約108.5 mAだが、USB100の入力制限は90/95/100 mA（最小/典型/最大、TIの表の条件下）。実充電電流は入力制限から本体負荷を差し引いた電流にも制限され、109 mAへ増える変更ではない。50/100 mA切替はXIAOの別方式で、TS52Kには追加しない。

## 結線と採用容量

```text
USB VBUS ─┬─ BQ24072 IN ──内部パワーパス── OUT ── MDBT50Q VDDH(30)
          │   1 µF                       4.7 µF       10 µF
          └─ 2.2 Ω ── MDBT50Q VBUS(32)
                       4.7 µF

BQ24072 BAT ── 4.7 µF ── JST PH（1=BAT+、2=GND）
MDBT50Q DCCH(31) ── 10 µH ── VDD(28)
VDD(28) ── 4.7 µF＋1 µF＋100 nF×3（全てGNDへ）
```

| 接続先 | 容量・数量 | 配置 |
| --- | --- | --- |
| BQ IN | 1 µF×1 | 充電IC直近 |
| モジュールVBUS | 4.7 µF×1 | 2.2 Ωの後、モジュール直近 |
| BQ OUT | 4.7 µF×1 | 充電IC直近 |
| モジュールVDDH | 10 µF×1 | モジュール直近 |
| モジュールVDD | 4.7 µF×1＋1 µF×1＋100 nF×3 | モジュール直近、短い帰路 |
| BQ BAT | 4.7 µF×1 | 充電IC直近、セルを外しても基板上に残す |

型番は[容量選定表](capacitor-selection.md)。電源用10個＋LF負荷2個、全てBasic。電源用1 µF以上はX5R、100 nFはX7R、水晶用12 pFはC0G。X7R一律条件や旧候補型番は採用しない。OUTとVDDHは同じネットでも、それぞれICとモジュールへ寄せる2個のランドを用意する。

USBコネクタからつながる外付け容量は1＋4.7=**5.7 µF**、両方±10%の初期許容差上限は6.27 µF。OUT/VDDHの14.7 µFは充電ICの制御を介するため、この合計へ単純加算しない。この計算だけで突入電流の適合を実証したとは扱わない。

## VBUSの2.2 ΩとESD

**UNI-ROYAL 0603WAF220KT5E / C22939、2.2 Ω、±1%、0.1 W、0603、Basicを1個**採用する。[Nordic参考回路説明](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/ref_circuitry.html)の新設計への推奨と、[Raytac Version L](https://www.raytac.com/download/index.php?index_id=43) p42のR32=2.2 Ω（Optional）に基づく。[JLC登録](https://jlcpcb.com/partdetail/C22939)は2026-11-03確認済み。

抵抗を通すのはモジュールVBUS枝のみ。BQ INは抵抗の手前で分岐し、BQ OUT→VDDHは維持する。Raytac p42のUSB単独給電図のVBUS/VDDH一括給電はコピーしない。D+/D−の直列抵抗でもない。

H5VU10U / C22395519をD−、D+、コネクタ側VBUSに各1個、計3個継続。VBUSの保護素子は2.2 Ωの手前、4.7 µFは後。コネクタ付近に配置し、ESD電流のGND帰路とデータ線の枝線を短くする。

例えばVBUS枝10 mAなら抵抗の降下22 mV、損失0.22 mW。外付け4.7 µFとの時定数は約10 µsで、挿抜時の急峻な変化を緩和する。定常過電圧遮断の機能ではない。H5VU10Uの[メーカーRev.2.0](https://datasheet.lcsc.com/lcsc/2504101957_hongjiacheng-H5VU10U_C22395519.pdf)はVRWM=5 V、CJ最大0.8 pF、クランプ最大10 V（1 A、8/20 µs）／16 V（5 A）。部品耐量からTS52K全体のESD合格を保証せず、挿抜波形・ESD性能の実証は試作時に行う。

## USB電流申告の既知の制約

検証済みZMKの設定は`CONFIG_USB_SELF_POWERED=y`、`CONFIG_USB_MAX_POWER=50`。この版では2 mA単位なので申告は100 mA。Adafruit 0.11.0 nice_nanoブートローダも100 mAを申告する。ブートローダの属性はbus-poweredで、ZMKと同じではない。

同じZMKコミットのnice!nano/reviung41基準ビルドもSELF_POWERED=y、MAX_POWER=50。nice!nano公開回路にはMCUによるUSBサスペンド連動の充電停止配線がなく、P0.13 EXT_POWERは充電制御ではない。他の固定充電例とリビジョン差は[先行事例](charging-precedents.md)を参照。

| 状態 | 固定充電構成で残る制約 |
| --- | --- |
| 接続直後・列挙後 | BQ INの最大100 mAとは別にモジュールVBUS枝の消費がある。コネクタ全体の上限100 mAを保証した測定結果ではない |
| ホストのUSBサスペンド中、VBUSあり | 固定配線なのでサスペンドを理由として充電は停止しない |
| 電池なしでUSB給電 | ZMKの自己給電申告は実際の電源状態へ追従する構成ではない |

これらは記録済みの制約で、追加制御の作業候補ではない。初版は固定充電のまま実機評価へ進む。

## 根拠と試作時の確認

- [TI BQ2407x SLUS810N](https://www.ti.com/lit/ds/symlink/bq24072.pdf)：端子説明、USB100入力制限、ISETと入力制限の関係、入力容量と配置。
- [nice!nano v2公開回路](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/)：固定充電、デカップリング、USBの手本。
- [Adafruit USB記述子](https://github.com/adafruit/Adafruit_nRF52_Bootloader/blob/0.11.0/src/usb/usb_desc.c)、[固定TinyUSB版](https://github.com/hathach/tinyusb/blob/9775e76910d569ec73b8dd946f3fa5fe5414acdb/src/device/usbd.h)：100 mA申告。取得済みHEX中の記述子候補とも一致し、実機GET_DESCRIPTORは未確認。

試作時には電源立上り、USB挿抜、VDD/VDDH/VBUS、USB入力電流、USB/BLE動作を確認する。電池製品の選定とケース設計は今回行わない。USB100固定・TS固定抵抗・採用容量・2.2 Ω・既存ESDの決定は維持する。
