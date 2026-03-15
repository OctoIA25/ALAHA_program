#!/usr/bin/env bash
set -e

# ==========================================
#  ALAHA Program - Setup Completo Linux
# ==========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

INSTALL_DIR="${HOME}/.local/share/alaha-program"
SERVICE_FILE="${HOME}/.config/systemd/user/alaha-program.service"

echo ""
echo -e "${BLUE}  ___   _      ___  _   _   ___${NC}"
echo -e "${BLUE} / _ \\ | |    / _ \\| | | | / _ \\${NC}"
echo -e "${BLUE}| (_) || |   | (_) || |_| || (_) |${NC}"
echo -e "${BLUE} \\___/ ||___| \\___/  \\___/  \\___/${NC}"
echo -e "${BLUE} ALAHA Program - Setup Completo Linux${NC}"
echo ""
echo " =========================================="
echo ""

# -----------------------------------------------
# 1. Verificar Python
# -----------------------------------------------
echo -e " [1/6] ${YELLOW}Verificando Python...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e " ${RED}ERRO: python3 nao encontrado.${NC}"
    echo " Instale com: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi
PYVER=$(python3 --version 2>&1)
echo -e " ${GREEN}$PYVER encontrado.${NC}"

# -----------------------------------------------
# 2. Preparar diretorio de instalacao
# -----------------------------------------------
echo ""
echo -e " [2/6] ${YELLOW}Preparando diretorio...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$SCRIPT_DIR/main.py" ]; then
    INSTALL_DIR="$SCRIPT_DIR"
    echo -e " ${GREEN}Usando diretorio local: $INSTALL_DIR${NC}"
else
    echo " Usando diretorio: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    
    # Copiar arquivos se executando de outro lugar
    if [ -f "$(dirname "${BASH_SOURCE[0]}")/../main.py" ]; then
        cp -r "$(dirname "${BASH_SOURCE[0]}")/.."/* "$INSTALL_DIR/"
    fi
fi

cd "$INSTALL_DIR"

# -----------------------------------------------
# 3. Criar ambiente virtual
# -----------------------------------------------
echo ""
echo -e " [3/6] ${YELLOW}Criando ambiente virtual...${NC}"
if [ -d "venv" ]; then
    echo -e " ${GREEN}Ambiente virtual ja existe, pulando...${NC}"
else
    python3 -m venv venv
fi

# -----------------------------------------------
# 4. Instalar dependencias
# -----------------------------------------------
echo ""
echo -e " [4/6] ${YELLOW}Instalando dependencias...${NC}"
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
echo -e " ${GREEN}Dependencias instaladas.${NC}"

# -----------------------------------------------
# 5. Instalar Playwright
# -----------------------------------------------
echo ""
echo -e " [5/6] ${YELLOW}Instalando Playwright (chromium)...${NC}"
python -m playwright install chromium 2>/dev/null || {
    echo -e " ${YELLOW}AVISO: Playwright nao instalado (opcional).${NC}"
}

# -----------------------------------------------
# 6. Criar comandos e servico systemd
# -----------------------------------------------
echo ""
echo -e " [6/6] ${YELLOW}Criando comandos e servico...${NC}"

# Criar diretorio de binarios do usuario
mkdir -p "$HOME/.local/bin"

# Criar comando de execucao normal
LAUNCHER="$HOME/.local/bin/alaha-program"
cat > "$LAUNCHER" << EOF
#!/usr/bin/env bash
cd "$INSTALL_DIR"
source venv/bin/activate
python main.py "\$@"
EOF
chmod +x "$LAUNCHER"

# Criar comando de execucao em background
LAUNCHER_BG="$HOME/.local/bin/alaha-program-start"
cat > "$LAUNCHER_BG" << EOF
#!/usr/bin/env bash
cd "$INSTALL_DIR"
source venv/bin/activate
nohup python main.py > /dev/null 2>&1 &
echo "ALAHA Program iniciado em background (PID: \$!)"
EOF
chmod +x "$LAUNCHER_BG"

# Criar comando de parar
LAUNCHER_STOP="$HOME/.local/bin/alaha-program-stop"
cat > "$LAUNCHER_STOP" << EOF
#!/usr/bin/env bash
pkill -f "python.*main.py" && echo "ALAHA Program parado." || echo "ALAHA Program nao estava rodando."
EOF
chmod +x "$LAUNCHER_STOP"

# Criar servico systemd (para iniciar com o sistema)
mkdir -p "$HOME/.config/systemd/user"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=ALAHA Program - AI Agent
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py --headless
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
EOF

# Recarregar systemd
systemctl --user daemon-reload 2>/dev/null || true

echo ""
echo -e " ${GREEN}=========================================="
echo -e "  Instalacao concluida com sucesso!"
echo -e " ==========================================${NC}"
echo ""
echo " Comandos disponiveis:"
echo ""
echo -e "   ${BLUE}alaha-program${NC}"
echo "     Executa normalmente (com interface)"
echo ""
echo -e "   ${BLUE}alaha-program-start${NC}"
echo "     Inicia em segundo plano"
echo ""
echo -e "   ${BLUE}alaha-program-stop${NC}"
echo "     Para o programa em background"
echo ""
echo " Para iniciar com o sistema (systemd):"
echo ""
echo -e "   ${YELLOW}systemctl --user enable alaha-program${NC}"
echo -e "   ${YELLOW}systemctl --user start alaha-program${NC}"
echo ""
echo " Para verificar status:"
echo ""
echo -e "   ${YELLOW}systemctl --user status alaha-program${NC}"
echo ""
echo " =========================================="
echo ""

# Perguntar se quer iniciar agora
read -p " Deseja iniciar o programa agora? (s/N): " START_NOW
if [[ "$START_NOW" =~ ^[Ss]$ ]]; then
    echo -e " ${GREEN}Iniciando ALAHA Program...${NC}"
    python main.py
fi
