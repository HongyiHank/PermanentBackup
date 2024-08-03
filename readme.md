HH Permanent Backup
-----
## HH版說明

前陣子修改了雲鎮工藝的 [TimeBackup](https://github.com/HongyiHank/TimeBackup) 插件

後來發現它備份的時間有點長、體積有點大，我也用不太到自動備份，所以就找了一個新的插件 [PermanentBackup](https://github.com/TISUnion/PermanentBackup)

使用後我覺得還是有一些不足的地方，所以我還修改和新增了以下功能

1.增加進度條-代碼參考 [TimeBackup](https://github.com/HongyiHank/TimeBackup)

2.備份完成後顯示檔案大小-代碼參考 [TimeBackup](https://github.com/HongyiHank/TimeBackup)

3.增加別名(!!bk)功能-代碼參考 [Command Aliases](https://mcdreforged.com/zh-CN/plugin/command_aliases)

4.刪除(!!backup del)功能-靈感來源 [Prime Backup](https://mcdreforged.com/zh-CN/plugin/prime_backup)

5.列出備份時顯示刪除按鈕-代碼參考 [Where Is](https://mcdreforged.com/zh-CN/plugin/where_is) 

6.繁體中文化

## Fallen版(原版)說明

一個用於創建完整備份的 [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) 插件。備份的存檔將會被打包成 `.zip` 格式

與 [QuickBackupM](https://github.com/TISUnion/QuickBackupM) 類似，PermanentBackup 可以指定備份的世界文件夾，也可以修改所需的權限等級

備份的存檔將會存放至 perma_backup 文件夾中

## 指令格式說明

`!!backup` 顯示幫助資訊

`!!backup make [<comment>]` 創建一個備份，comment 為可選備註資訊

`!!backup list` 顯示最近的十個備份的資訊

`!!backup listall` 顯示所有備份的資訊

`!!backup del [<backup_number>]` 刪除指定序列號的備份

## 配置文件

配置文件為 `config/PermanentBackup.json`

具體修改方式類似 [QuickBackupM](https://github.com/TISUnion/QuickBackupM)

默認配置文件：

```json5
{
    "turn_off_auto_save": true,
    "ignore_session_lock": true,
    "backup_path": "./perma_backup",
    "server_path": "./server",
    "world_names": [
        "world"
    ],
    "minimum_permission_level": {
        "make": 2,
        "list": 0,
        "listall": 2,
        "del": 3
    },
    "alias": {
        "!!bk": "!!backup"
    }
}
```
