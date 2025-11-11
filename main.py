"""Minimal launcher for ImBridge GUI (keeps startup logic only)."""

def main():
    # Import here to keep startup lightweight for non-GUI operations
    from src.app import App

    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
