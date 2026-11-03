# USB固定充電の先行事例

2026-11-03。初版で決定した固定充電構成について、nice!nano以外の公開設計を追加照合した記録。

## 結論と適用範囲

USB給電時の充電を抵抗設定に任せ、MCUから充電停止を指示する配線を持たない設計は、nice!nano以外にも存在する。したがってTS52Kの固定充電方針には複数の設計上の先例がある。ただし、全機種・全リビジョンが同じではない。GPIOによる充電停止や電流切替の有無と、USB列挙・サスペンドに自動連動するかは別の事項。

TS52Kは引き続きBQ24072のEN1/EN2/CEをGNDに固定する。[電源・USB入力の決定事項](wireless-power-input.md)を維持する。他機種の充電ICや電源経路をそのまま移植する意味ではない。

## nRFMicro

確認対象は[公開回路図](https://github.com/joric/nrfmicro/blob/5ac390d9d133e781a46a9c9fe43880f4826422e0/hardware/nrfmicro.kicad_sch)（commit `5ac390d9d133e781a46a9c9fe43880f4826422e0`）。KiCadからXMLネットリストを出力して接続を確認した。

- U3はTP4054。VDD（4番）はUSBのVBUSへ直結。
- PROG（5番）はR5を介してGNDへ接続。MCUへの接続はない。
- VBAT（3番）は電池側、STAT（1番）は表示回路へ接続。
- この回路図では、MCUから充電を停止する経路がない。USBサスペンド状態を充電ICに伝える配線もない。

**リビジョンを限定する必要がある。** 作者の[Pinout](https://github.com/joric/nrfmicro/wiki/Pinout)ではP0.05によるPROG制御は1.2–1.3だけで、1.4からP0.05は空き端子。[Batteries](https://github.com/joric/nrfmicro/wiki/Batteries)には1.3でPROG抵抗をGPIOへ接続し、充電停止・電流変更ができることが明記されている。

ローカルZMK mainの `app/module/boards/joric/nrfmicro/pinmux.c` でも、1.3向けには設定に応じてP0.05をLOW出力／入力へ設定する初期化がある。したがって「nRFMicroには充電制御がない」と全版へ一般化してはいけない。この初期化処理自体にはUSB状態による切替はない。

## MDBTMicro-50Q

確認対象は[公開回路図](https://github.com/siderakb/mdbt-micro/blob/7821d9046258f650ddf8d9424e21c6a3fc065c32/MDBTMicro_50Q/MDBTMicro_50Q.kicad_sch)（commit `7821d9046258f650ddf8d9424e21c6a3fc065c32`）。こちらもXMLネットリストで接続を確認した。

- U3はTP4057。VCC（4番）はUSB VBUSへ直結。
- PROG（6番）はR3を介してGNDへ接続。MCUへの接続はない。
- CHRG（1番）はLED、STDBY（5番）は未接続。STDBYは充電完了の状態出力であり、USBサスペンド制御入力として扱わない。
- MCUから充電を停止する経路がなく、USB状態を受けた充電停止を行う配線もない。

MDBT50Qを使う近い設計例ではあるが、[リリース記録](https://github.com/siderakb/mdbt-micro/releases)では1.4は未製造・未試験、1.3も製造・はんだ付け済みだが未試験とされる。動作実績の裏付けとしての重みはnice!nanoと同等に扱わない。また外部3.3 VレギュレータとTP4057を使うため、TS52KのREG0/BQ24072構成そのものの検証例でもない。

## Seeed XIAO nRF52840

[メーカー公式説明](https://wiki.seeedstudio.com/XIAO_BLE/#battery-charging-current)では、P0.13をプルなしの高インピーダンス入力にすると約50 mA、LOW出力にすると約100 mAへ設定できる。これはMCUによる電流選択を備える別方式の例。

この説明からUSB列挙・サスペンド連動まで実装されているとは判断できない。今回確認した根拠はメーカーの機能説明であり、回路図全体・全ファームウェアのUSB動作を検証したという意味ではない。本文と低電流側のコード例に設定方法の不一致もあるため、本文の記載を引用する範囲に留める。

## 読み取れること

固定充電は他の公開設計でも採られている。一方、充電制御用GPIOを持つ機種もあり、業界全体の一律の方式とは言わない。今回の照合は初版の方針を支える設計先例の確認であり、他機種やTS52KのUSB適合試験結果を証明するものではない。
