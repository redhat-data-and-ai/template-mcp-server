FROM registry.access.redhat.com/ubi9/python-312:latest

# --------------------------------------------------------------------------------------------------
# set the working directory to /app
# --------------------------------------------------------------------------------------------------

WORKDIR /app

# --------------------------------------------------------------------------------------------------
# Copy manifest files and install python packages
# --------------------------------------------------------------------------------------------------

USER root
COPY pyproject.toml /app/pyproject.toml
RUN pip install uv \
    && uv venv \
    && uv pip install -r pyproject.toml
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
USER default

# --------------------------------------------------------------------------------------------------
# copy source code and files
# --------------------------------------------------------------------------------------------------

COPY template_mcp_server /app/template_mcp_server
COPY run_server.py /app/run_server.py

# --------------------------------------------------------------------------------------------------
# Set PYTHONPATH to include /app
# --------------------------------------------------------------------------------------------------

ENV PYTHONPATH=/app

# --------------------------------------------------------------------------------------------------
# Suppress known third-party deprecation warnings
# --------------------------------------------------------------------------------------------------

ENV PYTHONWARNINGS="ignore::DeprecationWarning:fastmcp.server.auth.providers.jwt,ignore::DeprecationWarning:websockets.legacy,ignore::DeprecationWarning:uvicorn.protocols.websockets.websockets_impl"

EXPOSE 5001

# --------------------------------------------------------------------------------------------------
# add entrypoint for the container
# --------------------------------------------------------------------------------------------------

CMD ["/app/.venv/bin/python", "/app/run_server.py"]
