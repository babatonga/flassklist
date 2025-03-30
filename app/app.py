from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
)
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from decouple import config
from werkzeug.middleware.proxy_fix import ProxyFix
from logging.config import dictConfig
import os
import multiprocessing
import time

# Logging configuration
dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

# Environment variables
LOCAL_PASSLISTDATA = config(
    "COMB_PASSLIST_DATA",
    default="/passlistdata",
)
RAMDISK_DIR = config("COMB_RAMDISK_DIR", default="/ramdiskdata")
RAM_PASSLISTDATA = os.path.join(RAMDISK_DIR, "data")

USE_PROXY = config("COMB_USE_PROXY", default=False, cast=bool)

REDIS_URL = config("COMB_REDIS_URL", default="redis://redis:6379")

# Flask app
app = Flask(__name__)

if USE_PROXY:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Redis
app.config["CACHE_TYPE"] = "RedisCache"
app.config["CACHE_REDIS_URL"] = REDIS_URL
cache = Cache(app)

# Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=REDIS_URL,
    storage_options={"socket_connect_timeout": 30},
    default_limits=["10 per minute", "1 per second"],
)

if not os.path.exists(LOCAL_PASSLISTDATA):
    app.logger.error(f"Data directory not found: {LOCAL_PASSLISTDATA}")
    exit(1)

if os.path.exists(RAM_PASSLISTDATA):
    PASSLISTDATA = RAM_PASSLISTDATA
    app.logger.info(f"Using RAM disk data directory: {RAM_PASSLISTDATA}")
else:
    app.logger.warning(f"RAM disk not found: {RAMDISK_DIR}")
    PASSLISTDATA = LOCAL_PASSLISTDATA
    app.logger.info(f"Using local data directory: {LOCAL_PASSLISTDATA}")


def is_safe_path(base_path, path):
    abs_base = os.path.abspath(base_path)
    abs_path = os.path.abspath(path)
    return abs_path.startswith(abs_base)


def search_query(query):
    """
    Searches the comb dataset for lines starting with the given query (case-insensitive).

    The function builds a list of potential file paths based on the query letters.
    For queries with 4 or more characters (e.g., "chri"), it first tries:
      PASSLISTDATA / letter1 / letter2 / letter3 / letter4
    Then Fallbacks:
      - PASSLISTDATA / letter1 / letter2 / letter3
      - PASSLISTDATA / letter1 / letter2 / symbols
      - PASSLISTDATA / letter1 / letter2
      - PASSLISTDATA / letter1 / symbols
      - PASSLISTDATA / letter1
      - PASSLISTDATA / symbols
    The first existing file is used to search for lines starting with the query.
    """
    import os

    results = []
    results_len = 0
    if not query:
        return results

    q_lower = query.lower()
    potential_paths = []

    if len(q_lower) >= 4:
        potential_paths.append(
            os.path.join(PASSLISTDATA, q_lower[0], q_lower[1], q_lower[2], q_lower[3])
        )

    if len(q_lower) >= 3:
        potential_paths.append(
            os.path.join(PASSLISTDATA, q_lower[0], q_lower[1], q_lower[2])
        )
        potential_paths.append(
            os.path.join(PASSLISTDATA, q_lower[0], q_lower[1], "symbols")
        )

    if len(q_lower) >= 2:
        potential_paths.append(os.path.join(PASSLISTDATA, q_lower[0], q_lower[1]))
        potential_paths.append(os.path.join(PASSLISTDATA, q_lower[0], "symbols"))

    potential_paths.append(os.path.join(PASSLISTDATA, q_lower[0]))

    potential_paths.append(os.path.join(PASSLISTDATA, "symbols"))

    candidate_file = None
    for path in potential_paths:
        if is_safe_path(PASSLISTDATA, path) and os.path.isfile(path):
            candidate_file = path
            break

    if candidate_file:
        try:
            with open(candidate_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.lower().startswith(q_lower):
                        if results_len >= 100:
                            return results
                        results.append(line.strip())
                        results_len += 1
        except Exception as e:
            print(f"Error reading file {candidate_file}: {e}")
    else:
        print(f"No candidate file found for query '{query}'. Tried: {potential_paths}")

    return results


def search_query_with_timeout(query, timeout=5):
    with multiprocessing.Pool(1) as pool:
        result = pool.apply_async(search_query, (query,))
        try:
            return result.get(timeout=timeout)
        except multiprocessing.TimeoutError:
            return TimeoutError


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def search():
    results = []
    warning = None
    error = None
    min_query_len = 6
    max_query_len = 50
    if request.method == "POST":
        query = request.form.get("query", "")
        query = query.strip()
        return redirect(url_for("search", query=query))

    elif request.method == "GET":
        query = request.args.get("query", "")
        if query:
            if len(query) < min_query_len:
                return render_template(
                    "search.html",
                    query=query,
                    error=f"Query must be at least {min_query_len} characters",
                )
            elif len(query) > max_query_len:
                return render_template(
                    "search.html",
                    query=query,
                    error=f"Query must be at most {max_query_len} characters",
                )
            try:
                search_time = time.time()
                cache_key = f"search_results:{query.lower()}"
                results = cache.get(cache_key)
                if results is None or len(results) == 0:
                    results = search_query_with_timeout(query)
                    cache.set(cache_key, results, timeout=600)
                search_duration = time.time() - search_time
                app.logger.debug(
                    f"Search query: {query}, results: {len(results)}, duration: {search_duration:.2f}s"
                )
                if len(results) >= 100:
                    warning = "More than 100 results found. Only showing the first 100."
                elif len(results) == 0:
                    warning = f"No results found for query '{query}'."
            except TimeoutError:
                return render_template(
                    "search.html",
                    query=query,
                    error="Search took too long. Please try a different query.",
                )

    return render_template(
        "search.html", results=results, warning=warning, error=error, query=query
    )


@app.errorhandler(429)
def ratelimit_handler(e):
    query = request.args.get("query", "")
    error_message = f"Too many requests: {e.description}"
    return render_template("search.html", error=error_message, query=query), 429


if __name__ == "__main__":
    app.run(debug=False)
