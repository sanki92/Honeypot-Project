from flask import Flask, Response, request
import os

app = Flask(__name__)
PERSONA = os.getenv("APP_PERSONA", "wordpress").strip().lower()
VERSION = os.getenv("APP_VERSION", "unknown")


def html(title: str, body: str) -> Response:
    return Response(
        f"<!doctype html><html><head><title>{title}</title></head><body>{body}</body></html>",
        mimetype="text/html",
    )


@app.get("/")
def index() -> Response:
    if PERSONA == "wordpress":
        body = (
            "<h1>WordPress</h1>"
            f"<meta name=\"generator\" content=\"WordPress {VERSION}\">"
            "<p>Welcome to WordPress.</p>"
            "<a href=\"/wp-login.php\">Log in</a>"
        )
        return html("WordPress", body)

    if PERSONA == "joomla":
        body = (
            "<h1>Joomla!</h1>"
            f"<meta name=\"generator\" content=\"Joomla! - Open Source CMS {VERSION}\">"
            "<p>Joomla content management system.</p>"
            "<a href=\"/administrator/index.php\">Administrator</a>"
        )
        return html("Joomla", body)

    body = (
        "<h1>phpMyAdmin</h1>"
        f"<meta name=\"generator\" content=\"phpMyAdmin {VERSION}\">"
        "<p>Database administration interface.</p>"
        "<a href=\"/phpmyadmin/index.php\">Open phpMyAdmin</a>"
    )
    return html("phpMyAdmin", body)


@app.get("/wp-login.php")
def wp_login() -> Response:
    return html(
        "WordPress Login",
        "<h2>Log In</h2><form method='post'><input name='log'><input name='pwd' type='password'></form>",
    )


@app.post("/xmlrpc.php")
def xmlrpc() -> Response:
    payload = request.get_data(as_text=True)
    if "system.multicall" in payload:
        return Response("<methodResponse><fault>blocked</fault></methodResponse>", mimetype="text/xml")
    return Response("<methodResponse><params /></methodResponse>", mimetype="text/xml")


@app.get("/administrator/index.php")
def joomla_admin() -> Response:
    return html(
        "Joomla Administrator",
        "<h2>Joomla! Administration Login</h2><form method='post'><input name='username'><input name='passwd' type='password'></form>",
    )


@app.get("/language/en-GB/en-GB.xml")
def joomla_lang() -> Response:
    return Response(
        f"<metafile><name>Joomla</name><version>{VERSION}</version></metafile>",
        mimetype="application/xml",
    )


@app.get("/phpmyadmin/")
@app.get("/phpmyadmin/index.php")
def pma_login() -> Response:
    return html(
        "phpMyAdmin",
        "<h2>Welcome to phpMyAdmin</h2><form method='post'><input name='pma_username'><input name='pma_password' type='password'></form>",
    )


@app.get("/robots.txt")
def robots() -> Response:
    return Response("User-agent: *\nAllow: /\n", mimetype="text/plain")


@app.get("/login.html")
def legacy_login() -> Response:
    return Response(
        "<!doctype html><html><head><title>Login</title></head><body>"
        "<h3>Add entry</h3><p> Add another Article</p>"
        "<form action=\"login.html\" method=\"post\">"
        "<label for=\"username\">Username</label> <input type=\"username\" id=\"usename\" name=\"username\"><br /><br />"
        "<label for=\"password\">Password:</label> <input type=\"text\" id=\"password\" name=\"password\"><br /><br />"
        "<button type=\"submit\">Login</button></form>"
        "</body></html>",
        mimetype="text/html",
    )


@app.get("/healthz")
def healthz() -> Response:
    return Response("ok", mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
