from genericpath import exists
import os
from os.path import join
from typing import Optional
from pydantic import BaseModel
from pytezos.cli import ligo, smartpy
from pytezos.cli.config import DEFAULT_LIGO_IMAGE
from pytezos.cli.utils import create_directory


class ContractArtifact(BaseModel):
    path: str


class ParameterArtifact(BaseModel):
    path: str


class LambdaArtifact(BaseModel):
    path: str


def compile_contract(
    alias: str,
    path: str,
    workdir: Optional[str] = None,
    entrypoint: Optional[str] = None,
) -> ContractArtifact:
    if not exists(path):
        raise Exception

    output_directory = create_directory(join(os.getcwd(), 'build', alias))

    if path.endswith('ligo'):
        if entrypoint is None:
            raise Exception
        ligo.compile_contract(
            image=DEFAULT_LIGO_IMAGE,
            path=path,
            workdir=workdir,
            entrypoint=entrypoint,
            output_directory=output_directory,
        )
        return ContractArtifact(path=join(output_directory, 'contract.tz'))
    else:
        raise NotImplementedError



def compile_parameter(
    alias: str,
    path: str,
    expression: str,
    workdir: Optional[str] = None,
    entrypoint: Optional[str] = None,
) -> ParameterArtifact:
    if not exists(path):
        raise Exception

    output_directory = create_directory(join(os.getcwd(), 'build', alias))

    if path.endswith('ligo'):
        if entrypoint is None:
            raise Exception
        ligo.compile_parameter(
            image=DEFAULT_LIGO_IMAGE,
            path=path,
            workdir=workdir,
            expression=expression,
            entrypoint=entrypoint,
            output_directory=output_directory,
        )
        return ParameterArtifact(path=join(output_directory, 'parameter.tz'))
    else:
        raise NotImplementedError


def compile_lambda(
    alias: str,
    path: str,
    workdir: Optional[str] = None,
) -> LambdaArtifact:
    if not exists(path):
        raise Exception

    output_directory = create_directory(join(os.getcwd(), 'build', alias))

    if path.endswith('ligo'):
        ligo.compile_expression(
            image=DEFAULT_LIGO_IMAGE,
            path=path,
            workdir=workdir,
            expression='lambda',
            output_directory=output_directory,
        )
        return LambdaArtifact(path=join(output_directory, 'lambda.tz'))
    else:
        raise NotImplementedError
