# CHMAYCO RK3588 直播机设备树

[English version](README.en.md)

本仓库记录 CHMAYCO RK3588 直播机的设备树逆向结果，同时维护 Android、vendor Linux 和主线 Linux 三套板级描述。硬件信息以从 Android 5.10.110 系统提取的工厂 DTB 为准。

## 版本目录

| 目录 | 目标系统 | 启动语义 |
| --- | --- | --- |
| `dts-5.10-android` | Android 12 / vendor 5.10 | FIQ debugger、`ttyFIQ0`、Android init、A/B 参数 |
| `dts-6.1-linux` | Armbian / vendor 6.1 | UART2 普通串口、`ttyS2`、extlinux 根设备 |
| `dts-7.3-linux` | Linux 7.3 主线 | 主线 MMC/PCIe/USB/VOP/eDP/HDMI、NPU/RGA/VPU/JPEG/VDEC/AV1，`ttyS2` |
| `dtb-5.10-android` | 原厂提取文件 | 只存放工厂原始 DTB，不归档重建产物 |

原厂 DTB：

```text
dtb-5.10-android/rk3588-chmayco.dtb
SHA256: 89E405463A92259DD5490DB515BBB0468016757D77B7FB2EA742505831925D4E
```

三套 DTS 共享板级硬件事实，但 OS 启动参数、串口控制方式和根文件系统策略严格分离。

5.10 和 6.1 均已改为独立单文件结构：只包含 `rk3588.dtsi`、
`rk3588-rk806-single.dtsi` 和对应 OS 语义 DTSI，不再包含
`rk3588-evb7-lp4.dtsi`。EVB7 原先隐式提供的 CPU/NPU 电源、USB、
display、storage、PCIe/SATA 和 pinctrl 依赖均由板级文件显式描述。

## 板级硬件概览

| 功能 | 配置 |
| --- | --- |
| SoC | RK3588，4×Cortex-A76 + 4×Cortex-A55 |
| 内存 | LPDDR4 拓扑，设备树可见内存窗口覆盖低 4 GB 地址空间 |
| 主存储 | 8 bit eMMC 5.1，HS400，不可移除 |
| 主显示 | 1920×1080 eDP 面板，PWM 背光 |
| 视频输出 | HDMI1、DP0；工厂 FDT 未启用 HDMI0、DP1、DSI0/1 |
| 视频输入 | LT6911UXC 转 MIPI CSI-2 |
| 内置摄像头 | IMX766 + DW9800W 自动对焦 + OTP EEPROM |
| 网络 | GMAC1、RGMII、PHY 地址 1 |
| 扩展 | PCIe 2.0 x1 lane 0、SATA0 |
| USB | USB3 OTG0、USB3 Host1、两路 USB2 Host、Type-C PD |
| 音频 | ES8388、HDMI1 音频、DP0 音频 |
| RTC | SD3078/HYM8563 兼容设备，I2C 地址 `0x32` |
| 风扇 | PWM3，50 kHz |

## 硬件拓扑

```text
                    ┌──────────────┐
                    │ 12V DC 输入  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ vcc5v0_sys   │
                    │ 5V 系统电源  │
                    └───┬───┬───┬──┘
          ┌─────────────┘   │   └──────────────┐
          │                 │                  │
   ┌──────▼──────┐   ┌──────▼──────┐    ┌──────▼──────┐
   │ RK806 PMIC  │   │ RK8602/8603 │    │ RK8602 NPU  │
   │ SoC/CPU-L   │   │ CPU Big0/1  │    │ I2C1 0x42   │
   └──────┬──────┘   └──────┬──────┘    └──────┬──────┘
          └─────────────────┼──────────────────┘
                     ┌──────▼───────┐
                     │  RK3588 SoC  │
                     └──┬──┬──┬──┬──┘
          ┌─────────────┘  │  │  └──────────────┐
          │                │  │                 │
   ┌──────▼──────┐  ┌──────▼──▼──────┐   ┌──────▼──────┐
   │ eMMC 5.1    │  │ VOP2 显示控制   │   │ USB 控制器   │
   │ HS400       │  │ eDP/HDMI/DP     │   │ USB2/USB3    │
   └─────────────┘  └──┬───┬───┬─────┘   └──┬───┬───────┘
                       │   │   │            │   │
                 ┌─────▼┐ ┌▼───┐ ┌─────────▼┐ ┌▼────────┐
                 │ eDP0 │ │HDMI1│ │DP0/TypeC │ │HUSB311  │
                 │Panel │ │ TX  │ │Alt Mode  │ │PD       │
                 └──────┘ └─────┘ └──────────┘ └─────────┘

   ┌──────────────┐       ┌──────────────┐
   │ GMAC1/RGMII  │──────►│ Ethernet PHY │──► RJ45
   └──────────────┘       │ MDIO addr 1  │
                          └──────────────┘

   ┌──────────────┐       ┌──────────────┐
   │ PCIe 2.0 x1  │──────►│ combphy1     │
   └──────────────┘       └──────────────┘
   ┌──────────────┐       ┌──────────────┐
   │ SATA0        │──────►│ combphy0     │
   └──────────────┘       └──────────────┘

   I2S0 ──► ES8388 ──► 耳机功放 / 扬声器功放
   I2S6 ──► HDMI1 音频
   SPDIF TX2 ──► DP0 音频

   IMX766 ──► MIPI DCPHY0 ──► MIPI CSI2 #0 ──► RKCIF0 ──► RKISP0
      └────► DW9800W VCM
      └────► OTP EEPROM 0x50

   LT6911UXC ◄── HDMI IN
      └────► MIPI DPHY0 4-lane ──► MIPI CSI2 #2 ──► RKCIF2 ──► RKISP1
```

## 电源拓扑

```text
12V DC
  │
  vcc12v_dcin
  ├──────────────► vcc5v0_sys ──┬──► RK806
  │                             ├──► RK8602 (Big0)
  │                             ├──► RK8603 (Big1)
  │                             └──► vcc_1v1_nldo_s3
  │
  └──► vcc5v0_usbdcin ──► vcc5v0_usb
                           ├──► vcc5v0_host
                           ├──► vcc5v0_USB30
                           └──► vbus5v0_typec

RK806
  ├──► vdd_cpu_lit_s0      0.55–0.95V
  ├──► vdd_gpu_s0          0.55–0.95V
  ├──► vdd_log_s0          0.675–0.75V
  ├──► vdd_ddr_s0          0.675–0.90V
  ├──► vdd2_ddr_s3
  ├──► vddq_ddr_s0
  ├──► vcc_3v3_s3
  └──► vcc_1v8_s3

RK8602 (I2C0 0x42) ──► CPU Big0   0.55–1.05V
RK8603 (I2C0 0x43) ──► CPU Big1   0.55–1.05V
RK8602 (I2C1 0x42) ──► NPU        0.55–0.95V
```

## GPIO 分配

引脚编号采用 Rockchip bank + port + index；有效电平取自工厂 DTB。

| 功能 | 引脚 | GPIO 宏 | 有效电平 | 设备树节点或信号 |
| --- | --- | --- | --- | --- |
| RK806 中断 | GPIO0_D7 | `RK_PD7` | Low | `rk806single@0` |
| Type-C PD 中断 | GPIO0_D3 | `RK_PD3` | Low | HUSB311 `usbc0_int` |
| RTC 中断 | GPIO0_B0 | `RK_PB0` | Low | SD3078 `hym8563_int` |
| SDIO/WiFi reset | GPIO0_C4 | `RK_PC4` | Low | `sdio_pwrseq`，原厂 SDIO 关闭 |
| IMX766 PWDN | GPIO1_A2 | `RK_PA2` | High | `pwdn-gpios` |
| IMX766 reset | GPIO1_A3 | `RK_PA3` | High | `reset-gpios` |
| eDP 面板 enable | GPIO1_A4 | `RK_PA4` | High | `panel-edp0.enable-gpios` |
| LT6911 power | GPIO1_B0 | `RK_PB0` | High | `lt6911.power-gpios` |
| 耳机检测 | GPIO1_C4 | `RK_PC4` | High | `hp-det-gpio` |
| LT6911 插入检测 | GPIO1_C6 | `RK_PC6` | Low | `plugin-det-gpios` |
| 摄像头/VCM 电源 | GPIO1_D2 | `RK_PD2` | High | IMX766、DW9800W `power-gpios` |
| 音量加键 | GPIO2_B0 | `RK_PB0` | Low | `gpio-keys` |
| 音量减键 | GPIO2_B1 | `RK_PB1` | Low | `gpio-keys` |
| 背光 enable | GPIO2_C1 | `RK_PC1` | High | `backlight.enable-gpios` |
| LT6911 reset | GPIO2_C3 | `RK_PC3` | High | `lt6911.reset-gpios` |
| GMAC1 PHY reset | GPIO3_B7 | `RK_PB7` | Low | `snps,reset-gpio` |
| LT6911 HPD 控制 | GPIO3_D4 | `RK_PD4` | High | `hpd-ctl-gpios` |
| eDP 面板 switch | GPIO3_D5 | `RK_PD5` | High | `panel-edp0.switch-gpios` |
| Type-C VBUS enable | GPIO4_A1 | `RK_PA1` | High | `vbus5v0_typec` |
| 扬声器功放 enable | GPIO4_A3 | `RK_PA3` | High | `spk-con-gpio` |
| 耳机功放 enable | GPIO4_A4 | `RK_PA4` | High | `hp-con-gpio` |
| Type-C SBU1 | GPIO4_A6 | `RK_PA6` | High | USB-DP PHY |
| Type-C SBU2 | GPIO4_A7 | `RK_PA7` | High | USB-DP PHY |
| HDMI1 enable | GPIO4_B2 | `RK_PB2` | High | `hdmi1.enable-gpios` |
| USB3 电源 enable | GPIO4_C6 | `RK_PC6` | High | `vcc5v0_USB30` |

> **冲突处理：** GPIO3_B7 同时出现在 GMAC1 PHY reset 和心跳灯定义中。驱动 LED 可能复位以太网 PHY，因此两版 DTS 均关闭该 LED。

ADC 按键使用 SARADC：

| 通道 | 功能 | 判定阈值 |
| --- | --- | --- |
| ADC1 | Volume Down / Back / Menu / Volume Up | 417 mV / 1235 mV / 890 mV / 17 mV |
| ADC3 | 耳机插入与 `play/pause` | 2 mV |

## I2C 拓扑

| 总线 | 复用 | 地址 | 设备 | 用途 |
| --- | --- | --- | --- | --- |
| I2C0 | M2 | `0x42` | RK8602 | CPU Big0 动态供电 |
| I2C0 | M2 | `0x43` | RK8603 | CPU Big1 动态供电 |
| I2C1 | 默认 | `0x42` | RK8602 | NPU 供电 |
| I2C2 | M4 | `0x50` | OTP EEPROM | 摄像头模组信息 |
| I2C2 | M4 | `0x0C` | DW9800W | IMX766 对焦马达 |
| I2C2 | M4 | `0x10` | IMX766 | MIPI 摄像头 |
| I2C3 | M0 | `0x2B` | LT6911UXC | HDMI→MIPI 桥 |
| I2C5 | M0 | `0x14` | GT9xx | 触摸屏 |
| I2C6 | M0 | `0x32` | SD3078/HYM8563 兼容 RTC | 时钟与唤醒 |
| I2C6 | M0 | `0x4E` | HUSB311 | Type-C PD 与角色切换 |
| I2C7 | 默认 | `0x11` | ES8388 | 板载音频 Codec |

## 视频链路

```text
显示输出
  VOP2 ──► eDP0 ──► 1920×1080 面板
    ├────► HDMI1 TX
    └────► DP0 ──► Type-C Alt Mode

摄像头采集
  IMX766 ──► MIPI DCPHY0 ──► MIPI CSI2 #0
       └──► RKCIF MIPI LVDS ──► RKISP0

HDMI 采集
  HDMI IN ──► LT6911UXC ──► MIPI DPHY0 / 4-lane
       └──► MIPI CSI2 #2 ──► RKCIF MIPI LVDS2 ──► RKISP1
```

## 音频链路

| 声卡节点 | CPU DAI | Codec / Sink | 格式 | 说明 |
| --- | --- | --- | --- | --- |
| `es8388-sound` | `i2s0_8ch` | `es8388@11` | I2S | 耳机、扬声器、麦克风 |
| `hdmi1-sound` | `i2s6_8ch` | `hdmi1` | I2S | HDMI1 音频输出 |
| `dp0-sound` | `spdif_tx2` | `dp0` | S/PDIF | Type-C DP 音频 |
| 板载 HDMI-in 音频 | `i2s7_8ch` | HDMI RX controller | I2S | 工厂 FDT 保留 |

ES8388 控制引脚：

| 信号 | 引脚 | 有效电平 |
| --- | --- | --- |
| 扬声器功放 enable | GPIO4_A3 | High |
| 耳机功放 enable | GPIO4_A4 | High |
| 耳机插入检测 | GPIO1_C4 | High |

## 外设接口

| 分类 | 接口 | 控制器 | 工作方式 | 状态 |
| --- | --- | --- | --- | --- |
| 存储 | eMMC | `mmc@fe2e0000` | 8-bit HS400 | 启用 |
| 存储 | SATA0 | `sata@fe210000` | SATA + combphy0 | 启用 |
| 扩展 | PCIe 2.0 x1 lane0 | `pcie@fe170000` | domain 2 + combphy1 | 启用 |
| 网络 | RJ45 | `ethernet@fe1c0000` | RGMII，PHY@1，`tx_delay=0x43` | 启用 |
| 显示 | eDP0 | `edp@fdec0000` | 1920×1080 | 启用 |
| 显示 | HDMI1 | `hdmi@fdea0000` | HDMI TX | 启用 |
| 显示 | DP0 | `dp@fde50000` | DP Alt Mode | 启用 |
| USB | Type-C | USB3 OTG0 + HUSB311 | OTG / PD / DP Alt | 启用 |
| USB | USB3 Host1 | USB3 OTG1 | Host | 启用 |
| USB | USB2 Host0/1 | EHCI + OHCI | Host | 启用 |
| 采集 | LT6911UXC | I2C3 + MIPI DPHY0 | 4-lane | 启用 |
| 采集 | IMX766 | I2C2 + MIPI DCPHY0 | 3-lane | 启用 |
| RTC | SD3078 | I2C6 `0x32` | 32.768 kHz | 启用 |
| 风扇 | PWM3 | 50 kHz | 5 档温控 | 启用 |

## DTS 状态策略

工厂 FDT 中相关输出状态如下：

- 启用：eDP0、HDMI1、DP0、GMAC1、PCIe 2.0 x1 lane0、SATA0、eMMC、USB OTG/Host、IMX766、LT6911、ES8388。
- 关闭：HDMI0、DP1、DSI0、DSI1、eDP1、SD、SDIO、PCIe 3.0、USB Host3。
- 原厂 PWM3 被关闭但风扇引用 PWM3，因此重建版本主动启用 PWM3。
- 心跳灯与 GMAC1 reset 共用 GPIO3_B7，因此重建版本关闭心跳灯。

## SoC 媒体与加速能力

这些设备位于 RK3588 SoC 内，不随单板 BOM 变化。虽然工厂 FDT 关闭了部分媒体节点，重建版本仍按芯片能力显式启用：

- 5.10/6.1 vendor DTS：`rknpu` 与 MMU、RGA3 双核、RGA2、JPEG 解码、JPEG 编码 0–3、VENC0/1、VDEC0/1、IEP、MPP、JPEG/VENC/VDEC CCU、AV1、AVSD 和 `rkvtunnel`；
- 7.3 mainline DTS：`rknn_core_0/1/2` 与三组 MMU、RGA3 双核、双核 RGA2、VPU121、VEPU121 JPEG 编码 0–3、RKVDEC0/1、AV1 及对应 MMU；
- 7.3 同时绑定 `pd_npu` 到 `vdd_npu_s0`，并把 `pd_rkvdec0/1`、`pd_venc0/1` 绑定到 `vdd_vdenc_s0`。

7.3 mainline 当前没有 RK3588 RKCIF/RKISP 采集设备节点，也没有独立的 RKVENC H.264/H.265 编码节点；这些 vendor 能力不能直接照搬到 mainline。

## Linux 7.3 主线端口

`dts-7.3-linux` 按主线 binding 重写，不复用 vendor DTSI 属性。当前包含：

- RK806、RK8602/RK8603 与八核 CPU 供电；
- eMMC、UART2/M0、GMAC1、PCIe 2.0 x1 lane0、SATA0；
- USB3 OTG0/Host1、USB2 Host0/1、HUSB311 Type-C；
- VOP2、eDP0 面板、HDMI1、DP0；
- 三核 NPU、RGA3/RGA2、VPU121、四核 VEPU121 JPEG、RKVDEC0/1 和 AV1；
- ES8388 声卡、SD3078 RTC、PWM3 风扇和 ADC/GPIO 按键。

Linux 7.3 主线尚未提供本机所需的 RKCIF/RKISP 采集节点，因此 IMX766 和 LT6911UXC 的完整采集链路没有强行移植。主线驱动行为、eDP 面板时序和 Type-C/DP 切换仍需实机验证。

## 已知限制

1. 原厂 `rkisp1_vir0` 与 `rkcif_mipi_lvds_sditf` 共用同一端点，DTC 会报告非双向 graph 连接。基础启动不受影响，第二条 ISP 路径需要实机采集验证。
2. 工厂 FDT 存在 Goodix 触摸信息，但目前未纳入最小启动路径，仍需驱动和坐标验证。
3. Android DTB 保留本机原厂序列号和 `_a` slot；批量部署时必须由引导层替换设备专属参数。
4. 设备树只描述内核侧硬件。正式启动仍依赖匹配的 loader、U-Boot 和 eMMC 分区布局。
