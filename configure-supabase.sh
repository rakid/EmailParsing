#!/bin/bash

# Configuration Supabase pour Vercel
# Ce script vous aide à configurer Supabase comme base de données principale

echo "🔧 Configuration Supabase pour Inbox Zen"
echo "========================================"

# Vérifier si Vercel CLI est installé
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI n'est pas installé. Installez-le avec:"
    echo "   npm install -g vercel"
    exit 1
fi

echo "📋 Vous devez obtenir ces informations depuis votre dashboard Supabase:"
echo "   1. Allez sur https://supabase.com/dashboard"
echo "   2. Sélectionnez votre projet"
echo "   3. Allez dans Settings > API"
echo ""

# Demander les informations Supabase
read -p "🔗 Entrez votre SUPABASE_URL (ex: https://xxx.supabase.co): " SUPABASE_URL
if [ -z "$SUPABASE_URL" ]; then
    echo "❌ URL Supabase requise"
    exit 1
fi

read -p "🔑 Entrez votre SUPABASE_ANON_KEY: " SUPABASE_ANON_KEY
if [ -z "$SUPABASE_ANON_KEY" ]; then
    echo "❌ Clé anonyme Supabase requise"
    exit 1
fi

read -p "🔐 Entrez votre SUPABASE_SERVICE_ROLE_KEY (optionnel): " SUPABASE_SERVICE_ROLE_KEY

echo ""
echo "🚀 Configuration des variables d'environnement Vercel..."

# Configurer les variables dans Vercel
vercel env add SUPABASE_URL "$SUPABASE_URL" production
if [ $? -eq 0 ]; then
    echo "✅ SUPABASE_URL configurée"
else
    echo "❌ Erreur lors de la configuration de SUPABASE_URL"
fi

vercel env add SUPABASE_ANON_KEY "$SUPABASE_ANON_KEY" production
if [ $? -eq 0 ]; then
    echo "✅ SUPABASE_ANON_KEY configurée"
else
    echo "❌ Erreur lors de la configuration de SUPABASE_ANON_KEY"
fi

if [ ! -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    vercel env add SUPABASE_SERVICE_ROLE_KEY "$SUPABASE_SERVICE_ROLE_KEY" production
    if [ $? -eq 0 ]; then
        echo "✅ SUPABASE_SERVICE_ROLE_KEY configurée"
    else
        echo "❌ Erreur lors de la configuration de SUPABASE_SERVICE_ROLE_KEY"
    fi
fi

echo ""
echo "📊 Vérification de la configuration..."
vercel env ls

echo ""
echo "🔄 Redéploiement nécessaire pour appliquer les changements..."
read -p "Voulez-vous redéployer maintenant? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Redéploiement en cours..."
    vercel --prod
    
    echo ""
    echo "✅ Configuration terminée!"
    echo ""
    echo "🧪 Testez votre configuration:"
    echo "   1. Allez sur https://inzen.email/debug/supabase-status"
    echo "   2. Vérifiez que Supabase est configuré et connecté"
    echo "   3. Envoyez un email de test"
    echo "   4. Vérifiez votre dashboard Supabase pour voir les données"
else
    echo ""
    echo "⚠️  N'oubliez pas de redéployer avec: vercel --prod"
fi

echo ""
echo "📚 Ressources utiles:"
echo "   - Dashboard Supabase: https://supabase.com/dashboard"
echo "   - Documentation: https://supabase.com/docs"
echo "   - Status de votre app: https://inzen.email/debug/supabase-status"
