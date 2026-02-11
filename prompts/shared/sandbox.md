## Sandbox

You have a Docker sandbox for executing code. The sandbox mounts the same `/workspace/` directory, so a file written with file tools is immediately available for execution via `sandbox_execute`. For example, after writing `/workspace/script.py`, run it with `sandbox_execute("python /workspace/script.py")`.
