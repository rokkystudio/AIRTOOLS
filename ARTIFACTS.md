# Артефакты

Эта папка хранит полезные результаты сборок и внешние бинарники, которые нельзя держать в disposable `build`.

## Firmware Images

```text
dumps\original\   заводские recovery dumps
dumps\bases\      стабильные base images для пересборки
dumps\verified\   проверенные прошитые images
```

Текущий проверенный прошитый образ:

```text
dumps\verified\mtd4_at_wpa2_airtools_wn723n_20260920.bin
size:   3866624
sha256: 7443772442fbbc038305f75659d8b628b319b1da73f99f699a43904f8271124d
```

Base image для WN723N/airtools builder:

```text
dumps\bases\mtd4_connectivity_base_20260916.bin
```

## Binary Artifacts

```text
artifacts\binaries\mipsel\
  airapi_mipsel
  aireplay_mipsel
  airodump_mipsel
  airtools_mipsel
  airwifi
  endoscope-connectivity
  mtd4_lzma_extract_8188eu_mipsel
  rtap_capture_mipsel
  rtap_pcap_capture_mipsel

artifacts\drivers\rtl8188eus\
  8188eu_vendorabi_pm_skb_slim.ko
  8188eu_vendorabi_pm_skb_slim.ko.lzma

artifacts\vendor\
  mt_wifi.ko

artifacts\windows\
  AT-open-profile.xml
  ch341_driver_export\
```

`build\` теперь считается disposable output и игнорируется Git.
