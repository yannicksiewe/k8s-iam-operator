import kopf
import os
from app.config import Config
from .user_handlers import create_user_handler, update_user_handler, delete_user_handler
from .role_handlers import create_role_handler, delete_role_handler
from .group_handlers import create_group_handler, update_group_handler, delete_group_handler


# Setup tracer if enabled
if os.environ.get('ENABLE_TRACING', 'False') == 'True':
    from app.utils.tracing import setup_tracer
    tracer = setup_tracer()
else:
    tracer = None


# Define a decorator to handle tracing
def with_tracing(handler):
    def wrapper(*args, **kwargs):
        if tracer:
            with tracer.start_as_current_span(handler.__name__):
                return handler(*args, **kwargs)
        else:
            return handler(*args, **kwargs)
    return wrapper


# define the Kopf operator
@kopf.on.create(Config.GROUP, Config.VERSION, Config.GPLURAL)
@with_tracing
def create_group_fn(body, spec, **kwargs):
    create_group_handler(body, spec, **kwargs)


@kopf.on.update(Config.GROUP, Config.VERSION, Config.GPLURAL)
@with_tracing
def update_group_fn(body, spec, **kwargs):
    update_group_handler(body, spec, **kwargs)


@kopf.on.delete(Config.GROUP, Config.VERSION, Config.GPLURAL)
@with_tracing
def delete_group_fn(body, **kwargs):
    delete_group_handler(body, **kwargs)


@kopf.on.create(Config.GROUP, Config.VERSION, Config.RPLURAL)
@kopf.on.create(Config.GROUP, Config.VERSION, Config.CRPLURAL)
@kopf.on.update(Config.GROUP, Config.VERSION, Config.RPLURAL)
@kopf.on.update(Config.GROUP, Config.VERSION, Config.CRPLURAL)
@with_tracing
def create_role_fn(spec, **kwargs):
    create_role_handler(spec, **kwargs)


@kopf.on.delete(Config.GROUP, Config.VERSION, Config.RPLURAL)
@kopf.on.delete(Config.GROUP, Config.VERSION, Config.CRPLURAL)
@with_tracing
def delete_role_fn(**kwargs):
    delete_role_handler(**kwargs)


@kopf.on.create(Config.GROUP, Config.VERSION, Config.PLURAL)
@with_tracing
def create_user_fn(body, spec, **kwargs):
    create_user_handler(body, spec, **kwargs)


@kopf.on.update(Config.GROUP, Config.VERSION, Config.PLURAL)
@with_tracing
def update_user_fn(body, spec, **kwargs):
    update_user_handler(body, spec, **kwargs)


@kopf.on.delete(Config.GROUP, Config.VERSION, Config.PLURAL)
@with_tracing
def delete_user_fn(body, spec, **kwargs):
    delete_user_handler(body, spec, **kwargs)


# start the operator
def main():
    # Start Kopf
    kopf.run()
