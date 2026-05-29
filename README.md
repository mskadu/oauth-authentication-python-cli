# OAuth Authentication for Python CLI Tools: A Complete Guide

This repository contains code that was used for illustrating the article titled "[OAuth Authentication for Python CLI Tools: A Complete Guide](https://medium.com/@mskadu/oauth-authentication-for-python-cli-tools-a-complete-guide-453dca0c005b)"

## Setup

### Register Your OAuth App

Pick your provider and register an OAuth application:

**GitHub**
1. Visit [GitHub Developer Settings](https://github.com/settings/developers)
2. Create a new OAuth App
3. Set the Authorization callback URL to `http://localhost:8080/callback`
4. Note your `Client ID` and `Client Secret`

**Google**
1. Visit [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create an OAuth 2.0 Client ID (application type: "Web application")
3. Add `http://localhost:8080/callback` to Authorized redirect URIs
4. Note your `Client ID` and `Client Secret`

### Local setup

```bash
cd <your repo folder name>
uv venv && source .venv/bin/activate
uv sync
```

## Running the code

Set provider credentials via environment variables:

```bash
# GitHub (default)
export GITHUB_CLIENT_ID="your_client_id"
export GITHUB_CLIENT_SECRET="your_client_secret"
python oauth_cli.py

# Google
export GOOGLE_CLIENT_ID="your_client_id"
export GOOGLE_CLIENT_SECRET="your_client_secret"
python oauth_cli.py --provider google
```

### Override credentials via command line

Either or both can be supplied as arguments, overriding the corresponding env var:

```bash
python oauth_cli.py --client-id 9876 --client-secret pqrs
```

### All options

| Flag              | Default    | Description                                   |
|-------------------|------------|-----------------------------------------------|
| `--provider`      | `github`   | OAuth provider (`github`, `google`)           |
| `--client-id`     | —          | Override env-var-based client ID              |
| `--client-secret` | —          | Override env-var-based client secret          |
