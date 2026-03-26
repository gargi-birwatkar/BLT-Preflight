import os
import sys
import stat
import subprocess
def install_jq():
    import shutil
    
    # Linux almost always has jq pre-installed, skip it
    if sys.platform.startswith("linux"):
        return
    
    print("\n🔧 CHECKING JQ DEPENDENCY")
    if shutil.which("jq"):
        print("✅ jq already installed.")
        return
    
    print("⏳ Installing jq...")
    try:
        if os.name == "nt":  # Windows
            subprocess.run(["winget", "install", "jqlang.jq"], check=True)
        elif sys.platform == "darwin":  # Mac
            subprocess.run(["brew", "install", "jq"], check=True)
        print("✅ jq installed. You may need to restart your terminal.")
    except Exception as e:
        print(f"⚠️ Could not auto-install jq: {e}")
        print("   Please install manually: https://jqlang.github.io/jq/download/")
def setup_scout():
    print("\n" + "="*65)
    print("🚀 SCOUT-RISK: AUTOMATED SECURITY SETUP (OWASP-BLT INTEGRATION)")
    print("="*65)

    # 1. INTERACTIVE DEPENDENCY INSTALLATION (Using Unified Requirements)
    # Since we merged requirements into the root, we look for it there.
    req_path = "requirements.txt"
    
    if os.path.exists(req_path):
        print("\n📦 DEPENDENCY MANAGEMENT")
        print("[1] Create 'venv' and install (Recommended)")
        print("[2] Install to Base Python")
        print("[3] Skip Installation (I've already run pip install)")
        
        choice = input("\n👉 Enter choice (1/2/3): ").strip()

        if choice == '1':
            print("⏳ Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            # Find the correct pip path based on OS
            pip_path = os.path.join("venv", "Scripts", "pip") if os.name == "nt" else os.path.join("venv", "bin", "pip")
            print(f"⏳ Installing Scout-Risk dependencies into venv...")
            subprocess.run([pip_path, "install", "-r", req_path], check=True)
        elif choice == '2':
            print("⏳ Installing into Base Python...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path], check=True)
        elif choice=='3':
            print("Skipped Installation")
    else:
        print("⚠️ requirements.txt not found in root. Please ensure you are in the BLT-Preflight folder.")
    
    install_jq()  
    # 2. GIT INITIALIZATION & HOOK INJECTION
    print("\n🔧 GIT CONFIGURATION")
    if not os.path.exists(".git"):
        print("⏳ Running 'git init'...")
        subprocess.run(["git", "init"], check=True)
    else:
        print("✅ Git already initialized.")

    # Define the professional pre-commit hook content
    # Updated to call the correct endpoint in ai_server.py
    hook_content = r"""#!/bin/sh

# Only analyse code files, not docs/configs/assets
FILES=$(git diff --cached --name-only | grep -E '\.(py|js|ts|java|php|rb)$')

if [ -z "$FILES" ]; then
    echo "✅ [SCOUT-RISK]: No code files staged. Skipping analysis."
    exit 0
fi

BLOCKED=0

for FILE in $FILES; do
    DIFF_TEXT=$(git diff --cached -- "$FILE" | head -c 8000)
    
    if [ -z "$DIFF_TEXT" ]; then
        continue
    fi

    echo "🔍 Analysing $FILE..."

    PAYLOAD=$(jq -n --arg dt "$DIFF_TEXT" --arg fp "$FILE" \
        '{diff_text: $dt, file_path: $fp}')

    RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/scout-risk \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")

    if [ $? -ne 0 ] || [ -z "$RESPONSE" ]; then
        echo "⚠️ [SCOUT-RISK]: Server not reachable. Skipping analysis..."
        exit 0
    fi

    RISK=$(echo "$RESPONSE" | jq -r '.risk_level')

    if [ "$RISK" = "High" ] || [ "$RISK" = "Critical" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "❌ [SECURITY REJECTED]: CRITICAL VULNERABILITIES DETECTED in $FILE"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "$RESPONSE" | jq -r '.findings[] | "📍 ISSUE: \(.issue)\n   REASON: \(.reasoning)\n   FIX: \(.owasp_link)\n"'
        BLOCKED=1
    else
        echo "✅ [$FILE]: Risk level $RISK — OK"
    fi
done

if [ "$BLOCKED" = "1" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  Commit aborted. Please fix the security issues above."
    exit 1
fi

echo "✅ [SCOUT-RISK]: All files passed. Proceeding with commit..."
exit 0
"""
    
    hook_path = os.path.join(".git", "hooks", "pre-commit")
    
    try:
        with open(hook_path, "w", newline='\n', encoding="utf-8") as f:
            f.write(hook_content)
        
        # Set execution permissions
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC)
        print(f"✅ Pre-commit hook injected at: {hook_path}")
    except Exception as e:
        print(f"❌ Failed to write hook: {e}")
    
    # 3. FINAL INSTRUCTIONS (Updated for src/ folder structure)
    if os.name == "nt": # Windows
        activate_cmd = ".\\venv\\Scripts\\activate"
    else: # Linux / Mac
        activate_cmd = "source venv/bin/activate"

    # The Module notation for Uvicorn
    run_cmd = "python -m uvicorn src.advisory_engine.ai_server:app --reload"

    print("\n" + "="*65)
    print("🎉 SETUP COMPLETE! NEXT STEPS:")
    print(f"1. Activate environment: {activate_cmd}")
    print(f"2. Add your GEMINI_API_KEY to the '.env' file.")
    print(f"3. Start the AI server:  {run_cmd}")
    print("\n💡 Scout-Risk is now integrated into BLT-Preflight.")
    print("="*65 + "\n")

if __name__ == "__main__":
    setup_scout()