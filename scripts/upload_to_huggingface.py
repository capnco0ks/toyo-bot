import os
import sys
from huggingface_hub import HfApi


def upload_space(token: str, repo_id: str = "capncooks/toyobot"):
    api = HfApi(token=token)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    print(f"🚀 Uploading Toyo-bot files to Hugging Face Space: {repo_id}...")

    # Upload folder excluding virtual environments and caches
    api.upload_folder(
        folder_path=project_root,
        repo_id=repo_id,
        repo_type="space",
        ignore_patterns=[
            ".venv/*",
            ".venv/**",
            "__pycache__/*",
            "*.pyc",
            ".pytest_cache/*",
            ".git/*",
            ".dockerignore",
            "tests/*",
        ],
    )
    print("✅ Upload completed successfully!")
    print(f"🔗 Open your space: https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/upload_to_huggingface.py <HF_ACCESS_TOKEN>")
        print("Get your token with WRITE permission at: https://huggingface.co/settings/tokens")
        sys.exit(1)

    hf_token = sys.argv[1].strip()
    upload_space(token=hf_token)
