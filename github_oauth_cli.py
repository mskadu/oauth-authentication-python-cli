#!/usr/bin/env python3
"""
GitHub OAuth CLI Authentication Example
A complete implementation showing OAuth2 flow for CLI tools
"""

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


class OAuthConfig:
    """Configuration for OAuth2 authentication"""

    def __init__(self):
        self.client_id = os.getenv("GITHUB_CLIENT_ID")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        self.authorization_base_url = "https://github.com/login/oauth/authorize"
        self.token_url = "https://github.com/login/oauth/access_token"
        self.redirect_uri = "http://localhost:8080/callback"
        self.scope = ["user", "repo"]

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables"
            )


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback"""

    def do_GET(self):
        """Handle GET request to callback URL"""
        if self.path.startswith("/callback"):
            # Parse the authorization code from the callback URL
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
        """Suppress log messages"""
        pass


class GitHubOAuthCLI:
    """GitHub OAuth authentication for CLI tools"""

    def __init__(self):
        self.config = OAuthConfig()
        self.token_file = os.path.expanduser("~/.github_cli_token.json")
        self.session = None

    def get_stored_token(self):
        """Retrieve stored access token if available"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r") as f:
                    token_data = json.load(f)
                    return token_data
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def store_token(self, token):
        """Securely store access token"""
        try:
            # Ensure the file is only readable by the user
            with open(self.token_file, "w") as f:
                json.dump(token, f, indent=2)
            os.chmod(self.token_file, 0o600)  # Read/write for owner only
        except IOError as e:
            print(f"Error storing token: {e}")

    def start_local_server(self):
        """Start local HTTP server to handle OAuth callback"""
        server = HTTPServer(("localhost", 8080), CallbackHandler)
        server.auth_code = None

        # Start server in a separate thread
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        return server

    def authenticate(self):
        """Perform OAuth2 authentication flow"""
        print("Starting GitHub OAuth authentication...")

        # Check if we have a stored valid token
        stored_token = self.get_stored_token()
        if stored_token:
            print("Found stored token, testing validity...")
            if self.test_token(stored_token["access_token"]):
                print("Stored token is valid!")
                return stored_token["access_token"]
            else:
                print("Stored token is invalid, starting new authentication...")

        # Start local server to handle callback
        server = self.start_local_server()

        try:
            # Create OAuth2 session
            github = OAuth2Session(
                self.config.client_id,
                scope=self.config.scope,
                redirect_uri=self.config.redirect_uri,
            )

            # Generate authorization URL
            authorization_url, state = github.authorization_url(
                self.config.authorization_base_url, state=secrets.token_urlsafe(32)
            )

            print("Opening browser for authentication...")
            print(
                f"If the browser doesn't open automatically, visit: {authorization_url}"
            )

            # Open browser
            webbrowser.open(authorization_url)

            # Wait for callback
            print("Waiting for authentication callback...")
            timeout = 120  # 2 minutes timeout
            elapsed = 0

            while server.auth_code is None and elapsed < timeout:
                time.sleep(1)
                elapsed += 1

            if server.auth_code is None:
                raise TimeoutError("Authentication timed out")

            print("Authorization code received, exchanging for access token...")

            # Exchange authorization code for access token
            token = github.fetch_token(
                self.config.token_url,
                authorization_response=f"{self.config.redirect_uri}?code={server.auth_code}",
                client_secret=self.config.client_secret,
            )

            # Store token for future use
            self.store_token(token)
            print("Authentication successful! Token stored securely.")

            return token["access_token"]

        finally:
            server.shutdown()

    def test_token(self, access_token):
        """Test if access token is valid"""
        try:
            headers = {"Authorization": f"token {access_token}"}
            response = requests.get("https://api.github.com/user", headers=headers)
            return response.status_code == 200
        except Exception:
            return False

    def make_authenticated_request(self, access_token, endpoint):
        """Make an authenticated request to GitHub API"""
        headers = {"Authorization": f"token {access_token}"}
        response = requests.get(f"https://api.github.com/{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()


def main():
    """Main CLI application"""
    try:
        oauth_cli = GitHubOAuthCLI()
        access_token = oauth_cli.authenticate()

        # Make an authenticated request to demonstrate functionality
        print("\nFetching your GitHub profile information...")
        user_info = oauth_cli.make_authenticated_request(access_token, "user")

        print(f"Hello, {user_info['name']} (@{user_info['login']})!")
        print(f"You have {user_info['public_repos']} public repositories.")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
