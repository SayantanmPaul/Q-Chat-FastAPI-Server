import subprocess
import time
import requests

def run_command(command):
    """Runs a shell command with error handling."""
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing {command}: {e}")
        exit(1)

def build_image():
    print("\n🚀 Building the Docker image...")
    run_command(["docker", "build", "-t", "fastapi-multi-stage", "."])


def run_container():
    print("\n🚀 Running the container...")
    run_command(["docker", "run", "-d", "-p", "8000:8000", "--name", "fastapi-app", "fastapi-multi-stage"])
    time.sleep(3)

def check_status():
    """Check if the container is running by calling the /status endpoint."""
    url = "http://localhost:8000/api/v2/health"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("\n✅ Application is running successfully!")
            print(f"Response: {response.json()}")
        else:
            print(f"\n⚠️ Unexpected response: {response.status_code}")
    except requests.exceptions.RequestException:
        print("\n❌ Application failed to start. Check logs.")

if __name__ == "__main__":
    build_image()
    run_container()
    check_status()

    print("\n📸 The container is running and ready for Docker Scout scanning.")
    print("🛑 To stop and remove the container, run: docker stop fastapi-app && docker rm fastapi-app")