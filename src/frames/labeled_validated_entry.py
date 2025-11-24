import tkinter as tk
from tkinter import ttk
from src.frames.base_frame import BaseFrame
from src.utils.tooltip import Tooltip

class LabeledValidatedEntry(BaseFrame):
    
    """
    A Widget Integrating Label + Entry + Validation + Enable Logic.
    Usage:
        widget = LabeledValidatedEntry(parent, var, bounds, label_text, width=8, enable_condition=None)
    """

    def __init__(
        self,
        parent: tk.Widget,
        var: tk.Variable,
        bounds: tuple,
        label_prefix: str,
        width: int = 8,
        enable_condition: callable = None,
        trace_vars: list = None,
    ):
        super().__init__(parent)
        self.var = var
        self.bounds = bounds
        self.width = width
        self.enable_condition = enable_condition
        self.trace_vars = trace_vars or []
        # Type inference
        if isinstance(var, tk.IntVar):
            self.value_type = int
        elif isinstance(var, tk.DoubleVar):
            self.value_type = float
        elif isinstance(var, tk.StringVar):
            self.value_type = str
        else:
            self.value_type = str
        # Automatically generate label text
        lower, upper = bounds
        label_text = f"{label_prefix}:"
        self.label = ttk.Label(self, text=label_text)
        self.label.pack(side=tk.LEFT, padx=(0, 4))
        # Tooltip for range
        range_tip = f"允许范围: {lower} - {upper}"
        Tooltip(self.label, range_tip)
        Tooltip(self, range_tip)

        # Entry
        def validate(P):
            try:
                v = self.value_type(P)
                return lower <= v <= upper
            except:
                return False

        vcmd = (self.register(validate), "%P")

        self.entry = ttk.Spinbox(
            self,
            textvariable=var,
            width=width,
            from_=lower,
            to=upper,
            increment=1 if self.value_type is int else 0.1,
            validate="focusout",
            validatecommand=vcmd,
        )
        self.entry.pack(side=tk.LEFT)
        # Validate on focus out, revert to last valid value if invalid
        self._last_valid_value = str(var.get())

        def on_focus_out(event):
            val = self.entry.get()
            if validate(val):
                self._last_valid_value = val
            else:
                self.entry.delete(0, tk.END)
                self.entry.insert(0, self._last_valid_value)

        self.entry.bind("<FocusOut>", on_focus_out)
        # Enable/Disable logic
        if enable_condition is not None:

            def update_state(*_):
                enabled = enable_condition()
                if enabled:
                    self.entry.config(state="normal")
                    self.label.config(foreground="black")
                else:
                    self.entry.config(state="disabled")
                    self.label.config(foreground="gray")

            self.var.trace_add("write", update_state)
            for tvar in self.trace_vars:
                tvar.trace_add("write", update_state)
            update_state()
            var.trace_add("write", update_state)
            for tvar in self.trace_vars:
                tvar.trace_add("write", update_state)
            update_state()
