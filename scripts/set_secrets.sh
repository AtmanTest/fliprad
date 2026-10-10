#!/bin/bash
# Enregistre les clés dans les secrets GitHub du dépôt (saisie masquée, rien n'est affiché ni écrit sur disque).
# Usage : bash scripts/set_secrets.sh ebay   |   bash scripts/set_secrets.sh bricklink
set -e
REPO="AtmanTest/fliprad"
case "$1" in
  ebay) names="EBAY_CLIENT_ID EBAY_CLIENT_SECRET"; wf=ebay.yml ;;
  bricklink) names="BRICKLINK_CONSUMER_KEY BRICKLINK_CONSUMER_SECRET BRICKLINK_TOKEN BRICKLINK_TOKEN_SECRET"; wf=bricklink.yml ;;
  *) echo "usage: $0 ebay|bricklink"; exit 1 ;;
esac
for n in $names; do
  read -r -s -p "$n : " v; echo
  printf '%s' "$v" | gh secret set "$n" -R "$REPO"
done
gh workflow run "$wf" -R "$REPO" && echo "Collecte lancée : résultats sous ~1 min dans l'onglet Actions."
