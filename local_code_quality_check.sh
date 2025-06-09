#!/bin/bash

# Script pour exécuter localement les vérifications de qualité du code
# comme définies dans .github/workflows/code-quality.yml

# --- Prérequis ---
# 1. Assurez-vous d'avoir Python 3.12+ et pip installés.
# 2. Activez votre environnement virtuel si vous en utilisez un.
# 3. Installez les dépendances du projet :
#    pip install -r requirements.txt
# 4. Installez les outils de qualité spécifiques (s'ils ne sont pas dans requirements.txt) :
#    pip install mypy bandit safety vulture

# --- Configuration ---
SRC_DIRS="src/ tests/"
PYTHON_FILES_TO_CHECK="src/ tests/" # Pour Black et isort
MAX_LINE_LENGTH=88
FLAKE8_IGNORES="E203,W503,E501"
VULTURE_EXCLUDES="*/__pycache__"
VULTURE_MIN_CONFIDENCE=80

# Variables pour les couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # Pas de couleur

echo -e "${YELLOW}--- Démarrage des vérifications locales de qualité du code ---${NC}"
echo "Répertoires ciblés pour la plupart des vérifications: ${SRC_DIRS}"
echo ""

# Fonction pour exécuter une commande et afficher le résultat
run_check() {
    local tool_name="$1"
    local command_to_run="$2"
    
    echo -e "${YELLOW}Lancement de $tool_name...${NC}"
    if eval "$command_to_run"; then
        echo -e "${GREEN}$tool_name : Succès${NC}"
        return 0
    else
        echo -e "${RED}$tool_name : Échec${NC}"
        return 1
    fi
}

# --- Exécution des vérifications ---
declare -a FAILED_CHECKS

# 1. Black (Formatage du code)
if ! run_check "Black (formatage)" "black --check --diff ${PYTHON_FILES_TO_CHECK}"; then
    FAILED_CHECKS+=("Black")
fi
echo ""

# 2. isort (Tri des imports)
if ! run_check "isort (tri des imports)" "isort --check-only --diff src/ tests/"; then
    FAILED_CHECKS+=("isort")
fi
echo ""

# 3. flake8 (Linting)
if ! run_check "flake8 (linting)" "flake8 src --max-line-length=88 --extend-ignore=E203,W503,E501"; then
    FAILED_CHECKS+=("flake8")
fi
echo ""

# 4. mypy (Vérification des types)
# mypy peut être verbeux, donc on ne capture pas sa sortie de la même manière
echo -e "${YELLOW}Lancement de mypy (vérification des types)...${NC}"
# Note: `continue-on-error: true` est dans la CI, donc ici on ne fait pas échouer le script globalement
# mais on indique s'il y a des erreurs.
if mypy src/ --ignore-missing-imports --strict-optional; then
    echo -e "${GREEN}mypy : Succès (ou pas d'erreurs bloquantes)${NC}"
else
    echo -e "${RED}mypy : Des erreurs de typage ont été trouvées.${NC}"
    # Optionnel : décommentez pour faire échouer le script si mypy échoue
    # FAILED_CHECKS+=("mypy")
fi
echo ""

# 5. Bandit (Linting de sécurité)
# Bandit génère un rapport, donc on ne vérifie pas son code de sortie directement ici
# mais on informe l'utilisateur de vérifier le rapport.
echo -e "${YELLOW}Lancement de Bandit (linting de sécurité)...${NC}"
if bandit -r src/ -f json -o bandit-results.json; then
    echo -e "${GREEN}Bandit : Scan terminé. Vérifiez bandit-results.json pour les problèmes.${NC}"
else
    echo -e "${RED}Bandit : Erreur lors de l'exécution. Vérifiez bandit-results.json.${NC}"
    # FAILED_CHECKS+=("Bandit") # Vous pouvez choisir de le faire échouer ici
fi
echo "Rapport Bandit généré : bandit-results.json"
echo ""

# 6. Safety (Vérification des vulnérabilités des dépendances)
echo -e "${YELLOW}Lancement de Safety (vulnérabilités des dépendances)...${NC}"
if safety check --json > safety-results.json; then
    echo -e "${GREEN}Safety : Scan terminé. Vérifiez safety-results.json pour les problèmes.${NC}"
else
    echo -e "${RED}Safety : Erreur lors de l'exécution ou vulnérabilités trouvées. Vérifiez safety-results.json.${NC}"
    # FAILED_CHECKS+=("Safety") # Vous pouvez choisir de le faire échouer ici
fi
echo "Rapport Safety généré : safety-results.json"
echo ""

# 7. Vulture (Détection de code mort)
echo -e "${YELLOW}Lancement de Vulture (détection de code mort)...${NC}"
if vulture src/ --exclude=\"${VULTURE_EXCLUDES}\" --min-confidence ${VULTURE_MIN_CONFIDENCE}; then
    echo -e "${GREEN}Vulture : Scan terminé. Vérifiez la sortie pour le code mort potentiel.${NC}"
else
    echo -e "${RED}Vulture : Erreur lors de l'exécution ou code mort trouvé. Vérifiez la sortie.${NC}"
    # FAILED_CHECKS+=("Vulture") # Vous pouvez choisir de le faire échouer ici
fi
echo ""

# --- Résumé ---
echo -e "${YELLOW}--- Fin des vérifications de qualité du code ---${NC}"
if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 Toutes les vérifications principales (Black, isort, flake8) ont réussi ! 🎉${NC}"
    echo -e "Veuillez vérifier manuellement les rapports de mypy, Bandit, Safety et Vulture."
else
    echo -e "${RED}❌ Certaines vérifications ont échoué : ${FAILED_CHECKS[*]}${NC}"
    echo -e "Veuillez corriger les erreurs et vérifier les rapports générés."
    exit 1
fi

exit 0