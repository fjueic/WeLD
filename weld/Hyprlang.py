import ast
from typing import Union


def clamp(value, min_value=-float("inf"), max_value=float("inf")):
    return max(min(value, max_value), min_value)


class RGBA:
    """Represents a color in RGBA format"""

    def __init__(self, r: int, g: int, b: int, a: float = -1):
        self.r = clamp(r, 0, 255)
        self.g = clamp(g, 0, 255)
        self.b = clamp(b, 0, 255)
        self.a = a
        if a != -1:
            self.a = clamp(a, 0, 1)

    def hex(self):
        """Returns the hexadecimal color code of the color."""
        return f"rgb{'a' if self.a!=-1 else ''}({hex(self.r)[2:]}{hex(self.g)[2:]}{hex(self.b)[2:]}{f'{hex(int(self.a*255))[2:]}' if self.a!=-1 else ''})"

    @classmethod
    def from_hex(cls, hex: str):
        """Creates an RGBA instance from a hexadecimal color code."""
        """rgbf: RRGGBB"""
        """rgba: RRGGBBAA"""
        hex = hex.lstrip("#")

        if len(hex) == 6:
            return cls(*[int(hex[i : i + 2], 16) for i in (0, 2, 4)])
        return cls(
            *(
                [int(hex[i : i + 2], 16) for i in (0, 2, 4)]
                + [round(int(hex[6:8], 16) / 255, 2)]
            )
        )

    def __str__(self):
        return f"rgb{'a' if self.a!=-1 else ''}({self.r}, {self.g}, {self.b}{f', {self.a}' if self.a!=-1 else ''})"


class Gradient:
    def __init__(self, s: RGBA, e: RGBA, angle: int):
        self.s = s
        self.e = e
        self.angle = angle

    def __str__(self):
        return f"{self.s} {self.e} {self.angle}deg"


class Vec2:
    """Represents a 2-dimensional vector."""

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __str__(self):
        return f"{self.x} {self.y}"


class Parameters:
    """It's just list to be passed in a handler"""

    def __init__(self, *args):
        self.params = args

    def __str__(self):
        return ", ".join(str(param) for param in self.params)


class Handler:
    """A line in hyprlang"""

    def __init__(self, keyword: str, *params: Parameters):
        self.keyword = keyword
        self.params = params

    def __str__(self):
        res = ""
        for param in self.params:
            if self.keyword == "raw_text":
                res += f"{str(param)}\n"
            else:
                res += f"{self.keyword} = {str(param)}\n"
        return res


class Category:
    """A category in hyprlang, it a dictionary like structure"""

    def __init__(self, name: str, *props: Union["Handler", "Category"]):
        self.name = name
        self.props = props

    def __nested(self):
        """Returns the category as a string with 4 spaces before each line."""
        res = str(self).split("\n")
        res = [f"{' '*4}{line}" for line in res[:-1]] + [res[-1]]
        return "\n".join(res)

    @classmethod
    def from_dict(cls, name: str, config: dict):
        """Creates a Category instance from a dictionary"""
        res = []
        for key, value in config.items():
            if isinstance(value, tuple):
                res.append(Handler(key, Parameters(*value)))
            elif isinstance(value, dict):
                res.append(cls.from_dict(key, value))
            elif isinstance(value, list):
                for i in value:
                    if isinstance(i, dict):
                        res.append(cls.from_dict(key, i))
                    elif isinstance(i, tuple):
                        res.append(Handler(key, Parameters(*i)))
                    else:
                        res.append(Handler(key, Parameters(i)))
            else:
                res.append(Handler(key, Parameters(value)))
        return cls(name, *res)

    def __str__(self):
        res = f"{self.name} {{\n"
        for prop in self.props:
            if isinstance(prop, Handler):
                res += f"{' '*4}{prop}"
            else:
                res += f"{prop.__nested()}"
        res += "}\n"
        return res


class Hyprlang_config:
    """Just to store the config of the hyprlang
    Only one instance of class should be created per file and stored in a variable named `config`.
    """

    def __init__(self):
        self.config = []

    def add_config_entries(self, **kwargs):
        """Adds a handler or category to the hyprlang"""
        for key, value in kwargs.items():
            if isinstance(value, dict):
                self.config.append(Category.from_dict(key, value))
            elif isinstance(value, list):
                for i in value:
                    if isinstance(i, dict):
                        self.config.append(Category.from_dict(key, i))
                    elif isinstance(i, tuple):
                        self.config.append(Handler(key, Parameters(*i)))
                    else:
                        self.config.append(Handler(key, Parameters(i)))
            elif isinstance(value, tuple):
                self.config.append(Handler(key, Parameters(*value)))
            else:
                self.config.append(Handler(key, Parameters(value)))

    def add(self, *obj: Union["Handler", "Category"]):
        """Adds a handler or category to the hyprlang"""
        for o in obj:
            self.config.append(o)

    def add_config(self, config: "Hyprlang_config"):
        """Adds a config to the hyprlang"""
        self.config.extend(config.config)

    def __str__(self):
        res = ""
        for obj in self.config:
            res += str(obj) + "\n"
        return res


# Transformer class
class Transformer(ast.NodeTransformer):
    def __init__(self, tracker_name):
        self.tracker_name = tracker_name
        self.context_stack = []  # Tracks context
        self.variables = set()
        self.with_targets = set()

    def visit_FunctionDef(self, node):
        self.context_stack.append("function")
        self.generic_visit(node)
        self.context_stack.pop()
        return node

    def visit_ClassDef(self, node):
        self.context_stack.append("class")
        self.generic_visit(node)
        self.context_stack.pop()
        return node

    def visit_Lambda(self, node):
        self.context_stack.append("lambda")
        self.generic_visit(node)
        self.context_stack.pop()
        return node

    def visit_With(self, node):
        # Track variables defined in the with context
        for item in node.items:
            if isinstance(item.optional_vars, ast.Name):
                self.with_targets.add(item.optional_vars.id)
        self.generic_visit(node)
        return node

    def visit_Name(self, node):
        # Modify variables only if they're not in the with context's target or inside special scopes
        if (
            not self.context_stack
            and node.id in self.variables
            and node.id not in self.with_targets
        ):
            return ast.copy_location(
                ast.Name(id=f"{self.tracker_name}.{node.id}", ctx=node.ctx), node
            )
        return node

    def visit_Assign(self, node):
        # Modify assignments if not in a function, class, or lambda, but handle 'with' context separately
        if not self.context_stack:
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    self.variables.add(target.id)
                    target.id = f"{self.tracker_name}.{target.id}"
        self.generic_visit(node)
        return node


def send_notification(message, urgency="normal"):
    import subprocess

    subprocess.run(f"notify-send -u {urgency} '{message}'", shell=True)


class Source(ast.NodeTransformer):
    def __init__(self):
        self.filename = []

    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Name) and node.targets[0].id == "source":
            with open(node.value.value) as f:
                code = f.read()
            self.filename.append(node.value.value)
            return ast.parse(code)
        return node


def convert_code_to_hyprlang(d: str, alias={}):
    """This function is specfically made of WeLD"""
    code = (
        """class AutoTracker:
    def __init__(self):
        self._history = {}

    def __setattr__(self, name, value):
        if name != "_history":
            if name not in self._history:
                self._history[name] = []
            self._history[name].append(value)
        super().__setattr__(name, value)

    def get_history(self, name):
        return self._history.get(name, [])

    def get_all_history(self):
        return self._history

# Transform the code
_tracker = AutoTracker()

"""
        + d
    )

    tree = ast.parse(code)
    transformer = Transformer("_tracker")
    tree = transformer.visit(tree)
    code = ast.unparse(tree)
    variables = {}
    exec(code, {}, variables)
    data = variables["_tracker"].get_all_history()
    for key, value in alias.items():
        if key in data:
            data[value] = data[key]
            data.pop(key)
    config = Hyprlang_config()
    config.add_config_entries(**data)
    return str(config)


def convert_to_hyprlang(file, alias={}):
    if not file.endswith(".py"):
        return [file]
    code = (
        """class AutoTracker:
    def __init__(self):
        self._history = {}

    def __setattr__(self, name, value):
        if name != "_history":
            if name not in self._history:
                self._history[name] = []
            self._history[name].append(value)
        super().__setattr__(name, value)

    def get_history(self, name):
        return self._history.get(name, [])

    def get_all_history(self):
        return self._history

# Transform the code
_tracker = AutoTracker()

"""
        + open(file).read()
    )
    pre_code = code

    visited = []
    from os import path

    visited.append(path.abspath(file))
    while True:
        source_transformer = Source()
        tree = ast.parse(code)
        tree = source_transformer.visit(tree)
        code = ast.unparse(tree)
        if code == pre_code:
            break
        pre_code = code
        if source_transformer.filename in visited:
            send_notification(
                f"Circular dependency detected from {visited[-1]} to {source_transformer.filename}",
                "critical",
            )
            return visited
        for i in source_transformer.filename:
            if i:
                visited.append(path.abspath(i))

    tree = ast.parse(code)
    transformer = Transformer("_tracker")
    tree = transformer.visit(tree)
    code = ast.unparse(tree)

    variables = {}
    exec(code, {}, variables)
    # print(variables["_tracker"].get_all_history())
    data = variables["_tracker"].get_all_history()
    try:
        from os import path

        output = path.expanduser(data["output"][-1])
        data.pop("output")
        del path
    except:
        send_notification(f"{file}: Output variable of type str required", "critical")
        return visited
    for key, value in alias.items():
        if key in data:
            data[value] = data[key]
            data.pop(key)
    config = Hyprlang_config()
    config.add_config_entries(**data)
    with open(output, "w") as f:
        f.write(str(config))

    return visited


global observers
global files
observers = {
    # directory : obserber
}
files = {
    # main file : [dependencies]
    # dependencies include main file
}


def main(args, alias):
    from os import path

    main_files = set()
    for file in args:
        if path.exists(file):
            main_files.add(path.abspath(file))
        else:
            send_notification(f"File {file} does not exist", "critical")
    if not main_files:
        send_notification("No valid files found", "critical")
        return

    for file in main_files:
        files[file] = convert_to_hyprlang(file, alias)
        files[file] = [path.abspath(file) for file in files[file]]

    for file in files:
        for dependency in files[file]:
            directory = path.dirname(dependency)
            if directory not in observers:
                from watchdog.events import FileSystemEventHandler
                from watchdog.observers import Observer

                class Handler(FileSystemEventHandler):
                    def on_modified(self, event):
                        global files
                        global observers
                        if event.is_directory:
                            return
                        for key, value in files.items():
                            if path.abspath(event.src_path) in value:
                                while 1:
                                    try:
                                        files[key] = convert_to_hyprlang(key, alias)
                                        break
                                    except Exception as e:
                                        send_notification(
                                            f"Error in {key}: {e}.\nRETRY IN 10 sec",
                                            "critical",
                                        )
                                        from time import sleep

                                        sleep(10)
                                files[key] = [path.abspath(file) for file in files[key]]
                                break
                        for observer in observers.values():
                            observer.stop()

                        observers = {}
                        for file in files:
                            for dependency in files[file]:
                                directory = path.dirname(dependency)
                                if directory not in observers:
                                    observers[directory] = Observer()
                                    observers[directory].schedule(
                                        Handler(), path=directory, recursive=False
                                    )
                                    observers[directory].start()

                observers[directory] = Observer()
                observers[directory].schedule(
                    Handler(), path=directory, recursive=False
                )
                observers[directory].start()
    from time import sleep

    try:
        while 1:
            sleep(10**9)
    except KeyboardInterrupt:
        for observer in observers.values():
            observer.stop()
        del sleep
        return

    """
    observers= []
    for file in args:
        files = convert_to_hyprlang(file, alias)
        observers.append({
            "file": file,
            "dependencies": files,
            "observers": []
        })
        dir_to_watch = set()
        for file in files:
            dir_to_watch.add(path.dirname(path.expanduser(file)))
        for directory in dir_to_watch:
            if not path.exists(directory):
                continue
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
            class Handler(FileSystemEventHandler):
                def on_modified(self, event):
                    global flag
                    if flag:
                        return
                    flag = True
                    if event.is_directory:
                        return
                    for i in range(len(observers)):
                        if event.src_path in observers[i]["dependencies"]:
                            for observer in observers[i]["observers"]:
                                observer.stop()
                                # observer.join()
                            while 1:
                                try:
                                    files = convert_to_hyprlang(observers[i]["file"], alias)
                                    break
                                except Exception as e:
                                    send_notification(f"Error in {observers[i]['file']}: {e}.\nRETRY IN 10 sec", "critical")
                                    from time import sleep
                                    sleep(10)
                                    del sleep
                            observers[i]["dependencies"] = files
                            dir_to_watch = set()
                            for file in observers[i]["dependencies"]:
                                dir_to_watch.add(path.dirname(path.expanduser(file)))
                            for directory in dir_to_watch:
                                if not path.exists(directory):
                                    continue
                                observers[i]["observers"].append(Observer())
                                observers[i]["observers"][-1].schedule(Handler(), path=directory, recursive=False)
                                observers[i]["observers"][-1].start()
                    flag = False

                                
                                
            observers[-1]["observers"].append(Observer())
            observers[-1]["observers"][-1].schedule(Handler(), path=directory, recursive=False)
            observers[-1]["observers"][-1].start()

    from time import sleep
    sleep(10**9)
        """


if __name__ == "__main__":
    alias = {
        "exec_once": "exec-once",
        "input_field": "input-field",
    }
    import sys

    args = sys.argv[1:]
    del sys
    main(args, alias)
