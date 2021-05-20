import atexit
from enum import Enum
from functools import partial
import importlib


import logging
import os
import random
import string
import sys
from os.path import dirname, exists, join, split, splitext
import time
from pprint import pformat
from typing import List, Optional

from jinja2 import Template
from pytezos.cli import ligo, smartpy
from pytezos.cli.utils import create_directory, r, g, b
from typing import Iterator, Optional, List, Tuple, Union, Iterator

import click


from pytezos import ContractInterface, __version__, pytezos
from pytezos.cli.cache import PyTezosCLICache
from pytezos.cli.context import Context
from pytezos.cli.docker import run_container
from pytezos.cli.github import create_deployment, create_deployment_status
from pytezos.cli.config import (
    CONFIG_NAME,
    GenericJobConfig,
    DEFAULT_LIGO_IMAGE,
    DEFAULT_SMARTPY_IMAGE,
    DEFAULT_SMARTPY_PROTOCOL,
    LigoConfig,
    PyTezosConfig,
    SmartPyConfig,
)
from pytezos.cli.utils import create_directory
from pytezos.context.mixin import default_network  # type: ignore
from pytezos.logging import logger
from pytezos.michelson.types.base import generate_pydoc
from pytezos.operation.result import OperationResult
from pytezos.rpc.errors import RpcError
from pytezos.sandbox.node import SandboxedNodeTestCase
from pytezos.sandbox.parameters import EDO, FLORENCE


def make_bcd_link(network, address):
    return f'https://better-call.dev/{network}/{address}'


def _input(option: str, default):
    input_str = b(f'{option} [') + g(default or '') + b(']: ')
    return input(input_str) or default


# TODO: Move to pytezos.contract
def get_contract(path: str) -> ContractInterface:
    if exists(path):
        contract = ContractInterface.from_file(path)
    else:
        network, address = path.split(':')
        contract = pytezos.using(shell=network).contract(address)
    return contract


@click.group()
@click.version_option(__version__)
@click.pass_context
def cli(ctx, *_args, **_kwargs):
    logging.basicConfig()
    cache = PyTezosCLICache()
    atexit.register(cache.sync)
    ctx.obj = dict(cache=cache)


@cli.command(help='Manage contract storage')
@click.option('--action', '-a', type=str, help='One of `schema`, `default`.')
@click.option('--path', '-p', type=str, help='Path to the .tz file, or the following uri: <network>:<KT-address>')
@click.pass_context
def storage(_ctx, action: str, path: str) -> None:
    contract = get_contract(path)
    if action == 'schema':
        logger.info(generate_pydoc(type(contract.storage.data), title='storage'))
    elif action == 'default':
        logger.info(pformat(contract.storage.dummy()))
    else:
        raise Exception('Action must be either `schema` or `default`')


@cli.command(help='Manage contract parameter')
@click.option('--action', '-a', type=str, default='schema', help='One of `schema`')
@click.option('--path', '-p', type=str, help='Path to the .tz file, or the following uri: <network>:<KT-address>')
@click.pass_context
def parameter(_ctx, action: str, path: str) -> None:
    contract = get_contract(path)
    if action == 'schema':
        logger.info(contract.parameter.__doc__)
    else:
        raise Exception('Action must be `schema`')


@cli.command(help='Activate and reveal key from the faucet file')
@click.option('--path', '-p', type=str, help='Path to the .json file downloaded from https://faucet.tzalpha.net/')
@click.option('--network', '-n', type=str, default=default_network, help='Default is edo2net')
@click.pass_context
def activate(_ctx, path: str, network: str) -> None:
    ptz = pytezos.using(key=path, shell=network)
    logger.info(
        'Activating %s in the %s',
        ptz.key.public_key_hash(),
        network,
    )

    if ptz.balance() == 0:
        try:
            opg = ptz.reveal().autofill().sign()
            logger.info('Injecting reveal operation:')
            logger.info(pformat(opg.json_payload()))
            opg.inject(_async=False)
        except RpcError as e:
            logger.critical(pformat(e))
            sys.exit(-1)
        else:
            logger.info('Activation succeeded! Claimed balance: %s ꜩ', ptz.balance())
    else:
        logger.info('Already activated')

    try:
        opg = ptz.reveal().autofill().sign()
        logger.info('Injecting reveal operation:')
        logger.info(pformat(opg.json_payload()))
        opg.inject(_async=False)
    except RpcError as e:
        logger.critical(pformat(e))
        sys.exit(-1)
    else:
        logger.info('Your key %s is now active and revealed', ptz.key.public_key_hash())


@cli.command(help='Deploy contract to the specified network')
@click.option('--path', '-p', type=str, help='Path to the .tz file')
@click.option('--storage', type=str, default=None, help='Storage in JSON format (not Micheline)')
@click.option('--network', '-n', type=str, default=default_network, help='Default is edo2net')
@click.option('--key', type=str, default=None)
@click.option('--github-repo-slug', type=str, default=None)
@click.option('--github-oauth-token', type=str, default=None)
@click.option('--dry-run', type=bool, default=False, help='Set this flag if you just want to see what would happen')
@click.pass_context
def deploy(
    _ctx,
    path: str,
    storage: Optional[str],  # pylint: disable=redefined-outer-name
    network: str,
    key: Optional[str],
    github_repo_slug: Optional[str],
    github_oauth_token: Optional[str],
    dry_run: bool,
):
    ptz = pytezos.using(shell=network, key=key)
    logger.info('Deploying contract using %s in the %s', ptz.key.public_key_hash(), network)

    contract = get_contract(path)
    try:
        opg = ptz.origination(script=contract.script(initial_storage=storage)).autofill().sign()
        logger.info('Injecting origination operation:')
        logger.info(pformat(opg.json_payload()))

        if dry_run:
            logger.info(pformat(opg.preapply()))
            sys.exit(0)
        else:
            opg = opg.inject(_async=False)
    except RpcError as e:
        logger.critical(pformat(e))
        sys.exit(-1)
    else:
        originated_contracts = OperationResult.originated_contracts(opg)
        if len(originated_contracts) != 1:
            raise Exception('Operation group must has exactly one originated contract')
        bcd_link = make_bcd_link(network, originated_contracts[0])
        logger.info('Contract was successfully deployed: %s', bcd_link)

        if github_repo_slug:
            deployment = create_deployment(
                github_repo_slug,
                github_oauth_token,
                environment=network,
            )
            logger.info(pformat(deployment))
            status = create_deployment_status(
                github_repo_slug,
                github_oauth_token,
                deployment_id=deployment['id'],
                state='success',
                environment=network,
                environment_url=bcd_link,
            )
            logger.info(status)


# @cli.command(help='Run SmartPy CLI command "test"')
# @click.option('--path', '-p', type=str, help='Path to script', default='script.py')
# @click.option('--output-directory', '-o', type=str, help='Output directory', default='./smartpy-output')
# @click.option('--protocol', type=click.Choice(['delphi', 'edo', 'florence', 'proto10']), help='Protocol to use', default='edo')
# @click.option('--image', '-i', type=str, help='Version or tag of SmartPy to use', default=DEFAULT_SMARTPY_IMAGE)
# @click.pass_context
# def smartpy_test(
#     _ctx,
#     path: str,
#     output_directory: str,
#     protocol: str,
#     image: str,
# ):
#     output_directory = create_directory(output_directory)
#     _, filename = split(path)
#     click.echo(b('Testing ') + g(filename) + b(' with SmartPy'))

#     container = run_container(
#         image=image,
#         command=f'test /root/smartpy-cli/{filename} /root/output --protocol {protocol}',
#         copy_source=[path],
#         copy_destination='/root/smartpy-cli/',
#         mounts=[
#             docker.types.Mount(
#                 target='/root/output',
#                 source=output_directory,
#                 type='bind',
#             )
#         ],
#     )
#     wait_container(container, f'Failed to test {filename}')
#     container.remove()


# @cli.command(help='Run SmartPy CLI command "compile"')
# @click.option('--path', '-p', type=str, help='Path to script', default='script.py')
# @click.option('--output-directory', '-o', type=str, help='Output directory', default='./smartpy-output')
# @click.option('--protocol', type=click.Choice(['delphi', 'edo', 'florence', 'proto10']), help='Protocol to use', default='edo')
# @click.option('--image', '-t', type=str, help='Version or tag of SmartPy to use', default=DEFAULT_SMARTPY_IMAGE)
# @click.pass_context
# def smartpy_compile(
#     ctx,
#     path: str,
#     output_directory: str,
#     protocol: str,
#     image: str,
# ):
#     if not ctx.obj['cache'].compilation_needed(path):
#         quit()

#     output_directory = create_directory(output_directory)
#     _, filename = split(path)
#     click.echo(b('Compiling ') + g(filename) + b(' with SmartPy'))

#     container = run_container(
#         image=image,
#         command=f'compile /root/smartpy-cli/{filename} /root/output --protocol {protocol}',
#         copy_source=[path],
#         copy_destination='/root/smartpy-cli/',
#         mounts=[(output_directory, '/root/output')]
#     )
#     success = wait_container(container, f'Failed to compile {filename}')
#     if not success:
#         ctx.obj['cache'].compilation_failed(path)
#     container.remove()


# @cli.command(help='Test project')
# @click.pass_context
# def test(
#     ctx,
# ):
#     for type_, name, path in discover_contracts():
#         if type_ == SourceLang.smartpy:
#             ctx.invoke(
#                 smartpy_test,
#                 path=path,
#                 output_directory=f'build/{name}',
#                 protocol='florence',
#             )


@cli.command(help='Init project')
@click.pass_context
def init(
    ctx,
):

    if exists(CONFIG_NAME):
        return

    config = PyTezosConfig(
        name=_input('Project name', os.path.split(os.getcwd())[1]),
        description=_input('Description', None),
        license=_input('License', None),
    )

    if click.confirm(b('Configure SmartPy compiler?')):
        config.smartpy = SmartPyConfig(
            image=_input('SmartPy Docker image', DEFAULT_SMARTPY_IMAGE),
            protocol=_input('SmartPy protocol', DEFAULT_SMARTPY_PROTOCOL),
        )

    if click.confirm(b('Configure LIGO compiler?')):
        config.ligo = LigoConfig(
            image=_input('LIGO Docker image', DEFAULT_LIGO_IMAGE),
        )

    config.save()

    while click.confirm(b('Add job?')):
        ctx.invoke(add_job)

    while click.confirm(b('Add scenario?')):
        ctx.invoke(add_scenario)


@cli.command(help='Add job')
@click.pass_context
def add_job(
    ctx,
):
    jobs_directory = create_directory('jobs')

    config = PyTezosConfig.load()
    random_name = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    name = _input('Job name', f'job_{random_name}')
    if name in config.jobs:
        raise Exception
    description = _input('Description', '')
    path = join(jobs_directory, name + '.py')

    job_config = GenericJobConfig(
        description=description,
        path=path,
    )
    config.jobs[name] = job_config
    config.save()

    with open(join(dirname(__file__), 'templates', 'generic_job.py.j2')) as file:
        template = Template(file.read())
    job_code = template.render()
    with open(path, 'w') as file:
        file.write(job_code)


@cli.command(help='Add scenario')
@click.pass_context
def add_scenario(
    ctx,
):
    config = PyTezosConfig.load()
    name = _input('Scenario name', 'default')
    if name in config.scenarios:
        raise Exception

    print(config.jobs.keys())
    jobs = _input('Space separated jobs', None)
    if not jobs:
        raise Exception
    config.scenarios[name] = jobs.split()
    config.save()


@cli.command(help='Run scenario')
@click.option('--name', '-n', type=str, help='Scenario name', default='default')
@click.pass_context
def run(ctx, name: str):
    config = PyTezosConfig.load()
    if name not in config.scenarios:
        raise Exception

    job_names = config.scenarios[name]

    context = Context()

    for job_name in job_names:
        job_config = config.jobs[job_name]

        loader = importlib.machinery.SourceFileLoader('job_' + job_name, job_config.path)
        module = loader.load_module('job_' + job_name)
        entrypoint = getattr(module, 'job')

        try:
            entrypoint(context)
        except Exception:
            raise


@cli.command(help='Run containerized sandbox node')
@click.option('--image', type=str, help='Docker image to use', default=SandboxedNodeTestCase.IMAGE)
@click.option('--protocol', type=click.Choice(['florence', 'edo']), help='Protocol to use', default='florence')
@click.option('--port', '-p', type=int, help='Port to expose', default=8732)
@click.option('--interval', '-i', type=float, help='Interval between baked blocks (in seconds)', default=1.0)
@click.option('--blocks', '-b', type=int, help='Number of blocks to bake before exit')
@click.pass_context
def sandbox(
    _ctx,
    image: str,
    protocol: str,
    port: int,
    interval: float,
    blocks: int,
):
    protocol = {
        'edo': EDO,
        'florence': FLORENCE,
    }[protocol]

    SandboxedNodeTestCase.PROTOCOL = protocol
    SandboxedNodeTestCase.IMAGE = image
    SandboxedNodeTestCase.PORT = port
    SandboxedNodeTestCase.setUpClass()

    blocks_baked = 0
    while True:
        try:
            logger.info('Baking block %s...', blocks_baked)
            block_hash = SandboxedNodeTestCase.get_client().using(key='bootstrap1').bake_block().fill().work().sign().inject()
            logger.info('Baked block: %s', block_hash)
            blocks_baked += 1

            if blocks and blocks_baked == blocks:
                break

            time.sleep(interval)
        except KeyboardInterrupt:
            break


@cli.command(help='Compile contract using Ligo compiler.')
@click.option('--image', '-i', type=str, help='Version or tag of Ligo compiler', default=DEFAULT_LIGO_IMAGE)
@click.option('--path', '-p', type=str, help='Path to contract')
@click.option('--workdir', '-w', type=str, default=None, help='Source directory root')
@click.option('--entrypoint', '-e', type=str, help='Entrypoint for the invocation')
@click.option('--output-directory', '-o', type=str, help='Output directory', default='./ligo-output')
@click.pass_context
def ligo_compile_contract(
    _ctx,
    image: str,
    path: str,
    workdir: Optional[str],
    entrypoint: str,
    output_directory: str,
):
    ligo.compile_contract(
        image,
        path,
        workdir,
        entrypoint,
        output_directory,
    )


@cli.command(help='Compile expression using Ligo compiler.')
@click.option('--image', '-i', type=str, help='Version or tag of Ligo compiler', default=DEFAULT_LIGO_IMAGE)
@click.option('--path', '-p', type=str, help='Path to expression')
@click.option('--workdir', '-w', type=str, default=None, help='Source directory root')
@click.option('--expression', '--exp', type=str, help='Expression for the storage', default='')
@click.option('--output-directory', '-o', type=str, help='Output directory', default='./ligo-output')
@click.pass_context
def ligo_compile_expression(
    _ctx,
    image: str,
    path: str,
    workdir: Optional[str],
    expression: str,
    output_directory: str,
):
    ligo.compile_expression(
        image,
        path,
        workdir,
        expression,
        output_directory,
    )

# @cli.command(help='Define initial storage using Ligo compiler.')
# @click.option('--image', '-t', type=str, help='Version or tag of Ligo compiler', default=DEFAULT_LIGO_IMAGE)
# @click.option('--path', '-p', type=str, help='Path to contract')
# @click.option('--entrypoint', '-e', type=str, help='Entrypoint for the storage', default='')
# @click.option('--expression', '--exp', type=str, help='Expression for the storage', default='')
# @click.option('--output-directory', '-o', type=str, help='Output directory', default='./ligo-output')
# @click.pass_context
# def ligo_compile_storage(
#     _ctx,
#     image: str,
#     path: str,
#     entrypoint: str,
#     expression: str,
#     output_directory: str,
# ):
#     output_directory = create_directory(output_directory)
#     _, filename = split(path)
#     click.echo(b('Compiling ') + g(filename) + b(' with LIGO'))

#     container = run_container(
#         image=image,
#         command=f'compile-storage {path} "{entrypoint}" "{expression}"',
#         copy_source=[path],
#         copy_destination='root',
#     )
#     success = wait_container(container, f'Failed to compile {filename}')
#     if success:
#         with open(join(output_directory, 'contract.tz'), 'w+') as file:
#             for line in container.logs(stream=True):
#                 file.write(line.decode())
#     container.remove()


# @cli.command(help='Invoke a contract with a parameter using Ligo compiler.')
# @click.option('--image', '-i', type=str, help='Version or tag of Ligo compiler', default=DEFAULT_LIGO_IMAGE)
# @click.option('--path', '-p', type=str, help='Path to contract')
# @click.option('--entry-point', '-ep', type=str, help='Entrypoint for the invocation')
# @click.option('--expression', '-ex', type=str, help='Expression for the invocation')
# @click.option('--output-directory', '-o', type=str, help='Output directory', default='./ligo-output')
# @click.pass_context
# def ligo_compile_parameter(_ctx, image: str, path: str, entrypoint: str, expression: str, output_directory: str):
#     output_directory = create_directory(output_directory)
#     _, filename = split(path)
#     click.echo(b('Compiling ') + g(filename) + b(' with LIGO'))

#     container = run_container(
#         image=image,
#         command=f'compile-parameter {path} "{entrypoint}" "{expression}"',
#         copy_source=[path],
#         copy_destination='root',
#     )
#     success = wait_container(container, f'Failed to compile {filename}')
#     if success:
#         with open(join(output_directory, 'contract.tz'), 'w+') as file:
#             for line in container.logs(stream=True):
#                 file.write(line.decode())
#     container.remove()


if __name__ == '__main__':
    cli(prog_name='pytezos')
