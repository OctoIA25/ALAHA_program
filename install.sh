#!/usr/bin/env bash
# ALAHA Program - Instalação Rápida para Linux
# Uso: curl -fsSL https://raw.githubusercontent.com/OctoIA25/ALAHA_program/main/install.sh | bash
#   ou: wget -qO- https://raw.githubusercontent.com/OctoIA25/ALAHA_program/main/install.sh | bash

set -e

REPO_URL="https://github.com/OctoIA25/ALAHA_program.git"
INSTALL_DIR="${HOME}/.local/share/alaha-program"
BIN_DIR="${HOME}/.local/bin"

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${BLUE}  ___   _      ___  _   _   ___${NC}"
echo -e "${BLUE} / _ \ | |    / _ \| | | | / _ \${NC}"
echo -e "${BLUE}| (_) || |   | (_) || |_| || (_) |${NC}"
echo -e "${BLUE} \___/ ||___| \___/  \___/  \___/${NC}"
echo ""
echo " Instalador Rápido Linux"
echo " =========================================="
echo ""

# Verificar Python
if ! command -v python3 &>/dev/null; then
    echo " Erro: python3 não encontrado."
    echo " Instale com: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

echo -e " ${GREEN}✓${NC} Python encontrado: $(python3 --version)"

# Criar diretório
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Clonar ou atualizar
if [ -d ".git" ]; then
    echo -e " ${GREEN}✓${NC} Atualizando repositório..."
    git pull --quiet
else
    echo -e " ${GREEN}✓${NC} Clonando repositório..."
    git clone --depth 1 "$REPO_URL" . 2>/dev/null || {
        echo " Erro: Não foi possível clonar o repositório."
        echo " Verifique a URL ou sua conexão."
        exit 1
    }
fi

# Criar ambiente virtual
if [ ! -d "venv" ]; then
    echo -e " ${GREEN}✓${NC} Criando ambiente virtual..."
    python3 -m venv venv
fi

# Instalar dependências
echo -e " ${GREEN}✓${NC} Instalando dependências..."
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Criar comando global
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/alaha" << 'EOF'
#!/usr/bin/env bash
set -e

INSTALL_DIR="${HOME}/.local/share/alaha-program"
MARKER_FILE="${INSTALL_DIR}/.alaha_bootstrap_done"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "Erro: diretório do ALAHA não encontrado em $INSTALL_DIR"
    echo "Rode o instalador primeiro:"
    echo "curl -fsSL https://raw.githubusercontent.com/OctoIA25/ALAHA_program/main/install.sh | bash"
    exit 1
fi

cd "$INSTALL_DIR"

if ! command -v python3 &>/dev/null; then
    echo "Erro: python3 não encontrado."
    exit 1
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "Dependência de sistema ausente: tkinter"
    if command -v apt-get &>/dev/null; then
        if command -v sudo &>/dev/null; then
            echo "Instalando python3-tk/python3-dev via apt..."
            sudo apt-get update
            sudo apt-get install -y python3-tk python3-dev
        else
            echo "Rode como root para instalar: apt-get install -y python3-tk python3-dev"
            exit 1
        fi
    else
        echo "Instale manualmente o pacote tkinter para sua distro e tente novamente."
        exit 1
    fi
fi

if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
fi

source venv/bin/activate

if [ ! -f "$MARKER_FILE" ] || [ requirements.txt -nt "$MARKER_FILE" ]; then
    echo "Instalando/atualizando dependências Python..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    touch "$MARKER_FILE"
fi

exec python main.py "$@"
EOF
chmod +x "$BIN_DIR/alaha"

# Criar comando de atualização
cat > "$BIN_DIR/alaha-update" << 'EOF'
#!/usr/bin/env bash
set -e
echo "Atualizando ALAHA Program..."
cd "${HOME}/.local/share/alaha-program"
git pull
source venv/bin/activate
pip install -r requirements.txt
echo "Atualização concluída!"
EOF
chmod +x "$BIN_DIR/alaha-update"

# Adicionar ao PATH se necessário
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "${HOME}/.bashrc"
    echo -e " ${YELLOW}!${NC} PATH atualizado. Execute: source ~/.bashrc"
fi

echo ""
echo " =========================================="
echo -e " ${GREEN}✓ Instalação concluída!${NC}"
echo " =========================================="
echo ""
echo " Comandos disponíveis:"
echo "   alaha          - Inicia o programa"
echo "   alaha-update   - Atualiza para última versão"
echo ""
echo " Para atualizar no futuro:"
echo "   alaha-update"
echo ""
echo " Iniciando o programa..."
echo " Copie o SnowflakeID exibido para conectar na Dashboard."
echo ""

# Iniciar
exec python main.py
