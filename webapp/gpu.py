# gpu.py — thin SSH/SFTP wrapper over paramiko for the remote GPU server.
# Every call is deliberately bounded (timeouts) so a flaky link never wedges a request.

import paramiko, os, time, tempfile

DEFAULT_SSH_OPTS = dict(
    banner_timeout=30, auth_timeout=30, timeout=30,
    look_for_keys=False, allow_agent=False,
)


class GPU:
    def __init__(self, host, key_path, user='root', port=22):
        self.host = host
        self.key_path = key_path
        self.user = user
        self.port = port
        self._client = None
        self._sftp = None

    # ---- connection ----
    def connect(self):
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(hostname=self.host, port=self.port, username=self.user,
                  key_filename=self.key_path, **DEFAULT_SSH_OPTS)
        self._client = c
        return self

    def close(self):
        try:
            if self._sftp:
                self._sftp.close()
            if self._client:
                self._client.close()
        except Exception:
            pass
        self._client = None
        self._sftp = None

    @property
    def client(self):
        if self._client is None:
            self.connect()
        return self._client

    @property
    def sftp(self):
        if self._sftp is None:
            self._sftp = self.client.open_sftp()
        return self._sftp

    # ---- commands ----
    def run(self, cmd, timeout=25):
        _, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', 'replace')
        err = stderr.read().decode('utf-8', 'replace')
        code = stdout.channel.recv_exit_status()
        return code, out, err

    def launch_detached(self, cmd, logfile):
        """Fire-and-forget: setsid ... > log 2>&1 < /dev/null & (never blocks)."""
        parent = logfile.rsplit('/', 1)[0]
        self.run(f"mkdir -p {parent}", timeout=25)
        full = f"setsid bash -c \"{cmd}\" > {logfile} 2>&1 < /dev/null & echo LAUNCHED"
        code, out, _ = self.run(full, timeout=25)
        return ('LAUNCHED' in out)

    def tail(self, logfile, n=40):
        code, out, _ = self.run(f"tail -n {n} {logfile} 2>/dev/null", timeout=25)
        return out

    def exists(self, path):
        code, out, _ = self.run(f"test -e {path} && echo YES || echo NO", timeout=25)
        return 'YES' in out

    def mkdir(self, path):
        self.run(f"mkdir -p {path}", timeout=25)

    # ---- file transfer (ONE stream at a time by design) ----
    def put(self, local, remote):
        self.sftp.put(local, remote)
        return remote

    def put_text(self, remote, content):
        """Write a text blob (e.g. a bash script) to the server, preserving LF endings."""
        fd, tmp = tempfile.mkstemp(suffix='.sh')
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(content.encode('utf-8'))
            self.sftp.put(tmp, remote)
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
        return remote

    def get(self, remote, local):
        os.makedirs(os.path.dirname(local), exist_ok=True)
        self.sftp.get(remote, local)
        return local

    def list_remote(self, remote_dir, ext=''):
        """Recursive list of files (optionally filtered by extension) under remote_dir."""
        cmd = f"find {remote_dir} -type f"
        if ext:
            cmd += f" -name '*{ext}'"
        code, out, _ = self.run(cmd, timeout=60)
        return [p for p in out.splitlines() if p.strip()]

    # ---- pipeline-state helpers ----
    def pipeline_running(self):
        """True if a reel pipeline (tts/flux/assemble/ltx) is still running on the server.
        The '[.]' prevents pgrep matching its own command line (self-match -> would always
        be True)."""
        code, out, _ = self.run(
            "pgrep -f 'tts_29[.]py|flux_gen_opt[.]py|assemble_29[.]py|ltx_29[.]py' | head -5",
            timeout=25)
        return bool(out.strip())

    def kill_pipeline(self):
        """Gracefully stop this batch's pipeline on the server: SIGTERM the orchestrator
        scripts + their python workers, then clear the ComfyUI queue."""
        self.run("pkill -f 'web_flux[.]sh|web_ltx[.]sh|tts_29[.]py|flux_gen_opt[.]py|assemble_29[.]py|ltx_29[.]py' 2>/dev/null; sleep 1; echo KILLED",
                 timeout=40)
        self.run("curl -s -X POST http://127.0.0.1:8188/queue "
                 "-H 'Content-Type: application/json' -d '{\"clear\": true}' -o /dev/null; echo CLEARED",
                 timeout=20)
        return True
