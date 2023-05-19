import kopf

# import all your handlers here
from handlers import create_group_handler, create_role_handler, create_user_handler
from controllers import update_group_handler, update_user_handler
from controllers import delete_group_handler, delete_role_handler, delete_user_handler

GROUP = "k8sio.auth"
VERSION = "v1"
PLURAL = "users"
GPLURAL = "groups"
RPLURAL = "roles"
CRPLURAL = "clusterroles"


# define the Kopf operator
@kopf.on.create(GROUP, VERSION, GPLURAL)
def create_group_fn(body, spec, **kwargs):
    create_group_handler(body, spec, **kwargs)


@kopf.on.update(GROUP, VERSION, GPLURAL)
def update_group_fn(body, spec, **kwargs):
    update_group_handler(body, spec, **kwargs)


@kopf.on.delete(GROUP, VERSION, GPLURAL)
def delete_group_fn(body, **kwargs):
    delete_group_handler(body, **kwargs)


@kopf.on.create(GROUP, VERSION, RPLURAL)
@kopf.on.create(GROUP, VERSION, CRPLURAL)
@kopf.on.update(GROUP, VERSION, RPLURAL)
@kopf.on.update(GROUP, VERSION, CRPLURAL)
def create_role_fn(spec, **kwargs):
    create_role_handler(spec, **kwargs)


@kopf.on.delete(GROUP, VERSION, RPLURAL)
@kopf.on.delete(GROUP, VERSION, CRPLURAL)
def delete_role_fn(**kwargs):
    delete_role_handler(**kwargs)


@kopf.on.create(GROUP, VERSION, PLURAL)
def create_user_fn(body, spec, **kwargs):
    create_user_handler(body, spec, **kwargs)


@kopf.on.update(GROUP, VERSION, PLURAL)
def create_user_fn(body, spec, **kwargs):
    update_user_handler(body, spec, **kwargs)


@kopf.on.delete(GROUP, VERSION, PLURAL)
def delete_user_fn(body, **kwargs):
    delete_user_handler(body, **kwargs)


# start the operator
def main():
    kopf.run()


if __name__ == '__main__':
    main()
