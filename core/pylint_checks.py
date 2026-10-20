# pylint: disable=invalid-name
"""Custom pylint checkers for AyyadMusicBot project rules.

Activated via: load-plugins=pylint_custom_checks
"""
import astroid
from pylint.checkers import BaseChecker


class RedisPipelineFirstChecker(BaseChecker):
    """Detect asyncio.gather calls that contain database operations."""

    name = "redis-pipeline-first"
    msgs = {
        "R9001": (
            "asyncio.gather contains database call '%s' — use pipeline() instead",
            "redis-pipeline-first",
            "Multiple Redis operations must go through one database.pipeline(). "
            "Never use asyncio.gather for Redis.",
        ),
    }

    def visit_call(self, node):
        if not self._is_asyncio_gather(node):
            return
        for arg in node.args:
            if self._is_database_call(arg):
                self.add_message("redis-pipeline-first", node=node, args=f"database.{arg.func.attrname}")

    @staticmethod
    def _is_asyncio_gather(node):
        func = node.func
        if isinstance(func, astroid.Attribute) and func.attrname == "gather":
            if isinstance(func.expr, astroid.Name) and func.expr.name == "asyncio":
                return True
        return False

    @staticmethod
    def _is_database_call(node):
        if isinstance(node, astroid.Call) and isinstance(node.func, astroid.Attribute):
            obj = node.func.expr
            if isinstance(obj, astroid.Name) and obj.name == "database":
                return node.func.attrname in ("get", "set", "delete", "incr", "decr", "expire")
        return False


class SingleUseVariableChecker(BaseChecker):
    """Detect variables that are assigned once and used only once."""

    name = "no-single-use-var"
    msgs = {
        "R9002": (
            "Variable '%s' is assigned and used only once — inline it",
            "no-single-use-var",
            "No single-use variables — inline values directly.",
        ),
    }

    def visit_functiondef(self, node):
        self._check_scope(node)

    visit_asyncfunctiondef = visit_functiondef

    def _check_scope(self, scope_node):
        param_names = set()
        for arg in scope_node.args.args:
            param_names.add(arg.name)
        if scope_node.args.vararg:
            param_names.add(scope_node.args.vararg)
        if scope_node.args.kwarg:
            param_names.add(scope_node.args.kwarg)

        assigned = {}
        used = {}

        for child in scope_node.nodes_of_class((astroid.AssignName, astroid.Name)):
            if isinstance(child, astroid.AssignName):
                name = child.name
                if name.startswith("_") or name.isupper() or name in param_names:
                    continue
                if isinstance(child.parent, astroid.ExceptHandler):
                    continue
                parent = child.parent
                if (parent
                        and isinstance(parent, astroid.Assign)
                        and len(parent.targets) == 1
                        and isinstance(parent.targets[0], astroid.Tuple)):
                    continue
                if isinstance(child.parent, astroid.For):
                    continue
                if isinstance(child.parent, astroid.Tuple):
                    continue
                assigned[name] = child
            elif isinstance(child, astroid.Name) and child.name in assigned:
                used[child.name] = used.get(child.name, 0) + 1

        for name, node in assigned.items():
            if used.get(name, 0) == 1:
                self.add_message("no-single-use-var", node=node, args=name)


class RedisKeyInlineChecker(BaseChecker):
    """Detect Redis keys staged in variables before database calls."""

    name = "redis-key-inline"
    msgs = {
        "R9003": (
            "Redis key '%s' staged in variable — write it inline in the database call",
            "redis-key-inline",
            "Redis keys must be written INLINE inside database calls, "
            "never staged in a variable first.",
        ),
    }

    def visit_functiondef(self, node):
        self._check_scope(node)

    visit_asyncfunctiondef = visit_functiondef

    def _check_scope(self, scope_node):
        key_vars = {}

        for stmt in scope_node.body:
            if isinstance(stmt, astroid.Assign):
                targets = stmt.targets
                if (len(targets) == 1
                        and isinstance(targets[0], astroid.AssignName)
                        and isinstance(stmt.value, (astroid.JoinedStr, astroid.Const))):
                    var_name = targets[0].name
                    if var_name.startswith("_") or var_name.isupper():
                        continue
                    key_vars[var_name] = targets[0]

            if isinstance(stmt, astroid.Expr) and isinstance(stmt.value, astroid.Call):
                self._check_call(stmt.value, key_vars)

    def _check_call(self, call_node, key_vars):
        if not self._is_database_call(call_node):
            return
        for kwarg in [kw.value for kw in call_node.keywords]:
            if isinstance(kwarg, astroid.Name) and kwarg.name in key_vars:
                self.add_message("redis-key-inline", node=kwarg, args=kwarg.name)
        for arg in call_node.args:
            if isinstance(arg, astroid.Name) and arg.name in key_vars:
                self.add_message("redis-key-inline", node=arg, args=arg.name)

    @staticmethod
    def _is_database_call(node):
        func = node.func
        if isinstance(func, astroid.Attribute):
            obj = func.expr
            if isinstance(obj, astroid.Name) and obj.name == "database":
                return func.attrname in ("get", "set", "delete", "sadd", "srem",
                                         "smembers", "scard", "expire", "incr", "decr")
        return False


class FunctionWrapperChecker(BaseChecker):
    """Detect functions that are pure forwarding wrappers around a call."""

    name = "no-function-wrapper"
    msgs = {
        "R9004": (
            "Function '%s' is a pure forwarding wrapper — call the wrapped callable "
            "directly at each call site",
            "no-function-wrapper",
            "A def whose entire body is a single return <Call>(...) forwarding only "
            "its own parameters or constants is forbidden (pointless indirection). "
            "No inline disables for this rule — refactor instead.",
        ),
    }

    @staticmethod
    def _is_forwarded(func_node):
        body = [_stmt for _stmt in func_node.body if not isinstance(_stmt, astroid.Expr)]
        if len(body) != 1 or not isinstance(body[0], astroid.Return):
            return False
        value = body[0].value
        if not isinstance(value, astroid.Call):
            return False
        if not FunctionWrapperChecker._func_is_simple(value.func):
            return False
        args = func_node.args
        param_names = set()
        for arg in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
            param_names.add(arg.name)
        for vararg in (args.vararg, args.kwarg):
            if vararg is not None:
                param_names.add(vararg)
        for arg in value.args:
            if not FunctionWrapperChecker._is_plain_node(arg, param_names):
                return False
        for kw in value.keywords:
            if not FunctionWrapperChecker._is_plain_node(kw.value, param_names):
                return False
        return True

    @staticmethod
    def _func_is_simple(node):
        if isinstance(node, astroid.Name):
            return True
        if isinstance(node, astroid.Attribute):
            return FunctionWrapperChecker._func_is_simple(node.expr)
        return False

    @staticmethod
    def _is_plain_node(node, param_names):
        if isinstance(node, astroid.Const):
            return True
        if isinstance(node, astroid.Name):
            return node.name in param_names
        if isinstance(node, astroid.Call):
            for arg in node.args:
                if not FunctionWrapperChecker._is_plain_node(arg, param_names):
                    return False
            for kw in node.keywords:
                if not FunctionWrapperChecker._is_plain_node(kw.value, param_names):
                    return False
            return True
        return False

    def visit_functiondef(self, node):
        if FunctionWrapperChecker._is_forwarded(node):
            self.add_message("no-function-wrapper", node=node, args=node.name)

    visit_asyncfunctiondef = visit_functiondef


def register(linter):
    linter.register_checker(RedisPipelineFirstChecker(linter))
    linter.register_checker(SingleUseVariableChecker(linter))
    linter.register_checker(RedisKeyInlineChecker(linter))
    linter.register_checker(FunctionWrapperChecker(linter))
