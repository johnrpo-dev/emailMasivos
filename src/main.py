import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.app import App
import customtkinter as ctk

def main():
    # Configurar la apariencia de CustomTkinter
    ctk.set_appearance_mode("System")  # "System" (standard), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"
    
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
