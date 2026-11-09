# CHMAYCO RK3588 Livestream Box Device Trees

[中文版](README.md)

This repository documents the reverse-engineered device tree for the CHMAYCO RK3588 livestream box and maintains separate Android, vendor Linux and mainline Linux board descriptions. The hardware facts are taken from the factory DTB extracted from Android 5.10.110.

## Tree layout

| Directory | Target | Boot convention |
| --- | --- | --- |
| `dts-5.10-android` | Android 12 / vendor 5.10 | FIQ debugger, `ttyFIQ0`, Android init and A/B parameters |
| `dts-6.1-linux` | Armbian / vendor 6.1 | UART2 as `ttyS2`, extlinux-provided root |
| `dts-7.3-linux` | Linux 7.3 mainline | Mainline MMC/PCIe/USB/VOP/eDP/HDMI plus NPU/RGA/VPU/JPEG/VDEC/AV1, `ttyS2` |
| `dtb-5.10-android` | Factory-extracted DTB only | Original input artifact |

Factory DTB:

```text
dtb-5.10-android/rk3588-chmayco.dtb
SHA256: 89E405463A92259DD5490DB515BBB0468016757D77B7FB2EA742505831925D4E
```

Both DTS variants share the board hardware model but keep OS boot policy separate.

The 5.10 and 6.1 trees are standalone single-file board descriptions. They
include only `rk3588.dtsi`, `rk3588-rk806-single.dtsi` and the matching OS
semantics DTSI; `rk3588-evb7-lp4.dtsi` is no longer included. CPU/NPU rails,
USB, display, storage, PCIe/SATA and pinctrl dependencies formerly inherited
from EVB7 are now described explicitly by the board file.

## Board overview

| Feature | Configuration |
| --- | --- |
| SoC | RK3588, 4×Cortex-A76 + 4×Cortex-A55 |
| Main storage | 8-bit eMMC 5.1, HS400, non-removable |
| Main display | 1920×1080 eDP panel with PWM backlight |
| Video outputs | HDMI1 and DP0; HDMI0, DP1 and DSI0/1 are disabled in the factory FDT |
| HDMI input | LT6911UXC to MIPI CSI-2 |
| Camera | IMX766, DW9800W autofocus and OTP EEPROM |
| Ethernet | GMAC1, RGMII, PHY address 1 |
| Expansion | PCIe 2.0 x1 lane 0 and SATA0 |
| USB | USB3 OTG0, USB3 Host1, two USB2 hosts, Type-C PD |
| Audio | ES8388, HDMI1 audio and DP0 audio |
| RTC | SD3078/HYM8563-compatible device at I2C `0x32` |
| Fan | PWM3 at 50 kHz |

## Hardware topology

```text
                    ┌────────────────┐
                    │ 12V DC input   │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │ vcc5v0_sys 5V  │
                    └──┬────┬────┬───┘
          ┌────────────┘    │    └─────────────┐
   ┌──────▼───────┐  ┌──────▼───────┐  ┌───────▼───────┐
   │ RK806 PMIC   │  │ RK8602/8603  │  │ RK8602 NPU    │
   │ SoC/CPU-L    │  │ CPU Big0/1   │  │ I2C1 0x42     │
   └──────┬───────┘  └──────┬───────┘  └───────┬───────┘
          └─────────────────┼──────────────────┘
                     ┌──────▼───────┐
                     │  RK3588 SoC  │
                     └──┬───┬───┬───┘
          ┌─────────────┘   │   └──────────────┐
   ┌──────▼──────┐  ┌──────▼────────┐  ┌───────▼───────┐
   │ eMMC HS400  │  │ VOP2 display  │  │ USB2 / USB3   │
   └─────────────┘  └──┬───┬───┬────┘  └──┬───┬────────┘
                       │   │   │          │   │
                 ┌─────▼┐ ┌▼───┐ ┌────────▼┐ ┌▼────────┐
                 │ eDP0 │ │HDMI1│ │DP0/TypeC│ │HUSB311  │
                 └──────┘ └─────┘ └─────────┘ └─────────┘

GMAC1/RGMII ──► Ethernet PHY @ MDIO 1 ──► RJ45
PCIe 2.0 x1 ──► combphy1
SATA0       ──► combphy0

I2S0 ──► ES8388 ──► Headphone / Speaker amplifiers
I2S6 ──► HDMI1 audio
SPDIF TX2 ──► DP0 audio

IMX766 ──► MIPI DCPHY0 ──► MIPI CSI2 #0 ──► RKCIF0 ──► RKISP0
   ├────► DW9800W VCM
   └────► OTP EEPROM 0x50

HDMI IN ──► LT6911UXC ──► MIPI DPHY0 / 4-lane
       └──► MIPI CSI2 #2 ──► RKCIF2 ──► RKISP1
```

## Power topology

```text
12V DC
  │
  vcc12v_dcin
  ├────────────► vcc5v0_sys ──┬──► RK806
  │                            ├──► RK8602 (Big0)
  │                            ├──► RK8603 (Big1)
  │                            └──► vcc_1v1_nldo_s3
  │
  └──► vcc5v0_usbdcin ──► vcc5v0_usb
                           ├──► vcc5v0_host
                           ├──► vcc5v0_USB30
                           └──► vbus5v0_typec

RK806
  ├──► CPU-L / GPU / vdd_log
  ├──► DDR rails / 3.3V / 1.8V rails
  └──► PMIC-controlled power domains
```

## GPIO assignments

| Function | Pin | GPIO macro | Active level | Signal |
| --- | --- | --- | --- | --- |
| RK806 interrupt | GPIO0_D7 | `RK_PD7` | Low | `rk806single@0` |
| Type-C PD interrupt | GPIO0_D3 | `RK_PD3` | Low | HUSB311 |
| RTC interrupt | GPIO0_B0 | `RK_PB0` | Low | SD3078 |
| SDIO/WiFi reset | GPIO0_C4 | `RK_PC4` | Low | SDIO disabled in factory FDT |
| IMX766 PWDN | GPIO1_A2 | `RK_PA2` | High | Camera power-down |
| IMX766 reset | GPIO1_A3 | `RK_PA3` | High | Camera reset |
| eDP panel enable | GPIO1_A4 | `RK_PA4` | High | `panel-edp0` |
| LT6911 power | GPIO1_B0 | `RK_PB0` | High | HDMI input bridge |
| Headphone detect | GPIO1_C4 | `RK_PC4` | High | ES8388 card |
| LT6911 detect | GPIO1_C6 | `RK_PC6` | Low | Plug-in detect |
| Camera/VCM power | GPIO1_D2 | `RK_PD2` | High | IMX766 / DW9800W |
| Volume up | GPIO2_B0 | `RK_PB0` | Low | GPIO key |
| Volume down | GPIO2_B1 | `RK_PB1` | Low | GPIO key |
| Backlight enable | GPIO2_C1 | `RK_PC1` | High | PWM backlight |
| LT6911 reset | GPIO2_C3 | `RK_PC3` | High | HDMI input bridge |
| GMAC1 PHY reset | GPIO3_B7 | `RK_PB7` | Low | Ethernet PHY |
| LT6911 HPD control | GPIO3_D4 | `RK_PD4` | High | HDMI input bridge |
| eDP panel switch | GPIO3_D5 | `RK_PD5` | High | `panel-edp0` |
| Type-C VBUS enable | GPIO4_A1 | `RK_PA1` | High | Type-C regulator |
| Speaker amplifier | GPIO4_A3 | `RK_PA3` | High | ES8388 card |
| Headphone amplifier | GPIO4_A4 | `RK_PA4` | High | ES8388 card |
| Type-C SBU1/SBU2 | GPIO4_A6/A7 | `RK_PA6` / `RK_PA7` | High | USB-DP PHY |
| HDMI1 enable | GPIO4_B2 | `RK_PB2` | High | HDMI1 TX |
| USB3 power enable | GPIO4_C6 | `RK_PC6` | High | `vcc5v0_USB30` |

GPIO3_B7 is shared by the GMAC1 PHY reset and heartbeat LED in the factory FDT. Driving it as an LED can reset Ethernet, so the rebuilt trees disable the LED.

ADC keys use SARADC1 and SARADC3. ADC1 carries volume-down, back, menu and volume-up thresholds; ADC3 handles headphone detection and play/pause.

## I2C topology

| Bus | Mux | Address | Device | Purpose |
| --- | --- | --- | --- | --- |
| I2C0 | M2 | `0x42` | RK8602 | CPU Big0 |
| I2C0 | M2 | `0x43` | RK8603 | CPU Big1 |
| I2C1 | default | `0x42` | RK8602 | NPU |
| I2C2 | M4 | `0x50` | OTP EEPROM | Camera module data |
| I2C2 | M4 | `0x0C` | DW9800W | IMX766 autofocus |
| I2C2 | M4 | `0x10` | IMX766 | Camera |
| I2C3 | M0 | `0x2B` | LT6911UXC | HDMI to MIPI bridge |
| I2C5 | M0 | `0x14` | GT9xx | Touchscreen |
| I2C6 | M0 | `0x32` | SD3078/HYM8563-compatible RTC | Clock and wakeup |
| I2C6 | M0 | `0x4E` | HUSB311 | Type-C PD |
| I2C7 | default | `0x11` | ES8388 | Audio codec |

## Video and audio paths

```text
Display
  VOP2 ──► eDP0 ──► 1920×1080 panel
    ├────► HDMI1
    └────► DP0 ──► Type-C Alt Mode

Camera
  IMX766 ──► MIPI DCPHY0 ──► MIPI CSI2 #0 ──► RKCIF0 ──► RKISP0

HDMI input
  LT6911UXC ──► MIPI DPHY0 ──► MIPI CSI2 #2 ──► RKCIF2 ──► RKISP1
```

| Sound card | CPU DAI | Codec / sink | Purpose |
| --- | --- | --- | --- |
| `es8388-sound` | `i2s0_8ch` | `es8388@11` | Headphone, speaker and microphone |
| `hdmi1-sound` | `i2s6_8ch` | `hdmi1` | HDMI1 audio |
| `dp0-sound` | `spdif_tx2` | `dp0` | Type-C DP audio |

## Peripheral summary

| Interface | Controller | Mode | State |
| --- | --- | --- | --- |
| eMMC | `mmc@fe2e0000` | 8-bit HS400 | Enabled |
| SATA0 | `sata@fe210000` | SATA + combphy0 | Enabled |
| PCIe 2.0 x1 lane0 | `pcie@fe170000` | Domain 2 + combphy1 | Enabled |
| Ethernet | `ethernet@fe1c0000` | RGMII, PHY 1, `tx_delay=0x43` | Enabled |
| eDP0 | `edp@fdec0000` | 1920×1080 | Enabled |
| HDMI1 | `hdmi@fdea0000` | HDMI TX | Enabled |
| DP0 | `dp@fde50000` | DP Alt Mode | Enabled |
| Type-C | USB3 OTG0 + HUSB311 | OTG / PD / DP Alt | Enabled |
| USB3 Host1 | USB3 OTG1 | Host | Enabled |
| USB2 Host0/1 | EHCI + OHCI | Host | Enabled |
| LT6911UXC | I2C3 + MIPI DPHY0 | 4-lane input | Enabled |
| IMX766 | I2C2 + MIPI DCPHY0 | 3-lane input | Enabled |
| RTC | SD3078 / I2C6 | 32.768 kHz | Enabled |
| Fan | PWM3 | 50 kHz | Enabled |

## Status policy and limitations

The factory board enables eDP0, HDMI1, DP0, GMAC1, PCIe lane0, SATA0, eMMC, USB OTG/hosts, IMX766, LT6911 and ES8388. HDMI0, DP1, DSI0/1, eDP1, SD, SDIO, PCIe 3.0 and USB Host3 remain disabled.

The factory DTB disables PWM3 even though the fan references it; all rebuilt trees enable PWM3. The LED is disabled to protect the shared GMAC1 reset line.

## Linux 7.3 mainline port

The RK3588 media and accelerator blocks are SoC-wide capabilities rather than board-specific peripherals. The 5.10 and 6.1 vendor trees now explicitly enable the RKNN NPU and MMU, dual RGA3, RGA2, JPEG decode/encode, VENC0/1, VDEC0/1, IEP, MPP, all media CCUs, AV1, AVSD and `rkvtunnel`.

The 7.3 mainline tree explicitly enables `rknn_core_0/1/2` with their MMUs, dual RGA3, dual-core RGA2, VPU121, four VEPU121 JPEG encoders, RKVDEC0/1, AV1 and all associated MMUs. `pd_npu` is supplied from `vdd_npu_s0`, while `pd_rkvdec0/1` and `pd_venc0/1` are supplied from `vdd_vdenc_s0`.

`dts-7.3-linux` is written against mainline bindings rather than vendor DTSI properties. It also covers the RK806 and RK8602/RK8603 regulators, eight CPU cores, eMMC, UART2/M0, GMAC1, PCIe 2.0 x1 lane0, SATA0, USB3 OTG0/Host1, USB2 hosts, HUSB311 Type-C, VOP2, eDP0, HDMI1, DP0, ES8388, SD3078 RTC and PWM3 fan control.

Mainline 7.3 does not yet expose the RK3588 RKCIF/RKISP capture nodes or standalone RKVENC H.264/H.265 nodes. Those vendor capabilities are therefore not forced into the mainline DTS. Mainline driver behavior, eDP panel timing and Type-C/DP switching still require hardware validation.

`rkisp1_vir0` still shares an endpoint with `rkcif_mipi_lvds_sditf`, so DTC reports a non-bidirectional graph connection. This is not a base-boot blocker, but the second ISP path requires hardware validation.

The factory FDT contains Goodix touch data, but touch is outside the minimum boot path and still needs driver and coordinate validation. Android-specific serial number and slot suffix must be replaced by the boot flow for production devices.

The device tree only describes kernel-side wiring. A working loader, U-Boot and eMMC layout are still required for the board to boot.
