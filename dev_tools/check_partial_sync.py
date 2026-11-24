"""检查"只同步了部分上游文件"留下的接口不一致。

背景：上游出新活动时，本仓库常常只搬 `module/coalition/` 等业务模块，
没有同时搬它依赖的配置定义与公共接口，于是任务跑到一半才抛
`AttributeError`。本脚本在同步后、提交前先把这类缺口找出来：

1. 配置属性：`module/` 里所有 `self.config.<大写属性>` 是否能在
   `GeneratedConfig` / `ManualConfig` 中找到定义。
2. 联动活动契约：`module/coalition/` 里所有 `self.<方法>()` 调用
   能否在运行时类 `Coalition`（含继承）上解析。

用法：
    python -m dev_tools.check_partial_sync

退出码 0 表示通过，1 表示存在缺口。检查结果需人工复核：
个别属性来自运行期动态赋值（见 DYNAMIC_CONFIG_ATTRS）。
"""

import ast
import pathlib
import sys

from module.coalition.coalition import Coalition
from module.config.config import AzurLaneConfig

# 这些属性由运行期动态赋值或属于其它配置对象，不来自配置生成产物。
DYNAMIC_CONFIG_ATTRS = {
    'EquipmentCode_Config',
    'EXERCISE_FLEET_EQUIPMENT',
    'FLEET_HARD',
    'FLEET_HARD_EQUIPMENT',
    'OpsiHazard1_PreviousApInsufficient',
    'SCREEN_SHOT_SAVE_FOLDER',
    'SCREEN_SHOT_SAVE_FOLDER_BASE',
    'SCREEN_SHOT_SAVE_INTERVAL',
}

COALITION_FILES = [
    'module/coalition/coalition.py',
    'module/coalition/combat.py',
    'module/coalition/ui.py',
    'module/coalition/coalition_sp.py',
    'module/coalition/coalition_scuttle.py',
]


def known_config_attrs():
    """收集 AzurLaneConfig 上可解析的属性名（含生成产物与 ManualConfig 属性）。"""
    return {name for name in dir(AzurLaneConfig) if not name.startswith('__')}


def check_config_attrs():
    """检查 module/ 中的 self.config.<大写属性> 是否都有定义。"""
    valid = known_config_attrs()
    missing = {}
    for path in pathlib.Path('module').rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            if not (isinstance(node.value, ast.Attribute)
                    and node.value.attr == 'config'
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == 'self'):
                continue
            name = node.attr
            if not name[:1].isupper() or name.startswith('_'):
                continue
            if name in valid or name in DYNAMIC_CONFIG_ATTRS:
                continue
            missing.setdefault(name, []).append(f'{path.as_posix()}:{node.lineno}')
    return missing


def check_coalition_contract():
    """检查联动模块 self.<方法>() 调用是否都能在 Coalition 上解析。"""
    missing = {}
    for rel in COALITION_FILES:
        path = pathlib.Path(rel)
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == 'self'):
                continue
            name = node.func.attr
            if not hasattr(Coalition, name):
                missing.setdefault(name, []).append(f'{rel}:{node.lineno}')
    return missing


def main():
    config_missing = check_config_attrs()
    coalition_missing = check_coalition_contract()

    if config_missing:
        print('[!] self.config.<属性> 缺少定义：')
        for name, locations in sorted(config_missing.items()):
            print(f'    {name}  ({", ".join(locations[:3])})')
    if coalition_missing:
        print('[!] 联动模块调用了 Coalition 上不存在的方法：')
        for name, locations in sorted(coalition_missing.items()):
            print(f'    {name}()  ({", ".join(locations[:3])})')
    if config_missing or coalition_missing:
        print('同步上游模块代码时，请一并同步它依赖的配置定义与公共接口。')
        return 1

    print('[check_partial_sync] 通过 ✅')
    return 0


if __name__ == '__main__':
    sys.exit(main())
