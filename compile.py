import os
import re
import subprocess
from collections import defaultdict

IMPORT_WORDS = ("import", "from")

COMPILE_UI_FILES = True


def compile_ui_to_py(ui_path):
    py_file = os.path.splitext(ui_path)[0] + ".py"
    command = f"pyuic5 {ui_path} -o {py_file}"
    subprocess.run(command, shell=True)
    with open(py_file, encoding="utf-8") as p:
        data = p.readlines()
    os.remove(py_file)
    return data


def capitalise(string):
    if len(string) == 0:
        return string
    elif len(string) == 1:
        return string.upper()
    else:
        return string[0].upper() + string[1:]


def replace_whole_word(text, old_word, new_word):
    pattern = r'\b{}\b'.format(re.escape(old_word))
    replaced_text = re.sub(pattern, new_word, text)
    return replaced_text


def add_dependency(dependencies, module_a, module_b):
    dependencies[module_b].add(module_a)


def topological_sort(dependencies):
    visited = set()
    ordering = []

    def dfs(node):
        visited.add(node)
        for dependency in dependencies[node]:
            if dependency not in visited:
                dfs(dependency)
        ordering.append(node)

    for dep in list(dependencies):
        if dep not in visited:
            dfs(dep)

    return ordering


def determine_import_order(module_dependencies):
    dependencies = defaultdict(set)

    for dependency in module_dependencies:
        module_a, module_b = dependency
        add_dependency(dependencies, module_a, module_b)

    return topological_sort(dependencies)


def get_files_in_folder(folder, ext):
    """Recursively gets all Python files inside of folder"""
    pythonFiles = []

    for root, dirs, files in os.walk(folder):
        for p in files:
            if p.endswith(ext):
                pythonFiles.append(os.path.join(root, p))

    return pythonFiles


def import_divide_line_number(codeLines):
    """Determines which line the import statements end"""
    lineNo = 0
    for i, line in enumerate(codeLines, start=1):
        if len(line.split()) > 0 and line.split()[0] in IMPORT_WORDS:
            lineNo = i
    return lineNo


def simplify_imports(imports):
    """Removes unnecessary import statements"""
    simplified_imports = set()

    for import_line in imports:
        import_line = import_line.strip()

        # Skip empty lines and comments
        if not import_line or import_line.startswith('#'):
            continue

        # Skip imports of Python files
        if "modules." in import_line:
            continue

        # Add the import line to the set of simplified imports
        simplified_imports.add(import_line + "\n")

    return sorted(simplified_imports)


def get_module_name(text):
    """Extracts module name from string"""
    if "\\" in text:
        # File path
        return text.split("\\")[-1][:-3]
    elif "/" in text:
        return text.split("/")[-1][:-3]
    elif "modules." in text:
        # Code path
        return text.split()[1].split(".")[-1]
    else:
        return "main"


def find_internal_imports(codeLines, currentModule, order, directFuncs):
    """Finds Import Dependencies"""
    for line in codeLines:
        if "modules." in line:
            # Internal Import
            moduleName = get_module_name(line)
            # moduleName < currentModule
            order.append((moduleName, currentModule))

            # Check for direct imports
            if line[:4] == "from":
                funcs = [func.rstrip(",") for func in line.split()[3:] if func[0].isupper()]
                for func in funcs:
                    directFuncs.append((func, moduleName + func))
    return order, directFuncs


def rename_UI(moduleName, codeLines):
    for i, line in enumerate(codeLines):
        code = line.split()
        if len(code) > 0 and code[0] == "class":
            # Class Declaration Line
            codeLines[i] = f"class Ui_{capitalise(moduleName)}(object):\n"
    return codeLines

def get_class_name(line):
    i = line.find("(")
    if i == -1:
        i = line.find(":")
    return line[:i], line[i:]


def rename_classes(codeLines, moduleName):
    """Renames classes with duplicate names"""
    replacements = directImportsFunctions.copy()
    for i, line in enumerate(codeLines):
        code = line.split()
        if len(code) > 0 and code[0] == "class":
            # Class Declaration Line
            className, rest = get_class_name(code[1])
            replacements.append((className, moduleName + className))

            code[1] = moduleName + className + rest
            codeLines[i] = " ".join(code) + "\n"
        elif COMPILE_UI_FILES and len(code) > 0 and "uic.loadUi" in code[0]:
            # Compile .UI file
            uiName = get_module_name(code[0].split()[0].split("(")[1].rstrip(",").strip("\""))
            indent = len(line) - len(line.strip()) - 1
            codeLines[i] = f"{indent*' '}Ui_{capitalise(uiName)}().setupUi(self)\n"

    # Rename Classes
    for i, line in enumerate(codeLines):
        for mod in moduleNames:
            if f"{mod}." in line and ".ui" not in line:
                codeLines[i] = codeLines[i].replace(f"{mod}.", mod)

    # Replace Class Names
    for i, line in enumerate(codeLines):
        for replacement in replacements:
            old, new = replacement
            codeLines[i] = replace_whole_word(codeLines[i], old, new)

    return codeLines


modules = get_files_in_folder("modules", ".py") + ["main.py"]
moduleNames = [get_module_name(m) for m in modules]
directImportsFunctions = []
importOrder = []
importLines = set()
moduleContents = {}

for file in modules:
    with open(file, encoding="utf8") as f:
        lines = f.readlines()
        name = get_module_name(file)
        n = import_divide_line_number(lines)
        importLines = importLines.union(set(lines[:n]))
        importOrder, directImportsFunctions = \
            find_internal_imports(lines[:n], name, importOrder, directImportsFunctions)
        moduleContents[name] = rename_classes(lines[n:], name)

importLines = simplify_imports(importLines)

# Determine import order
importOrder = determine_import_order(importOrder)
for file in modules:
    module = get_module_name(file)
    if module not in importOrder:
        importOrder.append(module)

# Write compiled file
with open("compiledMain.pyw", "w", encoding="utf8") as f:
    f.writelines(importLines)

    if COMPILE_UI_FILES:
        # Compile .UI Files
        for file in get_files_in_folder("gui", ".ui"):
            contents = compile_ui_to_py(file)
            f.writelines(rename_UI(get_module_name(file), contents))

    for module in importOrder:
        f.writelines(moduleContents[module])
