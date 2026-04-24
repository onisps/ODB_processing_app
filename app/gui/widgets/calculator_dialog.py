from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QWidget,
)
import re

class CalculatorDialog(QDialog):
    """Dialog for performing mathematical operations on extracted data."""
    
    def __init__(self, active_series, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Field Calculator")
        self.active_series = active_series
        self._token_map = self._build_token_map(active_series)
        self._setup_ui()
        
    def _build_token_map(self, labels):
        used = set()
        token_map = {}
        for label in labels:
            token = re.sub(r"\W+", "_", label).strip("_")
            if not token:
                token = "var"
            if token[0].isdigit():
                token = "v_" + token
            base = token
            idx = 1
            while token in used:
                idx += 1
                token = "%s_%d" % (base, idx)
            used.add(token)
            token_map[token] = label
        return token_map

    def _setup_ui(self):
        """Builds the calculator dialog layout with variable selection and operations."""
        self.layout = QVBoxLayout(self)

        self.layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Expression", "Binary"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.layout.addWidget(self.mode_combo)

        self.expression_widget = QWidget()
        expr_layout = QVBoxLayout(self.expression_widget)
        expr_layout.setContentsMargins(0, 0, 0, 0)

        expr_layout.addWidget(QLabel("Expression:"))
        self.expr_edit = QLineEdit()
        self.expr_edit.setPlaceholderText("e.g., sin(U1_Mean) - 5")
        expr_layout.addWidget(self.expr_edit)

        insert_row = QHBoxLayout()
        self.var_combo = QComboBox()
        for token, label in self._token_map.items():
            self.var_combo.addItem("%s  (%s)" % (token, label), token)
        insert_row.addWidget(self.var_combo)
        self.insert_var_btn = QPushButton("Insert Var")
        self.insert_var_btn.clicked.connect(self._insert_variable)
        insert_row.addWidget(self.insert_var_btn)

        self.func_combo = QComboBox()
        self.func_combo.addItems(["sin()", "cos()", "tan()", "sqrt()", "log()", "exp()", "abs()"])
        insert_row.addWidget(self.func_combo)
        self.insert_func_btn = QPushButton("Insert Func")
        self.insert_func_btn.clicked.connect(self._insert_function)
        insert_row.addWidget(self.insert_func_btn)
        expr_layout.addLayout(insert_row)

        self.layout.addWidget(self.expression_widget)

        self.binary_widget = QWidget()
        bin_layout = QVBoxLayout(self.binary_widget)
        bin_layout.setContentsMargins(0, 0, 0, 0)

        bin_layout.addWidget(QLabel("Select Variable 1:"))
        self.var1_combo = QComboBox()
        self.var1_combo.addItems(self.active_series)
        bin_layout.addWidget(self.var1_combo)

        bin_layout.addWidget(QLabel("Operation:"))
        self.op_combo = QComboBox()
        self.op_combo.addItems(["+", "-", "*", "/"])
        bin_layout.addWidget(self.op_combo)

        bin_layout.addWidget(QLabel("Select Variable 2:"))
        self.var2_combo = QComboBox()
        self.var2_combo.addItems(self.active_series)
        bin_layout.addWidget(self.var2_combo)

        self.layout.addWidget(self.binary_widget)

        self.layout.addWidget(QLabel("Result Name:"))
        self.result_edit = QLineEdit()
        self.result_edit.setPlaceholderText("e.g., Calculated_Stress")
        self.layout.addWidget(self.result_edit)

        self.btn_layout = QHBoxLayout()
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.btn_layout.addWidget(self.calc_btn)
        self.btn_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(self.btn_layout)

        self._on_mode_changed()

    def _on_mode_changed(self):
        mode = self.mode_combo.currentText()
        self.expression_widget.setVisible(mode == "Expression")
        self.binary_widget.setVisible(mode == "Binary")

    def _insert_variable(self):
        token = self.var_combo.currentData()
        if not token:
            return
        self.expr_edit.insert(token)

    def _insert_function(self):
        fn = self.func_combo.currentText()
        if not fn:
            return
        if fn.endswith("()"):
            fn = fn[:-1]
        self.expr_edit.insert(fn)

    def get_payload(self):
        mode = self.mode_combo.currentText()
        name = self.result_edit.text()
        if mode == "Expression":
            return {"mode": "expression", "expression": self.expr_edit.text(), "result": name, "token_map": self._token_map}
        return {"mode": "binary", "var1": self.var1_combo.currentText(), "var2": self.var2_combo.currentText(), "op": self.op_combo.currentText(), "result": name}
