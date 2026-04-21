from __future__ import annotations

import wx

from .core import AdjustmentRequest, apply_adjustments, scan_path


class SimSetterFrame(wx.Frame):
    def __init__(self):
        super().__init__(
            None,
            title="Sim Setter",
            size=(1120, 720),
        )
        self.rows = []
        self.scan_errors = []
        self.root_entry = wx.TextCtrl(self)
        self.browse_folder_button = wx.Button(self, label="Browse Folder")
        self.browse_file_button = wx.Button(self, label="Browse File")
        self.scan_button = wx.Button(self, label="Refresh")
        self.backup_checkbox = wx.CheckBox(self, label="Create .oldsync backups")
        self.backup_checkbox.SetValue(True)

        self.list = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.error_label = wx.StaticText(self, label="Invalid songs")
        self.error_list = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.plus_button = wx.Button(self, label="Add 9ms")
        self.minus_button = wx.Button(self, label="Remove 9ms")
        self.select_all_button = wx.Button(self, label="Select All")

        self._build_layout()
        self._bind_events()
        self.CreateStatusBar()
        self.SetStatusText("Choose a file or folder, then scan.")

    def _build_layout(self):
        root_sizer = wx.BoxSizer(wx.VERTICAL)

        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer.Add(wx.StaticText(self, label="Path:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        path_sizer.Add(self.root_entry, 1, wx.RIGHT, 6)
        path_sizer.Add(self.browse_folder_button, 0, wx.RIGHT, 6)
        path_sizer.Add(self.browse_file_button, 0, wx.RIGHT, 6)
        path_sizer.Add(self.scan_button, 0)

        option_sizer = wx.BoxSizer(wx.HORIZONTAL)
        option_sizer.Add(self.backup_checkbox, 0)

        self._add_columns()
        self._add_error_columns()
        self.error_label.Hide()
        self.error_list.Hide()
        self.error_list.SetMinSize((-1, 140))

        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        action_sizer.Add(self.plus_button, 0, wx.RIGHT, 6)
        action_sizer.Add(self.minus_button, 0, wx.RIGHT, 6)
        action_sizer.Add(self.select_all_button, 0)

        root_sizer.Add(path_sizer, 0, wx.EXPAND | wx.ALL, 10)
        root_sizer.Add(option_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        root_sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        root_sizer.Add(self.error_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        root_sizer.Add(self.error_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        root_sizer.Add(action_sizer, 0, wx.ALL, 10)

        self.SetSizer(root_sizer)

    def _add_columns(self):
        columns = [
            ("File", 300),
            ("Slot", 230),
            ("OFFSET", 85),
            ("Split timing", 95),
            ("Title", 180),
            ("Artist", 140),
        ]
        for index, (label, width) in enumerate(columns):
            self.list.InsertColumn(index, label, width=width)

    def _add_error_columns(self):
        columns = [
            ("Title", 250),
            ("Error", 800),
        ]
        for index, (label, width) in enumerate(columns):
            self.error_list.InsertColumn(index, label, width=width)

    def _bind_events(self):
        self.Bind(wx.EVT_BUTTON, self.on_browse_folder, self.browse_folder_button)
        self.Bind(wx.EVT_BUTTON, self.on_browse_file, self.browse_file_button)
        self.Bind(wx.EVT_BUTTON, self.on_scan, self.scan_button)
        self.Bind(wx.EVT_BUTTON, self.on_apply_plus, self.plus_button)
        self.Bind(wx.EVT_BUTTON, self.on_apply_minus, self.minus_button)
        self.Bind(wx.EVT_BUTTON, self.on_select_all, self.select_all_button)
        self.error_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_error_row_selected)

    def on_browse_folder(self, _event):
        with wx.DirDialog(self, "Choose a simfile folder or pack root") as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.root_entry.SetValue(dialog.GetPath())
                self.scan()

    def on_browse_file(self, _event):
        wildcard = "StepMania files (*.ssc;*.sm)|*.ssc;*.sm|All files (*.*)|*.*"
        with wx.FileDialog(self, "Choose a simfile", wildcard=wildcard) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.root_entry.SetValue(dialog.GetPath())
                self.scan()

    def on_scan(self, _event):
        self.scan()

    def on_apply_plus(self, _event):
        self.apply_delta(+9.0)

    def on_apply_minus(self, _event):
        self.apply_delta(-9.0)

    def on_select_all(self, _event):
        for index in range(self.list.GetItemCount()):
            self.list.Select(index)
        self.SetStatusText(f"Selected {self.list.GetItemCount()} row(s).")

    def on_error_row_selected(self, event):
        wx.CallAfter(self.error_list.Select, event.GetIndex(), 0)

    def scan(self, status_text: str | None = None):
        root = self.root_entry.GetValue().strip()
        if not root:
            self.message("Choose a file or folder first.")
            return

        try:
            result = scan_path(root)
        except Exception as exc:
            self.show_error("Refresh failed", exc)
            return

        self.rows = result.rows
        self.scan_errors = result.errors

        self.list.DeleteAllItems()
        for row_index, row in enumerate(self.rows):
            file_label = str(row.path)
            index = self.list.InsertItem(row_index, file_label)
            self.list.SetItem(index, 1, row.slot)
            self.list.SetItem(index, 2, f"{row.effective_offset:0.3f}")
            self.list.SetItem(index, 3, yes_no(row.has_split_timing))
            self.list.SetItem(index, 4, row.title)
            self.list.SetItem(index, 5, row.artist)

        self.populate_error_list()

        message = status_text or f"{len(self.rows)} rows found."
        if self.scan_errors:
            message += f" {len(self.scan_errors)} invalid song(s) skipped."
        self.message(message)

    def apply_delta(self, delta_ms: float):
        selected_indices = self.selected_indices()
        if not selected_indices:
            self.message("Select one or more rows first.")
            return

        direction = f"{delta_ms:+0.0f} ms"
        if wx.MessageBox(
            f"Apply {direction} to {len(selected_indices)} selected row(s)?",
            caption="Sim Setter",
            style=wx.YES_NO | wx.ICON_WARNING,
        ) != wx.YES:
            return

        requests = [
            AdjustmentRequest(
                path=self.rows[index].path,
                target=self.rows[index].target,
                chart_index=self.rows[index].chart_index,
            )
            for index in selected_indices
        ]

        try:
            results = apply_adjustments(
                requests,
                delta_ms=delta_ms,
                make_backup=self.backup_checkbox.GetValue(),
            )
        except Exception as exc:
            self.show_error("Offset adjustment failed", exc)
            return

        changed = 0
        skipped = 0
        for result in results:
            if result.changed:
                changed += 1
            else:
                skipped += 1

        status = f"Changed {changed} row(s)."
        if skipped:
            status += f" Skipped {skipped} row(s)."
        self.scan(status)

    def selected_indices(self) -> list[int]:
        indices = []
        index = self.list.GetFirstSelected()
        while index != -1:
            indices.append(index)
            index = self.list.GetNextSelected(index)
        return indices

    def message(self, text: str):
        self.SetStatusText(text)

    def populate_error_list(self):
        self.error_list.DeleteAllItems()
        for row_index, error in enumerate(self.scan_errors):
            index = self.error_list.InsertItem(row_index, error.title)
            self.error_list.SetItem(index, 1, error.error)

        show_errors = bool(self.scan_errors)
        self.error_label.Show(show_errors)
        self.error_list.Show(show_errors)
        self.Layout()

    def show_error(self, title: str, exc: Exception):
        wx.MessageBox(str(exc), caption=title, style=wx.OK | wx.ICON_ERROR)
        self.message(f"{title}: {exc}")


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def main():
    app = wx.App(False)
    frame = SimSetterFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
