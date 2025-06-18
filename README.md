# OAuth Authentication for Python CLI Tools: A Complete Guide

This repository contains code that was used for illustrating the article titled "[OAuth Authentication for Python CLI Tools: A Complete Guide](https://medium.com/@mskadu/oauth-authentication-for-python-cli-tools-a-complete-guide-453dca0c005b)"

## Setup (before you run the code)

### Set Up Your OAuth Application within Github

Before coding, you will need to register your application with GitHub:

1. Visit [GitHub Developer Settings](https://github.com/settings/developers)
2. Create a new OAuth App
3. Set the Authorization callback URL to <http://localhost:8080/callback>
4. Note your `Client ID` and `Client Secret`

### Set the code repo

- Clone the repo in a dedicated folder
- Create a virtual environment and activate it

```bash
cd <your repo folder name>
pip -m venv .venv
# OR if you are using uv - my preference
uv venv

source .venv/bin/activate 
```

- Install dependencies with:

```bash
pip install --requirements requirements.txt

# OR if you are using uv - my preference
uv sync
```

## Running the code

- Set up the necessary environment variables (using values from Github step)

```bash
export GITHUB_CLIENT_ID="your_client_id"
export GITHUB_CLIENT_SECRET="your_client_secret"
```

- Run the code

`python github_oauth_cli.py`
