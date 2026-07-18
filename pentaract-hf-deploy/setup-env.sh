#!/bin/bash
# Run this after creating the HF Space to set environment variables
# You need: huggingface-cli login first

SPACE_NAME="YOUR_USERNAME/pentaract"

huggingface-cli repoVariables create $SPACE_NAME \
  -n SUPERUSER_EMAIL -v "admin@pentaract.app"

huggingface-cli repoVariables create $SPACE_NAME \
  -n SUPERUSER_PASS -v "pentaract2024"

huggingface-cli repoVariables create $SPACE_NAME \
  -n SECRET_KEY -v "7c5aa319018c0b718195595a494d00a8da4bcac344d335ee082c680a6773310d"

huggingface-cli repoVariables create $SPACE_NAME \
  -n DATABASE_USER -v "avnadmin"

huggingface-cli repoVariables create $SPACE_NAME \
  -n DATABASE_PASSWORD -v "YOUR_AIVEN_PASSWORD_HERE"

huggingface-cli repoVariables create $SPACE_NAME \
  -n DATABASE_NAME -v "pentaract"

huggingface-cli repoVariables create $SPACE_NAME \
  -n DATABASE_HOST -v "pg-752045-stanuserid-9476.a.aivencloud.com"

huggingface-cli repoVariables create $SPACE_NAME \
  -n DATABASE_PORT -v "26183"

echo "Done! Space will restart with new env vars."
