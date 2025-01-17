import ast
import astor
import pytest
import os
import sys

from shutil import copyfile
from trio._tools.gen_exports import (
    get_public_methods,
    create_passthrough_args,
    process,
)

SOURCE = '''from _run import _public

class Test:
    @_public
    def public_func(self):
        """With doc string"""

    @ignore_this
    @_public
    @another_decorator
    async def public_async_func(self):
        pass  # no doc string

    def not_public(self):
        pass

    async def not_public_async(self):
        pass
'''


def test_get_public_methods():
    methods = list(get_public_methods(ast.parse(SOURCE)))
    assert {m.name for m in methods} == {"public_func", "public_async_func"}


def test_create_pass_through_args():
    testcases = [
        ("def f()", "()"),
        ("def f(one)", "(one)"),
        ("def f(one, two)", "(one, two)"),
        ("def f(one, *args)", "(one, *args)"),
        (
            "def f(one, *args, kw1, kw2=None, **kwargs)",
            "(one, *args, kw1=kw1, kw2=kw2, **kwargs)",
        ),
    ]

    for funcdef, expected in testcases:
        func_node = ast.parse(funcdef + ":\n  pass").body[0]
        assert isinstance(func_node, ast.FunctionDef)
        assert create_passthrough_args(func_node) == expected


def test_process(tmp_path):
    modpath = tmp_path / "_module.py"
    genpath = tmp_path / "_generated_module.py"
    modpath.write_text(SOURCE, encoding="utf-8")
    assert not genpath.exists()
    with pytest.raises(SystemExit) as excinfo:
        process([(str(modpath), "runner")], do_test=True)
    assert excinfo.value.code == 1
    process([(str(modpath), "runner")], do_test=False)
    assert genpath.exists()
    process([(str(modpath), "runner")], do_test=True)
    # But if we change the lookup path it notices
    with pytest.raises(SystemExit) as excinfo:
        process([(str(modpath), "runner.io_manager")], do_test=True)
    assert excinfo.value.code == 1
