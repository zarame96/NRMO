"""modules/ 内の全モジュールを import して REGISTRY に登録する。新規ファイルを足せば自動で載る。"""
import importlib
import pkgutil

for _m in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_m.name}")
