import sys

import psycopg2.extras

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, QObject, QDate
from PySide6.QtGui import QColor, QShortcut, QKeySequence, QFont, QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTableView,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
    QDialog,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QMessageBox,
    QAbstractItemView,
    QDateEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QTabWidget,
)

from db import (
    DB_URL,
    upsert_stat,
    get_connection,
    search_records,
    save_adspower_profile,
    get_keitaro_prefixes,
    get_no_id_records,
    get_all_profiles,
    get_profile_by_name,
    update_profile,
    delete_profile,
    get_records_by_profile,
    delete_record,
)

# ===================== THEME (Obsidian) =====================
BG          = "#1e1e1e"
BG_ALT      = "#232323"
BORDER      = "#2d2d2d"
PANEL       = "#252525"
ACCENT      = "#6e8759"
ACCENT_DARK = "#4e5d42"
TEXT        = "#dcddde"
TEXT_DIM    = "#8a8a8a"
YELLOW      = "#e0c43c"
CYAN        = "#56b6c2"

HEADINGS = ["", "Date", "Campaign ID", "Name", "GEO", "LEAD", "SALE", "REG", "Updated"]
COL_KEY  = ["action", "date", "token_id", "token_name", "geo", "lead", "sale", "registration", "updated_at"]


class StatsModel(QAbstractTableModel):
    def __init__(self, rows=None):
        super().__init__()
        self.rows = rows if rows else []

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return HEADINGS[section]
        return super().headerData(section, orientation, role)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(HEADINGS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.column() == 0:
            return None
        value = self.rows[index.row()][COL_KEY[index.column()]]
        if role == Qt.DisplayRole:
            if isinstance(value, int):
                return str(value)
            return value or ""
        if role == Qt.ForegroundRole:
            if COL_KEY[index.column()] == "lead":
                return QColor(YELLOW)
            if COL_KEY[index.column()] == "sale":
                return QColor(CYAN)
            return QColor(TEXT)
        return None


def make_theme():
    return f"""
    QMainWindow, QWidget {{ background: {BG}; color: {TEXT}; }}
    QTableView {{
        background: {BG_ALT};
        alternate-background-color: {PANEL};
        gridline-color: {BORDER};
        border: 1px solid {BORDER};
        selection-background-color: {ACCENT_DARK};
        selection-color: white;
        outline: none;
    }}
    QHeaderView::section {{
        background: {PANEL};
        color: {TEXT_DIM};
        border: none;
        border-right: 1px solid {BORDER};
        border-bottom: 1px solid {BORDER};
        padding: 6px 8px;
    }}
    QLineEdit {{
        background: {BG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 6px 10px;
        color: {TEXT};
    }}
    QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
    QPushButton {{
        background: {PANEL};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 6px 14px;
    }}
    QPushButton:hover {{ border-color: {ACCENT}; color: white; }}
    QPushButton#accent {{
        background: {ACCENT};
        color: #111;
        font-weight: bold;
    }}
    QPushButton#accent:hover {{ background: #7d9a68; }}
    QPushButton#danger {{
        background: #8b2d2d;
        color: #f0d0d0;
        font-weight: bold;
    }}
    QPushButton#danger:hover {{ background: #a53b3b; }}
    QPushButton#delRow {{
        background: transparent;
        color: #e06c6c;
        border: none;
        border-radius: 3px;
        padding: 0px;
        font-weight: bold;
    }}
    QPushButton#delRow:hover {{ background: #8b2d2d; color: white; }}
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 4px;
        background: {BG};
        top: -1px;
    }}
    QTabBar::tab {{
        background: {PANEL};
        color: {TEXT_DIM};
        border: 1px solid {BORDER};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 7px 18px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{ background: {BG}; color: {TEXT}; }}
    QTabBar::tab:hover:!selected {{ color: white; }}
    QListWidget {{
        background: {BG};
        border: none;
        color: {TEXT};
        outline: none;
    }}
    QListWidget::item {{
        padding: 6px 10px;
        border-radius: 4px;
    }}
    QListWidget::item:selected {{ background: {ACCENT_DARK}; color: white; }}
    QListWidget::item:hover {{ background: {BORDER}; }}
    QLabel {{ color: {TEXT}; }}
    QLabel#dim {{ color: {TEXT_DIM}; }}
    QLabel#title {{
        font-size: 18px;
        font-weight: bold;
    }}
    QComboBox {{
        background: {BG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 5px 10px;
        color: {TEXT};
    }}
    QComboBox QAbstractItemView {{
        background: {PANEL};
        color: {TEXT};
        border: 1px solid {BORDER};
        selection-background-color: {ACCENT_DARK};
    }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background: {BG};
        width: 10px; height: 10px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {BORDER};
        border-radius: 5px;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{ background: none; height: 0; width: 0; }}
    """


class ManualDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add RC")
        self.setModal(True)
        self.resize(360, 240)
        form = QFormLayout()
        form.setSpacing(10)

        self.token_id = QLineEdit()
        self.token_name = QLineEdit()
        self.geo = QLineEdit()
        self.event = QComboBox()
        self.event.addItems(["Lead", "Sale", "Registration"])

        form.addRow("Campaign ID", self.token_id)
        form.addRow("Name", self.token_name)
        form.addRow("GEO", self.geo)
        form.addRow("Event", self.event)

        btns = QHBoxLayout()
        ok = QPushButton("Add")
        ok.setObjectName("accent")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)

        wrap = QVBoxLayout(self)
        wrap.addLayout(form)
        wrap.addLayout(btns)


class AdsPowerModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AdsPower Profile")
        self.setModal(True)
        self.resize(640, 560)

        self.attached = {}
        self.edit_attached = {}
        self._build_ui()
        self._connect_signals()

    # ---------- UI ----------
    def _build_ui(self):
        wrap = QVBoxLayout(self)
        wrap.setSpacing(10)

        self.tabs = QTabWidget()
        wrap.addWidget(self.tabs)
        self.tabs.addTab(self._build_add_tab(), "Add Profile")
        self.tabs.addTab(self._build_edit_tab(), "Edit Profile")

    def _build_add_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(8)

        self.add_name = QLineEdit()
        self.add_name.setPlaceholderText("AdsPower profile name / ID")
        form.addRow("Profile Name", self.add_name)

        self.add_mode_combo = QComboBox()
        self.add_mode_combo.addItems(["Search by Name", "Search by ID"])
        self.add_search = QLineEdit()
        self.add_search.setPlaceholderText("Search campaigns / SMS records...")
        self.add_search.setClearButtonEnabled(True)
        search_row = QHBoxLayout()
        search_row.addWidget(self.add_search, 1)
        search_row.addWidget(self.add_mode_combo)
        form.addRow("Search", search_row)

        layout.addLayout(form)

        results_label = QLabel("Search Results")
        results_label.setObjectName("dim")
        layout.addWidget(results_label)

        self.add_results = QListWidget()
        layout.addWidget(self.add_results, 1)

        attached_label = QLabel("Attached Items")
        attached_label.setObjectName("dim")
        layout.addWidget(attached_label)

        self.add_attached_list = QListWidget()
        layout.addWidget(self.add_attached_list)

        self.add_save_btn = QPushButton("Save Profile")
        self.add_save_btn.setObjectName("accent")
        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(self.add_save_btn)
        layout.addLayout(btns)
        return tab

    def _build_edit_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(8)

        self.edit_profile_combo = QComboBox()
        form.addRow("Profile", self.edit_profile_combo)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("New profile name")
        form.addRow("Rename To", self.edit_name)

        self.edit_mode_combo = QComboBox()
        self.edit_mode_combo.addItems(["Search by Name", "Search by ID"])
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Search records to add...")
        self.edit_search.setClearButtonEnabled(True)
        search_row = QHBoxLayout()
        search_row.addWidget(self.edit_search, 1)
        search_row.addWidget(self.edit_mode_combo)
        form.addRow("Search", search_row)

        layout.addLayout(form)

        results_label = QLabel("Search Results")
        results_label.setObjectName("dim")
        layout.addWidget(results_label)

        self.edit_results = QListWidget()
        layout.addWidget(self.edit_results, 1)

        bound_label = QLabel("Bound Records")
        bound_label.setObjectName("dim")
        layout.addWidget(bound_label)

        self.edit_attached_list = QListWidget()
        layout.addWidget(self.edit_attached_list)

        self.delete_btn = QPushButton("Delete Profile")
        self.delete_btn.setObjectName("danger")
        self.edit_save_btn = QPushButton("Save Changes")
        self.edit_save_btn.setObjectName("accent")
        self.cancel_btn = QPushButton("Cancel")
        btns = QHBoxLayout()
        btns.addWidget(self.delete_btn)
        btns.addStretch()
        btns.addWidget(self.edit_save_btn)
        btns.addWidget(self.cancel_btn)
        layout.addLayout(btns)
        return tab

    # ---------- Signals ----------
    def _connect_signals(self):
        self.add_save_btn.clicked.connect(self._save)
        self.edit_save_btn.clicked.connect(self._save_changes)
        self.delete_btn.clicked.connect(self._delete_profile)
        self.cancel_btn.clicked.connect(self.reject)

        self.add_search.textChanged.connect(self._perform_search)
        self.add_mode_combo.currentIndexChanged.connect(self._perform_search)
        self.add_results.itemChanged.connect(self._toggle_attached)

        self.edit_search.textChanged.connect(self._perform_search)
        self.edit_mode_combo.currentIndexChanged.connect(self._perform_search)
        self.edit_results.itemChanged.connect(self._toggle_attached)
        self.edit_profile_combo.currentIndexChanged.connect(self._load_profile)

        self._reload_profiles()

    # ---------- Helpers ----------
    def _record_identifier(self, row):
        return row["token_id"] if row["token_id"] else row["token_name"]

    def _format_row(self, row):
        return f"{row['token_id'] or '(no id)'} | {row['token_name']} | {row['geo'] or '-'}"

    def _search_context(self):
        is_add = self.tabs.currentIndex() == 0
        if is_add:
            return self.add_search, self.add_mode_combo, self.add_results, self.attached
        return self.edit_search, self.edit_mode_combo, self.edit_results, self.edit_attached

    def _perform_search(self):
        search_input, mode_combo, results_list, store = self._search_context()
        query = search_input.text().strip()
        search_by = "name" if mode_combo.currentIndex() == 0 else "id"
        results_list.blockSignals(True)
        results_list.clear()
        if query:
            for row in search_records(query, search_by=search_by):
                identifier = self._record_identifier(row)
                item = QListWidgetItem(self._format_row(row))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if identifier in store else Qt.Unchecked)
                item.setData(Qt.UserRole, row)
                results_list.addItem(item)
        results_list.blockSignals(False)

    def _toggle_attached(self, item):
        store = self.attached if self.sender() is self.add_results else self.edit_attached
        row = item.data(Qt.UserRole)
        identifier = self._record_identifier(row)
        if item.checkState() == Qt.Checked:
            store[identifier] = row
        else:
            store.pop(identifier, None)
        self._refresh_attached()

    def _refresh_attached(self):
        self.add_attached_list.clear()
        for row in self.attached.values():
            self.add_attached_list.addItem(self._format_row(row))
        self.edit_attached_list.clear()
        for row in self.edit_attached.values():
            self.edit_attached_list.addItem(self._format_row(row))

    # ---------- Edit tab ----------
    def _reload_profiles(self):
        self.edit_profile_combo.blockSignals(True)
        self.edit_profile_combo.clear()
        for profile in get_all_profiles():
            self.edit_profile_combo.addItem(profile["profile_name"], profile)
        self.edit_profile_combo.blockSignals(False)
        self._load_profile(self.edit_profile_combo.currentIndex())

    def _load_profile(self, index):
        combo_profile = self.edit_profile_combo.itemData(index)
        self.edit_attached.clear()
        profile = get_profile_by_name(combo_profile["profile_name"]) if combo_profile else None
        if profile:
            self.edit_name.setText(profile["profile_name"])
            for row in get_records_by_profile(profile["profile_name"]):
                self.edit_attached[self._record_identifier(row)] = row
        else:
            self.edit_name.clear()
        self._refresh_attached()
        self._perform_search()

    # ---------- Actions ----------
    def _save(self):
        name = self.add_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid", "Profile Name is required.")
            return
        if not self.attached:
            QMessageBox.warning(self, "Invalid", "Attach at least one record.")
            return
        save_adspower_profile(name, list(self.attached.keys()))
        self.accept()

    def _save_changes(self):
        index = self.edit_profile_combo.currentIndex()
        if index < 0:
            QMessageBox.warning(self, "Invalid", "Select a profile to edit.")
            return
        old_name = self.edit_profile_combo.itemData(index)["profile_name"]
        new_name = self.edit_name.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Invalid", "Profile name cannot be empty.")
            return
        if not self.edit_attached:
            QMessageBox.warning(self, "Invalid", "Attach at least one record.")
            return
        update_profile(old_name, new_name, list(self.edit_attached.keys()))
        self.accept()

    def _delete_profile(self):
        index = self.edit_profile_combo.currentIndex()
        if index < 0:
            QMessageBox.warning(self, "Invalid", "Select a profile to delete.")
            return
        profile = self.edit_profile_combo.itemData(index)
        answer = QMessageBox.question(
            self,
            "Delete Profile",
            f"Delete profile '{profile['profile_name']}'? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        delete_profile(profile["profile_name"])
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arbitration Monitor")
        self.resize(1280, 760)

        self._build_ui()
        self._setup_shortcuts()
        self.refresh()

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(1)

        sidebar = self._build_sidebar()
        sidebar.setFixedWidth(220)
        body_layout.addWidget(sidebar)
        body_layout.addWidget(self._build_table(), 1)

        outer.addWidget(body, 1)
        outer.addWidget(self._build_statusbar())

    def _build_header(self):
        bar = QWidget()
        bar.setObjectName("header")
        bar.setFixedHeight(58)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        title = QLabel("Arbitration Stats")
        title.setObjectName("title")
        lay.addWidget(title)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        lay.addWidget(self.date_edit)
        self.date_edit.dateChanged.connect(self._on_date_changed)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search token_id, name, geo...")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(320)
        lay.addWidget(self.search, 1)

        add_board = QPushButton("ADD ABoard")
        add_board.setObjectName("accent")
        add_board.clicked.connect(self.open_ads_power)
        lay.addWidget(add_board)

        add_rc = QPushButton("Add RC")
        add_rc.clicked.connect(self.open_manual)
        lay.addWidget(add_rc)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        lay.addWidget(settings_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        lay.addWidget(refresh_btn)

        self.count_label = QLabel("")
        self.count_label.setObjectName("dim")
        lay.addWidget(self.count_label)

        return bar

    def _build_sidebar(self):
        panel = QWidget()
        panel.setObjectName("sidebar")
        panel.setStyleSheet(f"QWidget#sidebar {{ background: {PANEL}; }}")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(6, 8, 6, 8)
        lay.setSpacing(6)

        title = QLabel("Folders")
        title.setObjectName("dim")
        lay.addWidget(title)

        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setSelectionMode(QAbstractItemView.SingleSelection)

        all_item = QTreeWidgetItem(["All entries"])
        all_item.setData(0, Qt.UserRole, ("folder", "All entries"))
        keitaro = QTreeWidgetItem(["Keitaro"])
        keitaro.setData(0, Qt.UserRole, ("folder", "Keitaro"))
        facebook = QTreeWidgetItem(["Profile"])
        facebook.setData(0, Qt.UserRole, ("folder", "Profile"))
        noid_item = QTreeWidgetItem(["NO ID"])
        noid_item.setData(0, Qt.UserRole, ("noid",))

        self.folder_tree.addTopLevelItem(all_item)
        self.folder_tree.addTopLevelItem(keitaro)
        self.folder_tree.addTopLevelItem(facebook)
        self.folder_tree.addTopLevelItem(noid_item)
        self.folder_tree.setCurrentItem(all_item)
        lay.addWidget(self.folder_tree, 1)
        self.folder_tree.itemClicked.connect(self.refresh)

        create_btn = QPushButton("+ Create folder")
        create_btn.clicked.connect(self.create_folder)
        lay.addWidget(create_btn)

        return panel

    def _build_table(self):
        self.model = StatsModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 32)
        return self.table

    def _load_rows(self, rows):
        self.model.beginResetModel()
        self.model.rows = rows
        self.model.endResetModel()
        self._attach_delete_buttons()
        lead = sum(r["lead"] for r in rows)
        sale = sum(r["sale"] for r in rows)
        reg = sum(r["registration"] for r in rows)
        self.count_label.setText(
            f"{len(rows)} | L:{lead} S:{sale} R:{reg}"
        )

    def _attach_delete_buttons(self):
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            record_id = self.model.rows[row]["id"]
            btn = QPushButton("✕")
            btn.setObjectName("delRow")
            btn.setToolTip("Delete this record")
            btn.clicked.connect(
                lambda checked=False, rid=record_id: self._confirm_delete(rid)
            )
            self.table.setIndexWidget(index, btn)

    def _confirm_delete(self, record_id):
        answer = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this record?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        delete_record(record_id)

    def _build_statusbar(self):
        bar = QLabel("Ready")
        bar.setObjectName("dim")
        bar.setContentsMargins(10, 4, 10, 4)
        bar.setFixedHeight(26)
        return bar

    # ---------- Shortcuts ----------
    def _setup_shortcuts(self):
        QShortcut(QKeySequence.Refresh, self, self.refresh)          # F5
        QShortcut(QKeySequence("Ctrl+N"), self, self.create_folder)
        QShortcut(QKeySequence.Find, self, self.focus_search)         # Ctrl+F

    def focus_search(self):
        self.search.setFocus()
        self.search.selectAll()

    # ---------- DB / refresh ----------
    def _current_node(self):
        item = self.folder_tree.currentItem()
        if item is None:
            return ("folder", "All entries")
        parent = item.parent()
        if parent is None:
            node = item.data(0, Qt.UserRole)
            return node if node else ("folder", item.text(0))
        node = item.data(0, Qt.UserRole)
        return node if node else ("folder", item.text(0))

    def _populate_tree(self):
        if getattr(self, "_updating_tree", False):
            return
        self._updating_tree = True
        try:
            root = self.folder_tree.invisibleRootItem()
            keitaro = profile = None
            for i in range(root.childCount()):
                text = root.child(i).text(0)
                if text == "Keitaro":
                    keitaro = root.child(i)
                elif text == "Profile":
                    profile = root.child(i)
            if keitaro is None or profile is None:
                return

            selected_prefix = None
            current = self.folder_tree.currentItem()
            if current is not None and current.parent() is keitaro:
                selected_prefix = current.text(0)
            keitaro.takeChildren()
            for prefix in get_keitaro_prefixes():
                child = QTreeWidgetItem([prefix])
                child.setData(0, Qt.UserRole, ("prefix", prefix))
                keitaro.addChild(child)
            keitaro.setExpanded(True)
            if selected_prefix:
                for i in range(keitaro.childCount()):
                    if keitaro.child(i).text(0) == selected_prefix:
                        self.folder_tree.setCurrentItem(keitaro.child(i))
                        break

            selected_profile = None
            current = self.folder_tree.currentItem()
            if current is not None and current.parent() is profile:
                selected_profile = current.text(0)
            profile.takeChildren()
            for p in get_all_profiles():
                child = QTreeWidgetItem([p["profile_name"]])
                child.setData(0, Qt.UserRole, ("profile", p["profile_name"]))
                profile.addChild(child)
            profile.setExpanded(True)
            if selected_profile:
                for i in range(profile.childCount()):
                    if profile.child(i).text(0) == selected_profile:
                        self.folder_tree.setCurrentItem(profile.child(i))
                        break
        finally:
            self._updating_tree = False

    def _on_date_changed(self):
        self.model.beginResetModel()
        self.model.rows = []
        self.model.endResetModel()

    def refresh(self):
        rows = self._query_rows()
        self._load_rows(rows)
        self._populate_tree()

    def _query_rows(self):
        node = self._current_node()
        if node[0] == "noid":
            return get_no_id_records()
        if node[0] == "profile":
            return get_records_by_profile(node[1])
        if node[0] == "prefix":
            return self._query_prefix_rows(node[1])
        if node[0] == "folder" and node[1] == "Profile":
            rows = []
            seen = set()
            for p in get_all_profiles():
                for r in get_records_by_profile(p["profile_name"]):
                    if r["id"] not in seen:
                        seen.add(r["id"])
                        rows.append(r)
            rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
            return rows

        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        folder = node[1] if node[0] == "folder" else None
        search = self.search.text().strip().lower()

        query = "SELECT id, " + ", ".join(COL_KEY[1:]) + " FROM daily_stats"
        clauses = ["date >= %s"]
        params = [date_str]

        if folder == "Keitaro":
            clauses.append("token_name LIKE %s")
            params.append("%keitaro%")

        if search:
            clauses.append("(token_id LIKE %s OR token_name LIKE %s OR geo LIKE %s)")
            like = f"%{search}%"
            params += [like, like, like]

        query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY date DESC, id DESC"

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
        finally:
            conn.close()

    def _query_prefix_rows(self, prefix):
        query = "SELECT id, " + ", ".join(COL_KEY[1:]) + " FROM daily_stats"
        params = [prefix + "%"]
        query += " WHERE token_name LIKE %s"
        query += " ORDER BY date DESC, id DESC"
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
        finally:
            conn.close()

    # ---------- Actions ----------
    def create_folder(self):
        name, ok = QInputDialog.getText(self, "New folder", "Folder name:")
        if ok and name.strip():
            item = QTreeWidgetItem([name.strip()])
            item.setData(0, Qt.UserRole, ("folder", name.strip()))
            self.folder_tree.addTopLevelItem(item)
            self.folder_tree.setCurrentItem(item)
            self.refresh()

    def open_ads_power(self):
        dlg = AdsPowerModal(self)
        dlg.exec()

    def open_manual(self):
        dlg = ManualDialog(self)
        if not dlg.exec():
            return
        token_id = dlg.token_id.text().strip()
        token_name = dlg.token_name.text().strip()
        event = dlg.event.currentText()
        geo = dlg.geo.text().strip()
        if not token_id and not token_name:
            QMessageBox.warning(self, "Invalid", "Campaign ID or Name required.")
            return
        upsert_stat(token_id=token_id, token_name=token_name, event_type=event, geo=geo)

    def open_settings(self):
        QMessageBox.information(
            self, "Settings",
            f"Database: {DB_URL}\nTable updates only on Refresh.",
        )


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(make_theme())
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()