#!/usr/bin/env python3
"""
OAuth CLI Authentication Example — multi-provider
Supports GitHub (default) and Google via --provider flag.
"""

import argparse
import json
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import requests
from requests_oauthlib import OAuth2Session


PROVIDERS = {
    "github": {
        "name": "GitHub",
        "authorization_base_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scope": ["user", "repo"],
        "client_id_env": "GITHUB_CLIENT_ID",
        "client_secret_env": "GITHUB_CLIENT_SECRET",
        "user_info_url": "https://api.github.com/user",
        "auth_header_prefix": "token",
        "user_info": lambda d: f"{d['name']} (@{d['login']}) — {d['public_repos']} public repos",
    },
    "google": {
        "name": "Google",
        "authorization_base_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": ["openid", "email", "profile"],
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "auth_header_prefix": "Bearer",
        "user_info": lambda d: f"{d.get('name', d.get('email', 'User'))} — {d.get('email', 'no email')}",
    },
}

DEFAULT_PROVIDER = "github"


class OAuthConfig:
    def __init__(self, provider: str, client_id: str | None = None, client_secret: str | None = None):
        if provider not in PROVIDERS:
            raise ValueError(f"Unsupported provider '{provider}'. Choose from: {', '.join(PROVIDERS)}")

        cfg = PROVIDERS[provider]
        self.provider = provider
        self.provider_name = cfg["name"]
        self.authorization_base_url = cfg["authorization_base_url"]
        self.token_url = cfg["token_url"]
        self.scope = cfg["scope"]
        self.redirect_uri = "http://localhost:8080/callback"
        self.user_info_url = cfg["user_info_url"]
        self.auth_header_prefix = cfg["auth_header_prefix"]
        self.user_info_mapping = cfg["user_info"]

        self.client_id = client_id or os.getenv(cfg["client_id_env"])
        self.client_secret = client_secret or os.getenv(cfg["client_secret_env"])

        missing = []
        if not self.client_id:
            missing.append(f"{cfg['client_id_env']} (or --client-id)")
        if not self.client_secret:
            missing.append(f"{cfg['client_secret_env']} (or --client-secret)")
        if missing:
            raise ValueError(
                f"Missing credentials for {self.provider_name}: {', '.join(missing)}"
            )


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/callback"):
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)

            if "code" in query_params:
                self.server.auth_code = query_params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                success_html = """
                <html>
                <body>
                    <h2>Authentication Successful!</h2>
                    <p>You can now close this window and return to your terminal.</p>
                    <script>window.close();</script>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode())
            else:
                self.send_error(400, "Authorization code not found")
        else:
            self.send_error(404, "Path not found")

    def log_message(self, format, *args):
        pass


class OAuthCLI:
    def __init__(self, config: OAuthConfig):
        self.config = config
        self.token_file = os.path.expanduser(f"~/.{config.provider}_cli_token.json")

    def get_stored_token(self):
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def store_token(self, token):
        try:
            with open(self.token_file, "w") as f:
                json.dump(token, f, indent=2)
            os.chmod(self.token_file, 0o600)
        except IOError as e:
            print(f"Error storing token: {e}")

    def start_local_server(self):
        server = HTTPServer(("localhost", 8080), CallbackHandler)
        server.auth_code = None
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        return server

    def authenticate(self):
        print(f"Starting {self.config.provider_name} OAuth authentication...")

        stored_token = self.get_stored_token()
        if stored_token:
            print("Found stored token, testing validity...")
            if self.test_token(stored_token["access_token"]):
                print("Stored token is valid!")
                return stored_token["access_token"]
            print("Stored token is invalid, starting new authentication...")

        server = self.start_local_server()

        try:
            oauth = OAuth2Session(
                self.config.client_id,
                scope=self.config.scope,
                redirect_uri=self.config.redirect_uri,
            )

            authorization_url, state = oauth.authorization_url(
                self.config.authorization_base_url,
                state=secrets.token_urlsafe(32),
            )

            print(f"Opening browser for {self.config.provider_name} authentication...")
            print(f"If the browser doesn't open automatically, visit: {authorization_url}")
            webbrowser.open(authorization_url)

            print("Waiting for authentication callback...")
            timeout = 120
            elapsed = 0
            while server.auth_code is None and elapsed < timeout:
                time.sleep(1)
                elapsed += 1

            if server.auth_code is None:
                raise TimeoutError("Authentication timed out")

            print("Authorization code received, exchanging for access token...")

            token = oauth.fetch_token(
                self.config.token_url,
                authorization_response=f"{self.config.redirect_uri}?code={server.auth_code}",
                client_secret=self.config.client_secret,
            )

            self.store_token(token)
            print("Authentication successful! Token stored securely.")
            return token["access_token"]
        finally:
            server.shutdown()

    def test_token(self, access_token):
        try:
            headers = {"Authorization": f"{self.config.auth_header_prefix} {access_token}"}
            response = requests.get(self.config.user_info_url, headers=headers)
            return response.status_code == 200
        except Exception:
            return False

    def make_authenticated_request(self, access_token):
        headers = {"Authorization": f"{self.config.auth_header_prefix} {access_token}"}
        response = requests.get(self.config.user_info_url, headers=headers)
        response.raise_for_status()
        return response.json()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OAuth2 authentication for CLI tools — multi-provider support",
    )
    parser.add_argument(
        "--provider",
        default=DEFAULT_PROVIDER,
        choices=list(PROVIDERS),
        help=f"OAuth provider to use (default: {DEFAULT_PROVIDER})",
    )
    parser.add_argument("--client-id", help="Override the client ID (env var takes precedence if not set)")
    parser.add_argument("--client-secret", help="Override the client secret (env var takes precedence if not set)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        config = OAuthConfig(
            provider=args.provider,
            client_id=args.client_id,
            client_secret=args.client_secret,
        )
        cli = OAuthCLI(config)
        access_token = cli.authenticate()

        print(f"\nFetching your {config.provider_name} profile information...")
        user_data = cli.make_authenticated_request(access_token)
        print(f"Hello, {config.user_info_mapping(user_data)}!")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
