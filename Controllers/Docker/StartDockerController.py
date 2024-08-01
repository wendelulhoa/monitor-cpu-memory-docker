import subprocess
import json
import time

class StartDockerController:
    def __init__(self):
        self.images = []
        self.containers = []

    def runCommand(self, command):
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout

    def getDockerImages(self):
        command = ["docker", "images", "--format", "{{json .}}"]
        result = self.runCommand(command)
        self.images = [json.loads(line) for line in result.splitlines()]

    def getContainerStatus(self):
        command = ["docker", "ps", "-a", "--format", "{{json .}}"]
        result = self.runCommand(command)
        self.containers = [json.loads(line) for line in result.splitlines()]

    def startInactiveContainers(self):
        for container in self.containers:
            if container["State"] == "exited":
                container_id = container["ID"]
                print(f"Starting container {container_id}")
                start_command = ["docker", "start", container_id]
                self.runCommand(start_command)

    def displayContainers(self):
        print("Docker Containers:")
        for container in self.containers:
            status = "active" if container["State"] == "running" else "inactive"
            print(f'Container ID: {container["ID"]}, Status: {status}')

def main():
    manager = StartDockerController()
    while True:
        try:
            manager.getDockerImages()
            manager.getContainerStatus()
            manager.displayContainers()
            manager.startInactiveContainers()
        except Exception as e:
            print(f"An error occurred: {e}")
        time.sleep(10)

if __name__ == "__main__":
    main()
