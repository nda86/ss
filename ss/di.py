import inspect
from functools import wraps


class Container:
    def __init__(self):
        self._cache = {}
        self._bind = {}

    def resolve(self, param):
        if param.default is not inspect.Parameter.empty:
            return param.default
        elif param.annotation is not inspect.Parameter.empty and param.annotation in self._bind:
            if param.annotation in self._cache:
                return self._cache[param.annotation]
            typ = self._bind[param.annotation]
            sig = inspect.signature(typ)

            kwargs = {name: self.resolve(param) for name, param in sig.parameters.items()}

            instance = typ(**kwargs)
            self._cache[typ] = instance
            return instance
        else:
            raise ValueError(f"Cannot resolve required argument {param.name}")

    def bind(self, type_, cls_):
        self._bind[type_] = cls_

    def override(self, target_func, replacement):
        self._cache.pop(target_func, None)

    def clear_cache(self):
        self._cache.clear()


container = Container()


def inject(func=None):
    def decorator(inner_func):
        is_coro = inspect.iscoroutinefunction(inner_func)

        @wraps(inner_func)
        def sync_wrapper(*args, **kwargs):
            sig = inspect.signature(inner_func)
            bounds = sig.bind_partial(*args, **kwargs)
            for name, param in sig.parameters.items():
                if name in bounds.arguments:
                    continue
                kwargs[name] = container.resolve(param)
            return inner_func(*args, **kwargs)

        @wraps(inner_func)
        async def async_wrapper(*args, **kwargs):
            sig = inspect.signature(inner_func)
            bounds = sig.bind_partial(*args, **kwargs)
            for name, param in sig.parameters.items():
                if name in bounds.arguments:
                    continue
                kwargs[name] = container.resolve(param)
            return await inner_func(*args, **kwargs)

        return async_wrapper if is_coro else sync_wrapper

    if func is not None:
        return decorator(func)
    return decorator
