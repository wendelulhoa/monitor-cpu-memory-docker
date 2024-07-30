import docker

print(docker.from_env().containers.list())