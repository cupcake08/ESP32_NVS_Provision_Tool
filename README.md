# ESP32 NVS Provisioning Tool ⚙️

A Python utility designed to streamline the process of generating and flashing device-specific Non-Volatile Storage (NVS) partitions for ESP32 devices, primarily focusing on embedding credentials like certificates and private keys.

## Usecase
- Generate device folder
---
Manual

```bash
python main.py --mac <mac> -g
```

Auto Detect
```bash
python main.py --port <port> -g
```
---
- Fill the certficate and private key file
---
- Generate Certificate and Flash

Auto Detect (Recommended)
```bash
python main.py --port <port> --hv <hardware version>
```

Manual
```bash
python main.py --mac <mac> --port <port> --hv <hardware version>
```


## Prerequisites 📋

- Esptool: required to flash the nvs partition
