# Flassklist

A web-based search interface for the **Compilation Of Many Breaches** (COMB) dataset. This application allows users to quickly search through the breach data folder (the "passlist" data) and retrieve results from compromised datasets.

The project uses Flask for the web application, Redis for caching and rate limiting, and optional RAM disk support for faster file access. It is containerized with Docker and can be deployed using Docker Compose.

You can find a magnet link for COMB here: https://gist.github.com/fawazahmed0/79764af8a026a9a5b380728e67f786d4

---

## Features

- **Responsive Design:** Uses Bootstrap to provide a mobile-friendly interface.
- **Secure Search:** Prevents path traversal and XSS attacks.
- **Rate Limiting:** Protects the application from DoS attacks with Flask-Limiter.
- **Redis Caching:** Speeds up repeated searches.
- **Optional RAM Disk:** Improves file access performance by utilizing a RAM disk.

---

## Environment Variables

The following environment variables are used by the application:

- **COMB_PASSLIST_DATA**  
  Path to the breach data folder.  
  _Default: `/passlistdata`_

- **COMB_RAMDISK_DIR (optional)**  
  Path to the RAM disk directory. If this directory exists, data is copied to it for faster access.  
  _Default: `/ramdiskdata`_

- **COMB_USE_PROXY**  
  Whether to use proxy settings (useful behind Nginx or another reverse proxy).  
  _Default: `False` (set to `True` in docker-compose if needed)_

- **COMB_REDIS_URL**  
  The Redis connection URL for caching and rate limiting.  
  _Default in Docker Compose: `redis://redis:6379`  
  Default locally: `redis://localhost:6379`_


---

## Getting Started

### Running Locally

Ensure you have Redis installed and running on your local machine.

1. **Clone the repository:**

   ```bash
   git clone https://github.com/babatonga/flassklist.git
   cd flassklist
   ```

2. **Set the environment variables** (if necessary):

   ```bash
   export COMB_PASSLIST_DATA=/path/to/your/data
   export COMB_REDIS_URL=redis://localhost:6379
   ```

3. **Start the application using the start script:**

   ```bash
   ./start.sh
   ```

   The application will run at [http://127.0.0.1:8080](http://127.0.0.1:8080).

### Running with Docker Compose

The project includes a `compose.yaml` file that sets up the Flask app and Redis in separate containers.

1. **Setup mounts of flassklist service in compose.yaml**
    ```yaml
        volumes:
            - /path/to/comb/data:/passlistdata
            #- /path/to/tmpfs:/ramdiskdata # optional ramdisk for faster access (needs ~107GB RAM tmpfs!)
    ```

2. **Build and run using Docker Compose:**

   ```bash
   docker compose up --build
   ```

3. **Access the application:**

   The Flask app will be available on port `8080`.

**Notes:**
- The `entrypoint.sh` script handles copying data to the RAM disk if available.
- The Dockerfile configures the production environment using Gunicorn with 4 workers.
- Redis is required as it serves both caching and rate limiting purposes.

---

## Files Overview

- **Dockerfile:**  
  Defines the container image based on Python 3, sets the working directory to `/app`, copies the application files, installs dependencies, and uses `entrypoint.sh` to start the app.

- **compose.yaml:**  
  Sets up the services for Redis and the Flask application. Redis runs using the official Redis Alpine image, while the Flask app is built from the Dockerfile. Volumes are used to mount the data directory and optionally a RAM disk.

- **start.sh:**  
  A script for local development. It sets up the necessary environment variables and starts the Flask app with Gunicorn.

---

## To Do:
* Improve query function (allow searching for passwords)
* Add REST API

---

## License

This project is licensed under the [MIT License](LICENSE).

---


Happy Searching!
