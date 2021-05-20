from os.path import join, split
from typing import Optional
from pytezos.cli.docker import run_container, wait_container
from pytezos.cli.utils import r, g, b, create_directory


def compile_contract(
    image: str,
    path: str,
    workdir: Optional[str],
    entrypoint: str,
    output_directory: str,
):
    output_directory = create_directory(output_directory)
    if workdir:
        workdir = create_directory(workdir)
    _, filename = split(path)
    print(b('Compiling ') + g(filename) + b(' with LIGO'))

    if workdir:
        mounts = [(workdir, '/root/src')]
        command = f'compile-contract {path} "{entrypoint}"'
    else:
        mounts = [(path, f'/root/{filename}')]
        command = f'compile-contract {filename} "{entrypoint}"'

    container = run_container(
        image=image,
        command=command,
        copy_source=[path],
        copy_destination='/root/',
        mounts=mounts,
    )
    success = wait_container(container, f'Failed to compile {filename}')
    if success:
        with open(join(output_directory, 'contract.tz'), 'w+') as file:
            for line in container.logs(stream=True, stderr=False):
                file.write(line.decode())
    container.remove()


def compile_parameter(
    image: str,
    path: str,
    workdir: Optional[str],
    expression: str,
    entrypoint: str,
    output_directory: str,
):
    output_directory = create_directory(output_directory)
    if workdir:
        workdir = create_directory(workdir)
    _, filename = split(path)
    print(b('Compiling ') + g(filename) + b(' with LIGO'))

    if workdir:
        mounts = [(workdir, '/root/src')]
        command = f'compile-parameter {path} "{entrypoint}" "{expression}"'
    else:
        mounts = [(path, f'/root/{filename}')]
        command = f'compile-parameter {filename} "{entrypoint}" "{expression}"'

    container = run_container(
        image=image,
        command=command,
        copy_source=[path],
        copy_destination='/root/',
        mounts=mounts,
    )
    success = wait_container(container, f'Failed to compile {filename}')
    if success:
        with open(join(output_directory, 'parameter.tz'), 'w+') as file:
            for line in container.logs(stream=True, stderr=False):
                file.write(line.decode())
    container.remove()


def compile_expression(
    image: str,
    path: str,
    workdir: Optional[str],
    expression: str,
    output_directory: str,
):
    output_directory = create_directory(output_directory)
    if workdir:
        workdir = create_directory(workdir)
    _, filename = split(path)
    print(b('Compiling ') + g(filename) + b(' with LIGO'))

    if workdir:
        mounts = [(workdir, '/root/src')]
        command = f'compile-expression --init-file {path} cameligo "{expression}"'
    else:
        mounts = [(path, f'/root/{filename}')]
        command = f'compile-expression --init-file {filename} cameligo "{expression}"'

    container = run_container(
        image=image,
        command=command,
        copy_source=[path],
        copy_destination='/root/',
        mounts=mounts,
    )
    success = wait_container(container, f'Failed to compile {filename}')
    if success:
        with open(join(output_directory, 'lambda.tz'), 'w+') as file:
            for line in container.logs(stream=True, stderr=False):
                file.write(line.decode())
    container.remove()
