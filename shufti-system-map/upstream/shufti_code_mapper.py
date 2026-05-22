#!/usr/bin/env python3
"""
Shufti code mapper for Python applications.

Features:
- map a single Python file or an application spanning directories/files
- emit a generated header with date, user, file count, line count, and stub count
- extract structure, dependencies, globals, locals, simple types, and call sites
- run heuristic pattern detection on top of the extracted structure

This tool is intentionally stdlib-only so it can run in an isolated venv
without external dependencies.
"""

from __future__ import annotations

import argparse
import ast
import getpass
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from shufti_code_topology import build_code_topology, write_code_topology
from shufti_diagram_theme import wrap_mermaid_diagram

FILESYSTEM_DIAGRAM_SKIP = frozenset({
    "dependency_graph",
    "class_map",
    "pattern_map",
    "single_file_map",
    "interaction_map",
})
PATTERN_CODES = {
    "facade": "FAC",
    "adapter": "ADP",
    "state_machine": "SM",
    "event_registry": "REG",
    "dispatcher": "DIS",
    "token_bucket": "TB",
    "hash_algorithm": "HASH",
}
STUB_PATTERN = re.compile(r"\b(todo|tbd|stub|stubb|fixme|xxx)\b", re.IGNORECASE)
DEFAULT_MAX_FILES = 250
DEFAULT_MAX_LINES = 100_000
DEFAULT_MAX_FILE_BYTES = 1_000_000
IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".venv-tests",
    ".venv-tdd",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "site-packages",
    "dist",
    "build",
    "htmlcov",

}
IP_HEADER = {
    "document_id": "SPEC-SELDER-DOCUMENT-STANDARD",
    "author": "Samuel Elder",
    "version": "1.0.0",
    "ip_notice": "IP Notice: © 2026 Samuel Elder, Revolution Lifecycle. All rights reserved. The LightSpeed Engine is proprietary."
}
LOG = logging.getLogger("shufti_code_mapper")
CLASS_DIAGRAM_MAX_CLASSES = 80
INTERACTION_MAX_NODES = 180
INTERACTION_MAX_EDGES = 350
MERMAID_TEXT_LIMIT_CHARS = 48_000


@dataclass
class VariableRecord:
    name: str
    line: int
    inferred_type: str
    annotation: Optional[str] = None
    value_preview: Optional[str] = None


@dataclass
class ImportRecord:
    line: int
    kind: str
    module: str
    names: list[str]
    level: int = 0
    resolved_local_targets: list[str] = field(default_factory=list)


@dataclass
class FunctionRecord:
    qualified_name: str
    signature: str
    start_line: int
    end_line: int
    decorators: list[str]
    locals: list[VariableRecord]
    calls: list[str]
    returns: Optional[str]
    is_async: bool


@dataclass
class ClassRecord:
    qualified_name: str
    signature: str
    start_line: int
    end_line: int
    bases: list[str]
    class_variables: list[VariableRecord]
    instance_variables: list[VariableRecord]
    methods: list[FunctionRecord]


@dataclass
class PatternRecord:
    name: str
    confidence: str
    evidence: list[str]


@dataclass
class FileAnalysis:
    path: str
    module_name: str
    line_count: int
    stub_count: int
    stub_lines: list[int]
    imports: list[ImportRecord]
    globals: list[VariableRecord]
    functions: list[FunctionRecord]
    classes: list[ClassRecord]
    patterns: list[PatternRecord]
    direct_dependency_paths: list[str]


@dataclass
class ReportHeader:
    generated_at_utc: str
    user: str
    mode: str
    files_included: int
    lines_reviewed: int
    stubs_detected: int
    analysis_errors: int
    targets: list[str]


@dataclass
class DiagramArtifact:
    name: str
    kind: str
    format: str
    path: str
    description: str


def iter_python_files(targets: Iterable[str], mode: str, max_files: int) -> list[Path]:
    files: list[Path] = []
    for raw_target in targets:
        path = Path(raw_target).resolve()
        if not path.exists():
            raise FileNotFoundError(f"target does not exist: {raw_target}")
        if path.is_file():
            if path.suffix != ".py":
                raise ValueError(f"only Python files are supported: {raw_target}")
            files.append(path)
            if mode == "file":
                files.extend(expand_direct_dependency_paths(path))
            enforce_file_limit(files, max_files)
            continue
        if mode == "file":
            raise ValueError(f"directory target not allowed in file mode: {raw_target}")
        files.extend(walk_python_files(path, max_files=max_files, existing_count=len(files)))
        enforce_file_limit(files, max_files)
    deduped = sorted({file.resolve() for file in files})
    if not deduped:
        raise ValueError("no Python files found in target scope")
    enforce_file_limit(deduped, max_files)
    return deduped


def enforce_file_limit(files: list[Path], max_files: int) -> None:
    if max_files > 0 and len(files) > max_files:
        raise ValueError(
            f"target scope resolved to {len(files)} Python files, which exceeds the limit of {max_files}; "
            "narrow the target scope or raise --max-files explicitly"
        )


def walk_python_files(root: Path, max_files: int, existing_count: int) -> list[Path]:
    files: list[Path] = []
    remaining_limit = max_files - existing_count if max_files > 0 else max_files
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in IGNORED_DIR_NAMES and not name.endswith(".egg-info")
        )
        current_path = Path(current_root)
        for filename in sorted(filenames):
            if filename.endswith(".py"):
                files.append(current_path / filename)
                enforce_file_limit(files, remaining_limit)
    return files


def expand_direct_dependency_paths(entry_file: Path) -> list[Path]:
    try:
        source = entry_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(entry_file))
    except Exception:
        return []

    results: list[Path] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = resolve_import_module_path(entry_file, alias.name, level=0)
                if resolved is not None:
                    results.append(resolved)
        elif isinstance(node, ast.ImportFrom):
            base_module = node.module or ""
            resolved_base = resolve_import_module_path(entry_file, base_module, level=node.level)
            if resolved_base is not None:
                results.append(resolved_base)
            for alias in node.names:
                nested_module = f"{base_module}.{alias.name}" if base_module else alias.name
                resolved_nested = resolve_import_module_path(entry_file, nested_module, level=node.level)
                if resolved_nested is not None:
                    results.append(resolved_nested)
    return sorted({path.resolve() for path in results if path.resolve() != entry_file.resolve()})


def resolve_import_module_path(entry_file: Path, module_name: str, level: int) -> Optional[Path]:
    if level > 0:
        base_dir = entry_file.parent
        for _ in range(max(level - 1, 0)):
            base_dir = base_dir.parent
        return module_name_to_path(base_dir, module_name)

    if not module_name:
        return None
    top_level = module_name.split(".")[0]
    search_root = None
    for ancestor in [entry_file.parent, *entry_file.parents]:
        if (ancestor / top_level).exists():
            search_root = ancestor
            break
    if search_root is None:
        return None
    return module_name_to_path(search_root, module_name)


def module_name_to_path(search_root: Path, module_name: str) -> Optional[Path]:
    parts = [part for part in module_name.split(".") if part]
    if not parts:
        return None
    base = search_root.joinpath(*parts)
    module_file = base.with_suffix(".py")
    if module_file.exists() and module_file.is_file():
        return module_file.resolve()
    init_file = base / "__init__.py"
    if init_file.exists() and init_file.is_file():
        return init_file.resolve()
    return None


def choose_mode(mode: str, resolved_files: list[Path], raw_targets: list[str]) -> str:
    if mode != "auto":
        return mode
    if len(resolved_files) == 1 and len(raw_targets) == 1 and Path(raw_targets[0]).resolve().is_file():
        return "file"
    return "app"


def derive_analysis_root(files: list[Path]) -> Path:
    common = Path(os.path.commonpath([str(path) for path in files]))
    if common.is_file():
        return common.parent
    return common


def module_name_for(path: Path, analysis_root: Path) -> str:
    relative = path.relative_to(analysis_root)
    parts = list(relative.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
        if not parts:
            return path.parent.name
    else:
        parts[-1] = path.stem
    return ".".join(part for part in parts if part)


def infer_value_type(node: ast.AST | None) -> str:
    if node is None:
        return "unknown"
    if isinstance(node, ast.Constant):
        if node.value is None:
            return "None"
        return type(node.value).__name__
    if isinstance(node, ast.List):
        return "list"
    if isinstance(node, ast.Tuple):
        return "tuple"
    if isinstance(node, ast.Set):
        return "set"
    if isinstance(node, ast.Dict):
        return "dict"
    if isinstance(node, ast.ListComp):
        return "list"
    if isinstance(node, ast.DictComp):
        return "dict"
    if isinstance(node, ast.SetComp):
        return "set"
    if isinstance(node, ast.GeneratorExp):
        return "generator"
    if isinstance(node, ast.Lambda):
        return "callable"
    if isinstance(node, ast.JoinedStr):
        return "str"
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return "call_result"
    if isinstance(node, ast.Await):
        return f"await[{infer_value_type(node.value)}]"
    if isinstance(node, ast.UnaryOp):
        return infer_value_type(node.operand)
    if isinstance(node, ast.BinOp):
        return infer_value_type(node.left)
    if isinstance(node, ast.Name):
        return f"ref:{node.id}"
    return node.__class__.__name__


def preview_expr(node: ast.AST | None) -> Optional[str]:
    if node is None:
        return None
    try:
        text = ast.unparse(node)
    except Exception:
        return None
    text = " ".join(text.split())
    return text[:120] + ("..." if len(text) > 120 else "")


def target_names(node: ast.AST) -> list[tuple[str, int]]:
    results: list[tuple[str, int]] = []
    if isinstance(node, ast.Name):
        results.append((node.id, node.lineno))
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            results.extend(target_names(elt))
    return results


def format_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[str]:
    decorators: list[str] = []
    for decorator in node.decorator_list:
        try:
            decorators.append(ast.unparse(decorator))
        except Exception:
            decorators.append("<decorator>")
    return decorators


def format_arguments(args: ast.arguments) -> str:
    parts: list[str] = []
    positional = [*args.posonlyargs, *args.args]
    positional_defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)

    for index, arg in enumerate(args.posonlyargs):
        parts.append(format_arg(arg, positional_defaults[index]))
    if args.posonlyargs:
        parts.append("/")

    for index, arg in enumerate(args.args, start=len(args.posonlyargs)):
        parts.append(format_arg(arg, positional_defaults[index]))

    if args.vararg is not None:
        parts.append(format_star_arg(args.vararg))
    elif args.kwonlyargs:
        parts.append("*")

    for kwarg, default in zip(args.kwonlyargs, args.kw_defaults):
        parts.append(format_arg(kwarg, default))

    if args.kwarg is not None:
        parts.append(format_star_kwarg(args.kwarg))

    return ", ".join(parts)


def format_arg(arg: ast.arg, default: ast.expr | None) -> str:
    chunk = arg.arg
    if arg.annotation is not None:
        chunk += f": {ast.unparse(arg.annotation)}"
    if default is not None:
        chunk += f" = {ast.unparse(default)}"
    return chunk


def format_star_arg(arg: ast.arg) -> str:
    chunk = f"*{arg.arg}"
    if arg.annotation is not None:
        chunk += f": {ast.unparse(arg.annotation)}"
    return chunk


def format_star_kwarg(arg: ast.arg) -> str:
    chunk = f"**{arg.arg}"
    if arg.annotation is not None:
        chunk += f": {ast.unparse(arg.annotation)}"
    return chunk


def function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}({format_arguments(node.args)}){returns}:"


def class_signature(node: ast.ClassDef) -> str:
    bases = [ast.unparse(base) for base in node.bases]
    keywords = []
    for keyword in node.keywords:
        if keyword.arg is None:
            keywords.append(f"**{ast.unparse(keyword.value)}")
        else:
            keywords.append(f"{keyword.arg}={ast.unparse(keyword.value)}")
    items = [*bases, *keywords]
    if items:
        return f"class {node.name}({', '.join(items)}):"
    return f"class {node.name}:"


class FunctionBodyAnalyzer(ast.NodeVisitor):
    def __init__(self, class_name: str | None = None) -> None:
        self.class_name = class_name
        self.locals: dict[str, VariableRecord] = {}
        self.instance_variables: dict[str, VariableRecord] = {}
        self.calls: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_Assign(self, node: ast.Assign) -> None:
        inferred = infer_value_type(node.value)
        preview = preview_expr(node.value)
        for target in node.targets:
            self._record_target(target, inferred, None, preview)
        self.generic_visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        annotation = ast.unparse(node.annotation) if node.annotation is not None else None
        inferred = annotation or infer_value_type(node.value)
        preview = preview_expr(node.value)
        self._record_target(node.target, inferred, annotation, preview)
        if node.value is not None:
            self.generic_visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._record_target(node.target, "augmented", None, None)
        self.generic_visit(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        try:
            self.calls.append(ast.unparse(node.func))
        except Exception:
            self.calls.append("<call>")
        self.generic_visit(node)

    def _record_target(
        self,
        target: ast.AST,
        inferred_type: str,
        annotation: Optional[str],
        preview: Optional[str],
    ) -> None:
        if isinstance(target, ast.Name):
            self.locals[target.id] = VariableRecord(
                name=target.id,
                line=target.lineno,
                inferred_type=inferred_type,
                annotation=annotation,
                value_preview=preview,
            )
            return
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
            self.instance_variables[target.attr] = VariableRecord(
                name=target.attr,
                line=target.lineno,
                inferred_type=inferred_type,
                annotation=annotation,
                value_preview=preview,
            )
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._record_target(elt, inferred_type, annotation, preview)


class FileAnalyzer:
    def __init__(self, path: Path, analysis_root: Path, max_file_bytes: int) -> None:
        self.path = path
        self.analysis_root = analysis_root
        file_size = path.stat().st_size
        if max_file_bytes > 0 and file_size > max_file_bytes:
            raise ValueError(
                f"file exceeds byte limit ({file_size} > {max_file_bytes}): {path}"
            )
        self.source = path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source, filename=str(path))
        self.module_name = module_name_for(path, analysis_root)
        self.line_count = len(self.source.splitlines())
        self.stub_lines = [
            index
            for index, line in enumerate(self.source.splitlines(), start=1)
            if STUB_PATTERN.search(line)
        ]

    def analyze(self) -> FileAnalysis:
        imports: list[ImportRecord] = []
        globals_found: list[VariableRecord] = []
        functions: list[FunctionRecord] = []
        classes: list[ClassRecord] = []

        for node in self.tree.body:
            if isinstance(node, ast.Import):
                imports.append(
                    ImportRecord(
                        line=node.lineno,
                        kind="import",
                        module="",
                        names=[alias.name for alias in node.names],
                    )
                )
            elif isinstance(node, ast.ImportFrom):
                imports.append(
                    ImportRecord(
                        line=node.lineno,
                        kind="from",
                        module=node.module or "",
                        names=[alias.name for alias in node.names],
                        level=node.level,
                    )
                )
            elif isinstance(node, ast.Assign):
                globals_found.extend(self._module_assignments(node))
            elif isinstance(node, ast.AnnAssign):
                globals_found.extend(self._module_ann_assignments(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._function_record(node, qual_prefix=None))
            elif isinstance(node, ast.ClassDef):
                classes.append(self._class_record(node))

        analysis = FileAnalysis(
            path=str(self.path),
            module_name=self.module_name,
            line_count=self.line_count,
            stub_count=len(self.stub_lines),
            stub_lines=self.stub_lines,
            imports=imports,
            globals=sorted(globals_found, key=lambda item: (item.line, item.name)),
            functions=functions,
            classes=classes,
            patterns=[],
            direct_dependency_paths=[str(path) for path in expand_direct_dependency_paths(self.path)],
        )
        analysis.patterns = detect_patterns(analysis)
        return analysis

    def _module_assignments(self, node: ast.Assign) -> list[VariableRecord]:
        inferred = infer_value_type(node.value)
        preview = preview_expr(node.value)
        records: list[VariableRecord] = []
        for target in node.targets:
            for name, line in target_names(target):
                records.append(
                    VariableRecord(
                        name=name,
                        line=line,
                        inferred_type=inferred,
                        value_preview=preview,
                    )
                )
        return records

    def _module_ann_assignments(self, node: ast.AnnAssign) -> list[VariableRecord]:
        annotation = ast.unparse(node.annotation) if node.annotation is not None else None
        inferred = annotation or infer_value_type(node.value)
        preview = preview_expr(node.value)
        records: list[VariableRecord] = []
        for name, line in target_names(node.target):
            records.append(
                VariableRecord(
                    name=name,
                    line=line,
                    inferred_type=inferred,
                    annotation=annotation,
                    value_preview=preview,
                )
            )
        return records

    def _function_record(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        qual_prefix: Optional[str],
    ) -> FunctionRecord:
        analyzer = FunctionBodyAnalyzer(class_name=qual_prefix)
        for statement in node.body:
            analyzer.visit(statement)
        qualified_name = node.name if not qual_prefix else f"{qual_prefix}.{node.name}"
        returns = ast.unparse(node.returns) if node.returns is not None else None
        return FunctionRecord(
            qualified_name=qualified_name,
            signature=function_signature(node),
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            decorators=format_decorators(node),
            locals=sorted(analyzer.locals.values(), key=lambda item: (item.line, item.name)),
            calls=sorted(dict.fromkeys(analyzer.calls)),
            returns=returns,
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )

    def _class_record(self, node: ast.ClassDef) -> ClassRecord:
        class_vars: list[VariableRecord] = []
        instance_vars: dict[str, VariableRecord] = {}
        methods: list[FunctionRecord] = []
        for statement in node.body:
            if isinstance(statement, ast.Assign):
                class_vars.extend(self._module_assignments(statement))
            elif isinstance(statement, ast.AnnAssign):
                class_vars.extend(self._module_ann_assignments(statement))
            elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_record = self._function_record(statement, qual_prefix=node.name)
                methods.append(method_record)
                method_analyzer = FunctionBodyAnalyzer(class_name=node.name)
                for method_statement in statement.body:
                    method_analyzer.visit(method_statement)
                for key, value in method_analyzer.instance_variables.items():
                    if key not in instance_vars:
                        instance_vars[key] = value
        return ClassRecord(
            qualified_name=node.name,
            signature=class_signature(node),
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            bases=[ast.unparse(base) for base in node.bases],
            class_variables=sorted(class_vars, key=lambda item: (item.line, item.name)),
            instance_variables=sorted(instance_vars.values(), key=lambda item: (item.line, item.name)),
            methods=methods,
        )


def resolve_local_imports(files: list[FileAnalysis]) -> dict[str, str]:
    return {file.module_name: file.path for file in files if file.module_name}


def qualify_relative_import(current_module: str, level: int, module: str) -> str:
    if not current_module:
        return module
    package_parts = current_module.split(".")[:-1]
    if level > 0:
        keep = max(0, len(package_parts) - (level - 1))
        package_parts = package_parts[:keep]
    parts = [*package_parts]
    if module:
        parts.extend(module.split("."))
    return ".".join(part for part in parts if part)


def build_path_module_index(files: list[FileAnalysis], analysis_root: Path) -> dict[str, str]:
    """Map dotted path suffixes and relative paths to module_name for import resolution."""
    index: dict[str, str] = {}
    root = analysis_root.resolve()
    for file in files:
        if not file.module_name:
            continue
        try:
            rel = Path(file.path).resolve().relative_to(root).as_posix()
        except ValueError:
            rel = Path(file.path).name
        index[rel] = file.module_name
        stem = rel[:-3] if rel.endswith(".py") else rel
        if stem:
            index[stem.replace("/", ".")] = file.module_name
        parts = stem.split("/")
        for idx in range(len(parts)):
            suffix = ".".join(parts[idx:])
            if suffix:
                index[suffix] = file.module_name
    return index


def annotate_import_resolution(files: list[FileAnalysis], analysis_root: Path | None = None) -> None:
    module_map = resolve_local_imports(files)
    module_names = sorted(module_map)
    path_index: dict[str, str] = {}
    if files and analysis_root is not None:
        path_index = build_path_module_index(files, analysis_root)
    for file in files:
        for record in file.imports:
            candidates: list[str] = []
            if record.kind == "import":
                for name in record.names:
                    candidates.extend(resolve_candidate_modules(name, module_names, path_index))
            else:
                base = qualify_relative_import(file.module_name, record.level, record.module)
                candidates.extend(resolve_candidate_modules(base, module_names, path_index))
                for name in record.names:
                    candidates.extend(resolve_candidate_modules(f"{base}.{name}" if base else name, module_names, path_index))
            record.resolved_local_targets = sorted(dict.fromkeys(candidates))


def resolve_candidate_modules(
    name: str,
    module_names: list[str],
    path_index: dict[str, str] | None = None,
) -> list[str]:
    results: list[str] = []
    if not name:
        return results
    seen: set[str] = set()
    for module_name in module_names:
        if module_name == name or module_name.startswith(f"{name}.") or name.startswith(f"{module_name}."):
            if module_name not in seen:
                seen.add(module_name)
                results.append(module_name)
    if path_index:
        dotted = name.replace("/", ".")
        for key, module_name in path_index.items():
            if module_name in seen:
                continue
            if key == dotted or key.endswith(f".{dotted}") or dotted.endswith(key):
                seen.add(module_name)
                results.append(module_name)
    return results


def detect_patterns(file: FileAnalysis) -> list[PatternRecord]:
    patterns: list[PatternRecord] = []
    for class_record in file.classes:
        lower_name = class_record.qualified_name.lower()
        method_names = {method.qualified_name.split(".")[-1] for method in class_record.methods}
        evidence: list[str] = []

        if "facade" in lower_name:
            evidence.append(
                f"{class_record.qualified_name} {class_record.start_line}:{class_record.end_line} name contains 'Facade'"
            )
        if {"handle_chat_completions", "_route_to_agent"} & method_names and any(
            "connect" in method.qualified_name.lower() for method in class_record.methods
        ):
            evidence.append(
                f"{class_record.qualified_name} exposes request handlers and downstream connection methods"
            )
        if evidence:
            patterns.append(PatternRecord(name="Facade/Adapter", confidence="high", evidence=evidence))

        state_evidence: list[str] = []
        if any("state" in variable.name or "status" in variable.name for variable in class_record.instance_variables):
            state_evidence.append(
                f"{class_record.qualified_name} stores state/status-bearing instance variables"
            )
        if any("transition" in method.qualified_name.lower() for method in class_record.methods):
            state_evidence.append(
                f"{class_record.qualified_name} defines transition methods"
            )
        if state_evidence:
            patterns.append(PatternRecord(name="State Machine", confidence="medium", evidence=state_evidence))

    setup_functions = [
        function
        for function in (
            file.functions + [method for class_record in file.classes for method in class_record.methods]
        )
        if function.qualified_name.endswith("_setup_events")
    ]
    for function in setup_functions:
        evidence = [f"{function.qualified_name} {function.start_line}:{function.end_line} wires event handlers"]
        patterns.append(PatternRecord(name="Event Handler Registry", confidence="high", evidence=evidence))

    for function in file.functions + [method for cls in file.classes for method in cls.methods]:
        evidence: list[str] = []
        call_blob = " ".join(function.calls).lower()
        if "hashlib" in call_blob or "sha256" in call_blob or "hash" in function.qualified_name.lower():
            evidence.append(f"{function.qualified_name} uses hashing-oriented calls")
            patterns.append(PatternRecord(name="Fingerprint Hashing", confidence="medium", evidence=evidence))
        if "tokens" in call_blob and "time" in call_blob:
            patterns.append(
                PatternRecord(
                    name="Token Bucket / Rate Limiter",
                    confidence="medium",
                    evidence=[f"{function.qualified_name} manipulates token-like state and time"],
                )
            )
    return dedupe_patterns(patterns)

PATTERN_NAME_TO_KEY = {
    "Facade/Adapter": "facade",
    "State Machine": "state_machine",
    "Event Handler Registry": "event_registry",
    "Fingerprint Hashing": "hash_algorithm",
    "Token Bucket / Rate Limiter": "token_bucket",
}


def pattern_tag(patterns: list[PatternRecord], symbol_name: str) -> str:
    for p in patterns:
        symbols = {ev.split()[0] for ev in p.evidence if ev}
        if symbol_name in symbols and p.confidence in ("medium", "high"):
            code = PATTERN_CODES.get(PATTERN_NAME_TO_KEY.get(p.name, ""), "")
            if code:
                return f"<<{code}>>"
    return ""

def dedupe_patterns(patterns: list[PatternRecord]) -> list[PatternRecord]:
    merged: dict[tuple[str, str], PatternRecord] = {}
    for pattern in patterns:
        key = (pattern.name, pattern.confidence)
        if key not in merged:
            merged[key] = PatternRecord(pattern.name, pattern.confidence, list(pattern.evidence))
            continue
        for evidence in pattern.evidence:
            if evidence not in merged[key].evidence:
                merged[key].evidence.append(evidence)
    return list(merged.values())


def aggregate_patterns(files: list[FileAnalysis]) -> list[PatternRecord]:
    patterns: list[PatternRecord] = []
    for file in files:
        patterns.extend(file.patterns)
    return dedupe_patterns(patterns)


def build_header(
    mode: str,
    targets: list[str],
    files: list[FileAnalysis],
    analysis_errors: list[str],
) -> ReportHeader:
    return ReportHeader(
        generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        user=getpass.getuser(),
        mode=mode,
        files_included=len(files),
        lines_reviewed=sum(file.line_count for file in files),
        stubs_detected=sum(file.stub_count for file in files),
        analysis_errors=len(analysis_errors),
        targets=targets,
    )


def render_markdown(header: ReportHeader, files: list[FileAnalysis], analysis_errors: list[str]) -> str:
    local_edges = collect_dependency_edges(files)
    external_imports = collect_external_imports(files)
    app_patterns = aggregate_patterns(files)

    lines: list[str] = []
    lines.append("# Shufti Code Map")
    lines.append("")
    lines.append("## Header")
    lines.append("")
    lines.append(f"- Date: `{header.generated_at_utc}`")
    lines.append(f"- User: `{header.user}`")
    lines.append(f"- Mode: `{header.mode}`")
    lines.append(f"- Files included: `{header.files_included}`")
    lines.append(f"- Lines reviewed: `{header.lines_reviewed}`")
    lines.append(f"- Stubs detected: `{header.stubs_detected}`")
    lines.append(f"- Analysis errors: `{header.analysis_errors}`")
    lines.append(f"- Targets: `{', '.join(header.targets)}`")
    lines.append("")

    if analysis_errors:
        lines.append("## Analysis Warnings")
        lines.append("")
        for error in analysis_errors:
            lines.append(f"- {error}")
        lines.append("")

    lines.append("## Application Shape")
    lines.append("")
    lines.append(f"- Local dependency edges: `{len(local_edges)}`")
    lines.append(f"- External import roots: `{len(external_imports)}`")
    lines.append(f"- Application-level pattern signals: `{len(app_patterns)}`")
    if app_patterns:
        for pattern in app_patterns:
            lines.append(f"- Pattern: `{pattern.name}` confidence=`{pattern.confidence}`")
            for evidence in pattern.evidence:
                lines.append(f"  Evidence: {evidence}")
    lines.append("")

    lines.append("## Dependency Edges")
    lines.append("")
    if local_edges:
        for src, dst in local_edges:
            lines.append(f"- `{src}` -> `{dst}`")
    else:
        lines.append("- No local dependency edges detected in the included scope.")
    lines.append("")

    lines.append("## Files")
    lines.append("")
    for file in files:
        lines.append(f"### `{file.path}`")
        lines.append("")
        lines.append(f"- Module: `{file.module_name or '<root>'}`")
        lines.append(f"- Lines: `{file.line_count}`")
        lines.append(f"- Stubs: `{file.stub_count}`")
        if file.stub_lines:
            lines.append(f"- Stub lines: `{', '.join(str(line) for line in file.stub_lines[:50])}`")
        lines.append("")

        local_imports = sorted({target for item in file.imports for target in item.resolved_local_targets})
        external_roots = sorted(
            {
                (item.module if item.kind == "from" else name).split(".")[0]
                for item in file.imports
                for name in (item.names if item.kind == "import" else [item.module or ""])
                if name and not item.resolved_local_targets
            }
        )
        lines.append("- Dependencies:")
        lines.append(f"  Local: `{', '.join(local_imports) if local_imports else 'none'}`")
        lines.append(f"  External: `{', '.join(external_roots) if external_roots else 'none'}`")
        lines.append("")

        lines.append("- Globals:")
        if file.globals:
            for variable in file.globals:
                annotation = f" annotation=`{variable.annotation}`" if variable.annotation else ""
                preview = f" value=`{variable.value_preview}`" if variable.value_preview else ""
                lines.append(
                    f"  - `{variable.name}` line `{variable.line}` type=`{variable.inferred_type}`{annotation}{preview}"
                )
        else:
            lines.append("  - none")
        lines.append("")

        lines.append("- Functions:")
        if file.functions:
            for function in file.functions:
                lines.append(
                    f"  - `{function.qualified_name}` `{function.signature}` `{function.start_line}:{function.end_line}`"
                )
                lines.append(
                    f"    Returns: `{function.returns or 'unknown'}` async=`{str(function.is_async).lower()}`"
                )
                lines.append(
                    f"    Locals: `{', '.join(f'{item.name}:{item.inferred_type}' for item in function.locals) or 'none'}`"
                )
                lines.append(f"    Calls: `{', '.join(function.calls) if function.calls else 'none'}`")
        else:
            lines.append("  - none")
        lines.append("")

        lines.append("- Classes:")
        if file.classes:
            for class_record in file.classes:
                lines.append(
                    f"  - `{class_record.qualified_name}` `{class_record.signature}` `{class_record.start_line}:{class_record.end_line}`"
                )
                lines.append(
                    f"    Bases: `{', '.join(class_record.bases) if class_record.bases else 'none'}`"
                )
                lines.append(
                    f"    Class vars: `{', '.join(f'{item.name}:{item.inferred_type}' for item in class_record.class_variables) or 'none'}`"
                )
                lines.append(
                    f"    Instance vars: `{', '.join(f'{item.name}:{item.inferred_type}' for item in class_record.instance_variables) or 'none'}`"
                )
                for method in class_record.methods:
                    lines.append(
                        f"    Method: `{method.qualified_name}` `{method.signature}` `{method.start_line}:{method.end_line}`"
                    )
                    lines.append(
                        f"    Method locals: `{', '.join(f'{item.name}:{item.inferred_type}' for item in method.locals) or 'none'}`"
                    )
                    lines.append(f"    Method calls: `{', '.join(method.calls) if method.calls else 'none'}`")
        else:
            lines.append("  - none")
        lines.append("")

        lines.append("- Pattern signals:")
        if file.patterns:
            for pattern in file.patterns:
                lines.append(f"  - `{pattern.name}` confidence=`{pattern.confidence}`")
                for evidence in pattern.evidence:
                    lines.append(f"    Evidence: {evidence}")
        else:
            lines.append("  - none")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_json(header: ReportHeader, files: list[FileAnalysis], analysis_errors: list[str]) -> str:
    payload = {
        **IP_HEADER,
        "header": asdict(header),
        "dependency_edges": collect_dependency_edges(files),
        "external_import_roots": collect_external_imports(files),
        "patterns": [asdict(pattern) for pattern in aggregate_patterns(files)],
        "analysis_errors": analysis_errors,
        "files": [asdict(file) for file in files],
    }
    return json.dumps(payload, indent=2) + "\n"


def configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )


def dot_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def mermaid_safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value) or "node"


def dependency_module_sets(
    files: list[FileAnalysis],
    edges: list[tuple[str, str]],
) -> tuple[list[str], list[str]]:
    """Split modules into edge-connected vs orphan (no resolved import edge)."""
    all_modules = sorted({file.module_name or file.path for file in files})
    if not edges:
        return [], all_modules
    connected: set[str] = set()
    for src, dst in edges:
        connected.add(src)
        connected.add(dst)
    primary = sorted(module for module in all_modules if module in connected)
    orphans = sorted(module for module in all_modules if module not in connected)
    return primary, orphans


def render_dependency_dot(files: list[FileAnalysis]) -> str:
    edges = collect_dependency_edges(files)
    primary, orphans = dependency_module_sets(files, edges)
    lines = ["digraph dependency_graph {", '  rankdir="LR";', '  node [shape="box"];']
    for module in primary:
        lines.append(f"  {dot_quote(module)};")
    for src, dst in edges:
        lines.append(f"  {dot_quote(src)} -> {dot_quote(dst)};")
    if orphans:
        lines.append('  subgraph cluster_orphans {')
        lines.append('    label="Unlinked modules (no resolved local import edge)";')
        lines.append('    style="dashed";')
        for module in orphans:
            lines.append(f"    {dot_quote(module)};")
        lines.append("  }")
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_dependency_mermaid(files: list[FileAnalysis]) -> str:
    edges = collect_dependency_edges(files)
    primary, orphans = dependency_module_sets(files, edges)
    lines = ["flowchart LR"]
    for module in primary:
        lines.append(f'  {mermaid_safe_id(module)}["{module}"]')
    for src, dst in edges:
        lines.append(f"  {mermaid_safe_id(src)} --> {mermaid_safe_id(dst)}")
    if orphans:
        lines.append('  subgraph orphans["Unlinked modules"]')
        for module in orphans:
            lines.append(f'    {mermaid_safe_id(module)}["{module}"]')
        lines.append("  end")
    return "\n".join(lines) + "\n"


def iter_class_records(files: list[FileAnalysis]) -> list[tuple[FileAnalysis, ClassRecord]]:
    records: list[tuple[FileAnalysis, object]] = []
    for file in files:
        for class_record in file.classes:
            records.append((file, class_record))
    return records


def render_class_dot(files: list[FileAnalysis]) -> str:
    class_records = iter_class_records(files)
    truncated = len(class_records) > CLASS_DIAGRAM_MAX_CLASSES
    if truncated:
        class_records = class_records[:CLASS_DIAGRAM_MAX_CLASSES]
    lines = ["digraph class_map {", '  rankdir="LR";', '  node [shape="record"];']
    if truncated:
        lines.append(
            f'  label="Showing first {CLASS_DIAGRAM_MAX_CLASSES} of '
            f'{len(iter_class_records(files))} classes";'
        )
    for file, class_record in class_records:
        module_name = file.module_name or Path(file.path).stem
        label = f"{class_record.qualified_name}|{module_name}"
        lines.append(f"  {dot_quote(class_record.qualified_name)} [label={dot_quote(label)}];")
        for base in class_record.bases:
            lines.append(
                f"  {dot_quote(class_record.qualified_name)} -> {dot_quote(base)} "
                f'[label="inherits", style="dashed"];'
            )
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_class_mermaid(files: list[FileAnalysis]) -> str:
    class_records = iter_class_records(files)
    truncated = len(class_records) > CLASS_DIAGRAM_MAX_CLASSES
    if truncated:
        class_records = class_records[:CLASS_DIAGRAM_MAX_CLASSES]
    lines = ["classDiagram"]
    if truncated:
        lines.append(
            f"  %% Showing first {CLASS_DIAGRAM_MAX_CLASSES} of "
            f"{len(iter_class_records(files))} classes"
        )
    seen: set[str] = set()
    for _file, class_record in class_records:
        if class_record.qualified_name not in seen:
            lines.append(f"  class {mermaid_safe_id(class_record.qualified_name)}")
            seen.add(class_record.qualified_name)
        for base in class_record.bases:
            lines.append(
                f"  {mermaid_safe_id(base)} <|-- {mermaid_safe_id(class_record.qualified_name)}"
            )
    return "\n".join(lines) + "\n"


def render_pattern_dot(files: list[FileAnalysis]) -> str:
    lines = ["digraph pattern_map {", '  rankdir="LR";', '  node [shape="ellipse"];']
    pattern_to_symbols: dict[str, set[str]] = {}
    for file in files:
        for pattern in file.patterns:
            symbols = pattern_to_symbols.setdefault(f"{pattern.name} ({pattern.confidence})", set())
            for evidence in pattern.evidence:
                symbol = evidence.split(" ")[0]
                symbols.add(symbol)
    for pattern_name, symbols in sorted(pattern_to_symbols.items()):
        lines.append(f"  {dot_quote(pattern_name)} [shape=\"diamond\"];")
        for symbol in sorted(symbols):
            lines.append(f"  {dot_quote(symbol)} [shape=\"box\"];")
            lines.append(f"  {dot_quote(pattern_name)} -> {dot_quote(symbol)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_pattern_mermaid(files: list[FileAnalysis]) -> str:
    lines = ["flowchart LR"]
    pattern_to_symbols: dict[str, set[str]] = {}
    for file in files:
        for pattern in file.patterns:
            symbols = pattern_to_symbols.setdefault(f"{pattern.name} ({pattern.confidence})", set())
            for evidence in pattern.evidence:
                symbol = evidence.split(" ")[0]
                symbols.add(symbol)
    for pattern_name, symbols in sorted(pattern_to_symbols.items()):
        pattern_id = mermaid_safe_id(f"pattern_{pattern_name}")
        lines.append(f'  {pattern_id}{{"{pattern_name}"}}')
        for symbol in sorted(symbols):
            symbol_id = mermaid_safe_id(f"symbol_{symbol}")
            lines.append(f'  {symbol_id}["{symbol}"]')
            lines.append(f"  {pattern_id} --> {symbol_id}")
    return "\n".join(lines) + "\n"
# --- SINGLE FILE MERMAID GRAPH ---

def render_single_file_mermaid(
    file: FileAnalysis,
    patterns: list[PatternRecord],
    all_files: list[FileAnalysis] | None = None,
) -> str:
    lines: list[str] = []
    nodes: dict[str, str] = {}
    external_calls: set[str] = set()
    safe_module = mermaid_safe_id(file.module_name or Path(file.path).stem)

    lines.append("flowchart LR")
    lines.append("")

    # --- module subgraph ---
    lines.append(f"subgraph {safe_module}[\"{file.module_name}\"]")
    lines.append("  direction TB")

    # globals
    if file.globals:
        lines.append(f"  subgraph {safe_module}_globals[\"Globals\"]")
        lines.append("    direction LR")
        for g in file.globals:
            nid = mermaid_safe_id(f"g_{g.name}")
            nodes[g.name] = nid
            lines.append(f'    {nid}(["{g.name}: {g.inferred_type}"])')
        lines.append("  end")

    # classes
    for c in file.classes:
        cls_id = mermaid_safe_id(f"cls_{c.qualified_name}")
        bases_str = f" ({', '.join(c.bases)})" if c.bases else ""
        lines.append(f'  subgraph {cls_id}["{c.qualified_name}{bases_str}"]')
        lines.append("    direction TB")

        # class variables
        if c.class_variables:
            cv_sub = mermaid_safe_id(f"cv_{c.qualified_name}")
            lines.append(f'    subgraph {cv_sub}["Class Vars"]')
            lines.append("      direction LR")
            for v in c.class_variables:
                nid = mermaid_safe_id(f"cv_{c.qualified_name}_{v.name}")
                lines.append(f'      {nid}>{"{0}: {1}"}]'.format(v.name, v.inferred_type))
            lines.append("    end")

        # instance variables
        if c.instance_variables:
            iv_sub = mermaid_safe_id(f"iv_{c.qualified_name}")
            lines.append(f'    subgraph {iv_sub}["Instance Vars"]')
            lines.append("      direction LR")
            for v in c.instance_variables:
                nid = mermaid_safe_id(f"iv_{c.qualified_name}_{v.name}")
                lines.append(f'      {nid}>{"{0}: {1}"}]'.format(v.name, v.inferred_type))
            lines.append("    end")

        # methods
        for m in c.methods:
            nid = mermaid_safe_id(f"m_{m.qualified_name}")
            tag = pattern_tag(patterns, m.qualified_name)
            async_mark = "async " if m.is_async else ""
            label = f"{async_mark}{m.qualified_name} L{m.start_line} {tag}".strip()
            nodes[m.qualified_name] = nid
            lines.append(f'    {nid}["{label}"]')

        lines.append("  end")

    # top-level functions
    for f in file.functions:
        nid = mermaid_safe_id(f"fn_{f.qualified_name}")
        tag = pattern_tag(patterns, f.qualified_name)
        async_mark = "async " if f.is_async else ""
        label = f"{async_mark}{f.qualified_name} L{f.start_line} {tag}".strip()
        nodes[f.qualified_name] = nid
        lines.append(f'  {nid}(["{label}"])')

    lines.append("end")
    lines.append("")

    # --- dependency subgraph ---
    local_deps = sorted({t for rec in file.imports for t in rec.resolved_local_targets})
    reverse_deps: list[str] = []
    if all_files:
        for other in all_files:
            if other.path == file.path:
                continue
            for rec in other.imports:
                if file.module_name in rec.resolved_local_targets:
                    reverse_deps.append(other.module_name or Path(other.path).stem)
                    break
        reverse_deps = sorted(set(reverse_deps))

    if local_deps or reverse_deps:
        lines.append(f'subgraph deps["Dependencies"]')
        lines.append("  direction TB")
        for dep in local_deps:
            dep_id = mermaid_safe_id(f"dep_{dep}")
            lines.append(f'  {dep_id}["{dep}"]')
        for dep in reverse_deps:
            dep_id = mermaid_safe_id(f"rdep_{dep}")
            lines.append(f'  {dep_id}["{dep}"]')
        lines.append("end")
        lines.append("")
        # edges: imports flow into this module, reverse deps flow out
        for dep in local_deps:
            dep_id = mermaid_safe_id(f"dep_{dep}")
            lines.append(f'{dep_id} -->|"imports"| {safe_module}')
        for dep in reverse_deps:
            dep_id = mermaid_safe_id(f"rdep_{dep}")
            lines.append(f'{safe_module} -->|"imported by"| {dep_id}')
        lines.append("")

    # --- external imports node ---
    ext_roots = sorted({
        (rec.module if rec.kind == "from" else name).split(".")[0]
        for rec in file.imports
        for name in (rec.names if rec.kind == "import" else [rec.module or ""])
        if name and not rec.resolved_local_targets
    })
    if ext_roots:
        ext_label = ", ".join(ext_roots[:12])
        if len(ext_roots) > 12:
            ext_label += f" +{len(ext_roots) - 12} more"
        lines.append(f'ExtPkgs[/"External: {ext_label}"/]')
        lines.append(f'ExtPkgs -->|"stdlib / 3rd-party"| {safe_module}')
        lines.append("")

    # --- internal call edges ---
    seen_edges: set[tuple[str, str]] = set()
    all_callables = list(file.functions)
    for c in file.classes:
        all_callables.extend(c.methods)

    for func in all_callables:
        src = nodes.get(func.qualified_name)
        if not src:
            continue
        for call in func.calls:
            if call in nodes:
                dst = nodes[call]
                edge = (src, dst)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    lines.append(f"{src} --> {dst}")
            else:
                external_calls.add(call)

    lines.append("")
    lines.append(render_pattern_legend().strip())
    return "\n".join(lines) + "\n"

def render_pattern_legend():
    return """
## Pattern Legend

<<FAC>>  Facade
<<ADP>>  Adapter
<<SM>>   State Machine
<<REG>>  Event Registry
<<DIS>>  Dispatcher
<<TB>>   Token Bucket
<<HASH>> Hash / Fingerprint Algorithm
"""

def build_interaction_model(
    files: list[FileAnalysis],
) -> tuple[dict[str, tuple[str, str]], list[tuple[str, str, str]]]:
    nodes: dict[str, tuple[str, str]] = {}
    edges: set[tuple[str, str, str]] = set()
    function_lookup: dict[tuple[str, str], str] = {}
    class_lookup: dict[tuple[str, str], str] = {}
    method_lookup: dict[tuple[str, str], dict[str, str]] = {}
    class_instance_types: dict[tuple[str, str], dict[str, str]] = {}

    for file in files:
        module_label = file.module_name or Path(file.path).stem
        for function in file.functions:
            node_id = f"{module_label}::{function.qualified_name}"
            nodes[node_id] = ("function", f"{module_label}.{function.qualified_name}")
            function_lookup[(module_label, function.qualified_name)] = node_id
        for class_record in file.classes:
            class_node_id = f"{module_label}::{class_record.qualified_name}"
            nodes[class_node_id] = ("class", f"{module_label}.{class_record.qualified_name}")
            class_lookup[(module_label, class_record.qualified_name)] = class_node_id
            method_map: dict[str, str] = {}
            for method in class_record.methods:
                method_node_id = f"{module_label}::{method.qualified_name}"
                nodes[method_node_id] = ("method", f"{module_label}.{method.qualified_name}")
                method_name = method.qualified_name.split(".")[-1]
                method_map[method_name] = method_node_id
            method_lookup[(module_label, class_record.qualified_name)] = method_map
            class_instance_types[(module_label, class_record.qualified_name)] = {
                item.name: item.inferred_type for item in class_record.instance_variables
            }

    def resolve_call_target(
        call: str,
        module_label: str,
        current_class: str | None,
        locals_map: dict[str, str],
    ) -> tuple[str, str] | None:
        if "." not in call:
            if (module_label, call) in function_lookup:
                return function_lookup[(module_label, call)], "calls"
            if (module_label, call) in class_lookup:
                return class_lookup[(module_label, call)], "instantiates"
            return None

        parts = call.split(".")
        if len(parts) == 2:
            left, right = parts
            if left == "self" and current_class is not None:
                method_target = method_lookup.get((module_label, current_class), {}).get(right)
                if method_target:
                    return method_target, "calls"
            method_target = method_lookup.get((module_label, left), {}).get(right)
            if method_target:
                return method_target, "calls"
            inferred_type = locals_map.get(left)
            if inferred_type:
                method_target = method_lookup.get((module_label, inferred_type), {}).get(right)
                if method_target:
                    return method_target, "calls"
            return None

        if len(parts) == 3 and parts[0] == "self" and current_class is not None:
            attr_name, method_name = parts[1], parts[2]
            inferred_type = class_instance_types.get((module_label, current_class), {}).get(attr_name)
            if inferred_type:
                method_target = method_lookup.get((module_label, inferred_type), {}).get(method_name)
                if method_target:
                    return method_target, "calls"
        return None

    for file in files:
        module_label = file.module_name or Path(file.path).stem
        for function in file.functions:
            source_id = function_lookup[(module_label, function.qualified_name)]
            locals_map = {item.name: item.inferred_type for item in function.locals}
            for call in function.calls:
                target = resolve_call_target(call, module_label, None, locals_map)
                if target:
                    target_id, relation = target
                    edges.add((source_id, target_id, relation))
        for class_record in file.classes:
            for method in class_record.methods:
                source_id = method_lookup[(module_label, class_record.qualified_name)][method.qualified_name.split(".")[-1]]
                locals_map = {item.name: item.inferred_type for item in method.locals}
                for call in method.calls:
                    target = resolve_call_target(call, module_label, class_record.qualified_name, locals_map)
                    if target:
                        target_id, relation = target
                        edges.add((source_id, target_id, relation))

    return nodes, sorted(edges)


def limit_interaction_model(
    nodes: dict[str, tuple[str, str]],
    edges: list[tuple[str, str, str]],
) -> tuple[dict[str, tuple[str, str]], list[tuple[str, str, str]], bool]:
    if len(nodes) <= INTERACTION_MAX_NODES and len(edges) <= INTERACTION_MAX_EDGES:
        return nodes, edges, False
    ranked_nodes = sorted(
        nodes.items(),
        key=lambda item: sum(1 for edge in edges if edge[0] == item[0] or edge[1] == item[0]),
        reverse=True,
    )[:INTERACTION_MAX_NODES]
    kept_ids = {node_id for node_id, _ in ranked_nodes}
    limited_nodes = {node_id: label for node_id, label in ranked_nodes}
    limited_edges = [
        edge for edge in edges if edge[0] in kept_ids and edge[1] in kept_ids
    ][:INTERACTION_MAX_EDGES]
    return limited_nodes, limited_edges, True


def render_interaction_dot(files: list[FileAnalysis]) -> str:
    nodes, edges = build_interaction_model(files)
    nodes, edges, truncated = limit_interaction_model(nodes, edges)
    shape_map = {"function": "ellipse", "method": "box", "class": "component"}
    lines = ["digraph interaction_map {", '  rankdir="LR";', '  edge [penwidth="2"];']
    if truncated:
        lines.append(
            f'  label="Truncated to {INTERACTION_MAX_NODES} nodes / '
            f'{INTERACTION_MAX_EDGES} edges for readability";'
        )
    for node_id, (kind, label) in sorted(nodes.items()):
        lines.append(f"  {dot_quote(node_id)} [label={dot_quote(label)}, shape=\"{shape_map.get(kind, 'box')}\"];")
    for src, dst, relation in edges:
        lines.append(f"  {dot_quote(src)} -> {dot_quote(dst)} [label=\"{relation}\"];")
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_interaction_mermaid(files: list[FileAnalysis]) -> str:
    nodes, edges = build_interaction_model(files)
    nodes, edges, truncated = limit_interaction_model(nodes, edges)
    lines = ["flowchart LR"]
    if truncated:
        lines.append(
            f"  %% Truncated to {INTERACTION_MAX_NODES} nodes / "
            f"{INTERACTION_MAX_EDGES} edges for Mermaid limits"
        )
    for node_id, (kind, label) in sorted(nodes.items()):
        safe_id = mermaid_safe_id(node_id)
        if kind == "class":
            lines.append(f'  {safe_id}[["{label}"]]')
        elif kind == "function":
            lines.append(f'  {safe_id}(["{label}"])')
        else:
            lines.append(f'  {safe_id}["{label}"]')
    for src, dst, relation in edges:
        lines.append(f"  {mermaid_safe_id(src)} -->|\"{relation}\"| {mermaid_safe_id(dst)}")
    return "\n".join(lines) + "\n"


def diagram_extension(diagram_format: str) -> str:
    return "dot" if diagram_format == "dot" else "mmd"


def render_diagram_content(files: list[FileAnalysis], diagram_name: str, diagram_format: str) -> str:
    if diagram_format == "dot":
        if diagram_name == "dependency_graph":
            return render_dependency_dot(files)
        if diagram_name == "class_map":
            return render_class_dot(files)
        if diagram_name == "pattern_map":
            return render_pattern_dot(files)
        if diagram_name == "interaction_map":
            return render_interaction_dot(files)
    if diagram_format == "mermaid":
        if diagram_name == "dependency_graph":
            return render_dependency_mermaid(files)
        if diagram_name == "class_map":
            return render_class_mermaid(files)
        if diagram_name == "pattern_map":
            return render_pattern_mermaid(files)
        if diagram_name == "interaction_map":
            return render_interaction_mermaid(files)
        if diagram_name == "single_file_map":
            return render_single_file_mermaid(files[0], files[0].patterns, files)
    raise ValueError(f"unsupported diagram combination: {diagram_name} / {diagram_format}")


def render_svg_from_dot(dot_path: Path, svg_path: Path) -> bool:
    if shutil.which("dot") is None:
        return False
    subprocess.run(
        ["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)],
        check=True,
    )
    return True

def write_diagrams(
    files: list[FileAnalysis],
    diagram_dir: Path,
    diagram_format: str,
    render_svg: bool,
    skip_diagrams: set[str] | None = None,
) -> tuple[list[DiagramArtifact], list[dict[str, str]]]:
    diagram_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[DiagramArtifact] = []
    diagram_errors: list[dict[str, str]] = []
    skip = skip_diagrams or set()
    diagram_specs = [
        ("dependency_graph", "module/file dependency graph"),
        ("class_map", "class inheritance and presence map"),
        ("pattern_map", "pattern-to-symbol evidence map"),
        ("single_file_map", "Single file call structure"),
        ("interaction_map", "function, method, and object interaction map"),
    ]
    extension = diagram_extension(diagram_format)

    for name, description in diagram_specs:
        if name in skip:
            continue
        output_path = diagram_dir / f"{name}.{extension}"
        try:
            content = render_diagram_content(files, name, diagram_format)
            if diagram_format == "mermaid":
                content = wrap_mermaid_diagram(content)
            if diagram_format == "mermaid" and len(content) > MERMAID_TEXT_LIMIT_CHARS:
                raise ValueError(
                    f"{name} mermaid source is {len(content)} chars "
                    f"(limit {MERMAID_TEXT_LIMIT_CHARS}); retry with diagram_format=dot "
                    "or a narrower target"
                )
            output_path.write_text(content, encoding="utf-8")
        except Exception as exc:
            message = str(exc)
            diagram_errors.append({"diagram": name, "error": message})
            LOG.warning("diagram %s skipped: %s", name, message)
            error_path = diagram_dir / f"{name}.error.txt"
            error_path.write_text(message + "\n", encoding="utf-8")
            artifacts.append(
                DiagramArtifact(
                    name=f"{name}_error",
                    kind="diagram_error",
                    format="text",
                    path=str(error_path),
                    description=f"{description} failed: {message}",
                )
            )
            continue
        artifacts.append(
            DiagramArtifact(
                name=name,
                kind="diagram_source",
                format=diagram_format,
                path=str(output_path),
                description=description,
            )
        )
        if render_svg and diagram_format == "dot":
            svg_path = diagram_dir / f"{name}.svg"
            try:
                if render_svg_from_dot(output_path, svg_path):
                    artifacts.append(
                        DiagramArtifact(
                            name=name,
                            kind="rendered_diagram",
                            format="svg",
                            path=str(svg_path),
                            description=f"{description} rendered from Graphviz DOT",
                        )
                    )
            except Exception as exc:
                diagram_errors.append({
                    "diagram": f"{name}.svg",
                    "error": str(exc),
                })
                LOG.warning("diagram %s svg render skipped: %s", name, exc)

    manifest_path = diagram_dir / "diagram_manifest.json"
    manifest_payload = {
        "artifacts": [asdict(artifact) for artifact in artifacts],
        "errors": diagram_errors,
    }
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    artifacts.append(
        DiagramArtifact(
            name="diagram_manifest",
            kind="manifest",
            format="json",
            path=str(manifest_path),
            description="List of generated diagram artifacts",
        )
    )
    return artifacts, diagram_errors


def write_diagram_manifest(
    diagram_dir: Path,
    artifacts: list[DiagramArtifact],
    diagram_errors: list[dict[str, str]],
) -> None:
    manifest_path = diagram_dir / "diagram_manifest.json"
    manifest_payload = {
        "artifacts": [asdict(artifact) for artifact in artifacts],
        "errors": diagram_errors,
    }
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2) + "\n",
        encoding="utf-8",
    )


def collect_dependency_edges(files: list[FileAnalysis]) -> list[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    path_to_module = {Path(file.path).resolve(): file.module_name for file in files if file.module_name}
    for file in files:
        src = file.module_name or file.path
        for record in file.imports:
            for target in record.resolved_local_targets:
                if target and target != file.module_name:
                    edges.add((src, target))
        for dep_str in file.direct_dependency_paths:
            try:
                dep_path = Path(dep_str).resolve()
            except (OSError, ValueError):
                continue
            target_mod = path_to_module.get(dep_path)
            if target_mod and target_mod != file.module_name:
                edges.add((src, target_mod))
    return sorted(edges)


def collect_external_imports(files: list[FileAnalysis]) -> list[str]:
    roots: set[str] = set()
    for file in files:
        for record in file.imports:
            if record.resolved_local_targets:
                continue
            if record.kind == "import":
                for name in record.names:
                    roots.add(name.split(".")[0])
            else:
                module = record.module or ""
                if module:
                    roots.add(module.split(".")[0])
    return sorted(root for root in roots if root)


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Map Python file or application structure with heuristic analysis.")
    parser.add_argument("targets", nargs="+", help="Python file(s) or directory target(s).")
    parser.add_argument(
        "--mode",
        choices=("auto", "file", "app"),
        default="auto",
        help="Treat the input as a single-file analysis, an application analysis, or infer automatically.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format.",
    )
    parser.add_argument(
        "--output",
        help="Optional output file. Defaults to stdout.",
    )
    parser.add_argument(
        "--snapshot-output",
        help="Optional JSON snapshot output written regardless of main output format.",
    )
    parser.add_argument(
        "--diagram-dir",
        help="Optional directory for separately generated diagrams.",
    )
    parser.add_argument(
        "--diagram-format",
        choices=("dot", "mermaid"),
        default="dot",
        help="Diagram source format. DOT is the default and generally more reliable than Mermaid.",
    )
    parser.add_argument(
        "--render-svg",
        action="store_true",
        help="When using DOT, also render SVG files if Graphviz `dot` is installed.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help="Maximum number of Python files allowed in scope before failing fast.",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=DEFAULT_MAX_LINES,
        help="Maximum total lines allowed across all analyzed files before failing fast.",
    )
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=DEFAULT_MAX_FILE_BYTES,
        help="Maximum size per Python file in bytes before failing fast.",
    )
    parser.add_argument(
        "--skip-diagrams",
        nargs="*",
        default=(),
        metavar="NAME",
        help="Diagram names to skip (e.g. interaction_map class_map).",
    )
    parser.add_argument(
        "--diagram-profile",
        choices=("full", "filesystem"),
        default="full",
        help="filesystem profile emits code_topology.json and skips legacy heavy diagrams.",
    )
    args = parser.parse_args()

    resolved_files = iter_python_files(args.targets, args.mode, args.max_files)
    effective_mode = choose_mode(args.mode, resolved_files, args.targets)
    analysis_root = derive_analysis_root(resolved_files)
    analyses: list[FileAnalysis] = []
    lines_reviewed = 0
    analysis_errors: list[str] = []
    for path in resolved_files:
        try:
            analysis = FileAnalyzer(path, analysis_root, args.max_file_bytes).analyze()
        except Exception as exc:
            if len(resolved_files) == 1:
                raise
            message = f"skipped `{path}` due to analysis error: {exc}"
            analysis_errors.append(message)
            LOG.warning(message)
            continue
        lines_reviewed += analysis.line_count
        if args.max_lines > 0 and lines_reviewed > args.max_lines:
            raise ValueError(
                f"target scope reached {lines_reviewed} lines, which exceeds the limit of {args.max_lines}; "
                "narrow the target scope or raise --max-lines explicitly"
            )
        analyses.append(analysis)
    if not analyses:
        raise ValueError("no analyzable Python files remained after error recovery")
    annotate_import_resolution(analyses, analysis_root)
    header = build_header(effective_mode, args.targets, analyses, analysis_errors)

    rendered = (
        render_json(header, analyses, analysis_errors)
        if args.format == "json"
        else render_markdown(header, analyses, analysis_errors)
    )
    snapshot_rendered = render_json(header, analyses, analysis_errors)

    artifacts: list[DiagramArtifact] = []
    diagram_errors: list[dict[str, str]] = []
    if args.diagram_dir:
        diagram_dir = Path(args.diagram_dir)
        topology = build_code_topology(
            analysis_root=analysis_root,
            files=[asdict(file) for file in analyses],
            module_edges=collect_dependency_edges(analyses),
            targets=args.targets,
            mode=effective_mode,
            header=asdict(header),
        )
        topology_path = write_code_topology(topology, diagram_dir)
        artifacts.append(
            DiagramArtifact(
                name="code_topology",
                kind="topology",
                format="json",
                path=str(topology_path),
                description="Canonical filesystem/package topology for JS battlefield viewer",
            )
        )
        system_map = diagram_dir / "system_map.json"
        if system_map.exists():
            artifacts.append(
                DiagramArtifact(
                    name="system_map",
                    kind="generated_system_map",
                    format="json",
                    path=str(system_map),
                    description="Generated system/component map with Shufti layout and live-overlay slots",
                )
            )
        overview_mmd = diagram_dir / "filesystem_overview.mmd"
        if overview_mmd.exists():
            artifacts.append(
                DiagramArtifact(
                    name="filesystem_overview",
                    kind="diagram_source",
                    format="mermaid",
                    path=str(overview_mmd),
                    description="Package-grouped filesystem overview (TB subgraphs)",
                )
            )
        skip_diagrams = set(args.skip_diagrams)
        if args.diagram_profile == "filesystem":
            skip_diagrams |= FILESYSTEM_DIAGRAM_SKIP
        diagram_artifacts, diagram_errors = write_diagrams(
            analyses,
            diagram_dir,
            args.diagram_format,
            args.render_svg,
            skip_diagrams=skip_diagrams,
        )
        artifacts.extend(diagram_artifacts)
        write_diagram_manifest(diagram_dir, artifacts, diagram_errors)
        if diagram_errors:
            LOG.warning(
                "diagram generation completed with %d skipped diagram(s)",
                len(diagram_errors),
            )

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.snapshot_output:
        Path(args.snapshot_output).write_text(snapshot_rendered, encoding="utf-8")
    if artifacts and not args.output:
        print("\nGenerated diagram artifacts:", end="\n")
        for artifact in artifacts:
            print(f"- {artifact.kind} {artifact.format} {artifact.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
