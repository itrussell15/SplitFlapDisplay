import os
import sys
import munch
import importlib.util


class AppLoader:

    def __init__(self, folder_path: str) -> None:
        files = self._get_files(folder_path)
        print(files)
        self._apps = munch.Munch()
        for file in files:
            tmp = self._get_classes(file)
            for this_class in tmp:
                self._apps[this_class] = munch.Munch()
                self._apps[this_class].obj = tmp[this_class]
                self._apps[this_class].path = file
        print(self._apps)

    def __getitem__(self, value: str) -> DisplayItem:
        if value not in self._apps:
            raise KeyError(f"No app {value} found")
        return self._apps[value].obj

    @staticmethod
    def _get_files(search_path: str) -> List[str]:
        paths = []
        for root, dirs, files in os.walk(search_path):
            for file in files:
                if os.path.splitext(file)[-1] != ".py":
                    continue
                path = os.path.join(root, file)
                paths.append(path)
        return paths

    @staticmethod
    def _get_classes(file: str) -> Any:
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
                class_objects[attr_name] = attr_obj
        return class_objects

    def get(self, name: str) -> DisplayItem:
        pass

        
if __name__ == "__main__":
    apps = AppLoader("/home/isaac/projects/SplitFlapDisplay/software/app/components/display_playlist/base_apps")
    print(apps["ClockApp"])
