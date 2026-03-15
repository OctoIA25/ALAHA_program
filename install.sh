#!/usr/bin/env bash
# ALAHA Program - Instalação Rápida para Linux
# Uso: curl -fsSL https://raw.githubusercontent.com/seu-usuario/alaha-program/main/install.sh | bash
#   ou: wget -qO- https://raw.githubusercontent.com/seu-usuario/alaha-program/main/install.sh | bash

set -e

REPO_URL="https://github.com/seu-usuario/alaha-program.git"
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

# Instalar Playwright
echo -e " ${GREEN}✓${NC} Instalando Playwright..."
python -m playwright install chromium 2>/dev/null || true

# Criar comando global
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/alaha" << 'EOF'
#!/usr/bin/env bash
cd "${HOME}/.local/share/alaha-program"
source venv/bin/activate
python main.py "$@"
EOF
chmod +x "$BIN_DIR/alaha"

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
echo " Comando disponível: alaha"
echo ""
echo " Iniciando o programa..."
echo " Copie o SnowflakeID exibido para conectar na Dashboard."
echo ""

# Iniciar
exec python main.py
