from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


class ExportSelectionDialog(QDialog):
    def __init__(self, scan_structure, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Selection")
        self._scan = scan_structure or {}
        self._setup_ui()
        self._populate()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)

        self.layout.addWidget(QLabel("Select what to export from the ODB:"))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item"])
        self.tree.setColumnCount(1)
        self.layout.addWidget(self.tree)

        self.layout.addWidget(QLabel("Aggregations:"))
        agg_row = QHBoxLayout()
        self.agg_mean = QCheckBox("Mean")
        self.agg_max = QCheckBox("Max")
        self.agg_min = QCheckBox("Min")
        self.agg_box = QCheckBox("Boxplot stats")
        for cb in (self.agg_mean, self.agg_max, self.agg_min, self.agg_box):
            cb.setChecked(True)
            agg_row.addWidget(cb)
        agg_row.addStretch(1)
        self.layout.addLayout(agg_row)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def _populate(self):
        self.tree.clear()

        instances_root = QTreeWidgetItem(self.tree, ["Instances"])
        instances_root.setFlags(instances_root.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

        instances = self._scan.get("Instances", {}) or {}
        for inst_name, inst_info in instances.items():
            inst_item = QTreeWidgetItem(instances_root, [inst_name])
            inst_item.setFlags(inst_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

            bodies = inst_info.get("Bodies", {}) or {}
            for body_key, body_info in bodies.items():
                label = body_info.get("label", body_key)
                body_item = QTreeWidgetItem(inst_item, [label])
                body_item.setFlags(body_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

                fields = body_info.get("Fields", {}) or {}
                for field_name, field_info in fields.items():
                    field_item = QTreeWidgetItem(body_item, [field_name])
                    field_item.setFlags(field_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

                    variants = []
                    components = field_info.get("components") or []
                    for c in components:
                        variants.append(("component", c))
                    invariants = field_info.get("invariants") or []
                    for inv in invariants:
                        variants.append(("invariant", inv))

                    if not variants:
                        variants.append(("scalar", "Value"))

                    for v_type, v_name in variants:
                        v_item = QTreeWidgetItem(field_item, [v_name])
                        v_item.setFlags(v_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        v_item.setCheckState(0, Qt.CheckState.Unchecked)
                        v_item.setData(
                            0,
                            Qt.ItemDataRole.UserRole,
                            {
                                "kind": "field",
                                "instance": inst_name,
                                "body_key": body_key,
                                "field": field_name,
                                "variant_type": v_type,
                                "variant": v_name,
                            },
                        )

        history_root = QTreeWidgetItem(self.tree, ["History Outputs"])
        history_root.setFlags(history_root.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
        history = self._scan.get("HistoryOutputs", {}) or {}
        for region_name, vars_list in history.items():
            region_item = QTreeWidgetItem(history_root, [region_name])
            region_item.setFlags(region_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            for var_name in vars_list or []:
                var_item = QTreeWidgetItem(region_item, [var_name])
                var_item.setFlags(var_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                var_item.setCheckState(0, Qt.CheckState.Unchecked)
                var_item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "history", "region": region_name, "variable": var_name})

        self.tree.expandAll()

    def get_selection(self):
        aggregations = []
        if self.agg_mean.isChecked():
            aggregations.append("Mean")
        if self.agg_max.isChecked():
            aggregations.append("Max")
        if self.agg_min.isChecked():
            aggregations.append("Min")
        if self.agg_box.isChecked():
            aggregations.append("Boxplot stats")

        field_items = []
        history_items = []

        def walk(item):
            for i in range(item.childCount()):
                child = item.child(i)
                meta = child.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(meta, dict):
                    if child.checkState(0) == Qt.CheckState.Checked:
                        if meta.get("kind") == "field":
                            field_items.append(meta)
                        elif meta.get("kind") == "history":
                            history_items.append(meta)
                walk(child)

        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))

        return {"aggregations": aggregations, "fields": field_items, "history": history_items}
