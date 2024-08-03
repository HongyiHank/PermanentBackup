import collections
import os
import shutil
import time
import zipfile
from threading import Lock
from typing import List, Dict

from mcdreforged.api.all import *
from mcdreforged.api.rtext import RTextList, RText, RColor, RAction
from mcdreforged.api.utils.serializer import Serializable


class Configure(Serializable):
    turn_off_auto_save: bool = True
    ignore_session_lock: bool = True
    backup_path: str = './perma_backup'
    server_path: str = './server'
    world_names: List[str] = [
        'world'
    ]
    # 0:guest 1:user 2:helper 3:admin 4:owner
    minimum_permission_level: Dict[str, int] = {
        'make': 2,
        'list': 0,
        'listall': 2,
        'del': 3
    }
    alias: Dict[str, str] = {
        '!!bk': '!!backup'
    }


config: Configure
Prefix = '!!backup'
CONFIG_FILE = os.path.join('config', 'PermanentBackup.json')
HelpMessage = '''
§7------§rMCDR-永久備份-HH修改版§7------§r
一個創建永久備份的插件
§a【指令說明】§r
§7{0}§r 顯示幫助資訊
§7{0} make [<comment>]§r 創建一個備份。§7[<comment>]§r為可選註釋資訊
§7{0} list§r 顯示最近的十個備份的資訊
§7{0} listall§r 顯示所有備份的資訊
§7{0} del [<backup_number>]§r 刪除指定序列號的備份
'''.strip().format(Prefix)
game_saved = False
plugin_unloaded = False
creating_backup = Lock()


def convert_bytes(size: int):
    for x in ["bytes", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return "%3.1f %s" % (size, x)
        size /= 1024.0


def info_message(source: CommandSource, msg: str, broadcast=False):
    for line in msg.splitlines():
        text = '[備份插件] ' + line
        if broadcast and source.is_player:
            source.get_server().broadcast(text)
        else:
            source.reply(text)


def touch_backup_folder():
    if not os.path.isdir(config.backup_path):
        os.makedirs(config.backup_path)


def format_file_name(file_name):
    for c in ['/', '\\', ':', '*', '?', '"', '|', '<', '>']:
        file_name = file_name.replace(c, '')
    return file_name


@new_thread('Perma-Backup')
def create_backup(source: CommandSource, context: dict):
    comment = context.get('cmt', None)
    global creating_backup
    acquired = creating_backup.acquire(blocking=False)
    auto_save_on = True
    if not acquired:
        info_message(source, '§c正在備份中，請不要重複輸入§r')
        return
    try:
        info_message(source, '備份中...請稍等', broadcast=True)
        start_time = time.time()

        # 保存世界
        if config.turn_off_auto_save:
            source.get_server().execute('save-off')
            auto_save_on = False
        global game_saved
        game_saved = False
        source.get_server().execute('save-all flush')
        while True:
            time.sleep(0.01)
            if game_saved:
                break
            if plugin_unloaded:
                source.reply('§c插件卸載，備份中斷！§r', broadcast=True)
                return

        # 複製世界
        def filter_ignore(path, files):
            return [file for file in files if file == 'session.lock' and config.ignore_session_lock]
        touch_backup_folder()
        for world in config.world_names:
            target_path = os.path.join(config.backup_path, world)
            if os.path.isdir(target_path):
                shutil.rmtree(target_path)
            shutil.copytree(os.path.join(config.server_path, world), target_path, ignore=filter_ignore)
        if not auto_save_on:
            source.get_server().execute('save-on')
            auto_save_on = True

        # 尋找檔案名稱
        file_name_raw = os.path.join(config.backup_path, time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()))
        if comment is not None:
            file_name_raw += '_' + format_file_name(comment)
        zip_file_name = file_name_raw
        counter = 0
        while os.path.isfile(zip_file_name + '.zip'):
            counter += 1
            zip_file_name = '{}_{}'.format(file_name_raw, counter)
        zip_file_name += '.zip'

        # 壓縮世界
        info_message(source, '創建壓縮文件§e{}§r中...'.format(os.path.basename(zip_file_name)), broadcast=True)
        zipf = zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED)
        total_files = sum(len(files) for _, _, files in os.walk(config.backup_path))
        processed_files = 0
        
        def update_progress():
            nonlocal processed_files
            processed_files += 1
            if processed_files % int(total_files / 8) == 0 or processed_files == total_files:
                progress = processed_files * 100 / total_files
                bar_length = int(progress / 10)
                progress_bar = f"[{'█'*bar_length}{' '*(10-bar_length)}]"
                info_message(source, f"{progress_bar} {progress:.1f}% [{processed_files}/{total_files}]", broadcast=True)

        for world in config.world_names:
            for dir_path, _, file_names in os.walk(os.path.join(config.backup_path, world)):
                for file_name in file_names:
                    full_path = os.path.join(dir_path, file_name)
                    arc_name = os.path.join(world, full_path.replace(os.path.join(config.backup_path, world), '', 1).lstrip(os.sep))
                    zipf.write(full_path, arcname=arc_name)
                    update_progress()
        
        zipf.close()

        # 清理世界
        for world in config.world_names:
            shutil.rmtree(os.path.join(config.backup_path, world))

        # 計算並顯示檔案大小
        backup_size = os.path.getsize(zip_file_name)
        info_message(source, 
            f'備份§a完成§r，耗時 {round(time.time() - start_time, 1)} 秒\n'
            f'共計 {convert_bytes(backup_size)}',
            broadcast=True
        )
    except Exception as e:
        info_message(source, '備份§a失敗§r，錯誤代碼{}'.format(e), broadcast=True)
        source.get_server().logger.exception('創建備份失敗')
    finally:
        creating_backup.release()
        if config.turn_off_auto_save and not auto_save_on:
            source.get_server().execute('save-on')


def list_backup(source: CommandSource, context: dict, *, amount=10):
    amount = context.get('amount', amount)
    touch_backup_folder()
    arr = []
    for name in os.listdir(config.backup_path):
        file_name = os.path.join(config.backup_path, name)
        if os.path.isfile(file_name) and file_name.endswith('.zip'):
            arr.append(collections.namedtuple('T', 'name stat')(os.path.basename(file_name)[: -len('.zip')], os.stat(file_name)))
    arr.sort(key=lambda x: x.stat.st_mtime, reverse=True)
    info_message(source, '共有§6{}§r個備份'.format(len(arr)))
    if amount == -1:
        amount = len(arr)
    for i in range(min(amount, len(arr))):
        delete_button = RText('[X]', RColor.red).h('刪除此備份').c(
            RAction.suggest_command, f'{Prefix} del {i+1}'
        )
        text = RTextList(
            f'§7{i + 1}.§r §e{arr[i].name} §r{convert_bytes(arr[i].stat.st_size)} ',
            delete_button
        )
        source.reply(text)


def delete_backup(source: CommandSource, context: dict):
    backup_number = context.get('backup_number')
    touch_backup_folder()
    arr = []
    for name in os.listdir(config.backup_path):
        file_name = os.path.join(config.backup_path, name)
        if os.path.isfile(file_name) and file_name.endswith('.zip'):
            arr.append(collections.namedtuple('T', 'name stat')(os.path.basename(file_name)[: -len('.zip')], os.stat(file_name)))
    arr.sort(key=lambda x: x.stat.st_mtime, reverse=True)
    
    if 1 <= backup_number <= len(arr):
        file_to_delete = os.path.join(config.backup_path, arr[backup_number-1].name + '.zip')
        try:
            os.remove(file_to_delete)
            info_message(source, f'已刪除備份檔：{arr[backup_number-1].name}', broadcast=True)
        except Exception as e:
            info_message(source, f'刪除備份檔失敗：{e}', broadcast=True)
    else:
        info_message(source, f'無效的備份檔序列號：{backup_number}', broadcast=True)


def on_info(server, info):
    if not info.is_user:
        if info.content == 'Saved the game':
            global game_saved
            game_saved = True


def on_load(server: PluginServerInterface, old):
    global creating_backup, config
    if hasattr(old, 'creating_backup') and type(old.creating_backup) == type(creating_backup):
        creating_backup = old.creating_backup
    server.register_help_message(Prefix, '創建永久備份')
    config = server.load_config_simple(CONFIG_FILE, target_class=Configure, in_data_folder=False)
    register_command(server)

    # 註冊別名
    for alias, command in config.alias.items():
        server.register_command(
            Literal(alias)
            .runs(get_handler(command))
            .then(
                GreedyText('content')
                .runs(get_handler(command))
            )
        )


def on_unload(server: PluginServerInterface):
    global plugin_unloaded
    plugin_unloaded = True


def on_mcdr_stop(server: PluginServerInterface):
    if creating_backup.locked():
        server.logger.info('等待最多300秒以完成永久備份')
        if creating_backup.acquire(timeout=300):
            creating_backup.release()


def register_command(server: PluginServerInterface):
    def permed_literal(literal: str):
        lvl = config.minimum_permission_level.get(literal, 0)
        return Literal(literal).requires(lambda src: src.has_permission(lvl), failure_message_getter=lambda: '§c權限不足！§r')

    server.register_command(
        Literal(Prefix).
        runs(lambda src: src.reply(HelpMessage)).
        on_error(UnknownCommand, lambda src: src.reply('參數錯誤！請輸入§7{}§r以獲取插件幫助'.format(Prefix)), handled=True).
        then(
            permed_literal('make').
            runs(create_backup).
            then(GreedyText('cmt').runs(create_backup))
        ).
        then(
            permed_literal('list').
            runs(list_backup).
            then(Integer('amount').runs(list_backup))
        ).
        then(
            permed_literal('listall').
            runs(lambda src: list_backup(src, {}, amount=-1))
        ).
        then(
            permed_literal('del').
            then(
                Integer('backup_number').runs(delete_backup)
            )
        )
    )

def get_handler(command):
    def handler(src, ctx):
        src.get_server().execute_command(
            f'{command} {ctx.get("content", "")}',
            src
        )

    return handler