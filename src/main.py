import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.app import App

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
