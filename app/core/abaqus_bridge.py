from PyQt6.QtCore import QObject, pyqtSignal, QProcess
import json
import os
import shutil
import locale
import sys
import tempfile
import uuid

class AbaqusBridge(QObject):
    """Handles communication between GUI (Python 3.11) and Abaqus (Python 2.7) using QProcess."""
    
    progress_updated = pyqtSignal(int, int, str) # current, total, message
    finished = pyqtSignal(dict, str) # data, error_message
    
    def __init__(self, abaqus_cmd=None):
        super().__init__()
        self.abaqus_cmd = abaqus_cmd or os.environ.get("ABAQUS_CMD", "abaqus")
        self.script_path = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "odb_extractor.py")
        self.process = None
        self._work_dir = None
        self._stdout_chunks = []
        self._stderr_chunks = []

    def _resolve_extractor_path(self):
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), "scripts", "odb_extractor.py"))
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(os.path.join(meipass, "scripts", "odb_extractor.py"))
        candidates.append(os.path.abspath(self.script_path))
        for p in candidates:
            if p and os.path.exists(p):
                return p
        return os.path.abspath(self.script_path)
        
    def _decode_bytes(self, data):
        if not data:
            return ""
        encodings = []
        preferred = locale.getpreferredencoding(False) or "utf-8"
        encodings.append(preferred)
        if os.name == "nt":
            encodings.append("cp866")
            encodings.append("mbcs")
        encodings.append("utf-8")

        best_text = None
        best_score = None
        seen = set()
        for enc in encodings:
            if not enc or enc in seen:
                continue
            seen.add(enc)
            try:
                text = data.decode(enc, errors="replace")
            except Exception:
                continue
            score = text.count("\ufffd")
            if best_score is None or score < best_score:
                best_score = score
                best_text = text
                if best_score == 0:
                    break
        return best_text if best_text is not None else data.decode(errors="replace")

    def run_full_extraction(self, odb_path, export_root="extracted_data"):
        return self.run_extraction(odb_path, selection=None, export_root=export_root)

    def run_scan(self, odb_path):
        args = {"odb_path": odb_path, "command": "scan", "params": {}}
        self._start(args)

    def run_extraction(self, odb_path, selection=None, export_root="extracted_data"):
        if export_root == "extracted_data":
            if getattr(sys, "frozen", False):
                export_root = os.path.join(os.path.dirname(sys.executable), "extracted_data")
            else:
                export_root = os.path.join(os.path.dirname(os.path.abspath(odb_path)), "extracted_data")
        elif not os.path.isabs(export_root):
            export_root = os.path.abspath(export_root)

        args = {"odb_path": odb_path, "command": "extract", "params": {"export_root": export_root}}
        if selection:
            args["selection"] = selection
        self._start(args)

    def _start(self, args):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.getcwd()

        work_root = os.path.join(base_dir, "abaqus_work")
        work_dir = os.path.join(work_root, "run_" + uuid.uuid4().hex)
        try:
            os.makedirs(work_dir, exist_ok=True)
            self._work_dir = work_dir
        except Exception:
            self._work_dir = tempfile.mkdtemp(prefix="odb_processing_app_abaqus_")

        self._stdout_chunks = []
        self._stderr_chunks = []

        input_file = os.path.join(self._work_dir, "abaqus_input.json")
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(args, f)

        self.process = QProcess()
        self.process.setWorkingDirectory(self._work_dir)

        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error_occurred)

        script_abs = self._resolve_extractor_path()
        input_abs = os.path.abspath(input_file)

        if os.name == "nt":
            program = "cmd.exe"
            cmd_args = ["/c", self.abaqus_cmd, "python", script_abs, input_abs]
        else:
            program = self.abaqus_cmd
            cmd_args = ["python", script_abs, input_abs]

        print(f"Starting process: {program} {' '.join(cmd_args)}")
        self.process.start(program, cmd_args)

    def _on_error_occurred(self, error):
        """Handles errors that occur when starting the process."""
        error_names = {
            QProcess.ProcessError.FailedToStart: "Failed to start (executable not found?)",
            QProcess.ProcessError.Crashed: "Process crashed",
            QProcess.ProcessError.Timedout: "Timed out",
            QProcess.ProcessError.WriteError: "Write error",
            QProcess.ProcessError.ReadError: "Read error",
            QProcess.ProcessError.UnknownError: "Unknown error"
        }
        err_msg = error_names.get(error, f"Process error: {error}")
        print(f"QProcess Error: {err_msg}")
        if self._work_dir:
            err_msg = err_msg + f"\nWork dir: {self._work_dir}"
        self.finished.emit({}, err_msg)

    def _handle_stdout(self):
        """Parses stdout for progress updates."""
        data = self._decode_bytes(self.process.readAllStandardOutput().data())
        if data:
            self._stdout_chunks.append(data)
        print(f"Abaqus Stdout: {data}") # Debug log
        for line in data.splitlines():
            if line.startswith("PROGRESS:"):
                try:
                    parts = line.split(":", 3)
                    current = int(parts[1])
                    total = int(parts[2])
                    msg = parts[3]
                    self.progress_updated.emit(current, total, msg)
                except (IndexError, ValueError):
                    pass
            elif line.startswith("ERROR:"):
                pass # Handled by stderr usually

    def _handle_stderr(self):
        """Logs stderr for debugging."""
        error_data = self._decode_bytes(self.process.readAllStandardError().data())
        if error_data:
            self._stderr_chunks.append(error_data)
            if self._work_dir:
                try:
                    with open(os.path.join(self._work_dir, "abaqus_stderr.log"), "a", encoding="utf-8", errors="replace") as f:
                        f.write(error_data)
                except Exception:
                    pass
            print(f"Abaqus Stderr: {error_data}")

    def _on_finished(self, exit_code, exit_status):
        """Cleanup and signal completion."""
        error_msg = None
        data = None
        
        if exit_status == QProcess.ExitStatus.CrashExit:
            error_msg = "Abaqus process crashed."
        elif exit_code != 0:
            error_msg = f"Abaqus process exited with code {exit_code}."
            error_log = os.path.join(self._work_dir or "", "abaqus_error.log")
            if os.path.exists(error_log):
                raw = None
                try:
                    with open(error_log, "rb") as f:
                        raw = f.read()
                except Exception:
                    raw = None
                if raw:
                    error_msg += "\nDetails:\n" + self._decode_bytes(raw)
            else:
                stderr_tail = "".join(self._stderr_chunks)[-4000:]
                if stderr_tail:
                    error_msg += "\nDetails:\n" + stderr_tail
        else:
            output_json = os.path.join(self._work_dir or "", "abaqus_output.json")
            if os.path.exists(output_json):
                with open(output_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                error_msg = "Abaqus output file not found."
                error_log = os.path.join(self._work_dir or "", "abaqus_error.log")
                if os.path.exists(error_log):
                    raw = None
                    try:
                        with open(error_log, "rb") as f:
                            raw = f.read()
                    except Exception:
                        raw = None
                    if raw:
                        error_msg += "\nDetails:\n" + self._decode_bytes(raw)
                else:
                    stderr_tail = "".join(self._stderr_chunks)[-4000:]
                    if stderr_tail:
                        error_msg += "\nDetails:\n" + stderr_tail

        if error_msg and self._work_dir:
            error_msg = error_msg + f"\nWork dir: {self._work_dir}"

        self._cleanup_temp_files(keep_dir=bool(error_msg))
        
        self.finished.emit(data if data else {}, error_msg if error_msg else "")

    def _cleanup_temp_files(self, keep_dir=False):
        """Removes temporary Abaqus files from the working directory."""
        import glob
        temp_patterns = ["abaqus_input.json", "abaqus_output.json", "abaqus_error.log", "abaqus_stderr.log",
                         "abaqus.rpy*", "abaqus.log", "abaqus.msg", "abaqus.sta", "abaqus.jnl"]
        work_dir = self._work_dir or os.getcwd()
        if not keep_dir:
            for pattern in temp_patterns:
                for f in glob.glob(os.path.join(work_dir, pattern)):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
        if not keep_dir and self._work_dir:
            shutil.rmtree(self._work_dir, ignore_errors=True)
        self._work_dir = None
