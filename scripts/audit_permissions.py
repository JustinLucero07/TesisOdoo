#!/usr/bin/env python3
"""
Estate Modules — Access Rights Audit
Detecta todos los permisos definidos en los módulos personalizados
y reporta modelos sin permisos asignados.

Uso: python scripts/audit_permissions.py [--module <nombre>]
"""
import os
import csv
import re
import sys
from pathlib import Path

# ── Configuración ────────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent.parent

CUSTOM_MODULES = [
    'estate_management',
    'estate_crm',
    'estate_calendar',
    'estate_reports',
    'estate_ai_agent',
    'estate_document',
    'estate_social',
    'estate_portal',
    'estate_wordpress',
    'estate_payroll',
]

GROUPS_DISPLAY = {
    'estate_group_agent':     'Agente',
    'estate_group_marketing': 'Marketing',
    'estate_group_manager':   'Gerente',
    'estate_group_admin':     'Admin',
}

PERM_LABELS = ['R', 'W', 'C', 'D']  # read, write, create, unlink

# ── Helpers ──────────────────────────────────────────────────────────────────

def short_group(group_raw: str) -> str:
    key = group_raw.split('.')[-1]
    return GROUPS_DISPLAY.get(key, key[:14])


def perm_str(row: dict) -> str:
    keys = ['perm_read', 'perm_write', 'perm_create', 'perm_unlink']
    return ''.join(
        label if row.get(k) == '1' else '·'
        for label, k in zip(PERM_LABELS, keys)
    )


def get_python_models(module_path: Path) -> dict[str, Path]:
    """Return {model_name: first_file_that_declares_it}."""
    models = {}
    skip = {'__pycache__', 'venv', '.git', 'static', 'tests'}
    for py in module_path.rglob('*.py'):
        if any(s in py.parts for s in skip):
            continue
        try:
            text = py.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        for m in re.finditer(r'_name\s*=\s*[\'"]([^\'"]+)[\'"]', text):
            name = m.group(1)
            if name not in models:
                models[name] = py.relative_to(BASE)
    return models


def get_access_rules(module_path: Path) -> list[dict]:
    csv_file = module_path / 'security' / 'ir.model.access.csv'
    if not csv_file.exists():
        return []
    with open(csv_file, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def model_key_to_name(model_id: str) -> str:
    """'model_estate_property_type' → 'estate.property.type'"""
    raw = model_id.split('.')[-1]  # strip module prefix
    raw = re.sub(r'^model_', '', raw)
    return raw.replace('_', '.')


# ── Main audit ───────────────────────────────────────────────────────────────

def audit_module(module_name: str, verbose: bool = True) -> dict:
    mod_path = BASE / module_name
    if not mod_path.exists():
        return {'error': f'Módulo no encontrado: {module_name}'}

    py_models = get_python_models(mod_path)
    rules = get_access_rules(mod_path)

    # Build set of models covered by access rules
    covered = {model_key_to_name(r['model_id:id']) for r in rules}

    # Filter out mixins, abstract helpers, inherited models not owned by this module
    own_models = {
        name: path for name, path in py_models.items()
        if '.' in name and not name.startswith('ir.')
        and not name.startswith('res.')
        and not name.startswith('mail.')
        and not name.startswith('base.')
    }

    missing = {n for n in own_models if n not in covered}

    return {
        'module': module_name,
        'py_models': own_models,
        'rules': rules,
        'covered': covered,
        'missing': missing,
    }


def print_report(filter_module: str | None = None):
    modules = [filter_module] if filter_module else CUSTOM_MODULES

    print()
    print('=' * 72)
    print('  INMOBI — AUDITORÍA DE PERMISOS DE ACCESO')
    print('=' * 72)

    total_rules = 0
    total_missing = 0

    for mod_name in modules:
        result = audit_module(mod_name)
        if 'error' in result:
            print(f'\n[ERROR] {result["error"]}')
            continue

        rules = result['rules']
        missing = result['missing']
        py_models = result['py_models']

        total_rules += len(rules)
        total_missing += len(missing)

        status = 'OK' if not missing else f'FALTAN {len(missing)}'
        print(f'\n{"─" * 72}')
        print(f'  MODULO: {mod_name:<35}  [{status}]  {len(rules)} reglas')
        print(f'{"─" * 72}')

        if rules:
            # Group rules by model
            by_model: dict[str, list] = {}
            for r in rules:
                m = model_key_to_name(r['model_id:id'])
                by_model.setdefault(m, []).append(r)

            col_m = 40
            print(f'  {"Modelo":<{col_m}} {"Grupo":<18} Perms')
            print(f'  {"─"*col_m} {"─"*18} {"─"*5}')
            for model_name in sorted(by_model):
                for i, r in enumerate(by_model[model_name]):
                    m_col = model_name if i == 0 else ''
                    print(
                        f'  {m_col:<{col_m}} '
                        f'{short_group(r["group_id:id"]):<18} '
                        f'{perm_str(r)}'
                    )
        else:
            print('  (sin archivo ir.model.access.csv)')

        if missing:
            print(f'\n  MODELOS SIN PERMISOS ({len(missing)}):')
            for m in sorted(missing):
                path = py_models.get(m, '?')
                print(f'    - {m:<45}  ({path})')

    # ── Summary ──────────────────────────────────────────────────────────────
    print()
    print('=' * 72)
    print(f'  RESUMEN TOTAL')
    print(f'    Reglas de acceso definidas : {total_rules}')
    print(f'    Modelos sin permisos       : {total_missing}')
    if total_missing == 0:
        print('    Estado                     : COMPLETO — todos los modelos cubiertos')
    else:
        print('    Estado                     : INCOMPLETO — revisar modelos listados')
    print('=' * 72)
    print()


def print_matrix():
    """Print a compact permissions matrix across all modules."""
    print()
    print('=' * 72)
    print('  MATRIZ COMPACTA DE PERMISOS — TODOS LOS MÓDULOS')
    print('  (R=read W=write C=create D=delete  ·=sin permiso)')
    print('=' * 72)

    all_rules: list[tuple[str, dict]] = []
    for mod_name in CUSTOM_MODULES:
        mod_path = BASE / mod_name
        for r in get_access_rules(mod_path):
            all_rules.append((mod_name, r))

    by_model: dict[str, list[tuple[str, dict]]] = {}
    for mod, r in all_rules:
        m = model_key_to_name(r['model_id:id'])
        by_model.setdefault(m, []).append((mod, r))

    col = 42
    print(f'\n  {"Modelo":<{col}} {"Grupo":<18} Perms  Módulo')
    print(f'  {"─"*col} {"─"*18} {"─"*5}  {"─"*20}')
    for model_name in sorted(by_model):
        for i, (mod, r) in enumerate(by_model[model_name]):
            m_col = model_name if i == 0 else ''
            print(
                f'  {m_col:<{col}} '
                f'{short_group(r["group_id:id"]):<18} '
                f'{perm_str(r)}  '
                f'{mod}'
            )
    print()


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    args = sys.argv[1:]
    filter_mod = None
    matrix_mode = False

    i = 0
    while i < len(args):
        if args[i] in ('--module', '-m') and i + 1 < len(args):
            filter_mod = args[i + 1]
            i += 2
        elif args[i] in ('--matrix', '-x'):
            matrix_mode = True
            i += 1
        else:
            i += 1

    if matrix_mode:
        print_matrix()
    else:
        print_report(filter_mod)
