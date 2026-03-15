import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_PY = os.path.join(ROOT, "main.py")


def build(console: bool = False):
    """Build ALAHA Program executable.
    
    Args:
        console: If True, shows console window (useful for debugging).
                 If False, runs without console (windowed mode).
    """
    # Determine separator based on OS
    sep = ";" if sys.platform == "win32" else ":"
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "ALAHAProgram",
        "--add-data", f"{os.path.join(ROOT, 'core')}{sep}core",
        "--add-data", f"{os.path.join(ROOT, 'actions')}{sep}actions",
        "--add-data", f"{os.path.join(ROOT, 'llm')}{sep}llm",
        "--add-data", f"{os.path.join(ROOT, 'screenshot')}{sep}screenshot",
        "--add-data", f"{os.path.join(ROOT, 'ui')}{sep}ui",
        "--hidden-import", "customtkinter",
        "--hidden-import", "pyautogui",
        "--hidden-import", "pygetwindow",
        "--hidden-import", "websockets",
        "--hidden-import", "httpx",
        "--hidden-import", "pydantic",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.ImageGrab",
        "--hidden-import", "PIL.ImageDraw",
        "--collect-all", "customtkinter",
        "--icon", os.path.join(ROOT, "installer", "icon.ico") if os.path.exists(os.path.join(ROOT, "installer", "icon.ico")) else "",
        MAIN_PY,
    ]
    
    # Remove empty icon path if no icon exists
    cmd = [c for c in cmd if c]
    
    # Add windowed flag if not console mode
    if not console:
        cmd.insert(3, "--windowed")

    print("=" * 50)
    print("ALAHA Program - Build Executable")
    print("=" * 50)
    print(f"\nMode: {'Console' if console else 'Windowed (background)'}")
    print(f"Output: {os.path.join(ROOT, 'dist', 'ALAHAProgram.exe')}")
    print("\nBuilding...")
    
    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("BUILD SUCCESSFUL!")
        print("=" * 50)
        exe_path = os.path.join(ROOT, "dist", "ALAHAProgram.exe")
        print(f"\nExecutable: {exe_path}")
        
        # Copy config.json to dist folder if exists
        config_src = os.path.join(ROOT, "config.json")
        config_dst = os.path.join(ROOT, "dist", "config.json")
        if os.path.exists(config_src):
            shutil.copy(config_src, config_dst)
            print(f"Config copied: {config_dst}")
        
        print("\nPara executar:")
        print(f"  {exe_path}")
        print("\nPara instalar no Startup do Windows:")
        print("  1. Win+R -> shell:startup")
        print("  2. Copie ALAHAProgram.exe para a pasta")
    else:
        print(f"\nBuild failed with code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build ALAHA Program executable")
    parser.add_argument("--console", action="store_true", help="Show console window (for debugging)")
    args = parser.parse_args()
    build(console=args.console)
