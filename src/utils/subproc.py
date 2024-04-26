import subprocess


def make_called_process_error(completed_process: subprocess.CompletedProcess):
    return subprocess.CalledProcessError(
        completed_process.returncode,
        completed_process.args,
        output=completed_process.stdout,
        stderr=completed_process.stderr,
    )
