from genericpath import exists
import os
from os.path import join
import click
from functools import partial


r = partial(click.style, fg='red')
g = partial(click.style, fg='green')
b = partial(click.style, fg='blue')


def create_directory(path: str):
    path = join(os.getcwd(), path)
    if not exists(path):
        os.mkdir(path)
    return path
