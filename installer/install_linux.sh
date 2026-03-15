#!/usr/bin/env bash
set -e

# ==========================================
#  ALAHA Program - Instalador Linux
# ==========================================

INSTALL_DIR="${HOME}/.alaha-program"
REPO_URL="https://github.com/SEU-USUARIO/alaha-program.git"

echo ""
echo "  ___   _      ___  _   _   ___"
echo " / _ \ | |    / _ \| | | | / _ \\"
echo "| (_) || |   | (_) || |_| || (_) |"
echo " \___/ ||___| \___/  \___/  \___/"
echo " ALAHA Program - Instalador Linux"
echo ""
echo " =========================================="
echo ""

# -----------------------------------------------
# 1. Verificar Python
# -----------------------------------------------
echo " [1/5] Verificando Python..."
if ! command -v python3 &>/dev/null; then
    echo " ERRO: python3 nao encontrado."
    echo " Instale com: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi
PYVER=$(python3 --version 2>&1)
echo " $PYVER encontrado."

# -----------------------------------------------
# 2. Criar diretorio de instalacao
# -----------------------------------------------
echo ""
echo " [2/5] Preparando diretorio..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$SCRIPT_DIR/main.py" ]; then
    INSTALL_DIR="$SCRIPT_DIR"
    echo " Usando diretorio local: $INSTALL_DIR"
else
    echo " Usando diretorio: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo " Atualizando repositorio..."
        cd "$INSTALL_DIR" && git pull
    else
        echo " Clonando repositorio..."
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
fi

cd "$INSTALL_DIR"

# -----------------------------------------------
# 3. Criar ambiente virtual
# -----------------------------------------------
echo ""
echo " [3/5] Criando ambiente virtual..."
if [ -d "venv" ]; then
    echo " Ambiente virtual ja existe, pulando..."
else
    python3 -m venv venv
fi

# -----------------------------------------------
# 4. Instalar dependencias
# -----------------------------------------------
echo ""
echo " [4/5] Instalando dependencias..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
echo " Dependencias instaladas."

# -----------------------------------------------
# 5. Criar atalho de execucao
# -----------------------------------------------
echo ""
echo " [5/5] Criando comando de execucao..."

LAUNCHER="$HOME/.local/bin/alaha-program"
mkdir -p "$HOME/.local/bin"

cat > "$LAUNCHER" << EOF
#!/usr/bin/env bash
cd "$INSTALL_DIR"
source venv/bin/activate
python main.py "\$@"
EOF

chmod +x "$LAUNCHER"

echo ""
echo " =========================================="
echo "  Instalacao concluida com sucesso!"
echo " =========================================="
echo ""
echo "  Para executar:"
echo "    alaha-program"
echo ""
echo "  Ou manualmente:"
echo "    cd $INSTALL_DIR"
echo "    source venv/bin/activate"
echo "    python main.py"
echo ""
echo "  Iniciando o programa..."
echo ""

python main.py
