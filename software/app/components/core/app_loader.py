import os
import sys
from copy import deepcopy
import logging
from dataclasses import dataclass
import importlib.util

from typing import Any

@dataclass
class AppInfo:
    name: str
    file_path: str
    source_folder: str
    obj: object


class DuplicateAppName(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"App '{name}' already loaded")


class AppNotAvailable(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"{name} is not an available app")


class AppLoader:

    def __init__(self, desired_class: object, sources: List[str] = None, app_infos: List[AppInfo] = None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._desired_class = desired_class
        self.sources = []
        self._apps = {}

        if sources is not None:
            assert isinstance(sources, list), f"Input sources must be a list of paths not {type(sources)}"
            for source in sources:
                self.add_source(source)

        if app_infos is not None:
            for app_info in app_infos:
                self.add_app_info(app_info)

    def __add__(self, other_loader: AppLoader) -> AppLoader:
        other_apps = other_loader.get_all_apps()
        for app in other_apps:
            if app in self._apps:
                self.logger.error(f"Eror while combining apps from {other_loader.source_path} and {self.source_path}")
                raise DuplicateAppName(app)
        all_apps = deepcopy(self._apps)
        all_apps.update(other_apps)
        return AppLoader(
            desired_class=self._desired_class,
            app_infos=list(all_apps.values())
        )

    def __getitem__(self, value: str) -> DisplayItem:
        if value not in self._apps:
            raise AppNotAvailable(value)
        return self._apps[value]

    @classmethod
    def from_app_info(cls, info: List[app_info], desired_class: object) -> AppLoader:
        return AppLoader(
            desired_class=desired_class,
            app_infos=info
        )

    def add_app_info(self, app_info: AppInfo) -> None:
        if not isinstance(app_info, AppInfo):
            raise TypeError(f"Unable to add item of {type(app_info)}")
        if app_info.name in self._apps:
            raise DuplicateAppName(f"{app_info.name} already exists in this AppLoader instance")
        self._apps[app_info.name] = app_info
        self.sources.append(app_info.source_folder)
    
    def add_source(self, folder_path: str) -> None:
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Unable to find path - {folder_path}")
        files = self._get_files(folder_path)
        count = 0
        for file in files:
            tmp = self._get_classes(file, self._desired_class)
            for this_class in tmp:
                if this_class in self._apps:
                    raise DuplicateAppName(f"Duplicate instances of {this_class} found")
                app_info = AppInfo(
                    name=this_class,
                    obj = tmp[this_class],
                    file_path=file,
                    source_folder=folder_path
                )
                self.sources.append(folder_path)
                count += 1
                self._apps[app_info.name] = app_info
        self.logger.info(f"Added {count} apps from {folder_path}")

    def get_all_apps(self) -> Dict[str, Any]:
        return self._apps

    def get(self, name: str) -> DisplayItem:
        return self.__getitem__(name)

    def list(self) -> List[str]:
        return list(self._apps.keys())

    def _is_desired_class(self, class_obj: object) -> bool:
        return issubclass(class_obj, self._desired_class) or isinstance(class_obj, self._desired_class)

    def _get_files(self, search_path: str) -> List[str]:
        paths = []
        for root, dirs, files in os.walk(search_path):
            for file in files:
                if os.path.splitext(file)[-1] != ".py":
                    continue
                path = os.path.join(root, file)
                paths.append(path)
        return paths

    def _get_classes(self, file: str, desired_class: obj) -> Any:
        module_name = os.path.splitext(os.path.basename(file))[0]

        # 2. Set up the dynamic import spec
        spec = importlib.util.spec_from_file_location(module_name, file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {file}")

        # 3. Create and execute the module (this loads it into memory)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module  # Optional: Register it in sys.modules
        spec.loader.exec_module(module)

        class_objects = {}
        for attr_name in dir(module):
            attr_obj = getattr(module, attr_name)
            
            # Check if the attribute is a class and was defined in this specific file
            # (This prevents grabbing imported helper classes like datetime, json, etc.)
            if isinstance(attr_obj, type) and attr_obj.__module__ == module_name:
                if not self._is_desired_class(attr_obj):
                # if not issubclass(attr_obj, self._desired_class) and not isinstance(attr_obj, self._desired_class):
                    self.logger.debug(f"{attr_name} is not of type {self._desired_class.__name__} - skipping")
                    continue
                class_objects[attr_name] = attr_obj
        return class_objects

if __name__ == "__main__":

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from app.components.display_playlist.display_item import DisplayItem, DisplayItemType, StaticDisplayItem
    from utils import create_logger
    create_logger()

    apps = AppLoader(DisplayItem, sources=["/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/base_apps"])
    other_apps = AppLoader(DisplayItem, sources=["/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/other_apps"])
    all_apps = apps + other_apps
