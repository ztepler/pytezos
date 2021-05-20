import io
from os.path import split
import tarfile
from typing import List, Optional, Tuple
from pytezos.cli.utils import r
import docker  # type: ignore


def get_docker_client():
    return docker.from_env()


def run_container(
    image: str,
    command: str,
    copy_source: Optional[List[str]] = None,
    copy_destination: Optional[str] = None,
    mounts: Optional[List[Tuple[str, str]]] = None,
) -> docker.models.containers.Container:

    if copy_source is None:
        copy_source = []
    if mounts is None:
        mounts = []

    docker_mounts = [
        docker.types.Mount(
            source=source,
            target=target,
            type='bind',
        )
        for source, target in mounts
    ]

    client = get_docker_client()
    try:
        client.images.get(image)
    except docker.errors.ImageNotFound:
        client.api.pull(image)

    container = client.containers.create(
        image=image,
        command=command,
        detach=True,
        mounts=docker_mounts,
    )

    if copy_source and copy_destination:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            for filename in copy_source:
                _, short_filename = split(filename)
                archive.add(filename, arcname=short_filename)
        buffer.seek(0)
        container.put_archive(
            copy_destination,
            buffer,
        )

    container.start()
    return container


def wait_container(
    container: docker.models.containers.Container,
    error: str,
) -> bool:
    result = container.wait()
    status_code = int(result['StatusCode'])
    if status_code:
        for line in container.logs(stream=True):
            print(line.decode().rstrip())
        print(r(error))
        return False
    return True
